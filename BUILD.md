Circuitpython on an Seeed Xiao ESP32-C3

python3.11 ../micropython/tools/mpremote/mpremote.py

##
## CircutPython
##

# build circutpython
cd ../circuitpython
git pull
cd ports/espressif/
make fetch-port-submodules
cd esp-idf/components
git submodule update --init --recursive
cd ../../../..
make -C mpy-cross
cd ports/espressif/
# use vendored esp-idf
cd ../esp-idf ; source ./export.sh
make clean BOARD=adafruit_qtpy_esp32s3_4mbflash_2mbpsram
make BOARD=adafruit_qtpy_esp32s3_4mbflash_2mbpsram

alias flashesp='~/.platformio/packages/tool-esptoolpy/esptool.py'
#flashesp --port /dev/tty.usbmodem14201 write_flash -z 0x0 firmware.bin
# hold boot, press release reset.
flashesp  --chip esp32s3 --port /dev/tty.usbmodem14201 erase_flash 
flashesp --chip esp32s3 --port /dev/tty.usbmodem14201 -b 460800 --before default_reset --after no_reset write_flash --flash_mode dio --flash_size 4MB --flash_freq 80m 0x0 build-adafruit_qtpy_esp32s3_4mbflash_2mbpsram/firmware.bin 
rm /Volumes/CIRCUITPY/code.py


mpremote connect /dev/tty.usbmodem4F21AFA5254E1


# Adafruit CircuitPython 9.0.0-beta.0-12-gcd28f1d678 on 2024-02-03; Adafruit QT Py ESP32-S3 4MB Flash 2MB PSRAM with ESP32S3
# Adafruit CircuitPython 9.0.0-beta.1-1-g8728c6de70 on 2024-02-18; Adafruit QT Py ESP32-S3 4MB Flash 2MB PSRAM with ESP32S3
free memory remaining = 1967.74 kB, 96.3228%, loop 2, max 2, error count 0
# Adafruit CircuitPython 9.0.0-beta.2-9-geb74d13a8f-dirty on 2024-02-22; Adafruit QT Py ESP32-S3 4MB Flash 2MB PSRAM with ESP32S3
free memory remaining = 1967.62 kB, 96.3165%, loop 2, max 2, error count 0
>>> foo.__name__
'foo'


adafruit_qtpy_esp32s3_nopsram
make clean BOARD=adafruit_qtpy_esp32s3_nopsram
make BOARD=adafruit_qtpy_esp32s3_nopsram
flashesp --chip esp32s3 --port /dev/tty.usbmodem14201 -b 460800 --before default_reset --after no_reset write_flash --flash_mode dio --flash_size 4MB --flash_freq 80m 0x0 build-adafruit_qtpy_esp32s3_nopsram/firmware.bin 
# Adafruit CircuitPython 9.0.0-beta.2-9-geb74d13a8f-dirty on 2024-02-23; Adafruit QT Py ESP32-S3 no psram with ESP32S3
free memory remaining = 122.32 kB, 61.9078%, loop 1, max 1, error count 0


cp tpad_cp.py color_palette.py main.py qtpy_esp32s3_and_seeed_round_display.py /Volumes/CIRCUITPY

# make mpy files
for f in *.py ; do ../../../circuitpython/mpy-cross/build/mpy-cross $f ; done

# SYNC LIB
# rsync files excluding source files *.py only  (so do .mpy compiled files)
rsync -v -r --prune-empty-dirs --exclude='*.py' lib /Volumes/CIRCUITPY




# Adafruit CircuitPython 9.0.0-rc.0-14-g20156b59c8-dirty on 2024-03-14; Adafruit QT Py ESP32-S3 4MB Flash 2MB PSRAM with ESP32S3
# /Volume/CIRCUITPY broken!! with 9.0.0-rc.0-14-g20156b59c8-dirty
