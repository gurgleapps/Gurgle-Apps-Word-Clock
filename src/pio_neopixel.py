import array, machine, rp2

# PIO program for WS2812
@rp2.asm_pio(
    sideset_init=rp2.PIO.OUT_LOW, # Data line starts low
    out_shiftdir=rp2.PIO.SHIFT_LEFT, # Shift bits out left to right
    autopull=True, # Automatically pull data from TX FIFO
    pull_thresh=24, # 24 bits per pixel (8 bits each for G,R,B
)
def ws2812():
    T1 = 2 # 0.625us
    T2 = 5 # 1.25us
    T3 = 3 # 0.375us
    label("bitloop") # Loop for each bit
    out(x, 1).side(0) [T3 - 1] # Shift out 1 bit to x
    jmp(not_x, "do_zero").side(1) [T1 - 1] # If bit is 1
    jmp("bitloop").side(1) [T2 - 1] # Continue with bitloop
    label("do_zero") # If bit is 0
    nop().side(0) [T2 - 1] # Stay low
    jmp("bitloop") # Continue with bitloop

class PioNeoMatrix:
    """
    NeoPixel-compatible PIO driver.
    Drop-in replacement for neopixel.NeoPixel
    which caused issues on picow2
    """
    def __init__(self, pin_num, n, sm_id=0):
        self.n = n
        self.pin = machine.Pin(pin_num, machine.Pin.OUT)
        self.buf = array.array("I", [0] * n)

        self.sm = rp2.StateMachine(
            sm_id, ws2812, freq=8_000_000, sideset_base=self.pin
        )
        self.sm.active(1)

    # ----- Drop-in NeoPixel compatibility -----

    # np[i] = (r,g,b)
    def __setitem__(self, i, color):
        r, g, b = color
        self.buf[i] = (g << 16) | (r << 8) | b

    # np[i] -> (r,g,b)
    def __getitem__(self, i):
        v = self.buf[i]
        return ((v >> 8) & 0xFF, v >> 16 & 0xFF, v & 0xFF)

    def __len__(self):
        return self.n

    def fill(self, color):
        r, g, b = color
        v = (g << 16) | (r << 8) | b
        for i in range(self.n):
            self.buf[i] = v

    def write(self):
        self.sm.put(self.buf, 8)