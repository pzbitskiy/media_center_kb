"""
Control action for each key
"""

from typing import Callable, Dict, Any


def enable_tv(relay, ysp):
    """
    power on soundbar
    turn on soundbar
    select TV/STB channel
    IR/radio to switch on projector?
    """
    def inner():
        relay.on()
        ysp.power_on()
        ysp.set_input_tv()
    return inner


def disable_tv(relay, ysp):
    """
    turn off soundbar
    power off soundbar

    """
    def inner():
        ysp.power_off()
        relay.off()
    return inner


def enable_turntable(relay1, relay2, ysp):
    """
    power on soundbar (relay 1)
    turn on soundbar
    select AUX channel
    power on turntable (relay 2)
    """
    def inner():
        relay1.on()
        relay2.on()
        ysp.power_on()
        ysp.set_input_aux1()
    return inner


def disable_turntable(relay1, relay2, ysp):
    """
    turn off soundbar
    power off soundbar
    power off turntable
    """
    def inner():
        ysp.power_off()
        relay2.off()
        relay1.off()
    return inner


def switch_off(relay1, relay2, relay4, ysp):
    """switch off everything except the controller"""
    def inner():
        ysp.power_off()
        relay4.off()
        relay2.off()
        relay1.off()
    return inner


def control_handlers(relays: Any, ysp: Any) -> Dict[str, Callable]:
    """Returns dict of handlers by keycode"""
    return {
        'KEY_KP7': enable_tv(relays.relay(1), ysp),
        'KEY_KP4': disable_tv(relays.relay(1), ysp),

        'KEY_KP8': enable_turntable(relays.relay(1), relays.relay(2), ysp),
        'KEY_KP5': disable_turntable(relays.relay(1), relays.relay(2), ysp),

        # printer
        'KEY_KPMINUS': relays.relay(4).on,
        'KEY_KPPLUS': relays.relay(4).off,

        'KEY_KPENTER': switch_off(relays.relay(1), relays.relay(2), relays.relay(4), ysp)
    }
