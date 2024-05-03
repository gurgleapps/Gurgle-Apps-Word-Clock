import machine
from ht16k33_matrix import ht16k33_matrix
from max7219_matrix import max7219_matrix
from ws2812b_matrix import ws2812b_matrix
import ntptime
import alt_ntptime
import utime as time
from gurgleapps_webserver import GurgleAppsWebserver
import uasyncio as asyncio
import json
import matrix_fonts
import urandom as random
from board import Board
import socket

config_file = 'config.json'

# Display modes
DISPLAY_MODE_RAINBOW = 'rainbow'
DISPLAY_MODE_SINGLE_COLOR = 'single_color'
DISPLAY_MODE_COLOR_PER_WORD = 'color_per_word'
DISPLAY_MODE_RANDOM = 'random'

current_display_mode = DISPLAY_MODE_RAINBOW

disable_access_point = False
brightness = 2
# Color data for different modes
single_color = (0, 0, 255)
# Color data for different words
minute_color = (0, 255, 0)
hour_color = (255, 0, 0)
past_to_color = (0, 0, 255)
# Ready to hold color data for each word
colour_per_word_array = []

last_wifi_connected_time = 0
last_wifi_disconnected_time = 0

ntp_synced_at = 0
# So we don't spam the NTP server
last_ntp_sync_attempt = None
last_dns_check_status = None

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
    'm_30': [0xc0, 0x00, 0xc0, 0x00, 0x00, 0x00, 0x00, 0x00],
    'a_f1': [0x00,0x00,0x00,0x18,0x18,0x00,0x00,0x00],
    'a_f2': [0x00,0x00,0x3c,0x24,0x24,0x3c,0x00,0x00],
    'a_f3': [0x00,0x7e,0x42,0x42,0x42,0x42,0x7e,0x00],
    'a_f4': [0xff,0x81,0x81,0x81,0x81,0x81,0x81,0xff],
    'error': [0xfe,0x62,0x68,0x78,0x68,0x62,0xfe,0x00],
    '0': [0x7c,0xc6,0xce,0xd6,0xe6,0xc6,0x7c,0x00],
    '1': [0x18,0x38,0x18,0x18,0x18,0x18,0x7e,0x00],
    '2': [0x7c,0xc6,0x06,0x1c,0x30,0x66,0xfe,0x00],
    '3': [0x7c,0xc6,0x06,0x3c,0x06,0xc6,0x7c,0x00],
    '4': [0x1c,0x3c,0x6c,0xcc,0xfe,0x0c,0x1e,0x00],
    '5': [0xfe,0xc0,0xc0,0xfc,0x06,0xc6,0x7c,0x00],
    '6': [0x7c,0xc6,0xc0,0xfc,0xc6,0xc6,0x7c,0x00],
    '7': [0xfe,0xc6,0x06,0x0c,0x18,0x18,0x18,0x00],
    '8': [0x7c,0xc6,0xc6,0x7c,0xc6,0xc6,0x7c,0x00],
    '9': [0x7c,0xc6,0xc6,0x7e,0x06,0x0c,0x78,0x00],
    '.': [0x00,0x00,0x00,0x00,0x00,0x18,0x18,0x00],
    'wifi': [0x3c,0x42,0x99,0xa5,0x24,0x00,0x18,0x18],
    'full': [0xff,0xff,0xff,0xff,0xff,0xff,0xff,0xff]
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

def read_temperature():
    # pico only
    if Board().type != Board.BoardType.PICO_W:
        return 0
    reading = machine.ADC(4).read_u16() * 3.3 / 65536
    return 27 - (reading - 0.706) / 0.001721

def test_dns():
    global last_dns_check_status
    try:
        ip = socket.getaddrinfo('www.google.com', 80)
        print("DNS resolution successful, IP:", ip)
        last_dns_check_status = True
    except OSError as e:
        print("DNS resolution failed:", e)
        last_dns_check_status = False
    return last_dns_check_status


