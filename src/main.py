import machine
from ht16k33_matrix import ht16k33_matrix
from max7219_matrix import max7219_matrix
from ws2812b_matrix import ws2812b_matrix
import ntptime
import utime as time
from gurgleapps_webserver import GurgleAppsWebserver
import uasyncio as asyncio
import json

config_file = 'config.json'

# Display modes
DISPLAY_MODE_RAINBOW = 'rainbow'
DISPLAY_MODE_SINGLE_COLOR = 'single_color'
DISPLAY_MODE_COLOR_PER_WORD = 'color_per_word'

current_display_mode = DISPLAY_MODE_RAINBOW

brightness = 2
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
    'h_0': [0x00, 0x00, 0x00, 0x00, 0x00, 0xf6, 0x00, 0x00], # 0 is the same as 12
    'm_5': [0x00, 0xd4, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
    'm_10': [0x00, 0x0d, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
    'm_15': [0x00, 0xef, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
    'm_20': [0x3f, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
    'm_25': [0x3f, 0xd4, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
    'm_30': [0xc0, 0x00, 0xc0, 0x00, 0x00, 0x00, 0x00, 0x00]
}

def read_config():
    try:
        with open(config_file, 'r') as file:
            return json.load(file)
    except (OSError):
        print(f"Configuration file not found or is invalid. Please create a valid {config_file} file.")
        return None

def save_config(data):
    try:
        with open(config_file, 'w') as file:
            json.dump(data, file)
            print("Configuration saved.")
    except OSError as e:
        print(f"Error saving configuration: {e}")

def scan_for_devices():
    i2c = machine.I2C(config['I2C_BUS'], sda=machine.Pin(config['I2C_SDA']), scl=machine.Pin(config['I2C_SCL']))
    time.sleep(1)
    devices = i2c.scan()
    if devices:
        for d in devices:
            print(hex(d))
    else:
        print('no i2c devices')

def sync_ntp_time():
    global time_offset, ntp_synced_at, config
    remember_time = time.localtime()
    ntptime.host = "pool.ntp.org"
    try:
        ntptime.settime()
        ntp_synced_at = time.time()
        config['NTP_SYNCED_AT'] = ntp_synced_at
        save_config(config)
    except OSError:
        print("Error setting time")


def get_corrected_time():
    return time.localtime(time.time() + time_offset)

def set_manual_time(year, month, day, hour, minute, second):
    global time_offset
    current_time = time.localtime()
    current_seconds = time.mktime(current_time)
    manual_seconds = time.mktime((year, month, day, hour, minute, second, 0, 0))
    time_offset = manual_seconds - current_seconds
    config['TIME_OFFSET'] = time_offset
    save_config(config)


def time_to_matrix():
    global colour_per_word_array
    word = [0, 0, 0, 0, 0, 0, 0, 0]
    now = get_corrected_time()
    hour = (now[3])
    minute = now[4]
    colour_per_word_array.clear()
    # round min to nearest 5
    minute = int(round(minute/5)*5)
    if minute > 0 and minute < 30:
        word = merge_chars(word, clockFont['past'])
        colour_per_word_array = merge_color_array(colour_per_word_array, clockFont['past'], past_to_color)
    elif minute == 60:
        if now[4] > 55: # just before the hour
            hour = hour + 1 # round up to next hour
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
    if config['ENABLE_MAX7219']:
        spi_matrix.show_char(word)
    if config['ENABLE_HT16K33']:            
        if not i2c_matrix.show_char(i2c_matrix.reverse_char(word)):
            print("Error writing to matrix")
    if config['ENABLE_WS2812B']:
        ws2812b_matrix.set_brightness(brightness)
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

def set_brightness(new_brightness):
    global brightness
    brightness = new_brightness
    config['BRIGHTNESS'] = brightness
    save_config(config)
    if config['ENABLE_MAX7219']:
        spi_matrix.set_brightness(brightness)
    if config['ENABLE_HT16K33']:
        i2c_matrix.set_brightness(brightness)
    if config['ENABLE_WS2812B']:
        ws2812b_matrix.set_brightness(brightness)

def display_rainbow_mode(word):
    ws2812b_matrix.show_char_with_color_array(word, ws2812b_matrix.get_rainbow_array())

def display_single_color_mode(word):
    ws2812b_matrix.show_char(word, single_color)

def display_color_per_word_mode(word):
    ws2812b_matrix.show_char_with_color_array(word, colour_per_word_array)

async def set_brightness_request(request, response):
    new_brightness = int(request.post_data['brightness'])
    print("Setting brightness to " + str(new_brightness))
    set_brightness(new_brightness)
    time_to_matrix()
    settings = settings_to_json()
    await response.send_json(settings, 200)

async def set_clock_settings_request(request, response):
    global current_display_mode
    global single_color
    global minute_color
    global hour_color
    global past_to_color
    print(request.post_data)
    set_brightness(int(request.post_data['brightness']))
    current_display_mode = request.post_data['display_mode']
    single_color = (int(request.post_data['single_color'][0]), int(request.post_data['single_color'][1]), int(request.post_data['single_color'][2]))
    minute_color = (int(request.post_data['minute_color'][0]), int(request.post_data['minute_color'][1]), int(request.post_data['minute_color'][2]))
    hour_color = (int(request.post_data['hour_color'][0]), int(request.post_data['hour_color'][0]), int(request.post_data['hour_color'][0]))
    past_to_color = (int(request.post_data['past_to_color'][0]), int(request.post_data['past_to_color'][1]), int(request.post_data['past_to_color'][2]))
    config['BRIGHTNESS'] = brightness
    config['DISPLAY_MODE'] = current_display_mode
    config['SINGLE_COLOR'] = single_color
    config['MINUTE_COLOR'] = minute_color
    config['HOUR_COLOR'] = hour_color
    config['PAST_TO_COLOR'] = past_to_color
    save_config(config)
    if request.post_data['timeChanged']:
        time_data = request.post_data['newTime']
        set_manual_time(int(time_data[0]), int(time_data[1]), int(time_data[2]), int(time_data[3]), int(time_data[4]), 0)
    time_to_matrix()
    response_data = {
        'status': 'OK',
        'success': True,
        'message': 'Settings updated',
        'settings': settings_object()
    }
    await response.send_json(json.dumps(response_data), 200)


async def get_clock_settings_request(request, response):
    global current_display_mode
    await response.send_json(settings_to_json())

def settings_object():
    return {
        'brightness': brightness,
        'display_mode': current_display_mode,
        'single_color': single_color,
        'minute_color': minute_color,
        'hour_color': hour_color,
        'past_to_color': past_to_color,
        'time': get_corrected_time(),
        'local_time': time.localtime(),
        'time_offset': time_offset,
        'wifi_connected': server.is_wifi_connected(),
        'wifi_ip_address': server.get_wifi_ip_address(),
        'wifi_ssid': server.get_wifi_ssid(),
        'ap_address': server.get_ap_ip_address(),
        'ap_ssid': server.get_ap_ssid(),
        'ap_active': server.is_access_point_active(),
        'status': 'OK'
    }

def settings_to_json():
    return json.dumps(settings_object())

def setup_routes(server):
    server.add_function_route('/set-brightness', set_brightness_request)
    server.add_function_route('/get-clock-settings', get_clock_settings_request)
    server.add_function_route('/set-clock-settings', set_clock_settings_request)

def connect_to_wifi():
    # Check if Wi-Fi SSID is set and not blank
    wifi_ssid = config.get('WIFI_SSID', '').strip()
    if wifi_ssid:
        # Password could be blank for open networks
        wifi_password = config.get('WIFI_PASSWORD', None)
        print("Connecting to Wi-Fi")
        success = server.connect_wifi(wifi_ssid, wifi_password)
        if success:
            print("Connected to Wi-Fi")
        else:
            print("Failed to connect to Wi-Fi")
        return success
    else:
        print("No Wi-Fi SSID set")
        return False

        
async def main():
    while True:
        time_to_matrix()
        if ntp_synced_at < (time.time() - 3600) and server.is_wifi_connected(): # Sync time every hour
            sync_ntp_time()
        await asyncio.sleep(10)

display_modes = {
    DISPLAY_MODE_RAINBOW: display_rainbow_mode,
    DISPLAY_MODE_SINGLE_COLOR: display_single_color_mode,
    DISPLAY_MODE_COLOR_PER_WORD: display_color_per_word_mode
}

config = read_config()

if config is None:
    raise SystemExit("Stopping execution due to missing configuration.")

brightness = config.get('BRIGHTNESS', 2)
single_color = config.get('SINGLE_COLOR', (0, 0, 255))
minute_color = config.get('MINUTE_COLOR', (0, 255, 0))
hour_color = config.get('HOUR_COLOR', (255, 0, 0))
past_to_color = config.get('PAST_TO_COLOR', (0, 0, 255))
current_display_mode = config.get('DISPLAY_MODE', DISPLAY_MODE_RAINBOW)
time_offset = config.get('TIME_OFFSET', 0)
ntp_synced_at = config.get('NTP_SYNCED_AT', 0)

        
if config['ENABLE_HT16K33']:
    scan_for_devices()
    i2c_matrix = ht16k33_matrix(config['I2C_SDA'], config['I2C_SCL'], config['I2C_BUS'],  int(config['I2C_ADDRESS'], 16))

if config['ENABLE_MAX7219']:
    spi = machine.SPI(config['SPI_PORT'], sck=machine.Pin(config['SPI_SCK']), mosi=machine.Pin(config['SPI_MOSI']))
    spi_matrix = max7219_matrix(spi, machine.Pin(config['SPI_CS'], machine.Pin.OUT, True))
    spi_matrix.set_brightness(17)

if config['ENABLE_WS2812B']:
    ws2812b_matrix = ws2812b_matrix(config['WS2812B_PIN'], 8, 8)
    ws2812b_matrix.set_brightness(1)

server = GurgleAppsWebserver(
    None,
    None,
    port=80,
    timeout=20,
    doc_root="/www",
    log_level=2
)
server.set_default_index_pages(["time.html"])
server.set_cors(True)
setup_routes(server)

connect_to_wifi()
sync_ntp_time()
print("starting access point")
success = server.start_access_point('gurgleapps', 'gurgleapps')
if success:
    print(success)
    asyncio.run(server.start_server_with_background_task(main))
else:
    print("Failed to start access point")
