

# GurgleApps Color Word Clock

This code is for our [GurgleApps Color Word Clock Kit project.](https://gurgleapps.com/reviews/electronics/wifi-controlled-color-word-clock-kit-micropython) You can buy our kit or make your own, it works with various matrix displays and microcontrollers. It has a web interface to set the time, colors, and other settings.

- [GurgleApps Color Word Clock](#gurgleapps-color-word-clock)
  - [Misc Notes](#misc-notes)
    - [ESP32-C3 super mini pinouts view from top](#esp32-c3-super-mini-pinouts-view-from-top)
    - [Development Environment](#development-environment)


## Misc Notes

### ESP32-C3 super mini pinouts view from top

```
         USB-C Port
          _______
         |       |
GPIO 05 [o]     [o] 5V
GPIO 06 [o]     [o] GND
GPIO 07 [o]     [o] 3V3
GPIO 08 [o]     [o] GPIO 04
GPIO 09 [o]     [o] GPIO 03
GPIO 10 [o]     [o] GPIO 02
GPIO 20 [o]     [o] GPIO 01
GPIO 21 [o]     [o] GPIO 00
         |_______|
```

### Development Environment

Set up test python web server for quick look and feel rather than copying files to the microcontroller repeatedly.

```bash
python3 -m http.server 8000 -d ./src/www
```