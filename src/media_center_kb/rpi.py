"""RPi GPIO implementation"""

from typing import Iterable

import RPi.GPIO as GPIO  # pylint: disable=consider-using-from-import

from media_center_kb.gpio import GPioIf


# pylint: disable=no-member
class GPio(GPioIf):
    """GPioIf implementation for rpi with RPi.GPIO"""

    def __init__(self, pins: Iterable):
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)

        for pin in pins:
            GPIO.setup(pin, GPIO.OUT)

    @property
    def HIGH(self) -> int:
        return GPIO.HIGH

    @property
    def LOW(self) -> int:
        return GPIO.LOW

    def input(self, pin: int) -> bool:
        return GPIO.input(pin)

    def output(self, pin: int, signal: int):
        return GPIO.output(pin, signal)
