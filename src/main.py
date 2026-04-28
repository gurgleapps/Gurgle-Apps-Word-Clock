import machine
from ht16k33_matrix import ht16k33_matrix as HT16K33Matrix
from max7219_matrix import max7219_matrix as MAX7219Matrix
from ws2812b_matrix import ws2812b_matrix as WS2812BMatrix
import ntptime
import alt_ntptime
import utime as time
from gurgleapps_webserver import GurgleAppsWebserver
import uasyncio as asyncio
import json
import gc
import matrix_fonts
import urandom as random
import os
from board import Board
import socket
import scene_manager
import schedule_manager
import time_sync
import rainbow_cycle
from matrix_rain import (
    MATRIX_RAIN_DEFAULT_AFFECT_TIME,
    MATRIX_RAIN_DEFAULT_BACKGROUND_COLOR,
    MATRIX_RAIN_DEFAULT_HOUR_COLOR,
    MATRIX_RAIN_DEFAULT_MINUTE_COLOR,
    MATRIX_RAIN_DEFAULT_PAST_TO_COLOR,
    MATRIX_RAIN_DEFAULT_SPAWN_RATE,
    MATRIX_RAIN_DEFAULT_SPEED_MS,
    MATRIX_RAIN_DEFAULT_TIME_BRIGHTNESS_CAP,
    MATRIX_RAIN_DEFAULT_TRAIL_LENGTH,
    MATRIX_RAIN_DEFAULT_WHITE_HEAD,
    MatrixRainState,
    render as render_matrix_rain_frame,
)
from rainbow_cycle import (
    RAINBOW_CYCLE_DEFAULT_SPEED_MS,
    RAINBOW_CYCLE_DEFAULT_SPREAD,
    RAINBOW_CYCLE_DEFAULT_STEP,
    RAINBOW_CYCLE_DEFAULT_STYLE,
    RAINBOW_CYCLE_MAX_SPEED_MS,
    RAINBOW_CYCLE_MAX_SPREAD,
    RAINBOW_CYCLE_MAX_STEP,
    RAINBOW_CYCLE_MIN_SPEED_MS,
    RAINBOW_CYCLE_MIN_SPREAD,
    RAINBOW_CYCLE_MIN_STEP,
    RainbowCycleState,
    render as render_rainbow_cycle_frame,
)

config_file = 'config.json'
scenes_file = 'scenes.json'
default_scenes_file = 'default_scenes.json'
schedules_file = 'schedules.json'

# Display modes
DISPLAY_MODE_RAINBOW = 'rainbow'
DISPLAY_MODE_RAINBOW_CYCLE = 'rainbow_cycle'
DISPLAY_MODE_SINGLE_COLOR = 'single_color'
DISPLAY_MODE_COLOR_PER_WORD = 'color_per_word'
DISPLAY_MODE_RANDOM = 'random'
DISPLAY_MODE_MATRIX_RAIN = 'matrix_rain'
MAX_BRIGHTNESS = 15
SCHEDULE_ACTION_TYPES = ('display_on', 'display_off', 'set_brightness', 'apply_scene')
WEEKDAY_NAMES = ('mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun')
MAIN_LOOP_SLEEP_SECONDS = 1
ANIMATION_IDLE_SLEEP_MS = 250
NTP_SYNC_INTERVAL_SECONDS = 3600
NTP_RETRY_INTERVAL_SECONDS = 300
NTP_INITIAL_DELAY_AFTER_WIFI_CONNECT_MS = 5_000
ACCESS_POINT_STOP_DELAY_MS = 10_000
ACCESS_POINT_START_DELAY_MS = 60_000
DISPLAY_MODE_REFRESH_MS = {
    DISPLAY_MODE_RANDOM: 10_000
}

SCENE_MODE_FIELDS = {
    DISPLAY_MODE_RAINBOW: (),
    DISPLAY_MODE_RAINBOW_CYCLE: (),
    DISPLAY_MODE_SINGLE_COLOR: ('single_color',),
    DISPLAY_MODE_COLOR_PER_WORD: ('minute_color', 'hour_color', 'past_to_color'),
    DISPLAY_MODE_RANDOM: (),
    DISPLAY_MODE_MATRIX_RAIN: (
        'matrix_rain_minute_color',
        'matrix_rain_hour_color',
        'matrix_rain_past_to_color',
        'matrix_rain_background_color'
    )
}

class AppState:
    def __init__(self):
        self.brightness = 2
        self.display_enabled = True
        self.current_display_mode = DISPLAY_MODE_RAINBOW
        self.current_scene_name = None
        self.last_display_minute_key = None
        self.last_dynamic_display_update_ms = None
        self.rainbow_cycle_style = RAINBOW_CYCLE_DEFAULT_STYLE
        self.rainbow_cycle_speed_ms = RAINBOW_CYCLE_DEFAULT_SPEED_MS
        self.rainbow_cycle_spread = RAINBOW_CYCLE_DEFAULT_SPREAD
        self.rainbow_cycle_step = RAINBOW_CYCLE_DEFAULT_STEP
        self.rainbow_cycle_state = RainbowCycleState()
        self.matrix_rain_minute_color = MATRIX_RAIN_DEFAULT_MINUTE_COLOR
        self.matrix_rain_hour_color = MATRIX_RAIN_DEFAULT_HOUR_COLOR
        self.matrix_rain_past_to_color = MATRIX_RAIN_DEFAULT_PAST_TO_COLOR
        self.matrix_rain_background_color = MATRIX_RAIN_DEFAULT_BACKGROUND_COLOR
        self.matrix_rain_white_head = MATRIX_RAIN_DEFAULT_WHITE_HEAD
        self.matrix_rain_affect_time = MATRIX_RAIN_DEFAULT_AFFECT_TIME
        self.matrix_rain_speed_ms = MATRIX_RAIN_DEFAULT_SPEED_MS
        self.matrix_rain_spawn_rate = MATRIX_RAIN_DEFAULT_SPAWN_RATE
        self.matrix_rain_trail_length = MATRIX_RAIN_DEFAULT_TRAIL_LENGTH
        self.matrix_rain_time_brightness_cap = MATRIX_RAIN_DEFAULT_TIME_BRIGHTNESS_CAP
        self.matrix_rain_state = MatrixRainState()

disable_access_point = False
# Color data for different modes
single_color = (0, 0, 255)
# Color data for different words
minute_color = (0, 255, 0)
hour_color = (255, 0, 0)
past_to_color = (0, 0, 255)
# Ready to hold color data for each word
colour_per_word_array = []
app_state = AppState()

last_wifi_connected_time = 0
last_wifi_disconnected_time = 0

ntp_synced_at = 0
# So we don't spam the NTP server
last_ntp_sync_attempt = None
last_dns_check_status = None
last_schedule_evaluation_key = None
valid_schedules = []
spi_matrix = None
i2c_matrix = None
ws2812b_matrix = None

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

def log_boot(message):
    print("[BOOT] " + message)

def log_scene(message):
    print("[SCENE] " + message)

def log_schedule(message):
    print("[SCHEDULE] " + message)

def enabled_display_backends():
    backends = []
    if config.get('ENABLE_WS2812B'):
        backends.append('WS2812B')
    if config.get('ENABLE_HT16K33'):
        backends.append('HT16K33')
    if config.get('ENABLE_MAX7219'):
        backends.append('MAX7219')
    if not backends:
        backends.append('none')
    return ', '.join(backends)

