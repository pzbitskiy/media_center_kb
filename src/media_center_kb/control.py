"""
Control action for each key
"""

from abc import ABC, abstractmethod
from enum import Enum
import time
from typing import (
    Callable,
    Dict,
    Iterable,
    NamedTuple,
    Optional,
    Tuple,
    Union,
    no_type_check,
)

from ysp4000.ysp import Ysp4000
from media_center_kb.relays import RelayModuleIf, RelayIf


class RelayMap(Enum):
    """Maps symbol names to relay numbers"""

    YSP = 1
    _TDB = 2
    TURNTABLE = 3
    PRINTER = 4


class YspVolumeTracker:
    """YSP4000 volume pct (numeric value) tracker"""

    def __init__(self, ysp: Ysp4000):
        self._ysp = ysp

        self._ysp.register_state_update_cb(self._ysp_state_update_cb)
        self._ysp_volume = 0

    def _ysp_state_update_cb(self, **kwargs):
        if (vol := kwargs.get("volume")) is not None:
            # volume returned as a string '0' - '100'
            self._ysp_volume = int(vol)

    @property
    def volume(self) -> int:
        """Set volume numeric value"""
        return self._ysp_volume

    def close(self):
        """unregister the state callback"""
        self._ysp.unregister_state_update_cb(self._ysp_state_update_cb)

    def __del__(self):
        self.close()


class PoweredDevice(ABC):
    """Device that can be powered on and off"""

    @abstractmethod
    def on(self):  # pylint: disable=invalid-name
        """Switch ON"""

    @abstractmethod
    def off(self):
        """Switch OFF"""

    @abstractmethod
    def state(self) -> bool:
        """Get power state"""


class SoundDevice(ABC):  # pylint: disable=too-few-public-methods
    """Device that have adjustable volume"""

    @property
    @abstractmethod
    def volume(self) -> int:
        """Get volume level"""

    @volume.setter
    @abstractmethod
    def volume(self, value: int):
        """Set volume level"""


class YspSoundDevice(SoundDevice):
    """YSP4000 device with volume control"""

    def __init__(self, ysp: Ysp4000):
        self._ysp = ysp
        self._volume_tracker = YspVolumeTracker(ysp)

    @property
    def volume(self) -> int:
        return self._volume_tracker.volume

    @volume.setter
    def volume(self, value: int):
        self._ysp.set_volume_pct(value)

    def __del__(self):
        self._volume_tracker.close()


# define here so can be redefined in tests
sleeper = time.sleep
clock = time.monotonic


class SoundbarOwner:  # pylint: disable=too-few-public-methods
    """The source currently playing via the soundbar, None if the soundbar is off.
    Shared by all soundbar sources because they share the soundbar relay and input.
    """

    def __init__(self) -> None:
        self.current: Optional[PoweredDevice] = None


class YspPoweredDevice(PoweredDevice):
    """Ysp4000 device with power on/off capability"""

    def __init__(self, ysp: Ysp4000):
        self._ysp = ysp
        self._state = False

    def on(self):
        self._ysp.power_on()
        self._state = True

    def off(self):
        self._ysp.power_off()
        self._state = False
        # give YSP change to power off. 1s looks a lot but who cares, it is being switched off
        sleeper(1)

    def state(self) -> bool:
        return self._state


class TV(YspPoweredDevice, YspSoundDevice):
    """TV Device"""

    def __init__(self, relay: RelayIf, ysp: Ysp4000, owner: SoundbarOwner):
        YspPoweredDevice.__init__(self, ysp)
        YspSoundDevice.__init__(self, ysp)

        self._relay = relay
        self._ysp = ysp
        self._owner = owner

    def on(self):
        """
        power on soundbar
        turn on soundbar
        select TV/STB channel
        select 5 beam
        select cinema mode
        IR/radio to switch on projector?
        """
        self._relay.on()
        YspPoweredDevice.on(self)

        self._ysp.set_input_tv()
        self._ysp.set_5beam()
        self._ysp.set_dsp_cinema()
        self._owner.current = self

    def off(self):
        """
        turn off soundbar
        power off soundbar
        """
        YspPoweredDevice.off(self)
        self._relay.off()
        self._owner.current = None

    def state(self):
        return self._owner.current is self


class BluetoothStreamer(YspPoweredDevice, YspSoundDevice):
    """Bluetooth Streaming Device"""

    def __init__(self, relay: RelayIf, ysp: Ysp4000, owner: SoundbarOwner):
        YspPoweredDevice.__init__(self, ysp)
        YspSoundDevice.__init__(self, ysp)

        self._relay = relay
        self._ysp = ysp
        self._owner = owner

    def on(self):
        """
        power on soundbar
        turn on soundbar
        select TV/STB channel
        select stereo mode
        """
        self._relay.on()
        YspPoweredDevice.on(self)

        self._ysp.set_input_tv()
        self._ysp.set_dsp_off()
        self._ysp.set_stereo()
        self._owner.current = self

    def off(self):
        """
        turn off soundbar
        power off soundbar
        """
        YspPoweredDevice.off(self)
        self._relay.off()
        self._owner.current = None

    def state(self):
        return self._owner.current is self


