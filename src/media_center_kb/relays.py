"""
Relays related functionality:
 - GPIO abstraction
 - Relays abstraction
"""

from abc import ABC, abstractmethod
from enum import Enum
import logging
from types import SimpleNamespace


class _RelayPins(Enum):
    RELAY1_PIN = 6
    RELAY2_PIN = 13
    RELAY3_PIN = 19
    RELAY4_PIN = 26


_PIN_TO_RELAY = {
    _RelayPins.RELAY1_PIN.value: 1,
    _RelayPins.RELAY2_PIN.value: 2,
    _RelayPins.RELAY3_PIN.value: 3,
    _RelayPins.RELAY4_PIN.value: 4,
}

_RELAYS_TO_PIN = {v: k for k, v in _PIN_TO_RELAY.items()}

Pins = _PIN_TO_RELAY.keys()


class GPioIf(ABC):
    """Base abstract class for GPIO operations"""

    @property
    @abstractmethod
    def HIGH(self) -> int:  # pylint: disable=invalid-name
        """HIGH level"""

    @property
    @abstractmethod
    def LOW(self) -> int:  # pylint: disable=invalid-name
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

    @abstractmethod
    def enabled(self) -> bool:
        """relays state: disabled (false), enabled (true)"""


class RelayModuleIf(ABC):
    """Relay module board interface"""

    @abstractmethod
    def reset(self):
        """Switch off all relays"""

    @abstractmethod
    def relay(self, relay: int) -> RelayIf:
        """Return a specific relay"""


def _wrap(method, *args):
    """helper that wraps method"""

    def inner():
        return method(*args)

    return inner


class RelayModule(RelayModuleIf):
    """Relay module class"""

    def __init__(self, gpio: GPioIf, logger: logging.Logger):
        self._gpio: GPioIf = gpio
        self._logger = logger
        self.reset()

    def reset(self):
        """Switch off all relays"""
        for pin in _PIN_TO_RELAY:
            self._relay_off(pin)

    def _relay_on(self, pin: int):
        state = self._gpio.input(pin)
        if not state:
            self._gpio.output(pin, self._gpio.HIGH)
            self._logger.debug("relay %d (%d) on", _PIN_TO_RELAY[pin], pin)

    def _relay_off(self, pin: int):
        state = self._gpio.input(pin)
        if state:
            self._gpio.output(pin, self._gpio.LOW)
            self._logger.debug("relay %d (%d) off", _PIN_TO_RELAY[pin], pin)

    def _get_state(self, pin: int) -> bool:
        state = self._gpio.input(pin)
        return state

    def relay(self, relay: int) -> RelayIf:
        """Return a simplenamespace object with on/off methods for specific relay"""
        return SimpleNamespace(  # type: ignore[return-value]
            **{
                "on": _wrap(self._relay_on, _RELAYS_TO_PIN[relay]),
                "off": _wrap(self._relay_off, _RELAYS_TO_PIN[relay]),
                "enabled": _wrap(self._get_state, _RELAYS_TO_PIN[relay]),
            }
        )
