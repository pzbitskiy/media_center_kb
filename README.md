# Media center controller with a numpad keyboard and Home Assistant integration

## Project goals

To control some connected electronics (soundbar, turntable, preamp, printer, etc) from a physical mini keyboard.
1. Turn on/off printer
2. Turn on/off soundbar + turntable
3. Turn on/off soundbar + select mode for movie watching or music streaming
4. Expose to HomeAssistant as MQTT device(s) to eventually control it via intents.

## Hardware

1. Raspberry Pi 2B
2. Relays controller with 4 relays
3. YSP-4000 soundbar (see [ysp4000 repository](https://github.com/pzbitskiy/yamaha-ysp-4000))
4. Dumb but solid Dell 1700 printer (CUPS + Lexmark E234 PPD)
5. Turntable and preamp

### Keyboard setup

Inspired by this [blog post](https://softsolder.com/2016/03/02/raspberry-pi-usb-keypad-via-evdev/)

```sh
cat /proc/bus/input/devices
```

Take vendor id and product id and created udev rule

```sh
sudo bash -c 'cat > /etc/udev/rules.d/KeyPad.rules << EOF
ATTRS{idVendor}=="04b4", ATTRS{idProduct}=="06b0", SYMLINK+="input/keypad"
EOF'

sudo udevadm control --reload
```

Now the keyboard can be opened as `/dev/input/keypad` device:

```python
keypad = InputDevice('/dev/input/keypad')
```

### Relays, outlets and RPi

See the wiring diagram
![wiring](docs/wiring.png)

## Installation instructions

### Build

```sh
python3 -m build
```

### Install

On the device

```sh
pip3 install --upgrade --user git+https://github.com/pzbitskiy/media_center_kb

# Run in foreground with verbose logging to ensure it works as intended
mediackb -v
```

Create systemd service

```sh
sudo bash -c 'cat > /etc/systemd/system/media-center-kb.service <<EOF
[Unit]
Description=Media center keyboard daemon

[Install]
WantedBy=multi-user.target

[Service]
User=pi
ExecStart=mediackb --mqtt /etc/mcb/mqtt.json
Type=idle
RemainAfterExit=no
Restart=on-failure
EOF'

sudo systemctl daemon-reload
sudo systemctl start media-center-kb
sudo systemctl enable media-center-kb
```

Ensure it is running

```sh
sudo systemctl --type=service --state=running
```

#### Python 3.10 and Raspberry Pi 2B / Raspbian GNU/Linux 11

After installing `python3.10` RPi.GPIO cannot be imported.
Simple fix is to give 3.10 extension assuming there were no extension API change 3.9->3.10:
```sh
sudo cp /usr/lib/python3/dist-packages/RPi/_GPIO.cpython-39-arm-linux-gnueabihf.so \
    /usr/lib/python3/dist-packages/RPi/_GPIO.cpython-310-arm-linux-gnueabihf.so
```

## Development

### Setup
```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[tests]'
# or pip3 install -e -r requirements.txt
```

### Test

```sh
pytest
```

#### HA+MQTT manual testing

```sh
docker run -d \
  --name homeassistant \
  --network=host \
  ghcr.io/home-assistant/home-assistant:stable

docker run -p 1883:1883 -v ./mosquitto.conf:/mosquitto/config/mosquitto.conf eclipse-mosquitto

python src/media_center_kb/main.py --no-kb --no-serial --no-gpio --mqtt mqtt.json
```