import array, machine, rp2

# PIO program for WS2812
@rp2.asm_pio(
    sideset_init=rp2.PIO.OUT_LOW,
    out_shiftdir=rp2.PIO.SHIFT_LEFT,
    autopull=True,
    pull_thresh=24,
)
def ws2812():
    T1 = 2
    T2 = 5
    T3 = 3
    label("bitloop")
    out(x, 1).side(0) [T3 - 1]
    jmp(not_x, "do_zero").side(1) [T1 - 1]
    jmp("bitloop").side(1) [T2 - 1]
    label("do_zero")
    nop().side(0) [T2 - 1]
    jmp("bitloop")

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