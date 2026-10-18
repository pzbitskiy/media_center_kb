"""HA device tests"""

from types import SimpleNamespace

import pytest
from ha_mqtt_discoverable.sensors import BinarySensor

from media_center_kb.ha import CachedBinarySensor, CachedSwitch, SmartOutletHaDevice

# pylint: disable=protected-access


class EntityMock:
    """records the last state or value published"""

    def __init__(self):
        self.value = None

    def update_state(self, state: bool):
        """Switch / BinarySensor"""
        self.value = state

    def set_value(self, value: float):
        """Number"""
        self.value = value


def test_update_all():
    """all devices are synced to HA"""
    device = SmartOutletHaDevice.__new__(SmartOutletHaDevice)
    device._devices = {
        name: SimpleNamespace(volume=vol, state=lambda on=on: on)
        for name, vol, on in [
            ("tv", 10, False),
            ("turntable", 20, False),
            ("bt", 30, True),
            ("printer", None, True),
            ("airplay", None, False),
        ]
    }
    entities = [
        "_tv_volume",
        "_turntable_volume",
        "_bt_volume",
        "_tv_switch",
        "_turntable_switch",
        "_bt_switch",
        "_printer_switch",
        "_airplay_active",
    ]
    mocks = {name: EntityMock() for name in entities}
    for name, mock in mocks.items():
        setattr(device, name, mock)

    device.update_all()

    assert {name: mock.value for name, mock in mocks.items()} == {
        "_tv_volume": 10,
        "_turntable_volume": 20,
        "_bt_volume": 30,
        "_tv_switch": False,
        "_turntable_switch": False,
        "_bt_switch": True,
        "_printer_switch": True,
        "_airplay_active": False,
    }


@pytest.mark.parametrize("cls", [CachedBinarySensor, CachedSwitch])
def test_cached_state(cls, monkeypatch):
    """state is published only when it changes"""
    published = []
    monkeypatch.setattr(
        BinarySensor, "update_state", lambda self, state: published.append(state)
    )
    entity = cls.__new__(cls)
    entity._state = None
    # used by Discoverable.__del__
    entity.mqtt_client = SimpleNamespace(
        disconnect=lambda: None, loop_stop=lambda: None
    )

    entity.update_state(True)
    entity.update_state(True)
    entity.off()
    entity.off()
    entity.on()
    assert published == [True, False, True]
