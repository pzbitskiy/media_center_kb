"""
Entry point module that starts infinite loop reading keyboard
"""

import argparse
import asyncio
import json
import logging
import os
import signal

from ysp4000.ysp import Ysp4000

from .control import commands_map, kb_handlers, POWEROFF_CMD
from .ha import ha_loop, SmartOutletHaDevice
from .kb import kb_event_loop
from .provider import Provider
from .relays import Relays, Pins
from .rpi import GPio

logging.basicConfig(level=logging.INFO)


class Shell:  # pylint: disable=too-few-public-methods
    """Callable shell cmd"""

    def __call__(self, cmd):
        logging.info("system: %s", cmd)
        if cmd == POWEROFF_CMD:
            # do not allow other commands at the moment
            os.system(cmd)


def shutdown(loop):
    """Handle signals to cancel event loop"""
    logging.info("Shutdown signal received")
    for task in asyncio.all_tasks(loop):
        task.cancel()


async def noop_loop():
    """Noop implementation when no HA stuff available or needed"""
    return


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
        mqtt_settings = json.load(args.mqtt)

    loop = asyncio.get_running_loop()

    # Handle shutdown signals
    for signame in ("SIGINT", "SIGTERM"):
        loop.add_signal_handler(getattr(signal, signame), lambda: shutdown(loop))

    try:
        gpio = GPio(Pins)
        relays = Relays(gpio)
        ysp = Ysp4000(verbose=True)
        shell = Shell()
        handlers = kb_handlers(relays, ysp, shell)

        ysp_coro = ysp.get_async_coro(loop)

        extra_loop = noop_loop()
        if mqtt_settings:
            handlers = commands_map(relays, ysp, shell)
            ha_device = SmartOutletHaDevice(
                Provider(relays, ysp), handlers, mqtt_settings
            )
            extra_loop = ha_loop(ha_device)

        await asyncio.gather(kb_event_loop(handlers), ysp_coro, extra_loop)
    except asyncio.CancelledError:
        logging.info("exiting main on cancel")
    finally:
        ysp.close()


if __name__ == "__main__":
    asyncio.run(main())