def log_boot_summary():
    uname = os.uname()
    wifi_ssid = config.get('WIFI_SSID', '').strip()
    log_boot("Board: " + uname.machine)
    log_boot("Runtime: " + uname.sysname)
    log_boot("Displays: " + enabled_display_backends())
    log_boot("Display mode: " + str(app_state.current_display_mode) + ", brightness: " + str(app_state.brightness))
    log_boot("Time offset: " + str(get_total_time_offset()) + " seconds")
    log_boot("Clock change region: " + str(seasonal_time_region))
    log_boot("Scenes loaded: " + str(len(scenes)))
    log_boot("Valid schedules loaded: " + str(len(valid_schedules)))
    log_boot("Wi-Fi configured: " + ('yes' if wifi_ssid else 'no'))
    log_boot("Access point disabled: " + str(disable_access_point))

def apply_scene_color_value(name, color):
    global single_color
    global minute_color
    global hour_color
    global past_to_color

    if name == 'single_color':
        single_color = color
    elif name == 'minute_color':
        minute_color = color
    elif name == 'hour_color':
        hour_color = color
    elif name == 'past_to_color':
        past_to_color = color
    elif name == 'matrix_rain_minute_color':
        app_state.matrix_rain_minute_color = color
    elif name == 'matrix_rain_hour_color':
        app_state.matrix_rain_hour_color = color
    elif name == 'matrix_rain_past_to_color':
        app_state.matrix_rain_past_to_color = color
    elif name == 'matrix_rain_background_color':
        app_state.matrix_rain_background_color = color

def apply_color_field(scene, field_name):

    scene_manager.apply_color_field(
        scene,
        field_name,
        normalise_color=normalise_color,
        log_scene=log_scene,
        apply_color_value=apply_scene_color_value
    )

def apply_mode_specific_scene_fields(scene, mode):
    scene_manager.apply_mode_specific_scene_fields(
        scene,
        mode,
        scene_mode_fields=SCENE_MODE_FIELDS,
        normalise_color=normalise_color,
        log_scene=log_scene,
        apply_color_value=apply_scene_color_value
    )

def normalise_color(value):
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        return None
    colour = []
    for channel in value:
        if isinstance(channel, bool) or not isinstance(channel, int) or channel < 0 or channel > 255:
            return None
        colour.append(channel)
    return tuple(colour)

def parse_bool_field(data, field_name, default_value=None):
    if field_name not in data:
        return default_value, None
    value = data[field_name]
    if isinstance(value, bool):
        return value, None
    return None, field_name + " must be a boolean"

def parse_int_field(data, field_name, min_value, max_value, default_value=None):
    if field_name not in data:
        return default_value, None
    try:
        if isinstance(data[field_name], bool):
            return None, field_name + " must be an integer"
        value = int(data[field_name])
    except (TypeError, ValueError):
        return None, field_name + " must be an integer"
    if value < min_value or value > max_value:
        return None, field_name + " must be between " + str(min_value) + " and " + str(max_value)
    return value, None

def parse_color_field(data, field_name, default_value=None):
    if field_name not in data:
        return default_value, None
    color = normalise_color(data[field_name])
    if color is None:
        return None, field_name + " must be an RGB array with values from 0 to 255"
    return color, None

def parse_time_array_field(data, field_name):
    value = data.get(field_name)
    if not isinstance(value, (list, tuple)) or len(value) < 5:
        return None, field_name + " must be a time array"
    try:
        parsed_time = (
            int(value[0]),
            int(value[1]),
            int(value[2]),
            int(value[3]),
            int(value[4])
        )
    except (TypeError, ValueError):
        return None, field_name + " must contain integer time values"
    year, month, day, hour, minute = parsed_time
    if year < 2020 or year > 2099:
        return None, field_name + " year must be between 2020 and 2099"
    if month < 1 or month > 12:
        return None, field_name + " month must be between 1 and 12"
    if day < 1 or day > 31:
        return None, field_name + " day must be between 1 and 31"
    if hour < 0 or hour > 23:
        return None, field_name + " hour must be between 0 and 23"
    if minute < 0 or minute > 59:
        return None, field_name + " minute must be between 0 and 59"
    return parsed_time, None

def parse_clock_settings_payload(data):
    if not isinstance(data, dict):
        return None, "Settings payload must be an object"

    brightness, error = parse_int_field(data, 'brightness', 0, MAX_BRIGHTNESS)
    if error:
        return None, error
    if brightness is None:
        return None, "brightness is required"

    display_mode = data.get('display_mode')
    if display_mode is None:
        return None, "display_mode is required"
    if display_mode not in display_modes:
        return None, "display_mode is not supported"

    schedules_enabled_value, error = parse_bool_field(data, 'schedules_enabled', False)
    if error:
        return None, error

    seasonal_region = time_sync.normalise_seasonal_time_region(
        data.get('seasonal_time_region', time_sync.SEASONAL_TIME_REGION_OFF)
    )

    parsed = {
        'brightness': brightness,
        'display_mode': display_mode,
        'schedules_enabled': schedules_enabled_value,
        'seasonal_time_region': seasonal_region
    }

    color_fields = (
        ('single_color', single_color),
        ('minute_color', minute_color),
        ('hour_color', hour_color),
        ('past_to_color', past_to_color),
        ('matrix_rain_minute_color', app_state.matrix_rain_minute_color),
        ('matrix_rain_hour_color', app_state.matrix_rain_hour_color),
        ('matrix_rain_past_to_color', app_state.matrix_rain_past_to_color),
        ('matrix_rain_background_color', app_state.matrix_rain_background_color)
    )
    for field_name, default_value in color_fields:
        value, error = parse_color_field(data, field_name, default_value)
        if error:
            return None, error
        parsed[field_name] = value

    bool_fields = (
        ('matrix_rain_white_head', MATRIX_RAIN_DEFAULT_WHITE_HEAD),
        ('matrix_rain_affect_time', MATRIX_RAIN_DEFAULT_AFFECT_TIME),
        ('timeChanged', False)
    )
    for field_name, default_value in bool_fields:
        value, error = parse_bool_field(data, field_name, default_value)
        if error:
            return None, error
        parsed[field_name] = value

    ranged_int_fields = (
        ('matrix_rain_speed_ms', 40, 400, MATRIX_RAIN_DEFAULT_SPEED_MS),
        ('matrix_rain_spawn_rate', 0, 100, MATRIX_RAIN_DEFAULT_SPAWN_RATE),
        ('matrix_rain_trail_length', 1, 8, MATRIX_RAIN_DEFAULT_TRAIL_LENGTH),
        ('matrix_rain_time_brightness_cap', 0, MAX_BRIGHTNESS, MATRIX_RAIN_DEFAULT_TIME_BRIGHTNESS_CAP),
        (
            'rainbow_cycle_speed_ms',
            RAINBOW_CYCLE_MIN_SPEED_MS,
            RAINBOW_CYCLE_MAX_SPEED_MS,
            RAINBOW_CYCLE_DEFAULT_SPEED_MS
        ),
        (
            'rainbow_cycle_spread',
            RAINBOW_CYCLE_MIN_SPREAD,
            RAINBOW_CYCLE_MAX_SPREAD,
            RAINBOW_CYCLE_DEFAULT_SPREAD
        ),
        (
            'rainbow_cycle_step',
            RAINBOW_CYCLE_MIN_STEP,
            RAINBOW_CYCLE_MAX_STEP,
            RAINBOW_CYCLE_DEFAULT_STEP
        )
    )
    for field_name, min_value, max_value, default_value in ranged_int_fields:
        value, error = parse_int_field(data, field_name, min_value, max_value, default_value)
        if error:
            return None, error
        parsed[field_name] = value

    rainbow_cycle_style = data.get('rainbow_cycle_style', RAINBOW_CYCLE_DEFAULT_STYLE)
    if rainbow_cycle_style not in rainbow_cycle.RAINBOW_CYCLE_STYLES:
        return None, "rainbow_cycle_style is not supported"
    parsed['rainbow_cycle_style'] = rainbow_cycle_style

    if parsed['timeChanged']:
        new_time, error = parse_time_array_field(data, 'newTime')
        if error:
            return None, error
        parsed['newTime'] = new_time

    return parsed, None

