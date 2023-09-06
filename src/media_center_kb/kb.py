"""
Keyboard related functions: event loop, keycodes, etc

Logged keys, bottom to top:

82 KEY_KP0
51 KEY_COMMA
83 KEY_KPDOT
96 KEY_KPENTER

79 KEY_KP1
80 KEY_KP2
81 KEY_KP3

75 KEY_KP4
76 KEY_KP5
77 KEY_KP6
78 KEY_KPPLUS

71 KEY_KP7
72 KEY_KP8
73 KEY_KP9
74 KEY_KPMINUS

// CLEAR
117 KEY_KPEQUAL
98 KEY_KPSLASH
55 KEY_KPASTERISK

1 KEY_ESC
15 KEY_TAB
14 KEY_BACKSPACE
// FN

udev rule
```sh
cat /etc/udev/rules.d/KeyPad.rules
ATTRS{idVendor}=="04b4", ATTRS{idProduct}=="06b0", SYMLINK+="input/keypad"
```

reload and check
```sh
sudo udevadm control --reload
sudo udevadm trigger
ls -al /dev/input/keypad
```

"""
from typing import Dict, Callable
import logging

from evdev import InputDevice, ecodes, KeyEvent

def kb_event_loop(handlers: Dict[str, Callable]):
    """Start keyboard reading loop and call handlers"""
    keypad = InputDevice('/dev/input/keypad')
    for evt in keypad.read_loop():
        if (evt.type == ecodes.EV_KEY) and (KeyEvent(evt).keystate == 1):  # pylint: disable=no-member
            if KeyEvent(evt).keycode == 'KEY_NUMLOCK':
                continue

            logging.debug('scan: %d, key: %s', KeyEvent(evt).scancode, KeyEvent(evt).keycode)
            handler = handlers.get(KeyEvent(evt).keycode, lambda: None)
            handler()
