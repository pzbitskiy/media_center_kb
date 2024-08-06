"""GPIO interface"""

from abc import ABC, abstractmethod


class GPioIf(ABC):
    """Base abstract class for GPIO operations"""

    @property
    @abstractmethod
    def HIGH(self) -> int:  # pylint: disable=invalid-name
        """HIGH level"""

    @property
    @abstractmethod
    def LOW(self) -> int:  # pylint: disable=invalid-name
        """LOW level"""

    @abstractmethod
    def input(self, pin: int) -> bool:
        """Read pin and return logical HIGH/LOW level"""

    @abstractmethod
    def output(self, pin: int, signal: int):
        """Set pin to HIGH/LOW logical level"""


class GPioNoOp(GPioIf):
    """GPIO noop"""

    def __init__(self, pins):
        self.pins = pins

    @property
    def HIGH(self):
        return 1

    @property
    def LOW(self):
        return 0

    def input(self, _: int) -> bool:
        return False

    def output(self, _: int, __: int):
        return