def clear_matrix():
    blank = [0] * 8
    if config['ENABLE_MAX7219']:
        spi_matrix.show_char(blank)
    if config['ENABLE_HT16K33']:
        i2c_matrix.show_char(i2c_matrix.reverse_char(blank))
    if config['ENABLE_WS2812B']:
        ws2812b_matrix.clear()

def is_animated_display_mode(mode):
    return mode == DISPLAY_MODE_MATRIX_RAIN or mode == DISPLAY_MODE_RAINBOW_CYCLE

def reset_matrix_rain_state():
    app_state.matrix_rain_state.reset(app_state.matrix_rain_trail_length)

def reset_matrix_rain_time_overlay():
    app_state.matrix_rain_state.reset_time_overlay()

def reset_rainbow_cycle_state():
    app_state.rainbow_cycle_state.reset()

def reset_display_refresh_state():
    app_state.last_display_minute_key = None
    app_state.last_dynamic_display_update_ms = None
    reset_rainbow_cycle_state()
    reset_matrix_rain_state()
    reset_matrix_rain_time_overlay()

def advance_matrix_rain_state():
    app_state.matrix_rain_state.advance(
        random,
        app_state.matrix_rain_spawn_rate,
        app_state.matrix_rain_trail_length
    )

def render_matrix_rain():
    render_matrix_rain_frame(
        app_state.matrix_rain_state,
        background_color=app_state.matrix_rain_background_color,
        white_head=app_state.matrix_rain_white_head,
        affect_time=app_state.matrix_rain_affect_time,
        trail_length=app_state.matrix_rain_trail_length,
        time_brightness_cap=app_state.matrix_rain_time_brightness_cap,
        brightness=app_state.brightness,
        config=config,
        spi_matrix=spi_matrix,
        i2c_matrix=i2c_matrix,
        ws2812b_matrix=ws2812b_matrix,
        current_display_minute_key=current_display_minute_key,
        build_time_word_data=build_time_word_data,
        matrix_mode=DISPLAY_MODE_MATRIX_RAIN
    )

def advance_rainbow_cycle_state():
    app_state.rainbow_cycle_state.advance(app_state.rainbow_cycle_step)

def render_rainbow_cycle(word=None):
    global colour_per_word_array
    if word is None:
        word, colour_per_word_array, _ = build_time_word_data()
    render_rainbow_cycle_frame(
        app_state.rainbow_cycle_state,
        char=word,
        time_color_array=colour_per_word_array,
        style=app_state.rainbow_cycle_style,
        spread=app_state.rainbow_cycle_spread,
        brightness=app_state.brightness,
        config=config,
        ws2812b_matrix=ws2812b_matrix,
        minute_color=minute_color,
        hour_color=hour_color,
        past_to_color=past_to_color
    )

def run_animation_frame(mode):
    if mode == DISPLAY_MODE_MATRIX_RAIN:
        advance_matrix_rain_state()
        render_matrix_rain()
    elif mode == DISPLAY_MODE_RAINBOW_CYCLE:
        advance_rainbow_cycle_state()
        time_to_matrix(force=True)

def get_animation_frame_delay_ms(mode):
    if mode == DISPLAY_MODE_MATRIX_RAIN:
        return app_state.matrix_rain_speed_ms
    if mode == DISPLAY_MODE_RAINBOW_CYCLE:
        return app_state.rainbow_cycle_speed_ms
    return ANIMATION_IDLE_SLEEP_MS

def build_time_word_data(mode=None):
    word = [0, 0, 0, 0, 0, 0, 0, 0]
    now = get_corrected_time()
    hour = now[3]
    minute = now[4]
    time_colour_array = []
    use_matrix_rain_colours = mode == DISPLAY_MODE_MATRIX_RAIN
    minute_word_color = app_state.matrix_rain_minute_color if use_matrix_rain_colours else minute_color
    hour_word_color = app_state.matrix_rain_hour_color if use_matrix_rain_colours else hour_color
    past_to_word_color = app_state.matrix_rain_past_to_color if use_matrix_rain_colours else past_to_color

    minute = int(round(minute / 5) * 5)
    if minute > 0 and minute <= 30:
        word = merge_chars(word, clockFont['past'])
        time_colour_array = merge_color_array(time_colour_array, clockFont['past'], past_to_word_color)
    elif minute == 60:
        if now[4] > 55:
            hour = hour + 1
    elif minute > 30:
        word = merge_chars(word, clockFont['to'])
        time_colour_array = merge_color_array(time_colour_array, clockFont['to'], past_to_word_color)
        hour = hour + 1

    hour = hour % 12
    hour_key = 'h_' + str(hour)
    word = merge_chars(word, clockFont[hour_key])
    time_colour_array = merge_color_array(time_colour_array, clockFont[hour_key], hour_word_color)

    if minute > 30:
        minute = 60 - minute
    if minute > 0:
        minute_key = 'm_' + str(minute)
        word = merge_chars(word, clockFont[minute_key])
        time_colour_array = merge_color_array(time_colour_array, clockFont[minute_key], minute_word_color)

    while len(time_colour_array) < 64:
        time_colour_array.append((0, 0, 0))

    return word, time_colour_array, now

def current_display_minute_key():
    now = get_corrected_time()
    return (now[0], now[1], now[2], now[3], now[4])

def should_refresh_display():
    if not app_state.display_enabled:
        return False

    if is_animated_display_mode(app_state.current_display_mode):
        return False

    refresh_ms = DISPLAY_MODE_REFRESH_MS.get(app_state.current_display_mode)
    if refresh_ms is not None:
        now_ms = time.ticks_ms()
        if app_state.last_dynamic_display_update_ms is None:
            return True
        return time.ticks_diff(now_ms, app_state.last_dynamic_display_update_ms) >= refresh_ms

    return current_display_minute_key() != app_state.last_display_minute_key

def set_display_enabled(enabled):
    app_state.display_enabled = bool(enabled)
    reset_display_refresh_state()
    if not app_state.display_enabled:
        clear_matrix()

def set_display_mode(mode, persist=False):
    if mode not in display_modes:
        raise ValueError("Unsupported display mode: " + str(mode))
    app_state.current_display_mode = mode
    reset_display_refresh_state()
    if persist:
        config['DISPLAY_MODE'] = app_state.current_display_mode