async def sync_ntp_time(use_alternative=False, timeout=2.0):
    global ntp_synced_at, last_ntp_sync_attempt, config, last_wifi_connected_time
    ntp_retry_interval = 300
    if last_ntp_sync_attempt and (time.time() - last_ntp_sync_attempt) < ntp_retry_interval:
        print(f"Last NTP sync attempt was less than {ntp_retry_interval} seconds ago.")
        return
    mtp_hosts = ['pool.ntp.org', 'time.nist.gov', 'time.google.com', 'time.windows.com']
    ntptime.timeout = timeout
    for ntp_host in mtp_hosts:
        try:
            if use_alternative:
                alt_ntptime.settime(ntp_host, timeout=timeout)
            else:
                ntptime.host = ntp_host
                ntptime.settime()
            ntp_synced_at = time.time()
            last_wifi_connected_time = time.ticks_ms()
            print(f"Time synced with {ntp_host} successfully using alternative method: {use_alternative}")
            return
        except OSError as e:
            await asyncio.sleep(3)
            print(f"Error syncing time with {ntp_host}: {e} using alternative method.{use_alternative}")
    if not use_alternative:
        print("Standard methods failed, trying alternative methods.")
        await sync_ntp_time(use_alternative=True)
    else:
        # both methods failed
        print(f"Failed to sync time with all NTP servers. DNS check status: {test_dns()}")
        try:
            ntp_test = alt_ntptime.test_ntp_server()
            print(f"NTP test result: {ntp_test}")
        except Exception as e:
            print(f"Failed to test NTP server: {e}")
        try:
            http_time = alt_ntptime.get_time_via_http()
            print(f"HTTP time: {http_time}")
        except Exception as e:
            print(f"Failed to get time via HTTP: {e}")
        if server.is_wifi_connected() and test_dns():
            print('wifi up, dns ok, but still failed to sync time rebooting')
            machine.reset()
    last_ntp_sync_attempt = time.time()


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

def startup_animation():
    indices = list(range(4)) + list(range(2, -1, -1)) + list(range(4))
    for i in indices:
        char = clockFont['a_f'+str(i+1)]
        if config['ENABLE_MAX7219']:
            spi_matrix.show_char(char)
        if config['ENABLE_HT16K33']:
            i2c_matrix.show_char(i2c_matrix.reverse_char(char))
        if config['ENABLE_WS2812B']:
            ws2812b_matrix.show_char_with_color_array(char, ws2812b_matrix.get_rainbow_array())
        time.sleep(0.1)
    test_pattern()

def test_pattern():
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
    for color in colors:
        if config['ENABLE_WS2812B']:
            ws2812b_matrix.show_char(clockFont['full'], color)
        if config['ENABLE_MAX7219']:
            spi_matrix.show_char(clockFont['full'])
        if config['ENABLE_HT16K33']:
            i2c_matrix.show_char(i2c_matrix.reverse_char(clockFont['full']))
        time.sleep(0.5)


async def show_string(string):
    for char in string:
        if config['ENABLE_MAX7219']:
            spi_matrix.show_char(clockFont[char])
        if config['ENABLE_HT16K33']:
            i2c_matrix.show_char(i2c_matrix.reverse_char(clockFont[char]))
        if config['ENABLE_WS2812B']:
            ws2812b_matrix.show_char_with_color_array(clockFont[char], ws2812b_matrix.get_rainbow_array())
        await asyncio.sleep(0.5)

async def scroll_message(font, message='hello', delay=0.1):
    message += '  '  # Add extra space for a clear end.
    for char_pos in range(len(message)-1):  # Adjust for loop to avoid IndexError
        char = font[message[char_pos]]
        next_char = font[message[char_pos + 1]]
        for shift in range(8):
            # Initialize a new character representation for the shift
            shifted_char = []
            for row in range(len(char)):
                # Shift current row and add part of the next row
                current_row = char[row] << 1
                next_row = next_char[row] >> (7 - shift) if row < len(next_char) else 0
                # Combine the bits from current and next character rows
                shifted_row = current_row & 0xFF | next_row
                shifted_char.append(shifted_row)
            
            # Display logic for different display types
            if config['ENABLE_MAX7219']:
                spi_matrix.show_char(shifted_char)
            if config['ENABLE_HT16K33']:
                i2c_matrix.show_char(i2c_matrix.reverse_char(shifted_char))
            if config['ENABLE_WS2812B']:
                ws2812b_matrix.show_char_with_color_array(shifted_char, ws2812b_matrix.get_rainbow_array())
            
            await asyncio.sleep(delay)

            # Update char to the newly shifted_char for the next iteration
            char = shifted_char


def show_char(char):
    if config['ENABLE_MAX7219']:
        spi_matrix.show_char(char)
    if config['ENABLE_HT16K33']:
        i2c_matrix.show_char(i2c_matrix.reverse_char(char))
    if config['ENABLE_WS2812B']:
        ws2812b_matrix.show_char(char)


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

def display_random_mode(word):
    random_array = ws2812b_matrix.get_rainbow_array()
    for i in range(len(random_array)):
        j = random.randint(0, len(random_array) - 1)
        random_array[i], random_array[j] = random_array[j], random_array[i]
    ws2812b_matrix.show_char_with_color_array(word, random_array)

