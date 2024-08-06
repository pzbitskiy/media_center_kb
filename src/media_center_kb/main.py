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

from media_center_kb.control import Controller
from media_center_kb.gpio import GPioNoOp
from media_center_kb.ha import ha_loop, SmartOutletHaDevice
from media_center_kb.kb import kb_event_loop
from media_center_kb.relays import RelayModule, Pins

try:
    from media_center_kb.rpi import GPio

    RAISED = None
except RuntimeError as ex:
    RAISED = ex


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


class RestrictedShell:  # pylint: disable=too-few-public-methods
    """Callable shell cmd"""

    _allowed_cmds = frozenset(
        [
            "sudo poweroff",
        ]
    )

    def __call__(self, cmd: str):
        logger.info("system: %s", cmd)
        if cmd in self._allowed_cmds:
            os.system(cmd)


def shutdown(loop):
    """Handle signals to cancel event loop"""
    logger.info("Shutdown signal received")
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
        help="Verbose output",
    )
    parser.add_argument(
        "--no-gpio",
        dest="no_gpio",
        action="store_true",
        help="No GPIO device. Useful when tunning without physical relays/control board",
    )
    parser.add_argument(
        "--no-kb",
        dest="no_keyboard",
        action="store_true",
        help="No keyboard. Useful when tunning without physical controls",
    )
    parser.add_argument(
        "--no-serial",
        dest="no_serial",
        action="store_true",
        help="No serial port. Useful when tunning without connected serial port",
    )
    parser.add_argument(
        "--no-ha",
        dest="no_ha",
        action="store_true",
        help="No MQTT. Useful when tunning without MQTT+HA integration",
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

    if not args.no_gpio and RAISED:
        raise RAISED

    try:
        gpio = GPio(Pins) if not args.no_gpio else GPioNoOp(Pins)
        relays = RelayModule(gpio, logging.getLogger("rly"))
        ysp = Ysp4000(verbose=verbose)
        shell = RestrictedShell()
        controller = Controller(relays, ysp, shell)

        coros = []
        if not args.no_keyboard:
            coros.append(kb_event_loop(controller.kb_handlers()))
        if not args.no_serial:
            coros.append(ysp.get_async_coro(loop))
        if mqtt_settings and not args.no_ha:
            coros.append(
                ha_loop(SmartOutletHaDevice(controller.devices, mqtt_settings))
            )

        await asyncio.gather(*coros)
    except asyncio.CancelledError:
        logger.info("exiting main on cancel")
    finally:
        ysp.close()


if __name__ == "__main__":
    asyncio.run(main())
