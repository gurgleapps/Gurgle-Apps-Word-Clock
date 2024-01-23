import machine, neopixel

class ws2812b_matrix:

    def __init__(self, pin, width, height):
        self.width = width
        self.height = height
        self.np = neopixel.NeoPixel(machine.Pin(pin), width*height)
        self.char = [0x3c,0x56,0x93,0xdb,0xff,0xff,0xdd,0x89]
        self.brightness = 7
        self.max_brightness = 15
        self.set_brightness(self.brightness)

    def show_char(self, char, colour=(255,255,255)):
        self.char = char
        adjusted_colour = self.adjust_for_brightness(colour)
        for i in range(8):
            for j in range(8):
                if char[i] & (1 << 7 - j):
                    self.np[i*8+j] = adjusted_colour
                else:
                    self.np[i*8+j] = (0,0,0)
        self.np.write()
        return True
    
    def set_brightness(self, brightness):
        if 0 <= brightness <= self.max_brightness:
            self.brightness = brightness
        else:
            raise ValueError(f"Brightness must be between 0 and {self.max_brightness}")

    def set_pixel(self, x, y, colour):
        self.np[x*8+y] = colour
        self.np.write()

    def adjust_for_brightness(self, colour):
        brightness_scale = self.brightness/self.max_brightness
        return tuple([int(x*brightness_scale) for x in colour])

    def show(self):
        self.np.write()

    def clear(self):
        for i in range(self.width*self.height):
            self.np[i] = (0,0,0)
        self.np.write()

    def fill(self, colour):
        for i in range(self.width*self.height):
            self.np[i] = colour
        self.np.write()

    def set_char(self, char):
        self.char = char

    def get_char(self):
        return self.char
    



