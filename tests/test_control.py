"""Relays tests"""

import unittest
from typing import Any, Iterable

from media_center_kb.relays import Relays, RelayIf
from media_center_kb.control import kb_handlers

from .mocks import GPMock, YspMock, ShellMock


class WrapRelays(Relays):  # pylint: disable=too-few-public-methods
    """Relays class wrapper for tests"""

    def __init__(self, gpio):
        self.cached = {}
        super().__init__(gpio)

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


class TestControl(unittest.TestCase):
    """Control class tests"""

    def assertOff(self, relays: Any):  # pylint: disable=invalid-name
        """assert all relays off"""
        for i in range(1, 5):
            rel = relays.relay(i)
            self.assertFalse(rel.is_on)

    def assertOn(
        self, relays: Any, on_relays: Iterable
    ):  # pylint: disable=invalid-name
        """assert some relays are on, others off"""
        for i in range(1, 5):
            rel = relays.relay(i)
            if i in on_relays:
                self.assertTrue(rel.is_on)
            else:
                self.assertFalse(rel.is_on)

    def test(self):
        """test all control handlers"""
        gpio_mock = GPMock()
        relays = WrapRelays(gpio_mock)
        ysp = YspMock()

        handlers = kb_handlers(relays, ysp)
        handlers.get("UNK", lambda: None)()

        # tv
        handlers.get("KEY_KP7")()
        self.assertOn(relays, [1])
        self.assertTrue(ysp.is_power_on)
        self.assertTrue(ysp.is_input_tv)
        self.assertTrue(ysp.is_5beam)

        handlers.get("KEY_KP4")()
        self.assertOff(relays)
        self.assertTrue(ysp.is_power_off)
        self.assertFalse(ysp.is_input_tv)
        self.assertFalse(ysp.is_input_aux1)

        # music stream
        handlers.get("KEY_KP9")()
        self.assertOn(relays, [1])
        self.assertTrue(ysp.is_power_on)
        self.assertTrue(ysp.is_input_tv)
        self.assertTrue(ysp.is_stereo)

        handlers.get("KEY_KP6")()
        self.assertOff(relays)
        self.assertTrue(ysp.is_power_off)
        self.assertFalse(ysp.is_input_tv)
        self.assertFalse(ysp.is_input_aux1)

        # turntable
        handlers.get("KEY_KP8")()
        self.assertOn(relays, [1, 3])
        self.assertTrue(ysp.is_power_on)
        self.assertTrue(ysp.is_input_aux1)
        self.assertTrue(ysp.is_stereo)

        handlers.get("KEY_KP5")()
        self.assertOff(relays)
        self.assertTrue(ysp.is_power_off)
        self.assertFalse(ysp.is_input_tv)
        self.assertFalse(ysp.is_input_aux1)

        # printer
        handlers.get("KEY_KPMINUS")()
        self.assertOn(relays, [4])
        self.assertTrue(ysp.is_power_off)

        handlers.get("KEY_KPPLUS")()
        self.assertOff(relays)
        self.assertTrue(ysp.is_power_off)

        # switch on all, shutdown
        handlers.get("KEY_KP7")()
        handlers.get("KEY_KP8")()
        handlers.get("KEY_KPMINUS")()
        self.assertOn(relays, [1, 3, 4])
        self.assertTrue(ysp.is_power_on)

        handlers.get("KEY_KPENTER")()
        self.assertOff(relays)
        self.assertTrue(ysp.is_power_off)

    def test_poweroff(self):
        """test poweroff"""

        gpio_mock = GPMock()
        relays = WrapRelays(gpio_mock)
        ysp = YspMock()
        shell = ShellMock()

        handlers = kb_handlers(relays, ysp, shell)
        handlers.get("KEY_ESC")()
        self.assertOff(relays)
        self.assertTrue(ysp.is_power_off)
        self.assertEqual("sudo poweroff", shell.last_cmd)
