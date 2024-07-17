"""HomeAssistant MQTT stuff"""

import asyncio
from dataclasses import dataclass
import logging
from typing import Any, Optional

REFRESH_INTERVAL = 5


@dataclass
class MqttSettings:
    """MQTT broker connectivity info"""

    host: str
    port: int
    username: Optional[str]
    password: Optional[str]


class SmartOutletHaDevice:
    """Smart outlet HA device with MQTT auto discovery"""

    def __init__(self, state_provider: Any, mqtt_settings: MqttSettings):
        self._state_provider = state_provider

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
