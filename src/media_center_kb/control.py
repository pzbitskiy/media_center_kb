"""
Control action for each key
"""

from enum import Enum
import time
from typing import Callable, Dict, Optional

from ysp4000.ysp import Ysp4000
from media_center_kb.relays import RelayModuleIf, RelayIf


class RelayMap(Enum):
    """Maps symbol names to relay numbers"""

    YSP = 1
    _TDB = 2
    TURNTABLE = 3
    PRINTER = 4


def ysp_graceful_power_off(ysp: Ysp4000):
    """Power offs YSP with 1s delay"""
    ysp.power_off()
    # give YSP change to power off. 1s looks a lot who cares, it is switching off
    time.sleep(1)


def enable_tv(relay: RelayIf, ysp: Ysp4000) -> Callable:
    """
    power on soundbar
    turn on soundbar
    select TV/STB channel
    select 5 beam
    select cinema mode
    IR/radio to switch on projector?
    """

    def inner():
        relay.on()
        ysp.power_on()
        ysp.set_input_tv()
        ysp.set_5beam()
        ysp.set_dsp_cinema()

    return inner


def disable_tv(relay: RelayIf, ysp: Ysp4000) -> Callable:
    """
    turn off soundbar
    power off soundbar

    """

    def inner():
        ysp_graceful_power_off(ysp)
        relay.off()

    return inner


def enable_music_stream(relay: RelayIf, ysp: Ysp4000) -> Callable:
    """
    power on soundbar
    turn on soundbar
    select TV/STB channel
    select stereo mode
    """

    def inner():
        relay.on()
        ysp.power_on()
        ysp.set_input_tv()
        ysp.set_dsp_off()
        ysp.set_stereo()

    return inner


def disable_music_stream(relay: RelayIf, ysp: Ysp4000) -> Callable:
    """
    turn off soundbar
    power off soundbar
    """

    def inner():
        ysp_graceful_power_off(ysp)
        relay.off()

    return inner


def enable_turntable(relay1: RelayIf, relay2: RelayIf, ysp: Ysp4000) -> Callable:
    """
    power on soundbar (relay 1)
    turn on soundbar
    select AUX1 channel
    select stereo mode
    power on turntable (relay 2)
    """

    def inner():
        relay1.on()
        relay2.on()
        ysp.power_on()
        ysp.set_input_aux1()
        ysp.set_dsp_off()
        ysp.set_stereo()

    return inner


def disable_turntable(relay1: RelayIf, relay2: RelayIf, ysp: Ysp4000) -> Callable:
    """
    turn off soundbar
    power off soundbar
    power off turntable
    """

    def inner():
        ysp_graceful_power_off(ysp)
        relay2.off()
        relay1.off()

    return inner


def switch_off(relays: RelayModuleIf, ysp: Ysp4000) -> Callable:
    """switch off everything except the controller"""

    def inner():
        ysp_graceful_power_off(ysp)
        relays.reset()

    return inner


def volume_down(ysp: Ysp4000) -> Callable:
    """YSP volume control"""

    def inner():
        ysp.volume_down()

    return inner


def volume_up(ysp: Ysp4000) -> Callable:
    """YSP volume control"""

    def inner():
        ysp.volume_up()

    return inner


def volume_set(ysp: Ysp4000) -> Callable:
    """YSP volume control"""

    def inner(val: int):
        ysp.set_volume(val)

    return inner


POWEROFF_CMD = "sudo poweroff"


def power_off(relays: RelayModuleIf, ysp: Ysp4000, shell: Callable) -> Callable:
    """power off the entire thing"""

    def inner():
        ysp_graceful_power_off(ysp)
        relays.reset()
        shell(POWEROFF_CMD)

    return inner


class Controller:
    """Controller class"""

    def __init__(
        self,
        relays: RelayModuleIf,
        ysp: Ysp4000,
        shell: Optional[Callable[[str], None]] = None,
    ):
        def noop(_):
            pass

        self._relays = relays
        self._ysp = ysp
        self._shell: Callable = noop if not shell else shell

        self._ysp.set_state_update_cb(self._ysp_state_update_cb)
        self._ysp_volume = 0

    def _ysp_state_update_cb(self, **kwargs):
        """Tracks state changes from YSP"""
        if (vol := kwargs.get("volume_pct")) is not None:
            self._ysp_volume = vol

    def switch(self, name: str) -> bool:
        """Returns switch state by name"""
        try:
            relay_num = RelayMap[name.upper()].value
        except KeyError:
            return False
        relay = self._relays.relay(relay_num)
        return relay.enabled()

    def volume(self) -> float:
        """Returns volume level"""
        return self._ysp_volume

    def commands_map(self) -> Dict[str, Callable]:
        """Returns dict of handlers by keycode"""
        return {
            "tv_on": enable_tv(self._relays.relay(RelayMap.YSP.value), self._ysp),
            "tv_off": disable_tv(self._relays.relay(RelayMap.YSP.value), self._ysp),
            "turntable_on": enable_turntable(
                self._relays.relay(RelayMap.YSP.value),
                self._relays.relay(RelayMap.TURNTABLE.value),
                self._ysp,
            ),
            "turntable_off": disable_turntable(
                self._relays.relay(RelayMap.YSP.value),
                self._relays.relay(RelayMap.TURNTABLE.value),
                self._ysp,
            ),
            "streaming_on": enable_music_stream(
                self._relays.relay(RelayMap.YSP.value), self._ysp
            ),
            "streaming_off": disable_music_stream(
                self._relays.relay(RelayMap.YSP.value), self._ysp
            ),
            "printer_on": self._relays.relay(RelayMap.PRINTER.value).on,
            "printer_off": self._relays.relay(RelayMap.PRINTER.value).off,
            "off": switch_off(self._relays, self._ysp),
            # YSP volume
            "volume_down": volume_down(self._ysp),
            "volume_up": volume_up(self._ysp),
            "volume_set": volume_set(self._ysp),
            "shutdown": power_off(self._relays, self._ysp, self._shell),
        }

    def kb_handlers(self) -> Dict[str, Callable]:
        """Return keys to commands mapping"""
        cmds = self.commands_map()

        return {
            "KEY_KP7": cmds["tv_on"],
            "KEY_KP4": cmds["tv_off"],
            "KEY_KP8": cmds["turntable_on"],
            "KEY_KP5": cmds["turntable_off"],
            "KEY_KP9": cmds["streaming_on"],
            "KEY_KP6": cmds["streaming_off"],
            "KEY_KPMINUS": cmds["printer_on"],
            "KEY_KPPLUS": cmds["printer_off"],
            "KEY_KPENTER": cmds["off"],
            "KEY_KP1": cmds["volume_up"],
            "KEY_KP0": cmds["volume_down"],
            "KEY_ESC": cmds["shutdown"],
        }
