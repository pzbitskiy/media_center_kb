"""Controller tests"""

from typing import Iterable

import pytest

import media_center_kb.control

from .conftest import WrapRelays
from .mocks import ShellMock, YspMock


def all_off(relays: WrapRelays):
    """assert all relays off"""
    for rel in relays:
        assert not rel.is_on  # some are None as non-defined/not used
    return True


def some_on(relays: WrapRelays, on_relays: Iterable[int]):
    """assert some relays are on, others off"""
    for i in range(1, 5):
        rel = relays.relay(i)
        if i in on_relays:
            assert rel.is_on is True
        else:
            assert not rel.is_on
    return True


def test_handlers(
    relays: WrapRelays, ysp: YspMock, nosleep
):  # pylint: disable=too-many-statements
    """test all control handlers"""
    _ = nosleep

    controller = media_center_kb.control.Controller(relays, ysp)
    commands = controller.commands_map()
    handlers = controller.kb_handlers()
    handlers.get("UNK", lambda: None)()

    # tv
    for action in [handlers.get("KEY_KP7"), commands["tv_on"]]:
        action()
        assert some_on(relays, [1])
        assert ysp.is_power_on
        assert ysp.is_input_tv
        assert ysp.is_5beam
        ysp.reset()

    for action in [handlers.get("KEY_KP4"), commands["tv_off"]]:
        action()
        assert all_off(relays)
        assert ysp.is_power_off
        assert not ysp.is_input_tv
        assert not ysp.is_input_aux1
        ysp.reset()

    # music stream
    for action in [handlers.get("KEY_KP9"), commands["streaming_on"]]:
        action()
        assert some_on(relays, [1])
        assert ysp.is_power_on
        assert ysp.is_input_tv
        assert ysp.is_stereo
        ysp.reset()

    for action in [handlers.get("KEY_KP6"), commands["streaming_off"]]:
        action()
        assert all_off(relays)
        assert ysp.is_power_off
        assert not ysp.is_input_tv
        assert not ysp.is_input_aux1
        ysp.reset()

    # turntable
    for action in [handlers.get("KEY_KP8"), commands["turntable_on"]]:
        action()
        assert some_on(relays, [1, 3])
        assert ysp.is_power_on
        assert ysp.is_input_aux1
        assert ysp.is_stereo
        ysp.reset()

    for action in [handlers.get("KEY_KP5"), commands["turntable_off"]]:
        action()
        assert all_off(relays)
        assert ysp.is_power_off
        assert not ysp.is_input_tv
        assert not ysp.is_input_aux1
        ysp.reset()

    # printer
    for action in [handlers.get("KEY_KPMINUS"), commands["printer_on"]]:
        action()
        assert some_on(relays, [4])
        assert not ysp.is_power_on
        assert ysp.power_state is None
        ysp.reset()

    for action in [handlers.get("KEY_KPPLUS"), commands["printer_off"]]:
        action()
        assert all_off(relays)
        assert not ysp.is_power_on
        assert ysp.power_state is None
        ysp.reset()

    # switch on all, shutdown
    handlers["KEY_KP7"]()
    handlers["KEY_KP8"]()
    handlers["KEY_KPMINUS"]()
    assert some_on(relays, [1, 3, 4])
    assert ysp.is_power_on

    handlers["KEY_KPENTER"]()
    assert all_off(relays)
    assert ysp.is_power_off

    ysp.reset()
    relays.reset()

    commands["tv_on"]()
    commands["turntable_on"]()
    commands["printer_on"]()
    assert some_on(relays, [1, 3, 4])
    assert ysp.is_power_on

    commands["off"]()
    assert all_off(relays)
    assert ysp.is_power_off

    ysp.reset()
    relays.reset()


def test_poweroff(relays: WrapRelays, ysp: YspMock, shell: ShellMock, nosleep):
    """test poweroff"""
    _ = nosleep

    controller = media_center_kb.control.Controller(relays, ysp, shell)
    handlers = controller.kb_handlers()
    handlers["KEY_ESC"]()
    assert all_off(relays)
    assert ysp.is_power_off
    assert "sudo poweroff" == shell.last_cmd


def test_controller_devices(relays: WrapRelays, ysp: YspMock, nosleep):
    """test controller named devices"""
    _ = nosleep

    controller = media_center_kb.control.Controller(relays, ysp)
    result = controller.devices(("tv",))
    assert len(result) == 1
    assert "tv" in result

    result = controller.devices(("tv", "turntable"))
    assert len(result) == 2
    assert "tv" in result
    assert "turntable" in result

    with pytest.raises(ValueError):
        controller.devices(("tv", "test"))
