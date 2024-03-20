#test_microdot.py

# this happens automatically when the board is plugged in
# ssid = os.getenv("CIRCUITPY_WIFI_SSID")
# password = os.getenv("CIRCUITPY_WIFI_PASSWORD")

# print("Connecting to", ssid)
# wifi.radio.connect(ssid, password)
# print("Connected to", ssid)

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
spi.configure(baudrate=20_000_000) # Configure SPI for 24MHz
spi.unlock()
sdcard = sdcardio.SDCard( spi, board.SD_CS)   # board.SPI()
vfs = storage.VfsFat(sdcard)
storage.mount(vfs, "/sd")

import os
import wifi

print("Connecting to", os.getenv("STELLA_WIFI_SSID"))
wifi.radio.connect(os.getenv("STELLA_WIFI_SSID"), os.getenv("STELLA_WIFI_PASSWORD"))
print("Connected as ip address", wifi.radio.ipv4_address)

import socketpool
import wifi
from adafruit_httpserver import Server, Request, Response, ChunkedResponse

pool = socketpool.SocketPool(wifi.radio)
server = Server(pool, "/sd", debug=True)

@server.route("/data.csv")
def chunked(request: Request):
    """
    Return the response with ``Transfer-Encoding: chunked``.
    """
    
    def body():
        f = io.open("/sd/data.csv", "r")
        buf = bytearray(31*1024)
        mv = memoryview(buf)
        while True:
            len = f.readinto(buf)
            if len == 0:
                break
            yield mv[:len]

    return ChunkedResponse(request, body)


try:
    server.serve_forever(str(wifi.radio.ipv4_address),port=8001)
finally:
    server.stop()
    storage.umount("/sd")
    sdcard.deinit()
    spi.deinit()


server.stop()
storage.umount("/sd")
sdcard.deinit()
spi.deinit()