def display_single_color_mode(word):
    ws2812b_matrix.show_char(word, single_color)

def display_color_per_word_mode(word):
    ws2812b_matrix.show_char_with_color_array(word, colour_per_word_array)

def webserver_event_handler(event):
    global last_wifi_connected_time, last_wifi_disconnected_time
    if event['event'] == GurgleAppsWebserver.EVENT_WIFI_CONNECTED:
        last_wifi_connected_time = time.ticks_ms()
        print("E: Wi-Fi connected")
    elif event['event'] == GurgleAppsWebserver.EVENT_WIFI_DISCONNECTED:
        last_wifi_disconnected_time = time.ticks_ms()
        print("E: Wi-Fi disconnected")

async def set_brightness_request(request, response):
    new_brightness = int(request.post_data['brightness'])
    print("Setting brightness to " + str(new_brightness))
    set_brightness(new_brightness)
    time_to_matrix()
    settings = settings_to_json()
    await response.send_json(settings, 200)

async def set_wifi_settings_request(request, response):
    global config
    print(request.post_data)
    wifi_ssid = request.post_data['wifi_ssid']
    wifi_password = request.post_data['wifi_password']
    config['WIFI_SSID'] = wifi_ssid
    config['WIFI_PASSWORD'] = wifi_password
    save_config(config)
    response_data = {
        'status': 'OK',
        'success': True,
        'message': 'Updated Wi-Fi',
        'settings': settings_object()
    }
    asyncio.create_task(connect_to_wifi())
    await response.send_json(json.dumps(response_data), 200)

async def disable_access_point_request(request, response):
    global disable_access_point
    disable_access_point = True
    config['DISABLE_ACCESS_POINT'] = True
    save_config(config)
    response_data = {
        'status': 'OK',
        'success': True,
        'message': 'Access Point disabled',
        'settings': settings_object()
    }
    await response.send_json(json.dumps(response_data), 200)

async def enable_access_point_request(request, response):
    global disable_access_point
    disable_access_point = False
    config['DISABLE_ACCESS_POINT'] = False
    save_config(config)
    response_data = {
        'status': 'OK',
        'success': True,
        'message': 'Access Point enabled',
        'settings': settings_object()
    }
    await response.send_json(json.dumps(response_data), 200)

async def set_time_request(request, response):
    print(request.post_data)
    time_data = request.post_data['time']
    set_manual_time(int(time_data[0]), int(time_data[1]), int(time_data[2]), int(time_data[3]), int(time_data[4]), 0)
    time_to_matrix()
    response_data = {
        'status': 'OK',
        'success': True,
        'message': 'Time updated',
        'settings': settings_object()
    }
    await response.send_json(json.dumps(response_data), 200)

async def test_pattern_request(request, response):
    response_data = {
        'status': 'OK',
        'success': True,
        'message': 'Test pattern started',
    }
    await response.send_json(json.dumps(response_data), 200)
    test_pattern()

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
    hour_color = (int(request.post_data['hour_color'][0]), int(request.post_data['hour_color'][1]), int(request.post_data['hour_color'][2]))
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
    global ntp_synced_at, last_ntp_sync_attempt
    return {
        'brightness': brightness,
        'display_mode': current_display_mode,
        'single_color': single_color,
        'minute_color': minute_color,
        'hour_color': hour_color,
        'past_to_color': past_to_color,
        'time': get_corrected_time(),
        'local_time': time.localtime(),
        'unix_time': time.time(),
        'time_offset': time_offset,
        'wifi_connected': server.is_wifi_connected(),
        'wifi_ip_address': server.get_wifi_ip_address(),
        'wifi_ssid': server.get_wifi_ssid(),
        'ap_address': server.get_ap_ip_address(),
        'ap_ssid': server.get_ap_ssid(),
        'ap_active': server.is_access_point_active(),
        'cpu_temp': read_temperature(),
        'ntp_synced_at': ntp_synced_at,
        'last_ntp_sync_attempt': last_ntp_sync_attempt,
        'dns_check_status': last_dns_check_status,
        'disable_access_point': disable_access_point,
        'status': 'OK'
    }

def settings_to_json():
    return json.dumps(settings_object())

