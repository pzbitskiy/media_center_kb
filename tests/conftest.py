"""pytest fixtures and stuff"""

from typing import Dict

import pytest

import media_center_kb.control
from media_center_kb.relays import RelayModule, GPioIf, RelayIf
from .mocks import GPMock, LoggerMock, ShellMock, YspMock


class WrapRelays(RelayModule):  # pylint: disable=too-few-public-methods
    """Relays class wrapper for tests"""

    def __init__(self, gpio: GPioIf):  # pylint: disable=redefined-outer-name
        self.cached: Dict[int, RelayIf] = {}
        self.max_relays = 4
        self.iter_idx = 1
        super().__init__(gpio, LoggerMock())

    def relay(self, relay: int):
        """Return a wrapped relay with extra methods for testing"""

        class Wrapped(RelayIf):
            """Wrap relay to track state changes"""

            def __init__(self, orig):
                self.is_on = None
                self.relay = orig

            def on(self):  # pylint: disable=invalid-name
                """enable and save state"""
                self.is_on = True
                self.relay.on()

            def off(self):
                """disable and save state"""
                self.is_on = False
                self.relay.off()

            def enabled(self) -> bool:
                return self.is_on

        result = self.cached.get(relay)
        if not result:
            result = Wrapped(super().relay(relay))
            self.cached[relay] = result
        return result

    def reset(self):
        """Wrapped Relays.reset"""
        super().reset()
        for relay in self.cached.values():
            relay.is_on = False

    def __iter__(self):
        self.iter_idx = 1
        return self

    def __next__(self):
        if self.iter_idx <= self.max_relays:
            res = self.relay(self.iter_idx)
            self.iter_idx += 1
            return res
        raise StopIteration


@pytest.fixture
def nosleep():
    """disable 1s sleep on graceful shutdown"""
    orig = media_center_kb.control.sleeper
    media_center_kb.control.sleeper = lambda x: None
    yield
    media_center_kb.control.sleeper = orig


@pytest.fixture
def gpio() -> GPioIf:
    """gpio for tests"""
    return GPMock()


@pytest.fixture
def rel_module(gpio: GPioIf) -> RelayModule:  # pylint: disable=redefined-outer-name
    """relay module for tests"""
    return RelayModule(gpio, LoggerMock())


@pytest.fixture
def relays(gpio: GPioIf) -> WrapRelays:  # pylint: disable=redefined-outer-name
    """wrapped relay module for tests"""
    return WrapRelays(gpio)


@pytest.fixture
def ysp():
    """ysp mock"""
    return YspMock()


@pytest.fixture
def shell():
    """shell mock"""
    return ShellMock()
