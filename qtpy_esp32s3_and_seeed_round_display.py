
from board import *
from micropython import const
# ESP32C3 Xiao Pinout, connected to a Seeed round display.
#D0 = const(1)  # A0/BAT or spare (KE switch)
VOLTAGE_MONITOR = A0
#D1 = const(2)  ; 
LCD_CS = A1
#D2 = const(3)  ; 
SD_CS = A2
#D3 = const(4)  ; 
LCD_DC = A3
#D4 = const(5)  ; #SDA = A4
#D5 = const(6)  ; #SCL = A5
#D6 = const(43) ; 
BACKLIGHT = TX #or spare (KE switch)
#D7 = const(44) ; 
TP_INT = RX # touch panel interrupt
#D8 = const(7)  ; #SCK = D8
#D9 = const(8)  ; #MISO = D9
#D10 = const(9) ; #MOSI = D10

SD_CARD_SLOT = 1
LCD_CARD_SLOT = 1

import busio
import sdcardio
import storage
# initialize spi bus and SD card storage
try:
    #sdcard = sdioio.SDCard( clock=board.SDIO_CLOCK, command=board.SDIO_COMMAND, data=board.SDIO_DATA, frequency=25000000 )
    SPI = busio.SPI(clock=SCK, MOSI= MOSI, MISO=MISO)
    while not SPI.try_lock():
            pass
    SPI.configure(baudrate=40_000_000) # Configure SPI for 24MHz
    SPI.unlock()
    SDCARD = sdcardio.SDCard( SPI, SD_CS)   # board.SPI()

    print( "initalized sd card" )
    VFS = storage.VfsFat(SDCARD)
    print( "established vfs" )
    storage.mount(VFS, "/sd")
    print( "mounted vfs" )

except( OSError, ValueError ) as err:
    print( "No SD card found, or card is full: {}".format(err) )
    SPI = False
    SDCARD = False
    VFS = False

import displayio
import atexit
import time


def bye():
    print("Goodbye")
    if VFS:
        storage.umount("/sd")
    if SDCARD:
        SDCARD.deinit()
    print( "sd card deinitialized" )
    # display.root_group = end_program_screen
    # display.refresh()
    displayio.release_displays()
    print( "displayio displays released" )
    if SPI:
        SPI.deinit()
    print( "i2c_buses and SPI bus deinitialized" ) 
    time.sleep(0.05)

atexit.register(bye)