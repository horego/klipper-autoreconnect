# Klipper auto reconnect
Allows you to automatically reconnect your klipper system when using usb cable.
## Klipper / RPI Host / USB
Since klipper can be used within different circumstances i'm trying to descibe my setup and usecase first.

My printer is have a mks robin nano 1.2 board with a raspberry pi 3b being connected via usb. The raspberry itself have a separate power supply. So i can turn the printer and the rpi off and on independently.

### Usecase turning printer off/on
When i turn the printer off and on again klipper should automatically reconnect. Because i don't want to click restart and or restart firmware manually.

### Usecase plug/unplug usb cable
When unplugging the usb cable and plugging it back in again  klipper should automatically reconnect. Because i don't want to click restart and or restart firmware manually.

### Problem with existing solutions
I created this repository because i had problems with the solution being mentioned on the klipper repo to automatically reconnect klipper when the printer is being connected to the rpi with usb cable
https://github.com/Klipper3d/klipper/issues/835. restart is not working and i also ran into problems when executing a script within a udev rule.

# Installation
## Requirements
Install the at scheduler and ensure python (python3) is installed.
 ```
apt-get install at
 ```
Copy the files `reconnect-klipper.py` and `99-klipper.rules` to your host system.

## Setup

### Configuration

Inside `99-klipper.rules` you need to adjust the value of
* idVendor `1a86`,
* idProduct `7523`,
* path of the script `/home/pi/reconnect-klipper.py` and the
* base url `http://localhost:7125` of moonraker.

To determine the idVendor and idProduct you can use `lsusb` command. Lsusb is also described here [Klipper Issue 835](https://github.com/Klipper3d/klipper/issues/835).

```
SUBSYSTEM=="usb", ATTRS{idVendor}=="1a86", ATTRS{idProduct}=="7523", ACTION=="add", RUN+="/bin/bash -c '/bin/echo \"/bin/python /home/pi/reconnect-klipper.py http://localhost:7125\" | at now'"

```

### Installation

Copy `reconnect-klipper.py` script in your home folder. Any other accessible path can also be fine.

Copy `99-klipper.rules` into `/etc/udev/rules.d/` and reload rules.
```
sudo cp ./99-klipper.rules /etc/udev/rules.d/99-klipper.rules
sudo udevadm control --reload-rules
```
This should do the trick. If you have problems try rebooting your klipper host or run `reonnect-klipper.py` manually by calling python reconnect-klipper.py.

## Additional notes
With my mks robin nano 1.2 board i also run into a problem where the `save&restart` functionality after editing printer.cfg was not working. I always ended up with the error message telling me i need to restart firmware. Adding the line `restart_method: command` to [mcu] section solved the problem for me.

This might not apply for your setup. But when you run into problems (also applies for this script) just give this a try.

```
[mcu]
serial: /dev/serial/by-id/usb-xxx_USB_Serial-if00-port0
restart_method: command

[mcu rpi]
serial: /tmp/klipper_host_mcu

```
