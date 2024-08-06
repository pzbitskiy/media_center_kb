"""Relays tests"""

from media_center_kb.relays import RelayModule, Pins

from .mocks import GPMock


def test_on_off(gpio: GPMock, rel_module: RelayModule):
    """Test relays switch on/off"""
    for pin in Pins:
        # pylint: disable=protected-access
        rel_module._relay_on(pin)
        assert gpio.high_count[pin] == 1

        # not changed second time
        rel_module._relay_on(pin)
        assert gpio.high_count[pin] == 1

        rel_module._relay_off(pin)
        assert gpio.high_count[pin] == 1
        assert gpio.low_count[pin] == 1

        # not changed second time
        rel_module._relay_off(pin)
        assert gpio.high_count[pin] == 1
        assert gpio.low_count[pin] == 1


def test_get_relay(gpio: GPMock, rel_module: RelayModule):
    """Test individual relays switch"""
    pins = iter(Pins)
    for i in range(1, 5):
        pin = next(pins)
        relay = rel_module.relay(i)
        relay.on()
        relay.on()

        relay.off()
        relay.off()
        assert gpio.high_count[pin] == 1
        assert gpio.low_count[pin] == 1


def test_reset(gpio: GPMock, rel_module: RelayModule):
    """Test all relays reset"""
    for pin in Pins:
        # pylint: disable=protected-access
        rel_module._relay_on(pin)

    for _ in range(2):
        rel_module.reset()
        for pin in Pins:
            assert gpio.low_count[pin] == 1
