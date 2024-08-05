"""Relays tests"""

import unittest
from typing import Any, Iterable

from media_center_kb.relays import RelayModule, RelayIf
import media_center_kb.control

from .mocks import GPMock, LoggerMock, ShellMock, YspMock


class WrapRelays(RelayModule):  # pylint: disable=too-few-public-methods
    """Relays class wrapper for tests"""

    def __init__(self, gpio):
        self.cached = {}
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

    def test(self):  # pylint: disable=too-many-statements
        """test all control handlers"""
        gpio_mock = GPMock()
        relays = WrapRelays(gpio_mock)
        ysp = YspMock()

        media_center_kb.control.sleeper = lambda x: None

        controller = media_center_kb.control.Controller(relays, ysp)
        commands = controller.commands_map()
        handlers = controller.kb_handlers()
        handlers.get("UNK", lambda: None)()

        # tv
        for action in [handlers.get("KEY_KP7"), commands["tv_on"]]:
            action()
            self.assertOn(relays, [1])
            self.assertTrue(ysp.is_power_on)
            self.assertTrue(ysp.is_input_tv)
            self.assertTrue(ysp.is_5beam)
            ysp.reset()

        for action in [handlers.get("KEY_KP4"), commands["tv_off"]]:
            action()
            self.assertOff(relays)
            self.assertTrue(ysp.is_power_off)
            self.assertFalse(ysp.is_input_tv)
            self.assertFalse(ysp.is_input_aux1)
            ysp.reset()

        # music stream
        for action in [handlers.get("KEY_KP9"), commands["streaming_on"]]:
            action()
            self.assertOn(relays, [1])
            self.assertTrue(ysp.is_power_on)
            self.assertTrue(ysp.is_input_tv)
            self.assertTrue(ysp.is_stereo)
            ysp.reset()

        for action in [handlers.get("KEY_KP6"), commands["streaming_off"]]:
            action()
            self.assertOff(relays)
            self.assertTrue(ysp.is_power_off)
            self.assertFalse(ysp.is_input_tv)
            self.assertFalse(ysp.is_input_aux1)
            ysp.reset()

        # turntable
        for action in [handlers.get("KEY_KP8"), commands["turntable_on"]]:
            action()
            self.assertOn(relays, [1, 3])
            self.assertTrue(ysp.is_power_on)
            self.assertTrue(ysp.is_input_aux1)
            self.assertTrue(ysp.is_stereo)
            ysp.reset()

        for action in [handlers.get("KEY_KP5"), commands["turntable_off"]]:
            action()
            self.assertOff(relays)
            self.assertTrue(ysp.is_power_off)
            self.assertFalse(ysp.is_input_tv)
            self.assertFalse(ysp.is_input_aux1)
            ysp.reset()

        # printer
        for action in [handlers.get("KEY_KPMINUS"), commands["printer_on"]]:
            action()
            self.assertOn(relays, [4])
            self.assertFalse(ysp.is_power_on)
            self.assertIsNone(ysp.power_state)
            ysp.reset()

        for action in [handlers.get("KEY_KPPLUS"), commands["printer_off"]]:
            action()
            self.assertOff(relays)
            self.assertFalse(ysp.is_power_on)
            self.assertIsNone(ysp.power_state)
            ysp.reset()

        # switch on all, shutdown
        handlers.get("KEY_KP7")()
        handlers.get("KEY_KP8")()
        handlers.get("KEY_KPMINUS")()
        self.assertOn(relays, [1, 3, 4])
        self.assertTrue(ysp.is_power_on)

        handlers.get("KEY_KPENTER")()
        self.assertOff(relays)
        self.assertTrue(ysp.is_power_off)

        ysp.reset()
        relays.reset()

        commands.get("tv_on")()
        commands.get("turntable_on")()
        commands.get("printer_on")()
        self.assertOn(relays, [1, 3, 4])
        self.assertTrue(ysp.is_power_on)

        commands.get("off")()
        self.assertOff(relays)
        self.assertTrue(ysp.is_power_off)

        ysp.reset()
        relays.reset()

    def test_poweroff(self):
        """test poweroff"""

        gpio_mock = GPMock()
        relays = WrapRelays(gpio_mock)
        ysp = YspMock()
        shell = ShellMock()

        media_center_kb.control.sleeper = lambda x: None

        controller = media_center_kb.control.Controller(relays, ysp, shell)
        handlers = controller.kb_handlers()
        handlers.get("KEY_ESC")()
        self.assertOff(relays)
        self.assertTrue(ysp.is_power_off)
        self.assertEqual("sudo poweroff", shell.last_cmd)