def reset_clock_settings_to_defaults():
    global single_color
    global minute_color
    global hour_color
    global past_to_color
    global schedules_enabled
    global manual_time_offset
    global seasonal_time_region

    app_state.brightness = 2
    app_state.display_enabled = True
    app_state.current_display_mode = DISPLAY_MODE_RAINBOW
    app_state.current_scene_name = None
    single_color = (0, 0, 255)
    minute_color = (0, 255, 0)
    hour_color = (255, 0, 0)
    past_to_color = (0, 0, 255)
    schedules_enabled = True
    app_state.matrix_rain_minute_color = MATRIX_RAIN_DEFAULT_MINUTE_COLOR
    app_state.matrix_rain_hour_color = MATRIX_RAIN_DEFAULT_HOUR_COLOR
    app_state.matrix_rain_past_to_color = MATRIX_RAIN_DEFAULT_PAST_TO_COLOR
    app_state.matrix_rain_background_color = MATRIX_RAIN_DEFAULT_BACKGROUND_COLOR
    app_state.matrix_rain_white_head = MATRIX_RAIN_DEFAULT_WHITE_HEAD
    app_state.matrix_rain_affect_time = MATRIX_RAIN_DEFAULT_AFFECT_TIME
    app_state.matrix_rain_speed_ms = MATRIX_RAIN_DEFAULT_SPEED_MS
    app_state.matrix_rain_spawn_rate = MATRIX_RAIN_DEFAULT_SPAWN_RATE
    app_state.matrix_rain_trail_length = MATRIX_RAIN_DEFAULT_TRAIL_LENGTH
    app_state.matrix_rain_time_brightness_cap = MATRIX_RAIN_DEFAULT_TIME_BRIGHTNESS_CAP
    app_state.rainbow_cycle_style = RAINBOW_CYCLE_DEFAULT_STYLE
    app_state.rainbow_cycle_speed_ms = RAINBOW_CYCLE_DEFAULT_SPEED_MS
    app_state.rainbow_cycle_spread = RAINBOW_CYCLE_DEFAULT_SPREAD
    app_state.rainbow_cycle_step = RAINBOW_CYCLE_DEFAULT_STEP
    manual_time_offset = 0
    seasonal_time_region = time_sync.SEASONAL_TIME_REGION_OFF
    reset_display_refresh_state()

    config['BRIGHTNESS'] = app_state.brightness
    config['DISPLAY_MODE'] = app_state.current_display_mode
    config['SCHEDULES_ENABLED'] = schedules_enabled
    config['SINGLE_COLOR'] = single_color
    config['MINUTE_COLOR'] = minute_color
    config['HOUR_COLOR'] = hour_color
    config['PAST_TO_COLOR'] = past_to_color
    config['MATRIX_RAIN_MINUTE_COLOR'] = app_state.matrix_rain_minute_color
    config['MATRIX_RAIN_HOUR_COLOR'] = app_state.matrix_rain_hour_color
    config['MATRIX_RAIN_PAST_TO_COLOR'] = app_state.matrix_rain_past_to_color
    config['MATRIX_RAIN_BACKGROUND_COLOR'] = app_state.matrix_rain_background_color
    config['MATRIX_RAIN_WHITE_HEAD'] = app_state.matrix_rain_white_head
    config['MATRIX_RAIN_AFFECT_TIME'] = app_state.matrix_rain_affect_time
    config['MATRIX_RAIN_SPEED_MS'] = app_state.matrix_rain_speed_ms
    config['MATRIX_RAIN_SPAWN_RATE'] = app_state.matrix_rain_spawn_rate
    config['MATRIX_RAIN_TRAIL_LENGTH'] = app_state.matrix_rain_trail_length
    config['MATRIX_RAIN_TIME_BRIGHTNESS_CAP'] = app_state.matrix_rain_time_brightness_cap
    config['RAINBOW_CYCLE_STYLE'] = app_state.rainbow_cycle_style
    config['RAINBOW_CYCLE_SPEED_MS'] = app_state.rainbow_cycle_speed_ms
    config['RAINBOW_CYCLE_SPREAD'] = app_state.rainbow_cycle_spread
    config['RAINBOW_CYCLE_STEP'] = app_state.rainbow_cycle_step
    persist_time_settings(save=False)
    save_config(config)

def apply_scene(scene_name_or_object, fallback_name=None):
    success, next_scene_name = scene_manager.apply_scene(
        scene_name_or_object,
        scenes=scenes,
        current_display_mode=app_state.current_display_mode,
        display_modes=display_modes,
        set_display_enabled=set_display_enabled,
        set_brightness=set_brightness,
        set_display_mode=set_display_mode,
        apply_mode_specific_scene_fields=apply_mode_specific_scene_fields,
        app_state=app_state,
        log_scene=log_scene,
        max_brightness=MAX_BRIGHTNESS,
        reset_matrix_rain_state=reset_matrix_rain_state,
        rainbow_cycle_styles=rainbow_cycle.RAINBOW_CYCLE_STYLES,
        rainbow_cycle_speed_limits=(RAINBOW_CYCLE_MIN_SPEED_MS, RAINBOW_CYCLE_MAX_SPEED_MS),
        rainbow_cycle_spread_limits=(RAINBOW_CYCLE_MIN_SPREAD, RAINBOW_CYCLE_MAX_SPREAD),
        rainbow_cycle_step_limits=(RAINBOW_CYCLE_MIN_STEP, RAINBOW_CYCLE_MAX_STEP),
        reset_rainbow_cycle_state=reset_rainbow_cycle_state,
        is_display_enabled=lambda: app_state.display_enabled,
        time_to_matrix=time_to_matrix,
        clear_matrix=clear_matrix,
        fallback_name=fallback_name
    )
    if success:
        app_state.current_scene_name = next_scene_name
    return success

def read_config():
    try:
        with open(config_file, 'r') as file:
            return json.load(file)
    except (OSError):
        print(f"Configuration file not found or is invalid. Please create a valid {config_file} file.")
        return None

def read_optional_json(filename, default_value):
    try:
        with open(filename, 'r') as file:
            return json.load(file)
    except OSError:
        return default_value
    except ValueError:
        print("Optional JSON file is invalid: " + filename)
        return default_value

def save_json_file(filename, data):
    try:
        with open(filename, 'w') as file:
            json.dump(data, file)
            print("Saved " + filename)
            return True
    except OSError as e:
        print("Error saving " + filename + ": " + str(e))
        return False

def validate_schedules(schedule_entries):
    return schedule_manager.validate_schedules(
        schedule_entries,
        log_schedule=log_schedule,
        weekday_names=WEEKDAY_NAMES,
        action_types=SCHEDULE_ACTION_TYPES,
        max_brightness=MAX_BRIGHTNESS,
        scenes=scenes
    )

def run_schedule_action(action):
    action_type = action['type']
    if action_type == 'display_on':
        set_display_enabled(True)
        time_to_matrix()
        return True
    if action_type == 'display_off':
        set_display_enabled(False)
        clear_matrix()
        return True
    if action_type == 'set_brightness':
        set_brightness(action['value'], persist=False)
        if app_state.display_enabled:
            time_to_matrix()
        return True
    if action_type == 'apply_scene':
        return apply_scene(action['scene'])
    return False

