"""HomeAssistant MQTT stuff"""

import asyncio
import logging
from typing import Any, Dict
import uuid

from ha_mqtt_discoverable import Settings, DeviceInfo
from ha_mqtt_discoverable.sensors import (
    Number,
    NumberInfo,
    Switch,
    SwitchInfo,
)
from paho.mqtt.client import Client, MQTTMessage

REFRESH_INTERVAL = 5


def get_mac_address() -> str:
    """Returns device MAC address"""
    mac = uuid.getnode()
    # pylint: disable=consider-using-f-string
    mac_address = ":".join(("%012X" % mac)[i : i + 2] for i in range(0, 12, 2))
    return mac_address


class SmartOutletHaDevice:  # pylint: disable=too-many-instance-attributes
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
        # add all devices
        rpi_device_id = get_mac_address()
        self._rpi_device_info = DeviceInfo(
            name="Media Center Controller",
            model="RPi Smart Outlet v1",
            manufacturer="RPi",
            identifiers=rpi_device_id,
        )
        tv_device_id = rpi_device_id + "-tv-sound"
        self._tv_device_info = DeviceInfo(
            name="TV Sound",
            model="YSP4000",
            manufacturer="Yamaha",
            identifiers=tv_device_id,
            via_device=rpi_device_id,
        )
        turntable_device_id = rpi_device_id + "-turntable"
        self._turntable_device_info = DeviceInfo(
            name="Turntable",
            model="SL-D3",
            manufacturer="Technics",
            identifiers=turntable_device_id,
            via_device=rpi_device_id,
        )
        printer_device_id = rpi_device_id + "-printer"
        self._printer_device_info = DeviceInfo(
            name="Printer",
            model="1700n",
            manufacturer="Dell",
            identifiers=printer_device_id,
            via_device=rpi_device_id,
        )

        # add switches
        rpi_switch_info = SwitchInfo(
            name="Media Center Controller Switch",
            device_class="outlet",
            unique_id=rpi_device_id + "-switch",
            device=self._rpi_device_info,
        )
        rpi_switch_settings = Settings(mqtt=self._mqtt_settings, entity=rpi_switch_info)
        self._rpi_switch = Switch(rpi_switch_settings, self.rpi_switch_mqtt)

        printer_switch_info = SwitchInfo(
            name="Printer",
            device_class="outlet",
            unique_id=printer_device_id + "-switch",
            device=self._printer_device_info,
        )
        printer_switch_settings = Settings(
            mqtt=self._mqtt_settings, entity=printer_switch_info
        )
        self._printer_switch = Switch(printer_switch_settings, self.printer_switch_mqtt)

        tv_switch_info = SwitchInfo(
            name="Soundbar",
            device_class="switch",
            unique_id=tv_device_id + "-switch",
            device=self._tv_device_info,
        )
        tv_switch_settings = Settings(mqtt=self._mqtt_settings, entity=tv_switch_info)
        self._tv_switch = Switch(tv_switch_settings, self.tv_switch_mqtt)

        turntable_switch_info = SwitchInfo(
            name="Turntable",
            device_class="switch",
            unique_id=turntable_device_id + "-switch",
            device=self._turntable_device_info,
        )
        turntable_switch_settings = Settings(
            mqtt=self._mqtt_settings, entity=turntable_switch_info
        )
        self._turntable_switch = Switch(
            turntable_switch_settings, self.turnable_switch_mqtt
        )

        tv_volume_info = NumberInfo(
            name="TV Volume",
            min=0,
            max=100,
            mode="slider",
            step=1,
            unique_id=tv_device_id + "-vol",
            device=self._tv_device_info,
        )
        tv_volume_settings = Settings(mqtt=self._mqtt_settings, entity=tv_volume_info)
        self._tv_volume = Number(
            tv_volume_settings, lambda c, u, m: self.volume_mqtt(c, m)
        )

        turntable_volume_info = NumberInfo(
            name="Turntable Volume",
            min=0,
            max=100,
            mode="slider",
            step=1,
            unique_id=turntable_device_id + "-vol",
            device=self._turntable_device_info,
        )
        turntable_volume_settings = Settings(mqtt=self._mqtt_settings, entity=turntable_volume_info)
        self._turntable_volume = Number(
            turntable_volume_settings, lambda c, u, m: self.volume_mqtt(c, m)
        )

    def announce(self):
        """Publish devices over MQTT"""
        self._rpi_switch.on()
        self._printer_switch.off()
        self._tv_switch.off()
        self._tv_volume.set_value(0)

    def rpi_switch_mqtt(
        self, client: Client, user_data, message: MQTTMessage
    ):  # pylint: disable=unused-argument
        """MQTT callback for rpi switch"""
        payload = message.payload.decode()
        logging.debug("rpi_switch_mqtt: %s", payload)
        if payload == "OFF":
            handler = self._handlers["shutdown"]
            # Let HA know that the switch was successfully deactivated
            self._rpi_switch.off()
            handler()
        elif payload == "ON":
            # cannot power on itself
            pass

    def printer_switch_mqtt(
        self, client: Client, user_data, message: MQTTMessage
    ):  # pylint: disable=unused-argument
        """MQTT callback for printer switch"""
        payload = message.payload.decode()
        logging.debug("printer_switch_mqtt: %s", payload)
        if payload == "OFF":
            self._handlers["printer_off"]()
            self._printer_switch.off()
        elif payload == "ON":
            self._handlers["printer_on"]()
            self._printer_switch.on()

    def tv_switch_mqtt(
        self, client: Client, user_data, message: MQTTMessage
    ):  # pylint: disable=unused-argument
        """MQTT callback for printer switch"""
        payload = message.payload.decode()
        logging.debug("tv_switch_mqtt: %s", payload)
        if payload == "OFF":
            self._handlers["tv_off"]()
            self._tv_switch.off()
        elif payload == "ON":
            self._handlers["tv_on"]()
            self._tv_switch.on()

    def turnable_switch_mqtt(
        self, client: Client, user_data, message: MQTTMessage
    ):  # pylint: disable=unused-argument
        """MQTT callback for printer switch"""
        payload = message.payload.decode()
        logging.debug("turntable_switch_mqtt: %s", payload)
        if payload == "OFF":
            self._handlers["turntable_off"]()
            self._tv_switch.off()
        elif payload == "ON":
            self._handlers["turntable_on"]()
            self._tv_switch.on()

    def volume_mqtt(
        self, client: Client, message: MQTTMessage
    ):  # pylint: disable=unused-argument
        """MQTT callback for volume"""
        vol = int(message.payload.decode())
        self._handlers["volume_set"](vol)

    def update_all(self):
        """update all sensors"""


async def ha_loop(device: SmartOutletHaDevice):
    """loop updating MQTT"""
    try:
        device.announce()
        while True:
            try:
                device.update_all()
            except Exception as ex:  # pylint: disable=broad-exception-caught
                logging.error("Error updating sensors: %s", ex)

            await asyncio.sleep(REFRESH_INTERVAL)
    except asyncio.CancelledError:
        logging.info("cancelled ha_loop")