def setup_routes(server):
    server.add_function_route('/set-brightness', set_brightness_request)
    server.add_function_route('/get-clock-settings', get_clock_settings_request)
    server.add_function_route('/set-clock-settings', set_clock_settings_request)
    server.add_function_route('/set-wifi-settings', set_wifi_settings_request)
    server.add_function_route('/set-time', set_time_request)
    server.add_function_route('/test-pattern', test_pattern_request)
    server.add_function_route('/disable-access-point', disable_access_point_request)
    server.add_function_route('/enable-access-point', enable_access_point_request)

async def connect_to_wifi():
    await scroll_message(matrix_fonts.textFont1, "Wifi", 0.05)
    if config['ENABLE_WS2812B']:
        ws2812b_matrix.show_char_with_color_array(clockFont['wifi'], ws2812b_matrix.get_rainbow_array())
    else:
        show_char(clockFont['wifi'])
    # Check if Wi-Fi SSID is set and not blank
    wifi_ssid = config.get('WIFI_SSID', '').strip()
    if wifi_ssid:
        # Password could be blank for open networks
        wifi_password = config.get('WIFI_PASSWORD', None)
        print("Connecting to Wi-Fi")
        await server.connect_wifi(wifi_ssid, wifi_password)
        if server.is_wifi_connected():
            print(f"Connected to Wi-Fi ip: {server.get_wifi_ip_address()}")
            await show_string(server.get_wifi_ip_address())
            await scroll_message(matrix_fonts.textFont1, server.get_wifi_ip_address(), 0.05)
            return True
        else:
            print("Failed to connect to Wi-Fi")
            return False
    else:
        print("No Wi-Fi SSID set")
        return False

        
async def main():
    global ntp_synced_at, last_wifi_connected_time, last_wifi_disconnected_time, disable_access_point
    ap_connnected = False
    await connect_to_wifi()
    if not server.is_wifi_connected() and not disable_access_point:
        ap_connnected = server.start_access_point('gurgleapps', 'gurgleapps')
        await scroll_message(matrix_fonts.textFont1, "No Wi-Fi", 0.05)
    print("Access Point active: " + str(ap_connnected)) 
    while True:
        if server.is_access_point_active():
            if server.is_wifi_connected():
                delta = time.ticks_diff(time.ticks_ms(), last_wifi_connected_time)
                print("Connected to Wi-Fi for " + str(delta // 1000) + " seconds")
                if delta > 10:
                    server.stop_access_point() # Stop access point after 10 seconds of Wi-Fi connection
                    print("Access Point stopped")
        if not server.is_wifi_connected() and not disable_access_point:
            if not server.is_access_point_active():
                delta = time.ticks_diff(time.ticks_ms(), last_wifi_disconnected_time)
                print("Disconnected from Wi-Fi for " + str(delta // 1000) + " seconds")
                if delta > 60: # Start access point after 60 seconds of Wi-Fi disconnection
                    ap_connnected = server.start_access_point('gurgleapps', 'gurgleapps')
                    print("Access Point started: " + str(ap_connnected))
        time_to_matrix()
        if ntp_synced_at < (time.time() - 3600) and server.is_wifi_connected(): # Sync time every hour
            await sync_ntp_time()
        await asyncio.sleep(10)

display_modes = {
    DISPLAY_MODE_RAINBOW: display_rainbow_mode,
    DISPLAY_MODE_SINGLE_COLOR: display_single_color_mode,
    DISPLAY_MODE_COLOR_PER_WORD: display_color_per_word_mode,
    DISPLAY_MODE_RANDOM: display_random_mode
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
disable_access_point = config.get('DISABLE_ACCESS_POINT', False)

        
if config['ENABLE_HT16K33']:
    scan_for_devices()
    i2c_matrix = ht16k33_matrix(config['I2C_SDA'], config['I2C_SCL'], config['I2C_BUS'],  int(config['I2C_ADDRESS'], 16))

if config['ENABLE_MAX7219']:
    spi = machine.SPI(config['SPI_PORT'], sck=machine.Pin(config['SPI_SCK']), mosi=machine.Pin(config['SPI_MOSI']))
    spi_matrix = max7219_matrix(spi, machine.Pin(config['SPI_CS'], machine.Pin.OUT, True))
    spi_matrix.set_brightness(17)

if config['ENABLE_WS2812B']:
    ws2812b_matrix = ws2812b_matrix(config['WS2812B_PIN'], 8, 8)
    ws2812b_matrix.set_brightness(brightness)

startup_animation()

server = GurgleAppsWebserver(
    port=80,
    timeout=20,
    doc_root="/www",
    log_level=2
)
server.add_event_listener(webserver_event_handler)
server.set_default_index_pages(["time.html"])
server.set_cors(True)
setup_routes(server)

asyncio.run(server.start_server_with_background_task(main))