class Turntable(YspPoweredDevice, YspSoundDevice):
    """Turntable Device"""

    def __init__(
        self, relay1: RelayIf, relay2: RelayIf, ysp: Ysp4000, owner: SoundbarOwner
    ):
        YspPoweredDevice.__init__(self, ysp)
        YspSoundDevice.__init__(self, ysp)

        self._relay1 = relay1
        self._relay2 = relay2
        self._ysp = ysp
        self._owner = owner

    def on(self):
        """
        power on soundbar (relay 1)
        turn on soundbar
        select AUX1 channel
        select stereo mode
        power on turntable (relay 2)
        """
        self._relay1.on()
        self._relay2.on()
        YspPoweredDevice.on(self)
        self._ysp.set_input_aux1()
        self._ysp.set_dsp_off()
        self._ysp.set_stereo()
        self._owner.current = self

    def off(self):
        """
        turn off soundbar
        power off soundbar
        """
        YspPoweredDevice.off(self)
        self._relay2.off()
        self._relay1.off()
        self._owner.current = None

    def state(self):
        return self._owner.current is self


AIRPLAY_MIN_DB = -30.0
# cap so connecting at full AirPlay volume does not blast the room
AIRPLAY_MAX_VOLUME_PCT = 80


def airplay_db_to_pct(db: float) -> int:
    """Map AirPlay volume (-30..0 dB, -144 is mute) to YSP volume pct"""
    if db <= AIRPLAY_MIN_DB:
        return 0
    db = min(db, 0.0)
    return round((db - AIRPLAY_MIN_DB) / -AIRPLAY_MIN_DB * AIRPLAY_MAX_VOLUME_PCT)


# volume received before the session started is applied only if this fresh, seconds
AIRPLAY_PENDING_VOLUME_TTL = 10.0


class _Snapshot(NamedTuple):
    """Soundbar state before an AirPlay session"""

    # source to restore, None if the soundbar was off
    owner: Optional[PoweredDevice]
    # raw YSP volume code, None if unknown
    volume: Optional[str]


class AirPlayReceiver(YspPoweredDevice):
    """AirPlay receiver (shairport-sync) playing via the soundbar DVD (HDMI) input.
    Remembers the soundbar state on session start and restores it on session end.
    """

    def __init__(self, relay: RelayIf, ysp: Ysp4000, owner: SoundbarOwner):
        YspPoweredDevice.__init__(self, ysp)

        self._relay = relay
        self._ysp = ysp
        self._owner = owner
        self._snapshot: Optional[_Snapshot] = None
        # (pct, clock() when received)
        self._pending_volume: Optional[Tuple[int, float]] = None

    def _apply_preset(self):
        """select DVD (HDMI) input, 5 beam and cinema mode"""
        self._ysp.set_input_dvd()
        self._ysp.set_5beam()
        self._ysp.set_dsp_cinema()

    def on(self):
        """
        remember the soundbar state
        power on soundbar
        turn on soundbar
        select DVD (HDMI) channel and the preset
        """
        # Already owning means the previous session's off() hook was lost:
        # keep its snapshot but set the soundbar up again,
        # it could have been put to standby or another input meanwhile.
        if not self.state():
            self._snapshot = _Snapshot(
                owner=self._owner.current,
                volume=self._ysp.state.get("volume"),
            )
            # own the soundbar before touching it so a failed start is undone by off()
            self._owner.current = self

        self._relay.on()
        YspPoweredDevice.on(self)
        self._apply_preset()

        pending, self._pending_volume = self._pending_volume, None
        if pending is not None and clock() - pending[1] <= AIRPLAY_PENDING_VOLUME_TTL:
            self._ysp.set_volume_pct(pending[0])

    def off(self):
        """
        restore the previous source and volume if the soundbar was on,
        otherwise turn off and power off soundbar
        """
        snapshot, self._snapshot = self._snapshot, None
        if not self.state() or snapshot is None:
            # not started, or the soundbar was switched off or to another source
            return

        if snapshot.owner is not None:
            # re-selects its input, beam and DSP and takes the ownership
            snapshot.owner.on()
            if snapshot.volume is not None:
                self._ysp.set_volume(snapshot.volume)
        else:
            YspPoweredDevice.off(self)
            self._relay.off()
            self._owner.current = None

    def state(self) -> bool:
        return self._owner.current is self

    def set_volume(self, db: float):
        """Set AirPlay volume in dB, applied only while AirPlay owns the soundbar"""
        pct = airplay_db_to_pct(db)
        if self.state():
            self._ysp.set_volume_pct(pct)
        else:
            self._pending_volume = (pct, clock())


