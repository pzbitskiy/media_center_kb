"""HomeAssistant MQTT stuff"""

import asyncio
import logging

REFRESH_INTERVAL = 5


class SmartOutletHaDevice:
    """Smart outlet HA device with MQTT auto discovery"""

    def __init__(self):
        pass

    def update_all(self):
        """update all sensors"""


async def ha_loop():
    """loop updating MQTT"""
    device = SmartOutletHaDevice()
    try:
        while True:
            try:
                device.update_all()
            except Exception as ex:  # pylint: disable=broad-exception-caught
                logging.error("Error updating sensors: %s", ex)

            await asyncio.sleep(REFRESH_INTERVAL)
    except asyncio.CancelledError:
        logging.info("cancelled ha_loop")
