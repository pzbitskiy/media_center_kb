"""
Control action for each key
"""

import time
from typing import Callable, Dict, Optional

from ysp4000 import YSP4000
from .relays import Relays, RelayIf


class RelayMap:  # pylint: disable=too-few-public-methods
    """Maps symbol names to relay numbers"""

    ysp = 1
    tbd = 2
    turntable = 3
    printer = 4


def ysp_graceful_power_off(ysp: YSP4000):
    """Power offs YSP with 1s delay"""
    ysp.power_off()
    # give YSP change to power off. 1s looks a lot who cares, it is switching off
    time.sleep(1)


def enable_tv(relay: RelayIf, ysp: YSP4000) -> Callable:
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


def disable_tv(relay: RelayIf, ysp: YSP4000) -> Callable:
    """
    turn off soundbar
    power off soundbar

    """

    def inner():
        ysp_graceful_power_off(ysp)
        relay.off()

    return inner


def enable_music_stream(relay: RelayIf, ysp: YSP4000) -> Callable:
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


def disable_music_stream(relay: RelayIf, ysp: YSP4000) -> Callable:
    """
    turn off soundbar
    power off soundbar
    """

    def inner():
        ysp_graceful_power_off(ysp)
        relay.off()

    return inner


def enable_turntable(relay1: RelayIf, relay2: RelayIf, ysp: YSP4000) -> Callable:
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


def disable_turntable(relay1: RelayIf, relay2: RelayIf, ysp: YSP4000) -> Callable:
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


def switch_off(relays: Relays, ysp: YSP4000) -> Callable:
    """switch off everything except the controller"""

    def inner():
        ysp_graceful_power_off(ysp)
        relays.reset()

    return inner


def volume_down(ysp: YSP4000) -> Callable:
    """YSP volume control"""

    def inner():
        ysp.volume_down()

    return inner


def volume_up(ysp: YSP4000) -> Callable:
    """YSP volume control"""

    def inner():
        ysp.volume_up()

    return inner


POWEROFF_CMD = "sudo poweroff"


def power_off(relays: Relays, ysp: YSP4000, shell: Callable) -> Callable:
    """power off the entire thing"""

    def inner():
        ysp_graceful_power_off(ysp)
        relays.reset()
        shell(POWEROFF_CMD)

    return inner


def commands_map(
    relays: Relays, ysp: YSP4000, shell: Optional[Callable] = None
) -> Dict[str, Callable]:
    """Returns dict of handlers by keycode"""
    if not shell:

        def noop(_):
            pass

        shell = noop

    return {
        "tv_on": enable_tv(relays.relay(RelayMap.ysp), ysp),
        "tv_off": disable_tv(relays.relay(RelayMap.ysp), ysp),
        "turntable_on": enable_turntable(
            relays.relay(RelayMap.ysp), relays.relay(RelayMap.turntable), ysp
        ),
        "turntable_off": disable_turntable(
            relays.relay(RelayMap.ysp), relays.relay(RelayMap.turntable), ysp
        ),
        "streaming_on": enable_music_stream(relays.relay(RelayMap.ysp), ysp),
        "streaming_off": disable_music_stream(relays.relay(RelayMap.ysp), ysp),
        "printer_on": relays.relay(RelayMap.printer).on,
        "printer_off": relays.relay(RelayMap.printer).off,
        "off": switch_off(relays, ysp),
        # YSP volume
        "volume_down": volume_down(ysp),
        "volume_up": volume_up(ysp),
        "shutdown": power_off(relays, ysp, shell),
    }


def kb_handlers(
    relays: Relays, ysp: YSP4000, shell: Optional[Callable] = None
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
        "KEY_KP0": cmds["volume_up"],
        "KEY_KP1": cmds["volume_down"],
        "KEY_ESC": cmds["shutdown"],
    }