class Printer(PoweredDevice):
    """Printer Device"""

    def __init__(self, relay: RelayIf):
        self._relay = relay
        self._powered = False

    def on(self):
        self._relay.on()
        self._powered = True

    def off(self):
        self._relay.off()
        self._powered = False

    def state(self):
        return self._powered


class VolumeControl(YspSoundDevice):
    """Volume control"""

    def __init__(self, ysp: Ysp4000):
        YspSoundDevice.__init__(self, ysp)

    def inc(self):
        """Increase volume"""
        self._ysp.volume_up()

    def dec(self):
        """Decrease volume"""
        self._ysp.volume_down()


class BoardControl:
    """Board control"""

    def __init__(
        self,
        relays: RelayModuleIf,
        ysp: Ysp4000,
        owner: SoundbarOwner,
        shell: Callable,
    ):
        self._relays = relays
        self._ypd = YspPoweredDevice(ysp)
        self._owner = owner
        self._shell = shell

    def reset(self):
        """Reset all relays"""
        self._ypd.off()
        self._relays.reset()
        self._owner.current = None

    def shutdown(self):
        """Shutdown the board"""
        self.reset()
        self._shell("sudo poweroff")


class Controller:  # pylint: disable=too-many-instance-attributes
    """Controller class"""

    def __init__(
        self,
        relays: RelayModuleIf,
        ysp: Ysp4000,
        shell: Optional[Callable[[str], None]] = None,
    ):
        def noop(_):
            pass

        self._relays = relays
        self._ysp = ysp
        self._shell: Callable = noop if not shell else shell

        owner = SoundbarOwner()
        ysp_relay = self._relays.relay(RelayMap.YSP.value)
        self._named_devices: Dict[str, Union[PoweredDevice, SoundDevice]] = {
            "tv": TV(ysp_relay, self._ysp, owner),
            "bt": BluetoothStreamer(ysp_relay, self._ysp, owner),
            "turntable": Turntable(
                ysp_relay,
                self._relays.relay(RelayMap.TURNTABLE.value),
                self._ysp,
                owner,
            ),
            "printer": Printer(self._relays.relay(RelayMap.PRINTER.value)),
            "airplay": AirPlayReceiver(ysp_relay, self._ysp, owner),
        }

        self._volume_control = VolumeControl(self._ysp)
        self._board_control = BoardControl(self._relays, self._ysp, owner, self._shell)

    def devices(
        self, wanted: Iterable[str]
    ) -> Dict[str, Union[PoweredDevice, SoundDevice]]:
        """Return requested devices.
        Raises ValueError if some device not found
        """
        result = {}
        for name in wanted:
            device = self._named_devices.get(name)
            if device is None:
                raise ValueError(f"unknown device: {name}")
            result[name] = device
        return result

    def shutdown(self):
        """Power off the controller"""
        self._board_control.shutdown()

    @no_type_check
    def commands_map(self) -> Dict[str, Callable]:
        """Returns dict of handlers by keycode"""
        return {
            "tv_on": self._named_devices["tv"].on,
            "tv_off": self._named_devices["tv"].off,
            "turntable_on": self._named_devices["turntable"].on,
            "turntable_off": self._named_devices["turntable"].off,
            "streaming_on": self._named_devices["bt"].on,
            "streaming_off": self._named_devices["bt"].off,
            "printer_on": self._named_devices["printer"].on,
            "printer_off": self._named_devices["printer"].off,
            # AirPlay session hooks, no keys
            "airplay_on": self._named_devices["airplay"].on,
            "airplay_off": self._named_devices["airplay"].off,
            "airplay_volume": self._named_devices["airplay"].set_volume,
            # board control functions
            "off": self._board_control.reset,
            "shutdown": self._board_control.shutdown,
            # YSP volume
            "volume_down": self._volume_control.dec,
            "volume_up": self._volume_control.inc,
            "volume_set": self._volume_control.volume,
        }

    def kb_handlers(self) -> Dict[str, Callable]:
        """Return keys to commands mapping"""
        cmds = self.commands_map()

        return {
            "KEY_KP7": cmds["tv_on"],
            "KEY_KP4": cmds["tv_off"],
            "KEY_KP8": cmds["turntable_on"],
            "KEY_KP5": cmds["turntable_off"],
            "KEY_KP9": cmds["streaming_on"],
            "KEY_KP6": cmds["streaming_off"],
            "KEY_KPMINUS": cmds["printer_on"],
            "KEY_KPPLUS": cmds["printer_off"],
            "KEY_KPENTER": cmds["off"],
            "KEY_KP1": cmds["volume_up"],
            "KEY_KP0": cmds["volume_down"],
            "KEY_ESC": cmds["shutdown"],
        }