def evaluate_schedules():
    global last_schedule_evaluation_key
    last_schedule_evaluation_key = schedule_manager.evaluate_schedules(
        schedules_enabled=schedules_enabled,
        valid_schedules=valid_schedules,
        last_schedule_evaluation_key=last_schedule_evaluation_key,
        get_corrected_time=get_corrected_time,
        run_schedule_action=run_schedule_action,
        log_schedule=log_schedule,
        weekday_names=WEEKDAY_NAMES
    )

def save_config(data):
    if save_json_file(config_file, data):
        print("Configuration saved.")

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
    last_dns_check_status = time_sync.test_dns(socket)
    return last_dns_check_status


async def sync_ntp_time(use_alternative=False, timeout=2.0):
    global ntp_synced_at, last_ntp_sync_attempt, last_wifi_connected_time
    result = await time_sync.sync_ntp_time(
        use_alternative=use_alternative,
        timeout=timeout,
        time_module=time,
        ticks_ms=time.ticks_ms,
        asyncio_module=asyncio,
        ntptime_module=ntptime,
        alt_ntptime_module=alt_ntptime,
        retry_interval_seconds=NTP_RETRY_INTERVAL_SECONDS,
        last_ntp_sync_attempt=last_ntp_sync_attempt,
        test_dns=test_dns,
        is_wifi_connected=server.is_wifi_connected,
        logger=print
    )
    if result['ntp_synced_at'] is not None:
        ntp_synced_at = result['ntp_synced_at']
        last_wifi_connected_time = result['last_wifi_connected_ticks']
    last_ntp_sync_attempt = result['last_ntp_sync_attempt']
    return result['success']


def should_attempt_ntp_sync():
    return time_sync.should_attempt_ntp_sync(
        is_wifi_connected=server.is_wifi_connected,
        is_access_point_active=server.is_access_point_active,
        ticks_diff=time.ticks_diff,
        ticks_ms=time.ticks_ms,
        last_wifi_connected_time=last_wifi_connected_time,
        initial_delay_ms=NTP_INITIAL_DELAY_AFTER_WIFI_CONNECT_MS,
        now=time.time(),
        ntp_synced_at=ntp_synced_at,
        sync_interval_seconds=NTP_SYNC_INTERVAL_SECONDS,
        last_ntp_sync_attempt=last_ntp_sync_attempt,
        retry_interval_seconds=NTP_RETRY_INTERVAL_SECONDS
    )


def get_corrected_time():
    return time_sync.get_corrected_time(time, get_total_time_offset())

def get_effective_utc_seconds():
    return time.time() + manual_time_offset

def get_timezone_offset_seconds(unix_time=None):
    if unix_time is None:
        unix_time = get_effective_utc_seconds()
    return time_sync.get_region_time_offset_seconds(time, unix_time, seasonal_time_region)

def get_total_time_offset():
    return manual_time_offset + get_timezone_offset_seconds()

def persist_time_settings(save=True):
    config['MANUAL_TIME_OFFSET'] = manual_time_offset
    config['SEASONAL_TIME_REGION'] = seasonal_time_region
    config['TIME_OFFSET'] = get_total_time_offset()
    if save:
        save_config(config)

def set_manual_time(year, month, day, hour, minute, second):
    global manual_time_offset
    manual_time_offset = time_sync.calculate_manual_time_offset(
        time,
        year,
        month,
        day,
        hour,
        minute,
        second,
        base_offset_seconds=time_sync.infer_region_offset_for_local_datetime(
            time,
            seasonal_time_region,
            year,
            month,
            day,
            hour,
            minute,
            second
        )
    )
    persist_time_settings()


def time_to_matrix(force=False):
    global colour_per_word_array
    if not app_state.display_enabled:
        app_state.last_display_minute_key = current_display_minute_key()
        app_state.last_dynamic_display_update_ms = time.ticks_ms()
        clear_matrix()
        return
    if is_animated_display_mode(app_state.current_display_mode) and not force:
        app_state.last_dynamic_display_update_ms = time.ticks_ms()
        return
    word, colour_per_word_array, now = build_time_word_data()
    if config['ENABLE_MAX7219']:
        spi_matrix.show_char(word)
    if config['ENABLE_HT16K33']:            
        if not i2c_matrix.show_char(i2c_matrix.reverse_char(word)):
            print("Error writing to matrix")
    if config['ENABLE_WS2812B']:
        ws2812b_matrix.set_brightness(app_state.brightness)
        display_function = display_modes.get(app_state.current_display_mode)
        if display_function:
            display_function(word)
    app_state.last_display_minute_key = (now[0], now[1], now[2], now[3], now[4])
    app_state.last_dynamic_display_update_ms = time.ticks_ms()

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

def set_brightness(new_brightness, persist=True):
    app_state.brightness = new_brightness
    if persist:
        config['BRIGHTNESS'] = app_state.brightness
        save_config(config)
    if config['ENABLE_MAX7219']:
        spi_matrix.set_brightness(app_state.brightness)
    if config['ENABLE_HT16K33']:
        i2c_matrix.set_brightness(app_state.brightness)
    if config['ENABLE_WS2812B']:
        ws2812b_matrix.set_brightness(app_state.brightness)

def display_rainbow_mode(word):
    ws2812b_matrix.show_char_with_color_array(word, ws2812b_matrix.get_rainbow_array())

def display_rainbow_cycle_mode(word):
    render_rainbow_cycle(word)

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

def display_matrix_rain_mode(word):
    if not app_state.matrix_rain_state.has_state():
        advance_matrix_rain_state()
    render_matrix_rain()

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
    global config, last_wifi_disconnected_time
    print(request.post_data)
    wifi_ssid = request.post_data['wifi_ssid']
    wifi_password = request.post_data.get('wifi_password', None)
    config['WIFI_SSID'] = wifi_ssid
    if wifi_password is not None and wifi_password != '':
        config['WIFI_PASSWORD'] = wifi_password
    save_config(config)
    last_wifi_disconnected_time = time.ticks_ms()
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

