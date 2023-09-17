"""
Relays related functionality:
 - GPIO abstraction
 - Relays abstraction
"""
from abc import ABC, abstractmethod
import logging
from types import SimpleNamespace
from typing import Any


RELAY1_PIN = 6
RELAY2_PIN = 13
RELAY3_PIN = 19
RELAY4_PIN = 26


PIN_TO_RELAY = {
    RELAY1_PIN: 1,
    RELAY2_PIN: 2,
    RELAY3_PIN: 3,
    RELAY4_PIN: 4,
}

RELAYS_TO_PIN = {v: k for k, v in PIN_TO_RELAY.items()}

Pins = PIN_TO_RELAY.keys()

class GPioIf(ABC):
    """Base abstract class for GPIO operations"""
    @property
    @abstractmethod
    def HIGH(self) -> int:  # pylint: disable=invalid-name
        """HIGH level"""

    @property
    @abstractmethod
    def LOW(self) -> int:   # pylint: disable=invalid-name
        """LOW level"""

    @abstractmethod
    def input(self, pin: int) -> bool:
        """Read pin and return logical HIGH/LOW level"""

    @abstractmethod
    def output(self, pin: int, signal: int):
        """Set pin to HIGH/LOW logical level"""


class RelayIf(ABC):
    """Single relay interface"""
    @abstractmethod
    def on(self):  # pylint: disable=invalid-name
        """enable relay"""

    @abstractmethod
    def off(self):
        """disable relay"""

def wrap(method, *args):
    """helper that wraps method"""
    def inner():
        return method(*args)
    return inner


class Relays:
    """Relays class"""
    def __init__(self, gpio: Any):
        self.gpio = gpio
        self.reset()

    def reset(self):
        """Switch off all relays"""
        for pin in PIN_TO_RELAY:
            self._relay_off(pin)

    def _relay_on(self, pin: int):
        state = self.gpio.input(pin)
        if not state:
            self.gpio.output(pin, self.gpio.HIGH)
            logging.debug('relay %d (%d) on', PIN_TO_RELAY[pin], pin)

    def _relay_off(self, pin: int):
        state = self.gpio.input(pin)
        if state:
            self.gpio.output(pin, self.gpio.LOW)
            logging.debug('relay %d (%d) off', PIN_TO_RELAY[pin], pin)

    def relay(self, relay: int) -> RelayIf:
        """Return a simplenamespace object with on/off methods for specific relay"""
        return SimpleNamespace(**{
            'on': wrap(self._relay_on, RELAYS_TO_PIN[relay]),
            'off': wrap(self._relay_off, RELAYS_TO_PIN[relay]),
        })
