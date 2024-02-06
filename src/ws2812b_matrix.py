import machine
import neopixel

class ws2812b_matrix:

    def __init__(self, pin, width, height):
        self.width = width
        self.height = height
        self.np = neopixel.NeoPixel(machine.Pin(pin), width*height)
        self.char = [0x3c,0x56,0x93,0xdb,0xff,0xff,0xdd,0x89]
        self.brightness = 7
        self.max_brightness = 15
        self.set_brightness(self.brightness)

    def show_char(self, char, color=(255, 255, 255)):
        self.char = char
        adjusted_color = self.adjust_for_brightness(color)
        for i in range(8):
            for j in range(8):
                if char[i] & (1 << 7 - j):
                    self.np[i*8+j] = adjusted_color
                else:
                    self.np[i*8+j] = (0, 0, 0)
        self.np.write()
        return True
    
    def show_char_with_color_array(self, char, color_array):
        self.char = char
        for i in range(8):
            for j in range(8):
                if char[i] & (1 << 7 - j):
                    adjusted_color = self.adjust_for_brightness(color_array[i*8+j])
                    self.np[i*8+j] = adjusted_color
                else:
                    self.np[i*8+j] = (0, 0, 0)
        self.np.write()
        return True
    
    def set_brightness(self, brightness):
        if 0 <= brightness <= self.max_brightness:
            self.brightness = brightness
        else:
            raise ValueError(f"Brightness must be between 0 and {self.max_brightness}")

    def set_pixel(self, x, y, color):
        self.np[x*8+y] = color
        self.np.write()

    def adjust_for_brightness(self, color):
        brightness_scale = (self.brightness+1)/(self.max_brightness+1)
        return tuple([int(x*brightness_scale) for x in color])

    def show(self):
        self.np.write()

    def clear(self):
        for i in range(self.width*self.height):
            self.np[i] = (0, 0, 0)
        self.np.write()

    def fill(self, color):
        for i in range(self.width*self.height):
            self.np[i] = color
        self.np.write()

    def set_char(self, char):
        self.char = char

    def get_char(self):
        return self.char
    
    def get_rainbow_array(self):
        rainbow = []
        for i in range(self.width * self.height):
            color_position = int(i * 256 / (self.width * self.height))
            rainbow.append(self.wheel(color_position))
        return rainbow

    def wheel(self, pos):
        # Input a value 0 to 255 to get a color value.
        # The colors are a transition r - g - b - back to r.
        if pos < 0 or pos > 255:
            return (0, 0, 0)
        if pos < 85:
            return (255 - pos * 3, pos * 3, 0)
        if pos < 170:
            pos -= 85
            return (0, 255 - pos * 3, pos * 3)
        pos -= 170
        return (pos * 3, 0, 255 - pos * 3)
