#test_gc9a01.py

import qtpy_esp32s3_and_seeed_round_display as board
import displayio
from gc9a01 import GC9A01
import busio
import busdisplay

if 'spi' in globals():
    spi.deinit()
    del spi
spi = busio.SPI(clock=board.SCK, MOSI= board.MOSI, MISO=board.MISO)
while not spi.try_lock():
    pass
spi.configure(baudrate=20_000_000) # Configure SPI for 24MHz
spi.unlock()
WIDTH = 240
HEIGHT = 240
FONTSCALE = 1
ROTATION = 270
displayio.release_displays()
display_bus = displayio.FourWire(spi, command=board.LCD_DC, chip_select=board.LCD_CS, reset=None)
display = GC9A01(display_bus, width=WIDTH, height=WIDTH, rotation=ROTATION, backlight_pin=board.BACKLIGHT)


from adafruit_display_shapes.rect import Rect
from adafruit_display_shapes.circle import Circle
from adafruit_display_shapes.roundrect import RoundRect

my_display_group = displayio.Group()
display.root_group = my_display_group

roundrect0 = RoundRect(80, 150, 20, 60, 15, fill=0x00FF00, outline=0xFF00FF, stroke=3)
roundrect1 = RoundRect(50, 100, 40, 80, 10, fill=0x0, outline=0xFF00FF, stroke=3)

my_display_group.append(roundrect0)
my_display_group.append(roundrect1)


