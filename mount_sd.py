import qtpy_esp32s3_and_seeed_round_display as board
import busio
import sdcardio
import storage
import io
import gc

if 'sdcard' in globals():
    sdcard.deinit()
    del sdcard
if 'spi' in globals():
    spi.deinit()
    del spi
spi = busio.SPI(clock=board.SCK, MOSI= board.MOSI, MISO=board.MISO)
while not spi.try_lock():
    pass
spi.configure(baudrate=40_000_000) # Configure SPI
spi.unlock()
sdcard = sdcardio.SDCard( spi, board.SD_CS)   # board.SPI()
vfs = storage.VfsFat(sdcard)
storage.mount(vfs, "/sd")