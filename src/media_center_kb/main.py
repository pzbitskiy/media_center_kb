"""
Entry point module that starts infinite loop reading keyboard
"""

import logging
import os
import sys

from ysp4000 import YSP4000

from .control import kb_handlers
from .kb import kb_event_loop
from .relays import Relays, Pins
from .rpi import GPio

logging.basicConfig(level=logging.INFO)


class Shell:  # pylint: disable=too-few-public-methods
    """Callable shell cmd"""

    def __call__(self, cmd):
        os.system(cmd)


def main():
    """init dependencies and run kb read loop"""
    argv = sys.argv
    if len(argv) > 1:
        if argv[1] in ("-d", "--debug", "-v", "--verbose"):
            logging.basicConfig(level=logging.DEBUG, force=True)

    try:
        gpio = GPio(Pins)
        relays = Relays(gpio)
        ysp = YSP4000()
        shell = Shell()

        handlers = kb_handlers(relays, ysp, shell)
        kb_event_loop(handlers)
    finally:
        ysp.close()


if __name__ == "__main__":
    main()
