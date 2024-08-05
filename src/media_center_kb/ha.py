"""HomeAssistant MQTT stuff"""

import asyncio
import logging
from typing import Any, Callable, Dict, Iterable
import uuid

from ha_mqtt_discoverable import Settings, DeviceInfo
from ha_mqtt_discoverable.sensors import (
    Number,
    NumberInfo,
    Switch,
    SwitchInfo,
)
from paho.mqtt.client import Client, MQTTMessage

from media_center_kb.control import PoweredDevice

REFRESH_INTERVAL = 5


def get_mac_address() -> str:
    """Returns device MAC address"""
    mac = uuid.getnode()
    # pylint: disable=consider-using-f-string
    mac_address = "".join(("%012x" % mac)[i : i + 2] for i in range(0, 12, 2))
    return mac_address


class SmartOutletHaDevice:  # pylint: disable=too-many-instance-attributes
    """Smart outlet HA device with MQTT auto discovery"""

    def __init__(
        self,
        device_provider: Callable[[Iterable[str]], Dict[str, PoweredDevice]],
        mqtt_settings: Dict[str, Any],
    ):
        self._devices = device_provider(["tv", "turntable", "printer"])
        self._mqtt_settings = Settings.MQTT(**mqtt_settings)

        self._initialize_ha_devices()

    def _initialize_ha_devices(self):  # pylint: disable=too-many-locals
        """Add sensors/switches/devices"""
        # add all devices
        rpi_device_id = get_mac_address()
        self._rpi_device_info = DeviceInfo(
            name="Media Center Controller",
            model="RPi Smart Outlet v2",
            manufacturer="DIY(tm)",
            identifiers=rpi_device_id,
        )
        tv_device_id = rpi_device_id + "-tv"
        self._tv_device_info = DeviceInfo(
            name="TV",
            identifiers=tv_device_id,
            via_device=rpi_device_id,
        )
        turntable_device_id = rpi_device_id + "-turntable"
        self._turntable_device_info = DeviceInfo(
            name="Turntable",
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
        # rpi_switch_info = SwitchInfo(
        #     name="Media Center Controller Switch",
        #     device_class="outlet",
        #     unique_id=rpi_device_id + "-switch",
        #     device=self._rpi_device_info,
        # )
        # rpi_switch_settings = Settings(mqtt=self._mqtt_settings, entity=rpi_switch_info)
        # self._rpi_switch = Switch(rpi_switch_settings, self.rpi_switch_mqtt)

        tv_switch_info = SwitchInfo(
            name="TV",
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

        # add volume
        tv_volume_info = NumberInfo(
            name="Bluetooth Sound Volume",
            min=0,
            max=100,
            mode="slider",
            step=1,
            unique_id=tv_device_id + "-vol",
            device=self._tv_device_info,
        )
        tv_volume_settings = Settings(mqtt=self._mqtt_settings, entity=tv_volume_info)
        self._tv_volume = Number(
            tv_volume_settings, lambda c, u, m: self.tv_volume_mqtt(c, m)
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
        turntable_volume_settings = Settings(
            mqtt=self._mqtt_settings, entity=turntable_volume_info
        )
        self._turntable_volume = Number(
            turntable_volume_settings, lambda c, u, m: self.turntable_volume_mqtt(c, m)
        )

    def announce(self):
        """Publish devices over MQTT"""
        # self._rpi_switch.on()

        self._printer_switch.off()
        self._tv_switch.off()
        self._turntable_switch.off()

        self._tv_volume.set_value(0)
        self._turntable_volume.set_value(0)

    # def rpi_switch_mqtt(
    #     self, client: Client, user_data, message: MQTTMessage
    # ):  # pylint: disable=unused-argument
    #     """MQTT callback for rpi switch"""
    #     payload = message.payload.decode()
    #     logging.debug("rpi_switch_mqtt: %s", payload)
    #     if payload == "OFF":
    #         # Let HA know that the switch was successfully deactivated
    #         self._rpi_switch.off()
    #         self._handlers["shutdown"]()
    #     elif payload == "ON":
    #         # cannot power on itself
    #         pass

    def printer_switch_mqtt(
        self, client: Client, user_data, message: MQTTMessage
    ):  # pylint: disable=unused-argument
        """MQTT callback for printer switch"""
        payload = message.payload.decode()
        logging.debug("printer_switch_mqtt: %s", payload)
        if payload == "OFF":
            self._devices["printer"].off()
            self._printer_switch.off()
        elif payload == "ON":
            self._devices["printer"].on()
            self._printer_switch.on()

    def tv_switch_mqtt(
        self, client: Client, user_data, message: MQTTMessage
    ):  # pylint: disable=unused-argument
        """MQTT callback for printer switch"""
        payload = message.payload.decode()
        logging.debug("tv_switch_mqtt: %s", payload)
        if payload == "OFF":
            self._devices["tv"].off()
            self._tv_switch.off()
        elif payload == "ON":
            self._devices["tv"].on()
            self._tv_switch.on()

    def turnable_switch_mqtt(
        self, client: Client, user_data, message: MQTTMessage
    ):  # pylint: disable=unused-argument
        """MQTT callback for printer switch"""
        payload = message.payload.decode()
        logging.debug("turntable_switch_mqtt: %s", payload)
        if payload == "OFF":
            self._devices["turntable"].off()
            self._turntable_switch.off()
        elif payload == "ON":
            self._devices["turntable"].on()
            self._turntable_switch.on()

    def tv_volume_mqtt(
        self, client: Client, message: MQTTMessage
    ):  # pylint: disable=unused-argument
        """MQTT callback for volume"""
        vol = int(message.payload.decode())
        self._devices["tv"].volume = vol  # type: ignore[attr-defined]

    def turntable_volume_mqtt(
        self, client: Client, message: MQTTMessage
    ):  # pylint: disable=unused-argument
        """MQTT callback for volume"""
        vol = int(message.payload.decode())
        self._devices["turntable"].volume = vol  # type: ignore[attr-defined]

    def update_all(self):
        """update all sensors"""
        self._tv_volume.set_value(self._devices["tv"].volume)
        self._turntable_volume.set_value(self._devices["turntable"].volume)

        self._tv_switch.update_state(self._devices["tv"].state())
        self._turntable_switch.update_state(self._devices["turntable"].state())
        self._printer_switch.update_state(self._devices["printer"].state())


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


async def main():
    """main func used for quick tests"""
    ha_device = SmartOutletHaDevice(
        None, mqtt_settings={"host": "localhost", "port": 1883}
    )
    extra_loop = ha_loop(ha_device)
    await asyncio.gather(extra_loop)


if __name__ == "__main__":
    asyncio.run(main())
