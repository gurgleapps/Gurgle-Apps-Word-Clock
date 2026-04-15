MATRIX_RAIN_DEFAULT_BACKGROUND_COLOR = (0, 255, 0)
MATRIX_RAIN_DEFAULT_MINUTE_COLOR = (255, 0, 0)
MATRIX_RAIN_DEFAULT_HOUR_COLOR = (255, 255, 0)
MATRIX_RAIN_DEFAULT_PAST_TO_COLOR = (255, 128, 0)
MATRIX_RAIN_DEFAULT_SPEED_MS = 120
MATRIX_RAIN_DEFAULT_WHITE_HEAD = False
MATRIX_RAIN_DEFAULT_AFFECT_TIME = False
MATRIX_RAIN_DEFAULT_SPAWN_RATE = 18
MATRIX_RAIN_DEFAULT_TRAIL_LENGTH = 4
MATRIX_RAIN_DEFAULT_TIME_BRIGHTNESS_CAP = 3
MATRIX_RAIN_FADE_STEP = 36


class MatrixRainState:
    def __init__(self):
        self.intensity = []
        self.columns = []
        self.time_char = None
        self.time_color_array = None
        self.time_minute_key = None

    def has_state(self):
        return bool(self.intensity)

    def reset(self, trail_length):
        self.intensity = [[0 for _ in range(8)] for _ in range(8)]
        self.columns = []
        for _ in range(8):
            self.columns.append({
                'active': False,
                'head': 0,
                'trail_length': trail_length
            })

    def reset_time_overlay(self):
        self.time_char = None
        self.time_color_array = None
        self.time_minute_key = None

    def color_for_intensity(self, intensity, background_color, white_head):
        if intensity <= 0:
            return (0, 0, 0)
        if white_head and intensity >= 235:
            return (255, 255, 255)
        return tuple((channel * intensity) // 255 for channel in background_color)

    def get_frame_data(self, background_color, white_head, trail_length):
        if not self.intensity:
            self.reset(trail_length)
        char = [0] * 8
        color_array = [(0, 0, 0)] * 64
        for row in range(8):
            row_bits = 0
            for column in range(8):
                intensity = self.intensity[row][column]
                if intensity > 0:
                    row_bits |= (1 << (7 - column))
                    color_array[row * 8 + column] = self.color_for_intensity(
                        intensity,
                        background_color,
                        white_head
                    )
            char[row] = row_bits
        return char, color_array

    def get_time_overlay(self, current_display_minute_key, build_time_word_data, matrix_mode):
        minute_key = current_display_minute_key()
        if self.time_char is None or self.time_color_array is None or self.time_minute_key != minute_key:
            self.time_char, self.time_color_array, _ = build_time_word_data(matrix_mode)
            self.time_minute_key = minute_key
        return self.time_char, self.time_color_array

    def advance(self, random_module, spawn_rate, trail_length):
        if not self.intensity:
            self.reset(trail_length)

        for row in range(8):
            for column in range(8):
                next_value = self.intensity[row][column] - MATRIX_RAIN_FADE_STEP
                self.intensity[row][column] = next_value if next_value > 0 else 0

        for column_index in range(8):
            column_state = self.columns[column_index]
            if not column_state['active']:
                if random_module.randint(0, 99) < spawn_rate:
                    column_state['active'] = True
                    column_state['head'] = 0
                    column_state['trail_length'] = trail_length
                continue

            head_row = column_state['head']
            active_trail_length = column_state['trail_length']
            for offset in range(active_trail_length):
                row = head_row - offset
                if 0 <= row < 8:
                    intensity = 255 - (offset * 45)
                    current_intensity = self.intensity[row][column_index]
                    if intensity > current_intensity:
                        self.intensity[row][column_index] = intensity

            column_state['head'] += 1
            if column_state['head'] - active_trail_length > 7:
                column_state['active'] = False


def apply_brightness_cap_to_color(color, brightness, cap_brightness):
    if brightness <= cap_brightness:
        return color

    current_scale = brightness + 1
    capped_scale = cap_brightness + 1
    return tuple((channel * capped_scale) // current_scale for channel in color)


def render(
    state,
    *,
    background_color,
    white_head,
    affect_time,
    trail_length,
    time_brightness_cap,
    brightness,
    config,
    spi_matrix,
    i2c_matrix,
    ws2812b_matrix,
    current_display_minute_key,
    build_time_word_data,
    matrix_mode
):
    rain_char, rain_color_array = state.get_frame_data(background_color, white_head, trail_length)
    time_char, time_color_array = state.get_time_overlay(
        current_display_minute_key,
        build_time_word_data,
        matrix_mode
    )
    char = [0] * 8
    color_array = [(0, 0, 0)] * 64

    for row in range(8):
        if affect_time:
            char[row] = rain_char[row] | time_char[row]
        else:
            char[row] = (rain_char[row] & (~time_char[row] & 0xFF)) | time_char[row]

    for pixel_index in range(64):
        row = pixel_index // 8
        column = pixel_index % 8
        time_bit = time_char[row] & (1 << (7 - column))
        rain_color = rain_color_array[pixel_index]
        if time_bit:
            if affect_time and rain_color != (0, 0, 0):
                rr, rg, rb = rain_color
                tr, tg, tb = time_color_array[pixel_index]
                blended_color = (
                    max(tr, rr),
                    max(tg, rg),
                    max(tb, rb)
                )
                color_array[pixel_index] = apply_brightness_cap_to_color(
                    blended_color,
                    brightness,
                    time_brightness_cap
                )
            else:
                color_array[pixel_index] = apply_brightness_cap_to_color(
                    time_color_array[pixel_index],
                    brightness,
                    time_brightness_cap
                )
        else:
            color_array[pixel_index] = rain_color

    if config['ENABLE_MAX7219']:
        spi_matrix.show_char(char)
    if config['ENABLE_HT16K33']:
        if not i2c_matrix.show_char(i2c_matrix.reverse_char(char)):
            print("Error writing to matrix")
    if config['ENABLE_WS2812B']:
        ws2812b_matrix.set_brightness(brightness)
        ws2812b_matrix.show_char_with_color_array(char, color_array)
