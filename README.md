# GurgleApps Color Word Clock

This repository contains the **MicroPython source code** for the GurgleApps WiFi‑Controlled Color Word Clock.  
It runs on multiple boards including **Raspberry Pi Pico W**, **Pico 2 W**, and **ESP32-based boards**, and supports WS2812B / NeoPixel LED matrices.

> **Pico W / Pico 2 W Users:**  
> MicroPython’s built‑in `neopixel` driver is not reliably timed on Pico W / Pico 2 W.  
> Both WiFi interrupts **and** differences in RP2040 / RP2350 timing can cause corrupted colors or flicker.  
> This project therefore uses a fast, stable **PIO NeoPixel driver (`pio_neopixel.py`)** to guarantee perfectly timed LED output.

> **⚠️ Pin Change (v1 → v2):**  
> The default `WS2812B_PIN` in `config.json` changed from **2** to **27**.  
> If you are upgrading from an older version, be sure to update your `config.json` accordingly.

[GurgleApps Color Word Clock](#gurgleapps-color-word-clock)
- [GurgleApps Color Word Clock](#gurgleapps-color-word-clock)
  - [📚 Help Articles](#-help-articles)
  - [✨ Features](#-features)
  - [🚀 Quick Start](#-quick-start)
  - [🧰 Compatibility Notes](#-compatibility-notes)
    - [Raspberry Pi Pico W / Pico 2 W](#raspberry-pi-pico-w--pico-2-w)
    - [ESP32, ESP32‑C3, ESP32‑S2, ESP8266](#esp32-esp32c3-esp32s2-esp8266)
  - [🧩 Hardware Reference](#-hardware-reference)
    - [ESP32‑C3 Super Mini — Pinout (Top View)](#esp32c3-super-mini--pinout-top-view)
  - [🖥 Development Environment](#-development-environment)
  - [🚀 Project Links](#-project-links)


---


## 📚 Help Articles

Click for full build guides and setup instructions:

[<img width="480px" src="https://gurgleapps.com/assets/image-c/6a/6ad8f434848ca3c80c485122c52f9b3c9e1734db.jpg">](https://gurgleapps.com/learn/projects/configuring-wifi-word-clock-software)

[<img width="480px" src="https://gurgleapps.com/assets/image-c/19/19ca210702bff2adc577a6032224d2285e5c9a63-960w.webp">](https://gurgleapps.com/learn/projects/wifi-color-word-clock-instructions)

---

## ✨ Features


The Color Word Clock is designed to be fun, reliable, and easy to customise—whether you're assembling a full kit or building from scratch.

It's also an ideal starter project for makers, students, and hobbyists who want a hands‑on introduction to MicroPython, LEDs, and WiFi‑enabled electronics.

- **Dual Wi-Fi Mode**  
  The clock connects to your home WiFi while also running its own access point, so you can *always* access the admin panel.

- **Web‑Based Control Panel**  
  Adjust brightness, colors, animations, and time settings from your phone or laptop.

- **Customizable Display**  
  Choose color themes, effects, per‑pixel patterns, special modes, and more.

- **Matrix‑Agnostic**  
  Works with many WS2812B matrix sizes (8×8 recommended for classic Word Clock layout).

- **Rock‑Solid LED Output**  
  Uses PIO‑based NeoPixel driver for glitch‑free lighting on Pico W / Pico 2 W.

---

## 🚀 Quick Start

1. **Flash MicroPython**  
   Install the latest MicroPython firmware on your Pico W, Pico 2 W, or ESP32.

2. **Copy the Project Files**  
   Upload all files from the `src` directory to your device using Thonny or `mpremote`.

3. **Edit `config.json`**  
   Set:
   - `WIFI_SSID`
   - `WIFI_PASSWORD`
   - `WS2812B_PIN` (27 for V2 kits and later; 2 for V1 kits) 

4. **Reboot the Board**  
   After restarting, the clock will start automatically.

5. **Connect to the Web Dashboard**  
   Use either:
   - Your home WiFi network if you set it up in `config.json`, or
   - The clock’s built-in AP  
   to open the admin panel in your browser.

---

## 🧰 Compatibility Notes

### Raspberry Pi Pico W / Pico 2 W  
Use the PIO driver:

```
from pio_neopixel import PioNeoMatrix
```

This is a **drop‑in replacement** for `neopixel.NeoPixel`.

### ESP32, ESP32‑C3, ESP32‑S2, ESP8266  
These boards do **not** need the PIO driver.  
You may use the standard MicroPython NeoPixel module:

```
import neopixel
np = neopixel.NeoPixel(machine.Pin(pin), width * height)
```

Edit `ws2812b_matrix.py` accordingly.

---

## 🧩 Hardware Reference

### ESP32‑C3 Super Mini — Pinout (Top View)

```
         USB‑C Port
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

---

## 🖥 Development Environment

For fast UI testing without copying files to the microcontroller repeatedly:

```
python3 -m http.server 8000 -d ./src/www
```

This serves the web interface locally.

---

## 🚀 Project Links

- Word Clock Kit: https://gurgleapps.com/reviews/electronics/wifi-controlled-color-word-clock-kit-micropython  
- MicroPython Web Server Framework: https://github.com/gurgleapps/pico-web-server-control

---

Enjoy building your clock! If you create new animations or improvements, feel free to send a PR.