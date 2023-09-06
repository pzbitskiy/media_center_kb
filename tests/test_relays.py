"""Relays tests"""

import unittest

from media_center_kb.relays import Relays, Pins

from .mocks import GPMock

class TestRelays(unittest.TestCase):
    """Relays class tests"""

    def test_on_off(self):
        """Test relays switch on/off"""
        gpio_mock = GPMock()
        relays = Relays(gpio_mock)

        for pin in Pins:
            # pylint: disable=protected-access
            relays._relay_on(pin)
            self.assertEqual(1, gpio_mock.high_count[pin])

            # not changed second time
            relays._relay_on(pin)
            self.assertEqual(1, gpio_mock.high_count[pin])

            relays._relay_off(pin)
            self.assertEqual(1, gpio_mock.high_count[pin])
            self.assertEqual(1, gpio_mock.low_count[pin])

            # not changed second time
            relays._relay_off(pin)
            self.assertEqual(1, gpio_mock.high_count[pin])
            self.assertEqual(1, gpio_mock.low_count[pin])

    def test_get_relay(self):
        """Test individual relays switch"""
        gpio_mock = GPMock()
        relays = Relays(gpio_mock)

        pins = iter(Pins)
        for i in range(1, 5):
            pin = next(pins)
            relay = relays.relay(i)
            relay.on()
            relay.on()

            relay.off()
            relay.off()
            self.assertEqual(1, gpio_mock.high_count[pin])
            self.assertEqual(1, gpio_mock.low_count[pin])

    def test_reset(self):
        """Test all relays reset"""
        gpio_mock = GPMock()
        relays = Relays(gpio_mock)

        for pin in Pins:
            # pylint: disable=protected-access
            relays._relay_on(pin)

        for _ in range(2):
            relays.reset()
            for pin in Pins:
                self.assertEqual(1, gpio_mock.low_count[pin])
