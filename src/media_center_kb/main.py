"""
Entry point module that starts infinite loop reading keyboard
"""

import argparse
import asyncio
import json
import logging
import os
import signal

from ysp4000 import YSP4000

from .control import kb_handlers
from .ha import ha_loop, MqttSettings, SmartOutletHaDevice
from .kb import kb_event_loop
from .provider import Provider
from .relays import Relays, Pins
from .rpi import GPio

logging.basicConfig(level=logging.INFO)


class Shell:  # pylint: disable=too-few-public-methods
    """Callable shell cmd"""

    def __call__(self, cmd):
        logging.info("system: %s", cmd)
        os.system(cmd)


def shutdown(loop):
    """Handle signals to cancel event loop"""
    logging.info("Shutdown signal received")
    for task in asyncio.all_tasks(loop):
        task.cancel()


async def main():
    """init dependencies and run kb read loop"""
    parser = argparse.ArgumentParser(description="App manager")
    parser.add_argument(
        "-d",
        "--debug",
        dest="debug",
        action="store_true",
        help="Debug output",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        dest="verbose",
        action="store_true",
        help="Verbose output",
    )
    parser.add_argument(
        "-m",
        "--mqtt",
        dest="mqtt",
        type=argparse.FileType("rt", encoding="utf8"),
        action="store_true",
        help="Verbose output",
    )
    args = parser.parse_args()

    if args.verbose or args.debug:
        logging.basicConfig(level=logging.DEBUG, force=True)
    mqtt_settings = None
    if args.mqtt:
        mqtt_dict = json.load(args.mqtt)
        mqtt_settings = MqttSettings(**mqtt_dict)

    loop = asyncio.get_running_loop()

    # Handle shutdown signals
    for signame in ("SIGINT", "SIGTERM"):
        loop.add_signal_handler(getattr(signal, signame), lambda: shutdown(loop))

    try:
        gpio = GPio(Pins)
        relays = Relays(gpio)
        ysp = YSP4000()
        shell = Shell()
        handlers = kb_handlers(relays, ysp, shell)
        ha_device = SmartOutletHaDevice(Provider(relays, ysp), mqtt_settings)

        await asyncio.gather(kb_event_loop(handlers), ha_loop(ha_device))
    except asyncio.CancelledError:
        logging.info("exiting main on cancel")
    finally:
        ysp.close()


if __name__ == "__main__":
    asyncio.run(main())
