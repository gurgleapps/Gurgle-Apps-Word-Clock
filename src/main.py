import machine
import config
from ht16k33_matrix import ht16k33_matrix
from max7219_matrix import max7219_matrix
from ws2812b_matrix import ws2812b_matrix
import ntptime
import utime as time
from gurgleapps_webserver import GurgleAppsWebserver
import uasyncio as asyncio

# Display modes
DISPLAY_MODE_RAINBOW = 'rainbow'
DISPLAY_MODE_SINGLE_COLOR = 'single_color'
DISPLAY_MODE_COLOR_PER_WORD = 'color_per_word'

current_display_mode = DISPLAY_MODE_COLOR_PER_WORD

# Color data for different modes
single_color = (0, 0, 255)
# Color data for different words
minute_color = (0, 255, 0)
hour_color = (255, 0, 0)
past_to_color = (0, 0, 255)
# Ready to hold color data for each word
colour_per_word_array = []

clockFont = {
    'past': [0x00, 0x00, 0x1e, 0x00, 0x00, 0x00, 0x00, 0x00],
    'to': [0x00, 0x00, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00],
    'h_1': [0x00, 0x00, 0x00, 0x00, 0xe0, 0x00, 0x00, 0x00],
    'h_2': [0x00, 0x00, 0x00, 0x00, 0x00, 0xc0, 0x40, 0x00],
    'h_3': [0x00, 0x00, 0x00, 0x00, 0x1f, 0x00, 0x00, 0x00],
    'h_4': [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xf0, 0x00],
    'h_5': [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x0f, 0x00],
    'h_6': [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xe0],
    'h_7': [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x1f],
    'h_8': [0x00, 0x00, 0x00, 0x1f, 0x00, 0x00, 0x00, 0x00],
    'h_9': [0x00, 0x00, 0x00, 0xf0, 0x00, 0x00, 0x00, 0x00],
    'h_10': [0x00, 0x00, 0x00, 0x01, 0x01, 0x01, 0x00, 0x00],
    'h_11': [0x00, 0x00, 0x00, 0x00, 0x00, 0x3f, 0x00, 0x00],
    'h_12': [0x00, 0x00, 0x00, 0x00, 0x00, 0xf6, 0x00, 0x00],
    'm_5': [0x00, 0xd4, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
    'm_10': [0x00, 0x0d, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
    'm_15': [0x00, 0xef, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
    'm_20': [0x3f, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
    'm_25': [0x3f, 0xd4, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
    'm_30': [0xc0, 0x00, 0xc0, 0x00, 0x00, 0x00, 0x00, 0x00]
}

def scan_for_devices():
    i2c = machine.I2C(config.I2C_BUS, sda=machine.Pin(config.I2C_SDA), scl=machine.Pin(config.I2C_SCL))
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
    global colour_per_word_array
    word = [0, 0, 0, 0, 0, 0, 0, 0]
    now = time.localtime()
    hour = (now[3])
    minute = now[4]
    colour_per_word_array.clear()
    # round min to nearest 5
    minute = int(round(minute/5)*5)
    if minute > 0 and minute < 30:
        word = merge_chars(word, clockFont['past'])
        colour_per_word_array = merge_color_array(colour_per_word_array, clockFont['past'], past_to_color)
    elif minute == 60:
        pass  # on the hour
    elif minute > 30:
        word = merge_chars(word, clockFont['to'])
        colour_per_word_array = merge_color_array(colour_per_word_array, clockFont['to'], past_to_color)
        hour = hour + 1
    hour = hour % 12
    word = merge_chars(word, clockFont['h_'+str(hour)])
    colour_per_word_array = merge_color_array(colour_per_word_array, clockFont['h_'+str(hour)], hour_color)
    if minute > 30:
        minute = 60 - minute
    if minute > 0:
        word = merge_chars(word, clockFont['m_'+str(minute)])
        colour_per_word_array = merge_color_array(colour_per_word_array, clockFont['m_'+str(minute)], minute_color)
    if config.ENABLE_MAX7219:
        spi_matrix.show_char(word)
    if config.ENABLE_HT16K33:            
        if not i2c_matrix.show_char(i2c_matrix.reverse_char(word)):
            print("Error writing to matrix")
    if config.ENABLE_WS2812B:
        display_fuction = display_modes.get(current_display_mode)
        if display_fuction:
            display_fuction(word)

def merge_chars(char1, char2):
    for i in range(8):
        char1[i] |= char2[i]
    return char1

def merge_color_array(color_array, char, color):
    for i in range(8):
        for j in range(8):
            if char[i] & (1 << (7 - j)):
                while len(color_array) <= i * 8 + j:
                    color_array.append((0, 0, 0))  # Fill with default color
                color_array[i * 8 + j] = color
    return color_array


def display_rainbow_mode(word):
    ws2812b_matrix.show_char_with_color_array(word, ws2812b_matrix.get_rainbow_array())

def display_single_color_mode(word):
    ws2812b_matrix.show_char(word, single_color)

def display_color_per_word_mode(word):
    ws2812b_matrix.show_char_with_color_array(word, colour_per_word_array)

display_modes = {
    DISPLAY_MODE_RAINBOW: display_rainbow_mode,
    DISPLAY_MODE_SINGLE_COLOR: display_single_color_mode,
    DISPLAY_MODE_COLOR_PER_WORD: display_color_per_word_mode
}

async def main():
    while True:
        time_to_matrix()
        await asyncio.sleep(10)
        
if config.ENABLE_HT16K33:
    scan_for_devices()
    i2c_matrix = ht16k33_matrix(config.I2C_SDA, config.I2C_SCL, config.I2C_BUS, config.I2C_ADDRESS)

if config.ENABLE_MAX7219:
    spi = machine.SPI(1, sck=machine.Pin(config.SPI_SCK), mosi=machine.Pin(config.SPI_MOSI))
    spi_matrix = max7219_matrix(spi, machine.Pin(config.SPI_CS, machine.Pin.OUT, True))
    spi_matrix.set_brightness(17)

if config.ENABLE_WS2812B:
    ws2812b_matrix = ws2812b_matrix(config.WS2812B_PIN, 8, 8)
    ws2812b_matrix.set_brightness(1)

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
success = server.start_access_point('gurgleapps', 'gurgleapps')
if success:
    print(success)
    asyncio.run(server.start_server_with_background_task(main))
else:
    print("Failed to start access point")
