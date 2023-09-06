"""
Entry point module that starts infinite loop reading keyboard
"""
import logging

from ysp4000 import YSP4000

from .control import control_handlers
from .kb import kb_event_loop
from .relays import Relays, Pins
from .rpi import GPio

logging.basicConfig(level=logging.INFO)


def main(argv):
    """init dependencies and run kb read loop"""
    if len(argv) > 1:
        if argv[1] in ('-d', '--debug', '-v', '--verbose'):
            logging.basicConfig(level=logging.DEBUG, force=True)

    try:
        gpio = GPio(Pins)
        relays = Relays(gpio)
        ysp = YSP4000()

        handlers = control_handlers(relays, ysp)
        kb_event_loop(handlers)
    finally:
        ysp.close()


if __name__ == '__main__':
    import sys
    main(sys.argv)
