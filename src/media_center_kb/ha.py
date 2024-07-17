"""HomeAssistant MQTT stuff"""

import asyncio
import logging
from typing import Any, Dict
import uuid

from ha_mqtt_discoverable import Settings, DeviceInfo
from ha_mqtt_discoverable.sensors import (
    Switch,
    SwitchInfo,
)
from paho.mqtt.client import Client, MQTTMessage

REFRESH_INTERVAL = 5


def get_mac_address() -> str:
    """Returns device MAC address"""
    mac = uuid.getnode()
    mac_address = ":".join(("%012X" % mac)[i : i + 2] for i in range(0, 12, 2))  # pylint: disable=consider-using-f-string
    return mac_address


class SmartOutletHaDevice:
    """Smart outlet HA device with MQTT auto discovery"""

    def __init__(
        self, state_provider: Any, handlers: Any, mqtt_settings: Dict[str, Any]
    ):
        self._state_provider = state_provider
        self._handlers = handlers
        self._mqtt_settings = Settings.MQTT(**mqtt_settings)

        self._initialize_devices()

    def _initialize_devices(self):
        """Add sensors/switches/devices"""
        rpi_device_id = get_mac_address()

        # add all devices
        self._rpi_device_info = DeviceInfo(
            name="Media Center Controller",
            model="RPi Smart Outlet v1",
            manufacturer="RPi",
            identifiers=rpi_device_id,
        )
        self._tv_device_info = DeviceInfo(
            name="TV Sound",
            model="YSP4000",
            manufacturer="Yamaha",
            identifiers=rpi_device_id + "-tv-sound",
            via_device=rpi_device_id,
        )

        self._turntable_device_info = DeviceInfo(
            name="Turntable",
            model="SL-D3",
            manufacturer="Technics",
            identifiers=rpi_device_id + "-turntable",
            via_device=rpi_device_id,
        )

        self._printer_device_info = DeviceInfo(
            name="Printer",
            model="1700n",
            manufacturer="Dell",
            identifiers=rpi_device_id + "-printer",
            via_device=rpi_device_id,
        )

        # add main switch
        rpi_switch_info = SwitchInfo(
            name="Media Center Controller Switch",
            device_class="connectivity",
            unique_id=rpi_device_id + "-switch",
            device=self._rpi_device_info,
        )
        rpi_switch_settings = Settings(mqtt=self._mqtt_settings, entity=rpi_switch_info)
        self._rpi_switch = Switch(rpi_switch_settings, self.rpi_switch_mqtt)

        # publish
        self._rpi_switch.on()

    def rpi_switch_mqtt(self, client: Client, user_data, message: MQTTMessage):  # pylint: disable=unused-argument
        """MQTT callback for rpi switch"""
        payload = message.payload.decode()
        if payload == "OFF":
            handler = self._handlers["shutdown"]
            # Let HA know that the switch was successfully deactivated
            self._rpi_switch.off()
            handler()
        elif payload == "ON":
            # cannot power on itself
            pass

    def update_all(self):
        """update all sensors"""


async def ha_loop(device: SmartOutletHaDevice):
    """loop updating MQTT"""
    try:
        while True:
            try:
                device.update_all()
            except Exception as ex:  # pylint: disable=broad-exception-caught
                logging.error("Error updating sensors: %s", ex)

            await asyncio.sleep(REFRESH_INTERVAL)
    except asyncio.CancelledError:
        logging.info("cancelled ha_loop")
