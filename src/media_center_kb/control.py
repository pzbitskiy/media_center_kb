"""
Control action for each key
"""
import time
from typing import Callable, Dict

from ysp4000 import YSP4000
from .relays import Relays, RelayIf


class RelayMap:
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


def power_off(relays: Relays, ysp: YSP4000, shell: Callable) -> Callable:
    """power off the entire thing"""
    def inner():
        ysp_graceful_power_off(ysp)
        relays.reset()
        shell('sudo poweroff')
    return inner


def control_handlers(relays: Relays, ysp: YSP4000, shell: Callable=None) -> Dict[str, Callable]:
    """Returns dict of handlers by keycode"""
    if not shell:
        def noop(_):
            pass
        shell = noop

    return {
        'KEY_KP7': enable_tv(relays.relay(RelayMap.ysp), ysp),
        'KEY_KP4': disable_tv(relays.relay(RelayMap.ysp), ysp),

        'KEY_KP8': enable_turntable(
            relays.relay(RelayMap.ysp), relays.relay(RelayMap.turntable), ysp),
        'KEY_KP5': disable_turntable(
            relays.relay(RelayMap.ysp), relays.relay(RelayMap.turntable), ysp),

        'KEY_KP9': enable_music_stream(relays.relay(RelayMap.ysp), ysp),
        'KEY_KP6': disable_music_stream(relays.relay(RelayMap.ysp), ysp),

        # printer
        'KEY_KPMINUS': relays.relay(RelayMap.printer).on,
        'KEY_KPPLUS': relays.relay(RelayMap.printer).off,

        'KEY_KPENTER': switch_off(relays, ysp),

        # YSP volume
        'KEY_KP0': volume_down(ysp),
        'KEY_KP1': volume_up(ysp),

        'KEY_ESC': power_off(relays, ysp, shell),
    }
