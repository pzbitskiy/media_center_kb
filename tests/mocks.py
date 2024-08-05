"""Test common utilities and mocks"""

import logging
from typing import Callable

from media_center_kb.relays import GPioIf

# pylint: disable=missing-function-docstring,invalid-name


class GPMock(GPioIf):
    """GPIO mock"""

    def __init__(self):
        self.high_count = {}
        self.low_count = {}
        self.states = {}

    @property
    def HIGH(self):
        return 1

    @property
    def LOW(self):
        return 0

    def input(self, pin: int) -> bool:
        return self.states.get(pin, False)

    def output(self, pin: int, signal: int):
        if signal:
            target = self.high_count
        else:
            target = self.low_count

        old = target.get(pin, 0)
        target[pin] = old + 1
        self.states[pin] = signal


class YspMock:
    """YSP mock class"""

    def __init__(self):
        self.power_state = None
        self.input = None
        self.sound_mode = None
        self.dsp = None
        self.cbs = set()

    def reset(self):
        self.power_state = None
        self.input = None
        self.sound_mode = None
        self.dsp = None
        self.cbs = set()

    def power_on(self):
        self.power_state = "on"

    def power_off(self):
        self.power_state = "off"
        self.input = None

    def set_input_tv(self):
        self.input = "tv"

    def set_input_aux1(self):
        self.input = "aux1"

    def set_5beam(self):
        self.sound_mode = "5beam"

    def set_stereo(self):
        self.sound_mode = "stereo"

    def set_dsp_cinema(self):
        self.dsp = "cinema"

    def set_dsp_off(self):
        self.dsp = "off"

    def register_state_update_cb(self, cb: Callable):
        self.cbs.add(cb)

    def unregister_state_update_cb(self, cb: Callable):
        if cb in self.cbs:
            self.cbs.remove(cb)

    @property
    def is_power_on(self):
        return self.power_state == "on"

    @property
    def is_power_off(self):
        return self.power_state == "off"

    @property
    def is_input_tv(self):
        return self.input == "tv"

    @property
    def is_input_aux1(self):
        return self.input == "aux1"

    @property
    def is_stereo(self):
        return self.sound_mode == "stereo"

    @property
    def is_5beam(self):
        return self.sound_mode == "5beam"


class ShellMock:  # pylint: disable=too-few-public-methods
    """Mock for cmd commands"""

    def __init__(self):
        self.last_cmd = None

    def __call__(self, cmd):
        self.last_cmd = cmd


class LoggerMock:
    """Mock for logging"""

    def __init__(self):
        self._level = None

    def setLevel(self, level):
        """
        Set the logging level of this logger.  level must be an int or a str.
        """
        self._level = level

    def debug(self, msg, *args, **kwargs):
        """
        Log 'msg % args' with severity 'DEBUG'.
        """
        self._log(logging.DEBUG, msg, args, **kwargs)

    def info(self, msg, *args, **kwargs):
        """
        Log 'msg % args' with severity 'INFO'.
        """
        self._log(logging.INFO, msg, args, **kwargs)

    def _log(self, level, msg, args, **kwargs):
        """no op logger"""
