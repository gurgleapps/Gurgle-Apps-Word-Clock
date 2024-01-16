import config
import machine
from ht16k33_matrix import ht16k33_matrix
from max7219_matrix import max7219_matrix
import ntptime
import utime as time
from gurgleapps_webserver import GurgleAppsWebserver
import uasyncio as asyncio

clockFont={
    'past':[0x00,0x00,0x1e,0x00,0x00,0x00,0x00,0x00],
    'to':[0x00,0x00,0x03,0x00,0x00,0x00,0x00,0x00],
    'h_1':[0x00,0x00,0x00,0x00,0xe0,0x00,0x00,0x00],
    'h_2':[0x00,0x00,0x00,0x00,0x00,0xc0,0x40,0x00],
    'h_3':[0x00,0x00,0x00,0x00,0x1f,0x00,0x00,0x00],
    'h_4':[0x00,0x00,0x00,0x00,0x00,0x00,0xf0,0x00],
    'h_5':[0x00,0x00,0x00,0x00,0x00,0x00,0x0f,0x00],
    'h_6':[0x00,0x00,0x00,0x00,0x00,0x00,0x00,0xe0],
    'h_7':[0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x1f],
    'h_8':[0x00,0x00,0x00,0x1f,0x00,0x00,0x00,0x00],
    'h_9':[0x00,0x00,0x00,0xf0,0x00,0x00,0x00,0x00],
    'h_10':[0x00,0x00,0x00,0x01,0x01,0x01,0x00,0x00],
    'h_11':[0x00,0x00,0x00,0x00,0x00,0x3f,0x00,0x00],
    'h_12':[0x00,0x00,0x00,0x00,0x00,0xf6,0x00,0x00],
    'm_5':[0x00,0xd4,0x00,0x00,0x00,0x00,0x00,0x00],
    'm_10':[0x00,0x0d,0x00,0x00,0x00,0x00,0x00,0x00],
    'm_15':[0x00,0xef,0x00,0x00,0x00,0x00,0x00,0x00],
    'm_20':[0x3f,0x00,0x00,0x00,0x00,0x00,0x00,0x00],
    'm_25':[0x3f,0xd4,0x00,0x00,0x00,0x00,0x00,0x00],
    'm_30':[0xc0,0x00,0xc0,0x00,0x00,0x00,0x00,0x00]
            }

def scan_for_devices():
    i2c = machine.I2C(config.I2C_BUS,sda=machine.Pin(config.I2C_SDA),scl=machine.Pin(config.I2C_SCL))
    devices = i2c.scan()
    if devices:
        for d in devices:
            print(hex(d))
    else:
        print('no i2c devices')

def set_time():
    ntptime.host = "pool.ntp.org"
    try:
        ntptime.settime()
    except OSError:
        print("Error setting time")

def time_to_matrix():
    word = [0,0,0,0,0,0,0,0]
    now = time.localtime()
    hour = (now[3])
    minute = now[4]
    # round min to nearest 5
    minute = int(round(minute/5)*5)
    if minute>0 and minute<30:
        word = merge_chars(word,clockFont['past'])
    elif minute==60:
        pass #on the hour
    elif minute>30:
        word = merge_chars(word,clockFont['to'])
        hour = hour+1
    hour = hour%12
    word = merge_chars(word,clockFont['h_'+str(hour)])
    if minute>30:
        minute = 60-minute
    if minute>0:
        word = merge_chars(word,clockFont['m_'+str(minute)])
    if config.ENABLE_MAX7219:
        spi_matrix.show_char(word)
    if config.ENABLE_HT16K33:            
        if not i2c_matrix.show_char(i2c_matrix.reverse_char(word)):
            print("Error writing to matrix")

def merge_chars(char1,char2):
    for i in range(8):
        char1[i] |= char2[i]
    return char1   

async def main():
    while True:
        time_to_matrix()
        await asyncio.sleep(10)
        
if config.ENABLE_HT16K33:
    scan_for_devices()
    i2c_matrix = ht16k33_matrix(config.I2C_SDA,config.I2C_SCL,config.I2C_BUS,config.I2C_ADDRESS)

if config.ENABLE_MAX7219:
    spi_matrix = max7219_matrix(machine.SPI(config.SPI_PORT), machine.Pin(config.SPI_CS))

set_time()

server = GurgleAppsWebserver(
    None,
    None,
    port=80,
    timeout=20,
    doc_root="/www",
    log_level=2
)
server.set_default_index_pages(["time.html"])
success = server.start_access_point('gurgleapps','gurgleapps')
if success:
    print(success)
    asyncio.run(server.start_server_with_background_task(main))
else:
    print("Failed to start access point")
