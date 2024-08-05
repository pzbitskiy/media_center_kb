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

from media_center_kb.control import Controller, POWEROFF_CMD
from media_center_kb.ha import ha_loop, SmartOutletHaDevice
from media_center_kb.kb import kb_event_loop
from media_center_kb.relays import RelayModule, Pins
from media_center_kb.rpi import GPio


def init_logging(level=None, **kwargs):
    """init logging"""
    if not level:
        level = logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s.%(msecs)03d - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        **kwargs,
    )


init_logging()
logger = logging.getLogger("mcc")


class Shell:  # pylint: disable=too-few-public-methods
    """Callable shell cmd"""

    def __call__(self, cmd: str):
        logger.info("system: %s", cmd)
        if cmd == POWEROFF_CMD:
            # do not allow other commands at the moment
            os.system(cmd)


def shutdown(loop):
    """Handle signals to cancel event loop"""
    logger.info("Shutdown signal received")
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
        help="Verbose output",
    )
    args = parser.parse_args()

    verbose = False
    if args.verbose or args.debug:
        verbose = True
        init_logging(level=logging.DEBUG, force=True)

    mqtt_settings = None
    if args.mqtt:
        mqtt_settings = json.load(args.mqtt)

    loop = asyncio.get_running_loop()

    # Handle shutdown signals
    for signame in ("SIGINT", "SIGTERM"):
        loop.add_signal_handler(getattr(signal, signame), lambda: shutdown(loop))

    try:
        gpio = GPio(Pins)
        relays = RelayModule(gpio, logging.getLogger("rly"))
        ysp = Ysp4000(verbose=verbose)
        shell = Shell()
        controller = Controller(relays, ysp, shell)

        ysp_coro = ysp.get_async_coro(loop)

        extra_loop = noop_loop()
        if mqtt_settings:
            extra_loop = ha_loop(SmartOutletHaDevice(controller.devices, mqtt_settings))

        await asyncio.gather(
            kb_event_loop(controller.kb_handlers()), ysp_coro, extra_loop
        )
    except asyncio.CancelledError:
        logger.info("exiting main on cancel")
    finally:
        ysp.close()


if __name__ == "__main__":
    asyncio.run(main())
