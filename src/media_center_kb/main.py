"""
Entry point module that starts infinite loop reading keyboard
"""

import asyncio
import logging
import os
import signal
import sys

from ysp4000 import YSP4000

from .control import kb_handlers
from .ha import ha_loop
from .kb import kb_event_loop
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
    argv = sys.argv
    if len(argv) > 1:
        if argv[1] in ("-d", "--debug", "-v", "--verbose"):
            logging.basicConfig(level=logging.DEBUG, force=True)

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

        await asyncio.gather(kb_event_loop(handlers), ha_loop())
    except asyncio.CancelledError:
        logging.info("exiting main on cancel")
    finally:
        ysp.close()


if __name__ == "__main__":
    asyncio.run(main())
