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


def commands_map(
    relays: RelayModuleIf, ysp: Ysp4000, shell: Optional[Callable] = None
) -> Dict[str, Callable]:
    """Returns dict of handlers by keycode"""
    if not shell:

        def noop(_):
            pass

        shell = noop

    return {
        "tv_on": enable_tv(relays.relay(RelayMap.YSP.value), ysp),
        "tv_off": disable_tv(relays.relay(RelayMap.YSP.value), ysp),
        "turntable_on": enable_turntable(
            relays.relay(RelayMap.YSP.value),
            relays.relay(RelayMap.TURNTABLE.value),
            ysp,
        ),
        "turntable_off": disable_turntable(
            relays.relay(RelayMap.YSP.value),
            relays.relay(RelayMap.TURNTABLE.value),
            ysp,
        ),
        "streaming_on": enable_music_stream(relays.relay(RelayMap.YSP.value), ysp),
        "streaming_off": disable_music_stream(relays.relay(RelayMap.YSP.value), ysp),
        "printer_on": relays.relay(RelayMap.PRINTER.value).on,
        "printer_off": relays.relay(RelayMap.PRINTER.value).off,
        "off": switch_off(relays, ysp),
        # YSP volume
        "volume_down": volume_down(ysp),
        "volume_up": volume_up(ysp),
        "volume_set": volume_set(ysp),
        "shutdown": power_off(relays, ysp, shell),
    }


def kb_handlers(
    relays: RelayModuleIf, ysp: Ysp4000, shell: Optional[Callable] = None
) -> Dict[str, Callable]:
    """Return keys to commands mapping"""
    cmds = commands_map(relays, ysp, shell)

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
