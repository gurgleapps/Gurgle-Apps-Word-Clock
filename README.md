





## ESP32-C3 super mini pinouts view from top

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

## Development Environment

Set up test python web server for quick look and feel rather than copying files to the microcontroller repeatedly.

```bash
python3 -m http.server 8000 -d ./src/www
```


