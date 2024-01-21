To Edit Font this is very a good tool

https://www.glyphrstudio.com/v2/app/


Hardest part was figuring SPI Port, MOSI and CLK on ESP32-C3 super mini pinouts online were incorrect

```python
import machine
machine.SPI(1)
```

prints 

```python
SPI(id=1, baudrate=500000, polarity=0, phase=0, bits=8, firstbit=0, sck=6, mosi=7, miso=2)
```

Since found out you can pick the SPI pins 

```python
spi =machine.SPI(1, sck=machine.Pin(20), mosi=machine.Pin(21))
```

so we know that SPI Port is 1, MOSI is 7 and CLK is 6

I2C sda was GPIO6 and clk was GPIO7