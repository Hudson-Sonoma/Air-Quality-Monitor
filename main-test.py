# STELLA-AQ Air Quality instrument
# NASA open source software license
# Paul Mirel 2023

# this software will work with any combination of these three sensors:
# BME280 WX(weather) sensor, SCD-40 carbon dioxide sensor, PMSA003I air quality (particulates) sensor.

SOFTWARE_VERSION_NUMBER = "1.5.0"
print( "SOFTWARE_VERSION_NUMBER = {}".format( SOFTWARE_VERSION_NUMBER ))

# load libraries
import gc
#gc.collect()
start_mem_free_kB = gc.mem_free()/1000
print("start memory free {} kB".format( start_mem_free_kB ))

import os
import microcontroller
import qtpy_esp32s3_and_seeed_round_display as board
import digitalio
import time
import rtc
import neopixel
import sdcardio  #replacement for sdioio
import storage
import busio
from analogio import AnalogIn
from adafruit_pcf8563.pcf8563 import PCF8563
from adafruit_bme280 import basic as adafruit_bme280
import adafruit_scd4x
from adafruit_pm25.i2c import PM25_I2C
import displayio
import terminalio
from gc9a01 import GC9A01

#from adafruit_display_text.bitmap_label import Label
from adafruit_display_text import label
import vectorio # for shapes
from color_palette import PALETTE
import touchpad as tpad_cp
import atexit
from his import History, timed_function, HistoryFiles
import microcontroller
import watchdog
from qr_group import qr_group

display = board.DISPLAY
display.root_group = qr_group(b"https://www.adafruit.com/circuitpython","line1",scale=4)

while True:
    time.sleep(0.5)