async def set_schedules_enabled_request(request, response):
    global schedules_enabled
    schedules_enabled = bool(request.post_data.get('schedules_enabled', False))
    config['SCHEDULES_ENABLED'] = schedules_enabled
    save_config(config)
    response_data = {
        'status': 'OK',
        'success': True,
        'message': 'Schedules ' + ('enabled' if schedules_enabled else 'disabled'),
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

async def set_schedules_request(request, response):
    global schedules, valid_schedules
    new_schedules = request.post_data.get('schedules', [])
    if not isinstance(new_schedules, list):
        response_data = {
            'status': 'ERROR',
            'success': False,
            'message': 'Schedules payload must be a list',
            'settings': settings_object()
        }
        await response.send_json(json.dumps(response_data), 400)
        return

    if not save_json_file(schedules_file, new_schedules):
        response_data = {
            'status': 'ERROR',
            'success': False,
            'message': 'Failed to save schedules',
            'settings': settings_object()
        }
        await response.send_json(json.dumps(response_data), 500)
        return

    schedules = new_schedules
    valid_schedules = validate_schedules(schedules)
    response_data = {
        'status': 'OK',
        'success': True,
        'message': 'Schedules updated',
        'settings': settings_object()
    }
    await response.send_json(json.dumps(response_data), 200)

async def set_scenes_request(request, response):
    global scenes, valid_schedules
    new_scenes = request.post_data.get('scenes', {})
    if not isinstance(new_scenes, dict):
        response_data = {
            'status': 'ERROR',
            'success': False,
            'message': 'Scenes payload must be an object',
            'settings': settings_object()
        }
        await response.send_json(json.dumps(response_data), 400)
        return

    if not save_json_file(scenes_file, new_scenes):
        response_data = {
            'status': 'ERROR',
            'success': False,
            'message': 'Failed to save scenes',
            'settings': settings_object()
        }
        await response.send_json(json.dumps(response_data), 500)
        return

    scenes = new_scenes
    valid_schedules = validate_schedules(schedules)
    response_data = {
        'status': 'OK',
        'success': True,
        'message': 'Scenes updated',
        'settings': settings_object()
    }
    await response.send_json(json.dumps(response_data), 200)

async def reset_default_scenes_request(request, response):
    global scenes, valid_schedules
    default_scenes = read_optional_json(default_scenes_file, None)
    if not isinstance(default_scenes, dict):
        response_data = {
            'status': 'ERROR',
            'success': False,
            'message': 'Failed to load default scenes',
            'settings': settings_object()
        }
        await response.send_json(json.dumps(response_data), 500)
        return

    if not save_json_file(scenes_file, default_scenes):
        response_data = {
            'status': 'ERROR',
            'success': False,
            'message': 'Failed to reset scenes',
            'settings': settings_object()
        }
        await response.send_json(json.dumps(response_data), 500)
        return

    scenes = default_scenes
    valid_schedules = validate_schedules(schedules)
    response_data = {
        'status': 'OK',
        'success': True,
        'message': 'Scenes reset to defaults',
        'settings': settings_object()
    }
    await response.send_json(json.dumps(response_data), 200)

async def test_scene_request(request, response):
    scene_payload = request.post_data.get('scene')
    scene_name = request.post_data.get('scene_name')

    if not isinstance(scene_payload, dict):
        response_data = {
            'status': 'ERROR',
            'success': False,
            'message': 'Scene payload must be an object',
            'settings': settings_object()
        }
        await response.send_json(json.dumps(response_data), 400)
        return

    if scene_name is not None and not isinstance(scene_name, str):
        scene_name = None

    if not apply_scene(scene_payload, fallback_name=scene_name):
        response_data = {
            'status': 'ERROR',
            'success': False,
            'message': 'Failed to test scene',
            'settings': settings_object()
        }
        await response.send_json(json.dumps(response_data), 400)
        return

    response_data = {
        'status': 'OK',
        'success': True,
        'message': 'Scene tested',
        'settings': settings_object()
    }
    await response.send_json(json.dumps(response_data), 200)

async def set_clock_settings_request(request, response):
    global single_color
    global minute_color
    global hour_color
    global past_to_color
    global schedules_enabled
    global seasonal_time_region
    print(request.post_data)

    parsed_settings, error = parse_clock_settings_payload(request.post_data)
    if error:
        response_data = {
            'status': 'ERROR',
            'success': False,
            'message': error,
            'settings': settings_object()
        }
        await response.send_json(json.dumps(response_data), 400)
        return

    set_brightness(parsed_settings['brightness'], persist=False)
    set_display_mode(parsed_settings['display_mode'], persist=False)
    app_state.current_scene_name = None
    schedules_enabled = parsed_settings['schedules_enabled']
    seasonal_time_region = parsed_settings['seasonal_time_region']
    single_color = parsed_settings['single_color']
    minute_color = parsed_settings['minute_color']
    hour_color = parsed_settings['hour_color']
    past_to_color = parsed_settings['past_to_color']
    app_state.matrix_rain_minute_color = parsed_settings['matrix_rain_minute_color']
    app_state.matrix_rain_hour_color = parsed_settings['matrix_rain_hour_color']
    app_state.matrix_rain_past_to_color = parsed_settings['matrix_rain_past_to_color']
    app_state.matrix_rain_background_color = parsed_settings['matrix_rain_background_color']
    app_state.matrix_rain_white_head = parsed_settings['matrix_rain_white_head']
    app_state.matrix_rain_affect_time = parsed_settings['matrix_rain_affect_time']
    app_state.matrix_rain_speed_ms = parsed_settings['matrix_rain_speed_ms']
    app_state.matrix_rain_spawn_rate = parsed_settings['matrix_rain_spawn_rate']
    app_state.matrix_rain_trail_length = parsed_settings['matrix_rain_trail_length']
    app_state.matrix_rain_time_brightness_cap = parsed_settings['matrix_rain_time_brightness_cap']
    app_state.rainbow_cycle_style = parsed_settings['rainbow_cycle_style']
    app_state.rainbow_cycle_speed_ms = parsed_settings['rainbow_cycle_speed_ms']
    app_state.rainbow_cycle_spread = parsed_settings['rainbow_cycle_spread']
    app_state.rainbow_cycle_step = parsed_settings['rainbow_cycle_step']
    reset_matrix_rain_state()
    reset_rainbow_cycle_state()
    config['BRIGHTNESS'] = app_state.brightness
    config['DISPLAY_MODE'] = app_state.current_display_mode
    config['SCHEDULES_ENABLED'] = schedules_enabled
    config['SINGLE_COLOR'] = single_color
    config['MINUTE_COLOR'] = minute_color
    config['HOUR_COLOR'] = hour_color
    config['PAST_TO_COLOR'] = past_to_color
    config['MATRIX_RAIN_MINUTE_COLOR'] = app_state.matrix_rain_minute_color
    config['MATRIX_RAIN_HOUR_COLOR'] = app_state.matrix_rain_hour_color
    config['MATRIX_RAIN_PAST_TO_COLOR'] = app_state.matrix_rain_past_to_color
    config['MATRIX_RAIN_BACKGROUND_COLOR'] = app_state.matrix_rain_background_color
    config['MATRIX_RAIN_WHITE_HEAD'] = app_state.matrix_rain_white_head
    config['MATRIX_RAIN_AFFECT_TIME'] = app_state.matrix_rain_affect_time
    config['MATRIX_RAIN_SPEED_MS'] = app_state.matrix_rain_speed_ms
    config['MATRIX_RAIN_SPAWN_RATE'] = app_state.matrix_rain_spawn_rate
    config['MATRIX_RAIN_TRAIL_LENGTH'] = app_state.matrix_rain_trail_length
    config['MATRIX_RAIN_TIME_BRIGHTNESS_CAP'] = app_state.matrix_rain_time_brightness_cap
    config['RAINBOW_CYCLE_STYLE'] = app_state.rainbow_cycle_style
    config['RAINBOW_CYCLE_SPEED_MS'] = app_state.rainbow_cycle_speed_ms
    config['RAINBOW_CYCLE_SPREAD'] = app_state.rainbow_cycle_spread
    config['RAINBOW_CYCLE_STEP'] = app_state.rainbow_cycle_step
    persist_time_settings(save=False)
    save_config(config)
    if parsed_settings['timeChanged']:
        year, month, day, hour, minute = parsed_settings['newTime']
        set_manual_time(year, month, day, hour, minute, 0)
    reset_matrix_rain_time_overlay()
    time_to_matrix()
    response_data = {
        'status': 'OK',
        'success': True,
        'message': 'Settings updated',
        'settings': settings_object()
    }
    await response.send_json(json.dumps(response_data), 200)


async def get_clock_settings_request(request, response):
    await response.send_json(settings_to_json())

async def reset_clock_settings_request(request, response):
    reset_clock_settings_to_defaults()
    time_to_matrix(force=True)
    response_data = {
        'status': 'OK',
        'success': True,
        'message': 'Clock settings reset',
        'settings': settings_object()
    }
    await response.send_json(json.dumps(response_data), 200)

def settings_object():
    global ntp_synced_at, last_ntp_sync_attempt
    return {
        'brightness': app_state.brightness,
        'display_enabled': app_state.display_enabled,
        'display_mode': app_state.current_display_mode,
        'current_scene': app_state.current_scene_name,
        'scenes': scenes,
        'scene_names': list(scenes.keys()),
        'schedules': schedules,
        'schedules_enabled': schedules_enabled,
        'schedule_count': len(valid_schedules),
        'single_color': single_color,
        'minute_color': minute_color,
        'hour_color': hour_color,
        'past_to_color': past_to_color,
        'matrix_rain_minute_color': app_state.matrix_rain_minute_color,
        'matrix_rain_hour_color': app_state.matrix_rain_hour_color,
        'matrix_rain_past_to_color': app_state.matrix_rain_past_to_color,
        'matrix_rain_background_color': app_state.matrix_rain_background_color,
        'matrix_rain_white_head': app_state.matrix_rain_white_head,
        'matrix_rain_affect_time': app_state.matrix_rain_affect_time,
        'matrix_rain_speed_ms': app_state.matrix_rain_speed_ms,
        'matrix_rain_spawn_rate': app_state.matrix_rain_spawn_rate,
        'matrix_rain_trail_length': app_state.matrix_rain_trail_length,
        'matrix_rain_time_brightness_cap': app_state.matrix_rain_time_brightness_cap,
        'rainbow_cycle_style': app_state.rainbow_cycle_style,
        'rainbow_cycle_speed_ms': app_state.rainbow_cycle_speed_ms,
        'rainbow_cycle_spread': app_state.rainbow_cycle_spread,
        'rainbow_cycle_step': app_state.rainbow_cycle_step,
        'time': get_corrected_time(),
        'local_time': time.localtime(),
        'unix_time': time.time(),
        'time_offset': get_total_time_offset(),
        'manual_time_offset': manual_time_offset,
        'seasonal_time_region': seasonal_time_region,
        'wifi_connected': server.is_wifi_connected(),
        'wifi_ip_address': server.get_wifi_ip_address(),
        'wifi_ssid': server.get_wifi_ssid(),
        'ap_address': server.get_ap_ip_address(),
        'ap_ssid': server.get_ap_ssid(),
        'ap_active': server.is_access_point_active(),
        'cpu_temp': read_temperature(),
        'mem_free': gc.mem_free(),
        'mem_alloc': gc.mem_alloc(),
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
    server.add_function_route('/reset-clock-settings', reset_clock_settings_request)
    server.add_function_route('/set-schedules-enabled', set_schedules_enabled_request)
    server.add_function_route('/set-scenes', set_scenes_request)
    server.add_function_route('/reset-default-scenes', reset_default_scenes_request)
    server.add_function_route('/test-scene', test_scene_request)
    server.add_function_route('/set-schedules', set_schedules_request)
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
        hostname = config.get('HOSTNAME', 'wordclock')
        print("Connecting to Wi-Fi")
        await server.connect_wifi(wifi_ssid, wifi_password, hostname)
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

async def animation_loop():
    while True:
        if app_state.display_enabled and is_animated_display_mode(app_state.current_display_mode):
            run_animation_frame(app_state.current_display_mode)
            await asyncio.sleep_ms(get_animation_frame_delay_ms(app_state.current_display_mode))
            continue
        await asyncio.sleep_ms(ANIMATION_IDLE_SLEEP_MS)

        
async def main():
    global ntp_synced_at, last_wifi_connected_time, last_wifi_disconnected_time, disable_access_point
    ap_connnected = False
    log_boot("Starting main background task")
    await connect_to_wifi()
    if not server.is_wifi_connected() and not disable_access_point:
        ap_connnected = server.start_access_point('gurgleapps', 'gurgleapps')
        await scroll_message(matrix_fonts.textFont1, "No Wi-Fi", 0.05)
    print("Access Point active: " + str(ap_connnected)) 
    asyncio.create_task(animation_loop())
    while True:
        if server.is_access_point_active():
            if server.is_wifi_connected():
                delta = time.ticks_diff(time.ticks_ms(), last_wifi_connected_time)
                if delta > ACCESS_POINT_STOP_DELAY_MS:
                    server.stop_access_point() # Stop access point after 10 seconds of Wi-Fi connection
                    print("Access Point stopped")
        if not server.is_wifi_connected() and not disable_access_point:
            if not server.is_access_point_active():
                delta = time.ticks_diff(time.ticks_ms(), last_wifi_disconnected_time)
                if delta > ACCESS_POINT_START_DELAY_MS: # Start access point after 60 seconds of Wi-Fi disconnection
                    ap_connnected = server.start_access_point('gurgleapps', 'gurgleapps')
                    print("Access Point started: " + str(ap_connnected))
        evaluate_schedules()
        if should_refresh_display():
            time_to_matrix()
        if should_attempt_ntp_sync():
            await sync_ntp_time()
        await asyncio.sleep(MAIN_LOOP_SLEEP_SECONDS)

display_modes = {
    DISPLAY_MODE_RAINBOW: display_rainbow_mode,
    DISPLAY_MODE_RAINBOW_CYCLE: display_rainbow_cycle_mode,
    DISPLAY_MODE_SINGLE_COLOR: display_single_color_mode,
    DISPLAY_MODE_COLOR_PER_WORD: display_color_per_word_mode,
    DISPLAY_MODE_RANDOM: display_random_mode,
    DISPLAY_MODE_MATRIX_RAIN: display_matrix_rain_mode
}

log_boot("Loading " + config_file)
config = read_config()

if config is None:
    raise SystemExit("Stopping execution due to missing configuration.")

app_state.brightness = config.get('BRIGHTNESS', 2)
single_color = config.get('SINGLE_COLOR', (0, 0, 255))
minute_color = config.get('MINUTE_COLOR', (0, 255, 0))
hour_color = config.get('HOUR_COLOR', (255, 0, 0))
past_to_color = config.get('PAST_TO_COLOR', (0, 0, 255))
app_state.matrix_rain_minute_color = config.get('MATRIX_RAIN_MINUTE_COLOR', MATRIX_RAIN_DEFAULT_MINUTE_COLOR)
app_state.matrix_rain_hour_color = config.get('MATRIX_RAIN_HOUR_COLOR', MATRIX_RAIN_DEFAULT_HOUR_COLOR)
app_state.matrix_rain_past_to_color = config.get('MATRIX_RAIN_PAST_TO_COLOR', MATRIX_RAIN_DEFAULT_PAST_TO_COLOR)
app_state.matrix_rain_background_color = config.get('MATRIX_RAIN_BACKGROUND_COLOR', MATRIX_RAIN_DEFAULT_BACKGROUND_COLOR)
app_state.matrix_rain_white_head = config.get('MATRIX_RAIN_WHITE_HEAD', MATRIX_RAIN_DEFAULT_WHITE_HEAD)
app_state.matrix_rain_affect_time = config.get('MATRIX_RAIN_AFFECT_TIME', MATRIX_RAIN_DEFAULT_AFFECT_TIME)
app_state.matrix_rain_speed_ms = config.get('MATRIX_RAIN_SPEED_MS', MATRIX_RAIN_DEFAULT_SPEED_MS)
app_state.matrix_rain_spawn_rate = config.get('MATRIX_RAIN_SPAWN_RATE', MATRIX_RAIN_DEFAULT_SPAWN_RATE)
app_state.matrix_rain_trail_length = config.get('MATRIX_RAIN_TRAIL_LENGTH', MATRIX_RAIN_DEFAULT_TRAIL_LENGTH)
app_state.matrix_rain_time_brightness_cap = config.get('MATRIX_RAIN_TIME_BRIGHTNESS_CAP', MATRIX_RAIN_DEFAULT_TIME_BRIGHTNESS_CAP)
app_state.rainbow_cycle_style = rainbow_cycle.normalise_style(config.get('RAINBOW_CYCLE_STYLE', RAINBOW_CYCLE_DEFAULT_STYLE))
app_state.rainbow_cycle_speed_ms = rainbow_cycle.clamp_speed_ms(config.get('RAINBOW_CYCLE_SPEED_MS', RAINBOW_CYCLE_DEFAULT_SPEED_MS))
app_state.rainbow_cycle_spread = rainbow_cycle.clamp_spread(config.get('RAINBOW_CYCLE_SPREAD', RAINBOW_CYCLE_DEFAULT_SPREAD))
app_state.rainbow_cycle_step = rainbow_cycle.clamp_step(config.get('RAINBOW_CYCLE_STEP', RAINBOW_CYCLE_DEFAULT_STEP))
app_state.current_display_mode = config.get('DISPLAY_MODE', DISPLAY_MODE_RAINBOW)
manual_time_offset = config.get('MANUAL_TIME_OFFSET', config.get('TIME_OFFSET', 0))
seasonal_time_region = config.get('SEASONAL_TIME_REGION', time_sync.SEASONAL_TIME_REGION_OFF)
disable_access_point = config.get('DISABLE_ACCESS_POINT', False)
schedules_enabled = config.get('SCHEDULES_ENABLED', True)

normalised_matrix_rain_background_color = normalise_color(app_state.matrix_rain_background_color)
if normalised_matrix_rain_background_color is None:
    app_state.matrix_rain_background_color = MATRIX_RAIN_DEFAULT_BACKGROUND_COLOR
else:
    app_state.matrix_rain_background_color = normalised_matrix_rain_background_color

normalised_matrix_rain_minute_color = normalise_color(app_state.matrix_rain_minute_color)
if normalised_matrix_rain_minute_color is None:
    app_state.matrix_rain_minute_color = MATRIX_RAIN_DEFAULT_MINUTE_COLOR
else:
    app_state.matrix_rain_minute_color = normalised_matrix_rain_minute_color

normalised_matrix_rain_hour_color = normalise_color(app_state.matrix_rain_hour_color)
if normalised_matrix_rain_hour_color is None:
    app_state.matrix_rain_hour_color = MATRIX_RAIN_DEFAULT_HOUR_COLOR
else:
    app_state.matrix_rain_hour_color = normalised_matrix_rain_hour_color

normalised_matrix_rain_past_to_color = normalise_color(app_state.matrix_rain_past_to_color)
if normalised_matrix_rain_past_to_color is None:
    app_state.matrix_rain_past_to_color = MATRIX_RAIN_DEFAULT_PAST_TO_COLOR
else:
    app_state.matrix_rain_past_to_color = normalised_matrix_rain_past_to_color

if not isinstance(app_state.matrix_rain_white_head, bool):
    app_state.matrix_rain_white_head = MATRIX_RAIN_DEFAULT_WHITE_HEAD

if not isinstance(app_state.matrix_rain_affect_time, bool):
    app_state.matrix_rain_affect_time = MATRIX_RAIN_DEFAULT_AFFECT_TIME

if not isinstance(app_state.matrix_rain_speed_ms, int):
    app_state.matrix_rain_speed_ms = MATRIX_RAIN_DEFAULT_SPEED_MS
elif app_state.matrix_rain_speed_ms < 40:
    app_state.matrix_rain_speed_ms = 40
elif app_state.matrix_rain_speed_ms > 400:
    app_state.matrix_rain_speed_ms = 400

if not isinstance(app_state.matrix_rain_spawn_rate, int):
    app_state.matrix_rain_spawn_rate = MATRIX_RAIN_DEFAULT_SPAWN_RATE
elif app_state.matrix_rain_spawn_rate < 0:
    app_state.matrix_rain_spawn_rate = 0
elif app_state.matrix_rain_spawn_rate > 100:
    app_state.matrix_rain_spawn_rate = 100

if not isinstance(app_state.matrix_rain_trail_length, int):
    app_state.matrix_rain_trail_length = MATRIX_RAIN_DEFAULT_TRAIL_LENGTH
elif app_state.matrix_rain_trail_length < 1:
    app_state.matrix_rain_trail_length = 1
elif app_state.matrix_rain_trail_length > 8:
    app_state.matrix_rain_trail_length = 8

if not isinstance(app_state.matrix_rain_time_brightness_cap, int):
    app_state.matrix_rain_time_brightness_cap = MATRIX_RAIN_DEFAULT_TIME_BRIGHTNESS_CAP
elif app_state.matrix_rain_time_brightness_cap < 0:
    app_state.matrix_rain_time_brightness_cap = 0
elif app_state.matrix_rain_time_brightness_cap > MAX_BRIGHTNESS:
    app_state.matrix_rain_time_brightness_cap = MAX_BRIGHTNESS

if not isinstance(manual_time_offset, int):
    manual_time_offset = 0

seasonal_time_region = time_sync.normalise_seasonal_time_region(seasonal_time_region)

scenes = read_optional_json(scenes_file, config.get('SCENES', {}))
if not isinstance(scenes, dict):
    log_boot("Invalid scenes config, ignoring it")
    scenes = {}

schedules = read_optional_json(schedules_file, config.get('SCHEDULES', []))
if not isinstance(schedules, list):
    log_boot("Invalid schedules config, ignoring it")
    schedules = []
valid_schedules = validate_schedules(schedules)

log_boot_summary()

        
if config['ENABLE_HT16K33']:
    log_boot("Initialising HT16K33 matrix")
    scan_for_devices()
    i2c_matrix = HT16K33Matrix(config['I2C_SDA'], config['I2C_SCL'], config['I2C_BUS'],  int(config['I2C_ADDRESS'], 16))

if config['ENABLE_MAX7219']:
    log_boot("Initialising MAX7219 matrix")
    spi = machine.SPI(config['SPI_PORT'], sck=machine.Pin(config['SPI_SCK']), mosi=machine.Pin(config['SPI_MOSI']))
    spi_matrix = MAX7219Matrix(spi, machine.Pin(config['SPI_CS'], machine.Pin.OUT, True))
    spi_matrix.set_brightness(17)

if config['ENABLE_WS2812B']:
    log_boot("Initialising WS2812B matrix")
    ws2812b_matrix = WS2812BMatrix(config['WS2812B_PIN'], 8, 8)
    ws2812b_matrix.set_brightness(app_state.brightness)

log_boot("Running startup animation")
startup_animation()

log_boot("Creating web server")
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

log_boot("Boot complete, starting event loop")
asyncio.run(server.start_server_with_background_task(main))
