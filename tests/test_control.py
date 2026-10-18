"""Controller tests"""

from typing import Iterable

import pytest

import media_center_kb.control

from .conftest import WrapRelays
from .mocks import ShellMock, YspMock


def powered(
    controller: media_center_kb.control.Controller, name: str
) -> media_center_kb.control.PoweredDevice:
    """named device narrowed to PoweredDevice"""
    device = controller.devices([name])[name]
    assert isinstance(device, media_center_kb.control.PoweredDevice)
    return device


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


def test_airplay_from_off(relays: WrapRelays, ysp: YspMock, nosleep):
    """airplay powers the soundbar on and off again"""
    _ = nosleep

    controller = media_center_kb.control.Controller(relays, ysp)
    commands = controller.commands_map()
    airplay = powered(controller, "airplay")

    commands["airplay_on"]()
    assert airplay.state()
    assert some_on(relays, [1])
    assert ysp.is_power_on
    assert ysp.is_input_dvd
    assert ysp.is_5beam
    assert ysp.dsp == "cinema"

    commands["airplay_off"]()
    assert not airplay.state()
    assert all_off(relays)
    assert ysp.is_power_off


@pytest.mark.parametrize(
    "source, input_name, sound_mode, on_relays",
    [
        ("tv", "tv", "5beam", [1]),
        ("streaming", "tv", "stereo", [1]),
        ("turntable", "aux1", "stereo", [1, 3]),
    ],
)
def test_airplay_restores_source(
    relays: WrapRelays,
    ysp: YspMock,
    nosleep,
    source: str,
    input_name: str,
    sound_mode: str,
    on_relays: Iterable[int],
):  # pylint: disable=too-many-arguments,too-many-positional-arguments
    """airplay restores the previously active source and its volume"""
    _ = nosleep

    commands = media_center_kb.control.Controller(relays, ysp).commands_map()
    commands[f"{source}_on"]()
    ysp.volume_code = "B2"
    commands["airplay_on"]()
    commands["airplay_volume"](0.0)
    assert ysp.is_input_dvd
    assert ysp.volume_pct == media_center_kb.control.AIRPLAY_MAX_VOLUME_PCT

    commands["airplay_off"]()
    assert some_on(relays, on_relays)
    assert ysp.is_power_on
    assert ysp.input == input_name
    assert ysp.sound_mode == sound_mode
    assert ysp.volume_code == "B2"


def test_airplay_restores_last_source(relays: WrapRelays, ysp: YspMock, nosleep):
    """only the last selected source is restored"""
    _ = nosleep

    controller = media_center_kb.control.Controller(relays, ysp)
    commands = controller.commands_map()
    devices = {name: powered(controller, name) for name in ("tv", "bt")}
    commands["tv_on"]()
    commands["streaming_on"]()
    assert not devices["tv"].state()
    assert devices["bt"].state()

    commands["airplay_on"]()
    assert not devices["bt"].state()
    commands["airplay_off"]()
    assert devices["bt"].state()
    assert ysp.is_stereo
    assert ysp.dsp == "off"


def test_airplay_after_reset(relays: WrapRelays, ysp: YspMock, nosleep):
    """a source switched off by a relays reset is not restored"""
    _ = nosleep

    commands = media_center_kb.control.Controller(relays, ysp).commands_map()
    commands["tv_on"]()
    commands["off"]()
    assert all_off(relays)
    ysp.reset()

    commands["airplay_on"]()
    assert ysp.is_input_dvd

    commands["airplay_off"]()
    assert all_off(relays)
    assert ysp.is_power_off
    assert not ysp.is_input_tv

    # source selected during the session after a reset is kept
    commands["tv_on"]()
    commands["off"]()
    commands["airplay_on"]()
    commands["tv_on"]()
    commands["airplay_off"]()
    assert some_on(relays, [1])
    assert ysp.is_power_on
    assert ysp.is_input_tv


def test_airplay_preempted(relays: WrapRelays, ysp: YspMock, nosleep):
    """other source selected during the session is left alone"""
    _ = nosleep

    controller = media_center_kb.control.Controller(relays, ysp)
    commands = controller.commands_map()
    airplay = powered(controller, "airplay")

    commands["airplay_on"]()
    commands["turntable_on"]()
    assert not airplay.state()

    # AirPlay volume no longer drives the soundbar
    commands["airplay_volume"](0.0)
    assert ysp.volume_pct is None

    commands["airplay_off"]()
    assert some_on(relays, [1, 3])
    assert ysp.is_power_on
    assert ysp.is_input_aux1

    # soundbar switched off during the session stays off
    commands["tv_on"]()
    commands["airplay_on"]()
    commands["off"]()
    ysp.reset()
    commands["airplay_off"]()
    assert all_off(relays)
    assert ysp.power_state is None


def test_airplay_idempotent(relays: WrapRelays, ysp: YspMock, nosleep):
    """repeated hooks do not overwrite the saved state"""
    _ = nosleep

    commands = media_center_kb.control.Controller(relays, ysp).commands_map()
    commands["airplay_off"]()
    assert ysp.power_state is None

    commands["tv_on"]()
    commands["airplay_on"]()
    commands["airplay_on"]()
    commands["airplay_off"]()
    assert ysp.is_input_tv

    ysp.reset()
    commands["airplay_off"]()
    assert ysp.power_state is None


def test_airplay_lost_off_hook(relays: WrapRelays, ysp: YspMock, nosleep):
    """next session sets the soundbar up again after a lost off hook"""
    _ = nosleep

    commands = media_center_kb.control.Controller(relays, ysp).commands_map()
    commands["tv_on"]()
    commands["airplay_on"]()
    # off hook lost, then the soundbar is put to standby with its remote
    ysp.power_off()

    commands["airplay_on"]()
    assert some_on(relays, [1])
    assert ysp.is_power_on
    assert ysp.is_input_dvd

    # the first session's snapshot is still restored
    commands["airplay_off"]()
    assert ysp.is_power_on
    assert ysp.is_input_tv


def test_airplay_volume(relays: WrapRelays, ysp: YspMock, nosleep, monkeypatch):
    """airplay volume is mapped, pending volume applied on start if fresh"""
    _ = nosleep

    now = [100.0]
    monkeypatch.setattr(media_center_kb.control, "clock", lambda: now[0])
    ttl = media_center_kb.control.AIRPLAY_PENDING_VOLUME_TTL
    max_pct = media_center_kb.control.AIRPLAY_MAX_VOLUME_PCT
    commands = media_center_kb.control.Controller(relays, ysp).commands_map()

    commands["airplay_volume"](-15.0)
    assert ysp.volume_pct is None
    now[0] += ttl
    commands["airplay_on"]()
    assert ysp.volume_pct == round(max_pct / 2)

    for db, pct in [(0.0, max_pct), (5.0, max_pct), (-30.0, 0), (-144.0, 0)]:
        commands["airplay_volume"](db)
        assert ysp.volume_pct == pct

    # stale pending volume is dropped
    commands["airplay_off"]()
    ysp.reset()
    commands["airplay_volume"](-144.0)
    now[0] += ttl + 1
    commands["airplay_on"]()
    assert ysp.volume_pct is None
