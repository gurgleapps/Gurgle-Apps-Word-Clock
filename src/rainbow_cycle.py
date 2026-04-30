RAINBOW_CYCLE_STYLE_PIXEL = 'pixel'
RAINBOW_CYCLE_STYLE_LETTER = 'letter'
RAINBOW_CYCLE_STYLE_WORD = 'word'
RAINBOW_CYCLE_STYLE_SINGLE = 'single'

RAINBOW_CYCLE_STYLES = (
    RAINBOW_CYCLE_STYLE_PIXEL,
    RAINBOW_CYCLE_STYLE_LETTER,
    RAINBOW_CYCLE_STYLE_WORD,
    RAINBOW_CYCLE_STYLE_SINGLE
)

RAINBOW_CYCLE_DEFAULT_STYLE = RAINBOW_CYCLE_STYLE_LETTER
RAINBOW_CYCLE_DEFAULT_SPEED_MS = 125
RAINBOW_CYCLE_DEFAULT_SPREAD = 7
RAINBOW_CYCLE_DEFAULT_STEP = 3
RAINBOW_CYCLE_MIN_SPEED_MS = 40
RAINBOW_CYCLE_MAX_SPEED_MS = 400
RAINBOW_CYCLE_MIN_SPREAD = 1
RAINBOW_CYCLE_MAX_SPREAD = 16
RAINBOW_CYCLE_MIN_STEP = 1
RAINBOW_CYCLE_MAX_STEP = 16


class RainbowCycleState:
    def __init__(self):
        self.offset = 0

    def reset(self):
        self.offset = 0

    def advance(self, step=RAINBOW_CYCLE_DEFAULT_STEP):
        step = clamp_step(step)
        self.offset = (self.offset - step) % 256


def normalise_style(style):
    if style in RAINBOW_CYCLE_STYLES:
        return style
    return RAINBOW_CYCLE_DEFAULT_STYLE


def clamp_speed_ms(speed_ms):
    if not isinstance(speed_ms, int):
        return RAINBOW_CYCLE_DEFAULT_SPEED_MS
    if speed_ms < RAINBOW_CYCLE_MIN_SPEED_MS:
        return RAINBOW_CYCLE_MIN_SPEED_MS
    if speed_ms > RAINBOW_CYCLE_MAX_SPEED_MS:
        return RAINBOW_CYCLE_MAX_SPEED_MS
    return speed_ms


def clamp_spread(spread):
    if not isinstance(spread, int):
        return RAINBOW_CYCLE_DEFAULT_SPREAD
    if spread < RAINBOW_CYCLE_MIN_SPREAD:
        return RAINBOW_CYCLE_MIN_SPREAD
    if spread > RAINBOW_CYCLE_MAX_SPREAD:
        return RAINBOW_CYCLE_MAX_SPREAD
    return spread


def clamp_step(step):
    if not isinstance(step, int):
        return RAINBOW_CYCLE_DEFAULT_STEP
    if step < RAINBOW_CYCLE_MIN_STEP:
        return RAINBOW_CYCLE_MIN_STEP
    if step > RAINBOW_CYCLE_MAX_STEP:
        return RAINBOW_CYCLE_MAX_STEP
    return step


def wheel(pos):
    pos = pos % 256
    if pos < 43:
        return (255, pos * 6, 0)
    if pos < 85:
        pos -= 43
        return (255 - pos * 6, 255, 0)
    if pos < 128:
        pos -= 85
        return (0, 255, pos * 6)
    if pos < 171:
        pos -= 128
        return (0, 255 - pos * 6, 255)
    if pos < 213:
        pos -= 171
        return (pos * 6, 0, 255)
    pos -= 213
    return (255, 0, 255 - pos * 6)


def _pixel_is_lit(char, row, column):
    return bool(char[row] & (1 << (7 - column)))


def _blank_color_array():
    return [(0, 0, 0)] * 64


def _render_pixel_rainbow(char, wheel, offset, spread):
    color_array = _blank_color_array()
    for row in range(8):
        for column in range(8):
            pixel_index = row * 8 + column
            if _pixel_is_lit(char, row, column):
                color_array[pixel_index] = wheel((offset + pixel_index * spread) % 256)
    return color_array


def _render_letter_rainbow(char, wheel, offset, spread):
    color_array = _blank_color_array()
    lit_index = 0
    for row in range(8):
        for column in range(8):
            pixel_index = row * 8 + column
            if _pixel_is_lit(char, row, column):
                color_array[pixel_index] = wheel((offset + lit_index * spread) % 256)
                lit_index += 1
    return color_array


def _render_single_color(char, wheel, offset):
    color_array = _blank_color_array()
    color = wheel(offset)
    for row in range(8):
        for column in range(8):
            pixel_index = row * 8 + column
            if _pixel_is_lit(char, row, column):
                color_array[pixel_index] = color
    return color_array


def _word_section_index(pixel_color, minute_color, hour_color, past_to_color):
    if pixel_color == minute_color:
        return 0
    if pixel_color == past_to_color:
        return 1
    if pixel_color == hour_color:
        return 2
    return 0


def _render_word_sections(char, time_color_array, wheel, offset, minute_color, hour_color, past_to_color):
    color_array = _blank_color_array()
    section_offsets = (0, 85, 170)
    for row in range(8):
        for column in range(8):
            pixel_index = row * 8 + column
            if _pixel_is_lit(char, row, column):
                section_index = _word_section_index(
                    time_color_array[pixel_index],
                    minute_color,
                    hour_color,
                    past_to_color
                )
                color_array[pixel_index] = wheel((offset + section_offsets[section_index]) % 256)
    return color_array


def build_color_array(
    char,
    *,
    style,
    spread,
    offset,
    wheel,
    time_color_array,
    minute_color,
    hour_color,
    past_to_color
):
    style = normalise_style(style)
    spread = clamp_spread(spread)
    if style == RAINBOW_CYCLE_STYLE_LETTER:
        return _render_letter_rainbow(char, wheel, offset, spread)
    if style == RAINBOW_CYCLE_STYLE_WORD:
        return _render_word_sections(
            char,
            time_color_array,
            wheel,
            offset,
            minute_color,
            hour_color,
            past_to_color
        )
    if style == RAINBOW_CYCLE_STYLE_SINGLE:
        return _render_single_color(char, wheel, offset)
    return _render_pixel_rainbow(char, wheel, offset, spread)


def render(
    state,
    *,
    char,
    time_color_array,
    style,
    spread,
    brightness,
    config,
    ws2812b_matrix,
    minute_color,
    hour_color,
    past_to_color
):
    if config['ENABLE_WS2812B']:
        ws2812b_matrix.set_brightness(brightness)
        color_array = build_color_array(
            char,
            style=style,
            spread=spread,
            offset=state.offset,
            wheel=wheel,
            time_color_array=time_color_array,
            minute_color=minute_color,
            hour_color=hour_color,
            past_to_color=past_to_color
        )
        ws2812b_matrix.show_char_with_color_array(char, color_array)
