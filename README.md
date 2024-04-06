

# GurgleApps Color Word Clock

This code is for our [GurgleApps Color Word Clock Kit project.](https://gurgleapps.com/reviews/electronics/wifi-controlled-color-word-clock-kit-micropython) You can buy our kit or make your own, it works with various matrix displays and microcontrollers. It has a web interface to set the time, colors, and other settings.

- [GurgleApps Color Word Clock](#gurgleapps-color-word-clock)
  - [Help Articles](#help-articles)
  - [Features](#features)
  - [Misc Notes](#misc-notes)
    - [ESP32-C3 super mini pinouts view from top](#esp32-c3-super-mini-pinouts-view-from-top)
    - [Development Environment](#development-environment)

## Help Articles

[<img width="480px" src="https://gurgleapps.com/assets/image-c/6a/6ad8f434848ca3c80c485122c52f9b3c9e1734db.jpg">](https://gurgleapps.com/learn/projects/configuring-wifi-word-clock-software)

[<img width="480px" src="https://gurgleapps.com/assets/image-c/19/19ca210702bff2adc577a6032224d2285e5c9a63-960w.webp">](https://gurgleapps.com/learn/projects/wifi-color-word-clock-instructions)

## Features

- Based on our [MicroPython Web Server](https://github.com/gurgleapps/pico-web-server-control).
- Dual WiFi Mode: The Word Clock can connect to your home network while also creating its own access point. This ensures you can always manage your clock, even if it's disconnected from the home network.
- Customizable Display: Through the admin panel, adjust settings like brightness, color, and display mode to match your style or mood.
- Seamless Integration: Easily connect the Word Clock to your home WiFi for uninterrupted functionality.
- Full Control: The admin panel gives you full control over customization and settings, allowing for a truly personalized experience.

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