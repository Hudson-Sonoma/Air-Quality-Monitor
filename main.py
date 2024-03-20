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
import tpad_cp
import atexit
from his import History, timed_function, HistoryFiles
import microcontroller
import watchdog
from qr_group import qr_group
import wifi

DAYS = { 0:"Sunday", 1:"Monday", 2:"Tuesday", 3:"Wednesday", 4:"Thursday", 5:"Friday", 6:"Saturday" }
DATA_FILE = "/sd/data.csv"
LOW_BATTERY_VOLTAGE = 3.4
RED =   ( 0, 255, 0 )
GREEN = ( 255, 0, 0 )
BLUE =  ( 0, 0, 255 )
ORANGE = ( 24, 64, 0 )
PURPLE = ( 0, 64, 64 )
OFF =   ( 0,0,0 )

TIME_START = ( 2020,  01,   01,   00,  00,  00,   0,   -1,    -1 )
TIME_START_S = time.mktime( TIME_START )

def main():
    try:
        null_time = time.struct_time(TIME_START)
        batch_number = 0
        displayio.release_displays()

        UID = int.from_bytes(microcontroller.cpu.uid, "big") % 10000
        print("unique identifier (UID) : {0}".format( UID ))

        # # initialize on board LED and on board neopixel
        # onboard_LED = digitalio.DigitalInOut( board.LED )
        # onboard_LED.direction = digitalio.Direction.OUTPUT
        # # flash to say hello
        # for i in range( 3 ):
        #     onboard_LED.value = True
        #     time.sleep( 0.1 )
        #     onboard_LED.value = False
        #     time.sleep( 0.1 )
        # onboard_LED.value = True

        on_board_neopixel_pin = board.NEOPIXEL
        num_pixels = 1
        ORDER = neopixel.RGB
        pixels = neopixel.NeoPixel( on_board_neopixel_pin, num_pixels, brightness=0.2, auto_write=True, pixel_order=ORDER )

        if not board.SPI:
            pixels.fill( RED )

        header = ( "STELLA-AQ, timestamp, UID, batch, AQIp, CO2_sensor_stale_data, CO2_ppm, CO2_tolerance, "
            "CO2_sensor_air_temperature_C, CO2_sensor_air_temperature_tolerance, CO2_sensor_relative_humidity_%, CO2_sensor_relative_humidity_tolerance, "
            "WX_sensor_air_temperature_C, WX_sensor_air_temperature_tolerance, WX_sensor_relative_humidity_%, WX_sensor_relative_humidity_tolerance, "
            "WX_sensor_barometric_pressure_hPa, WX_sensor_barometric_pressure_tolerance, WX_sensor_altitude_m, WX_sensor_altitude_tolerance, "
            "1um_concentration_ug_m^3, 2_5um_concentration_ug_m^3, 10um_concentration_ug_m^3, particle_concentration_tolerance_ug, "
            "0_3um_count_p_100mL, 0_5um_count_p_100mL, 1um_count_p_100mL, 2_5um_count_p_100mL, 5um_count_p_100mL, 10um_count_p_100mL, "
            "battery_voltage"
            "\n" )
        columns_and_units = [
        # "timestamp", # "timestamp" named column handled separately as uint32, everything else is a float.
        "UID.number",
        "batch.number",
        "AQIp.number",
        "CO2_stale_data.number",
        "CO2_conc.ppm",
        "CO2_tolerance.ppm",
        "CO2_air_temperature.degC",
        "CO2_air_temperature_tolerance.degC",
        "CO2_relative_humidity.percent",
        "CO2_relative_humidity_tolerance.percent",
        "WX_air_temperature.degC",
        "WX_air_temperature_tolerance.degC",
        "WX_relative_humidity.percent",
        "WX_relative_humidity_tolerance.percent",
        "WX_barometric_pressure.hPa",
        "WX_barometric_pressure_tolerance.hPa",
        "WX_altitude.meters",
        "WX_altitude_tolerance.meters",
        "concentration_1um.ug/m^3",
        "concentration_2_5um.ug/m^3",
        "concentration_10um.ug/m^3",
        "particle_conc_tolerance.ug/m^3",
        "count_0_3um.particles/100mL",
        "count_0_5um.particles/100mL",
        "count_1um.particles/100mL",
        "count_2_5um.particles/100mL",
        "count_5um.particles/100mL",
        "count_10um.particles/100mL",
        "main_battery_voltage.V",
        "dev_free_mem.bytes",
        "dev_free_mem_pct.percent",
        "dev_loop_count.number",
        "dev_max_loop_count.number",
        "dev_file_error_count.number",
        ]
        CO2_tolerance = "50ppm+5%_of_reading"
        CO2_sensor_air_temperature_tolerance = 6
        CO2_sensor_relative_humidity_tolerance = 1
        WX_sensor_air_temperature_tolerance = 1
        WX_sensor_relative_humidity_tolerance = 3
        WX_sensor_barometric_pressure_tolerance = 1
        WX_sensor_altitude_tolerance = 500
        particle_concentration_tolerance_ug_tol = 10

        # loop over columns, split on period, and take 0th element and return a list
        columns = [ c.split('.')[0] for c in columns_and_units ]
        units = [ c.split('.')[1] for c in columns_and_units ]

        # Init SD card and file
        if board.VFS:
            initialize_data_file("STELLA-AQ, " + ','.join(columns) + "\n", DATA_FILE)
            history_files = HistoryFiles(columns=columns)  # allocate exta recordsize space for more columns in future.


        # Init Local i2c_round_diplay bus
        try:
            i2c_local = busio.I2C(board.SCL, board.SDA, frequency=100_000) # need slower (100kHz) i2c bus speed for PM25 sensor
        except ValueError:
            i2c_local = False
            print( "i2c bus for round display fail -- press reset button, or power off to restart" )
            pixels.fill( ORANGE )

        # initialize stemma i2c bus
        try:
            i2c_stemma = board.STEMMA_I2C() # need slower (100kHz) i2c bus speed for PM25 sensor
        except ValueError:
            i2c_stemma = False
            print( "i2c bus STEMMA fail -- press reset button, or power off to restart" )
            pixels.fill( PURPLE )


        #
        # Init Display
        #
        if i2c_local:
            # initialize clock
            try:
                real_time_clock = PCF8563(i2c_local)
                timenow = real_time_clock.datetime
                if timenow.tm_wday not in range ( 0, 7 ):
                                        #(( year, mon, date, hour, min, sec, wday, yday, isdst ))
                    t = time.struct_time(( 2023,  01,   01,   00,  00,  00,   0,   -1,    -1 ))
                    real_time_clock.datetime = t
                timenow = real_time_clock.datetime
            except ValueError:
                timenow = null_time
            DAYS = ("Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday")
            print( "The date is %s %d-%d-%d" % ( DAYS[ timenow.tm_wday ], timenow.tm_year, timenow.tm_mon, timenow.tm_mday ))
            print( "The time is %d:%02d:%02d" % ( timenow.tm_hour, timenow.tm_min,timenow.tm_sec ))
            if real_time_clock:
                system_clock = rtc.RTC()
                system_clock.datetime = real_time_clock.datetime

        if i2c_stemma:
            batch_number = update_batch( timenow )
            # initialize WX
            try:
                WX_sensor = adafruit_bme280.Adafruit_BME280_I2C( i2c_stemma )
            except ValueError:
                WX_sensor = False

            # initialize CO2
            try:
                CO2_sensor = adafruit_scd4x.SCD4X( i2c_stemma )
                print( "CO2_sensor serial number:", [hex(i) for i in CO2_sensor.serial_number] )
                # DISABLE SENSOR HERE:
                CO2_sensor.start_periodic_measurement()
                CO2_reading = ( 0, 0, 0, 0 )
                last_CO2_reading = CO2_reading
            except ValueError:
                CO2_sensor = False

            # initialize PM25
            try:
                reset_pin = None
                pm25_sensor = PM25_I2C( i2c_stemma, reset_pin )
                pm25_reading = (0,0,0,0,0,0,0,0,0,0,0,0,0)
                last_pm25_reading = pm25_reading
            except (ValueError, RuntimeError):
                pm25_sensor = False

        # check for each device present. if not present, do not read, do not record that datum.
        # header should be for all devices, so the header works for a file even if a sensor has been added or subtracted

        # initialize display
        if board.SPI:
            try:
                WIDTH = 240
                HEIGHT = 240
                FONTSCALE = 1
                ROTATION = 270
                displayio.release_displays()
                display_bus = displayio.FourWire(board.SPI, command=board.LCD_DC, chip_select=board.LCD_CS, reset=None)
                display = GC9A01(display_bus, width=WIDTH, height=WIDTH, rotation=ROTATION, backlight_pin=board.BACKLIGHT)
                display.brighness = 0.25
                print( "initialized display" )
            except (OSError, ValueError) as err:
                print( "No LCD found: {}".format(err) )
                display = False

            info_screen = displayio.Group()
            time_screen = displayio.Group()
            data_screen = displayio.Group()
            end_program_screen = displayio.Group()
            qr_screen = qr_group(b"https://buildingpulse.org/","buildingpulse.org",scale=4,display_width=display.width,display_height=display.height)


        touchpad = False
        if display and i2c_local:
            try:
                touchpad = tpad_cp.TouchPad(i2c_local, width=240, height=240, screen_rotation=0, interrupt_pin=board.TP_INT)
            except ValueError:
                touchpad = False

        if display:
            WIDTH = 240
            HEIGHT = 240
            BORDER = 2
            XOFFSET = 56
            YOFFSET = 56

            def create_background_group():
                a_group = displayio.Group()
                border_color = PALETTE[13]
                border = displayio.Palette(1)
                border[0] = border_color
                outer_rectangle = vectorio.Rectangle(pixel_shader=border, width=WIDTH, height=HEIGHT, x=0, y=0)
                a_group.append( outer_rectangle )
                front_color = PALETTE[8]
                front = displayio.Palette(1)
                front[0] = front_color
                inner_rectangle = vectorio.Rectangle(pixel_shader=front, width=128-2*BORDER, height=128-2*BORDER, x=0+BORDER+XOFFSET, y=0+BORDER+YOFFSET)
                a_group.append( inner_rectangle)
                return a_group

            info_screen.append(create_background_group())
            time_screen.append(create_background_group())
            data_screen.append(create_background_group())
            end_program_screen.append(create_background_group())

            the_font_color = PALETTE[12]

            name_group = displayio.Group( scale=3, x=10+XOFFSET, y=25+YOFFSET )
            name_text = "STELLA"
            name_text_area = label.Label( terminalio.FONT, text=name_text, color=the_font_color )
            name_group.append( name_text_area )
            info_screen.append( name_group )

            subname_group = displayio.Group( scale=3, x=30+XOFFSET, y=60+YOFFSET ) #x=45, y=60 )
            subname_text = "-AQ-"
            subname_text_area = label.Label( terminalio.FONT, text=subname_text, color=the_font_color )
            subname_group.append( subname_text_area )
            info_screen.append( subname_group )

            UID_group = displayio.Group( scale=2, x=10+XOFFSET, y=90+YOFFSET )
            UID_text = "UID: " + str(UID)
            UID_text_area = label.Label( terminalio.FONT, text=UID_text, color=the_font_color )
            UID_group.append( UID_text_area )
            info_screen.append( UID_group )

            version_group = displayio.Group( scale=1, x=20+XOFFSET, y=113+YOFFSET )
            version_text = "Version: " + SOFTWARE_VERSION_NUMBER
            version_text_area = label.Label( terminalio.FONT, text=version_text, color=the_font_color )
            version_group.append( version_text_area )
            info_screen.append( version_group )

            print( "display welcome screen" )
            display.root_group = info_screen
            time.sleep(0.1)

        vbat_voltage_pin = AnalogIn(board.VOLTAGE_MONITOR)

        # colors = [RED, GREEN, BLUE]
        # for i in range (len(colors)):
        #     pixels.fill(colors[i])
        #     time.sleep( 0.75 )

        # if display:
        #     for i in range( 4 ):
        #         display_group.pop()

            # del name_group
            # del name_text
            # del name_text_area

            # del subname_group
            # del subname_text
            # del subname_text_area

            # del UID_group
            # del UID_text
            # del UID_text_area

            # del version_group
            # del version_text
            # del version_text_area
        if display:

            #gc.collect()
            timenow = real_time_clock.datetime

            date_group = displayio.Group( scale=2, x=5+XOFFSET, y=15+YOFFSET )
            date_text = ("{}-{:02d}-{:02d}".format( timenow.tm_year, timenow.tm_mon, timenow.tm_mday ))
            date_text_area = label.Label( terminalio.FONT, text=date_text, color=the_font_color )
            date_group.append( date_text_area )
            time_screen.append( date_group )

            time_group = displayio.Group( scale=2, x=11+XOFFSET, y=40+YOFFSET )
            time_text = ("{:02d}:{:02d}:{:02d}Z".format( timenow.tm_hour, timenow.tm_min, timenow.tm_sec ))
            time_text_area = label.Label( terminalio.FONT, text=time_text, color=the_font_color )
            time_group.append( time_text_area )
            time_screen.append( time_group )

            batch_group = displayio.Group( scale=2, x=15+XOFFSET, y=64+YOFFSET )
            batch_text = "batch {}".format(batch_number)
            batch_text_area = label.Label( terminalio.FONT, text=batch_text, color=the_font_color )
            batch_group.append( batch_text_area )
            time_screen.append( batch_group )

            main_battery_voltage = get_voltage(vbat_voltage_pin)
            if main_battery_voltage < LOW_BATTERY_VOLTAGE:
                main_battery_status = "LOW"
            elif main_battery_voltage > 4.0:
                main_battery_status = "FULL"
            else:
                main_battery_status = " OK"
            main_battery_group = displayio.Group( scale=1, x=10+XOFFSET, y=89+YOFFSET )
            main_battery_text = ("main battery: {}".format(main_battery_status))
            main_battery_text_area = label.Label( terminalio.FONT, text=main_battery_text, color=the_font_color )
            main_battery_group.append( main_battery_text_area )
            time_screen.append( main_battery_group )
            # if clock_battery_low:
            #     clock_battery_status = "LOW"
            # else:
            clock_battery_status = "OK"
            clock_battery_group = displayio.Group( scale=1, x=10+XOFFSET, y=109+YOFFSET )
            clock_battery_text = ("clock battery: {}".format( clock_battery_status ))
            clock_battery_text_area = label.Label( terminalio.FONT, text=clock_battery_text, color=the_font_color )
            clock_battery_group.append( clock_battery_text_area )
            time_screen.append( clock_battery_group )

        # create display structure
        # if display:
        #     for i in range( 5 ):
        #         display_group.pop()
                
        if display:
            display.root_group = time_screen
            time.sleep(0.05)
            print( "display time screen")
            colors = [RED, GREEN, BLUE, OFF]
            # for i in range (len(colors)):
            #     pixels.fill(colors[i])
            #     timenow = real_time_clock.datetime
            #     time_text_area.text = ("{:02d}:{:02d}:{:02d}Z".format( timenow.tm_hour, timenow.tm_min, timenow.tm_sec ))
            #     time.sleep( 0.75 )

            # del date_group
            # del date_text
            # del date_text_area

            # del time_screen
            # del time_text
            # del time_text_area

            # del batch_group
            # del batch_text
            # del batch_text_area

            # del main_battery_group
            # del main_battery_text
            # del main_battery_text_area

            # del clock_battery_group
            # del clock_battery_text
            # del clock_battery_text_area

        if display:
            #gc.collect()
            if CO2_sensor:
                CO2_label_group = displayio.Group( scale=2, x=6+XOFFSET, y=15+YOFFSET)
                CO2_label_text = "CO"
                CO2_label_text_area = label.Label( terminalio.FONT, text=CO2_label_text, color=the_font_color )
                CO2_label_group.append( CO2_label_text_area )
                data_screen.append( CO2_label_group )

                CO2_subscript_group = displayio.Group( scale=1, x=30+XOFFSET, y=20+YOFFSET)
                CO2_subscript_text = "2"
                CO2_subscript_text_area = label.Label( terminalio.FONT, text=CO2_subscript_text, color=the_font_color )
                CO2_subscript_group.append( CO2_subscript_text_area )
                data_screen.append( CO2_subscript_group )

                CO2_value_group = displayio.Group( scale=2, x=42+XOFFSET, y=15+YOFFSET)
                CO2_value_text = "0ppm"
                CO2_value_text_area = label.Label( terminalio.FONT, text=CO2_value_text, color=the_font_color )
                CO2_value_group.append( CO2_value_text_area )
                data_screen.append( CO2_value_group )

            # temperature
            if WX_sensor:
                temperature_label_group = displayio.Group( scale=2, x=6+XOFFSET, y=39+YOFFSET)
                temperature_label_text = "Temp"
                temperature_label_text_area = label.Label( terminalio.FONT, text=temperature_label_text, color=the_font_color )
                temperature_label_group.append( temperature_label_text_area )
                data_screen.append( temperature_label_group )

                temperature_value_group = displayio.Group( scale=2, x=60+XOFFSET, y=39+YOFFSET)
                temperature_value_text = "0C"
                temperature_value_text_area = label.Label( terminalio.FONT, text= temperature_value_text, color=the_font_color )
                temperature_value_group.append( temperature_value_text_area )
                data_screen.append( temperature_value_group )

                # relative_humidity
                humidity_label_group = displayio.Group( scale=2, x=18+XOFFSET, y=64+YOFFSET)
                humidity_label_text = "RH"
                humidity_label_text_area = label.Label( terminalio.FONT, text=humidity_label_text, color=the_font_color )
                humidity_label_group.append( humidity_label_text_area )
                data_screen.append( humidity_label_group )

                humidity_value_group = displayio.Group( scale=2, x=60+XOFFSET, y=64+YOFFSET)
                humidity_value_text = "0%"
                humidity_value_text_area = label.Label( terminalio.FONT, text= humidity_value_text, color=the_font_color )
                humidity_value_group.append( humidity_value_text_area )
                data_screen.append( humidity_value_group )

                # barometric pressure

            # particulates line 1
            if pm25_sensor:
                aqi_label_group = displayio.Group( scale=2, x=10+XOFFSET, y=87+YOFFSET)
                aqi_label_text = "AQI"
                aqi_label_text_area = label.Label( terminalio.FONT, text=aqi_label_text, color=the_font_color )
                aqi_label_group.append( aqi_label_text_area )
                data_screen.append( aqi_label_group )

                aqi_subscript_group = displayio.Group( scale=1, x=45+XOFFSET, y=92+YOFFSET)
                aqi_subscript_text = "p"
                aqi_subscript_text_area = label.Label( terminalio.FONT, text=aqi_subscript_text, color=the_font_color )
                aqi_subscript_group.append( aqi_subscript_text_area )
                data_screen.append( aqi_subscript_group )

                aqi_value_group = displayio.Group( scale=2, x=10+XOFFSET, y=110+YOFFSET)
                aqi_value_text = "TBD"
                aqi_value_text_area = label.Label( terminalio.FONT, text=aqi_value_text, color=the_font_color )
                aqi_value_group.append( aqi_value_text_area )
                data_screen.append( aqi_value_group )

                ## formerly commented out
                # particles10_label_group = displayio.Group( scale=1, x=60+XOFFSET, y=85+YOFFSET)
                # particles10_label_text = "P1"
                # particles10_label_text_area = label.Label( terminalio.FONT, text=particles10_label_text, color=the_font_color )
                # particles10_label_group.append( particles10_label_text_area )
                # data_screen.append( particles10_label_group )

                # particles10_value_group = displayio.Group( scale=1, x=90+XOFFSET, y=85+YOFFSET)
                # particles10_value_text = "0" #ug/m^3
                # particles10_value_text_area = label.Label( terminalio.FONT, text= particles10_value_text, color=the_font_color )
                # particles10_value_group.append( particles10_value_text_area )
                # data_screen.append( particles10_value_group )

                particles_unit_group = displayio.Group( scale=1, x=86+XOFFSET, y=85+YOFFSET)
                particles_unit_text = "ug/m^3"
                particles_unit_text_area = label.Label( terminalio.FONT, text= particles_unit_text, color=the_font_color )
                particles_unit_group.append( particles_unit_text_area )
                data_screen.append( particles_unit_group )

                particles25_label_group = displayio.Group( scale=1, x=60+XOFFSET, y=100+YOFFSET)
                particles25_label_text = "P2.5"
                particles25_label_text_area = label.Label( terminalio.FONT, text=particles25_label_text, color=the_font_color )
                particles25_label_group.append( particles25_label_text_area )
                data_screen.append( particles25_label_group )

                particles25_value_group = displayio.Group( scale=1, x=90+XOFFSET, y=100+YOFFSET)
                particles25_value_text = "0"#ug/m^3"
                particles25_value_text_area = label.Label( terminalio.FONT, text= particles25_value_text, color=the_font_color )
                particles25_value_group.append( particles25_value_text_area )
                data_screen.append( particles25_value_group )

                # particulates line 2
                particles100_label_group = displayio.Group( scale=1, x=60+XOFFSET, y=114+YOFFSET)
                particles100_label_text = "P10"
                particles100_label_text_area = label.Label( terminalio.FONT, text=particles100_label_text, color=the_font_color )
                particles100_label_group.append( particles100_label_text_area )
                data_screen.append( particles100_label_group )

                particles100_value_group = displayio.Group( scale=1, x=90+XOFFSET, y=114+YOFFSET)
                particles100_value_text = "0"#ug/m^3"
                particles100_value_text_area = label.Label( terminalio.FONT, text= particles100_value_text, color=the_font_color )
                particles100_value_group.append( particles100_value_text_area )
                data_screen.append( particles100_value_group )

        # batch_number
        #if display:
            # batch_border = 1
            # batch_width = 29
            # batch_height = 20
            # batch_x = 54
            # batch_y = 74
            # border_color = 0xFFFFFF
            # border = displayio.Palette(1)
            # border[0] = border_color
            # outer_rectangle = vectorio.Rectangle(pixel_shader=border, width=batch_width, height=batch_height, x=batch_x+XOFFSET, y=batch_y+YOFFSET)
            # data_screen.append( outer_rectangle )
            # front_color = 0x000000
            # front = displayio.Palette(1)
            # front[0] = front_color
            # inner_rectangle = vectorio.Rectangle(pixel_shader=front, width=batch_width-2*batch_border, height=batch_height-2*batch_border, x=batch_x+batch_border+XOFFSET, y=batch_y+batch_border+YOFFSET)
            # data_screen.append( inner_rectangle )

            # batch_number_group = displayio.Group( scale=2, x=57+XOFFSET, y=84+YOFFSET)
            # if int(batch_number) < 10:
            #     batch_number_text = (" " + batch_number )
            # else:
            #     batch_number_text = batch_number
            # batch_number_text_area = label.Label( terminalio.FONT, text=batch_number_text, color=the_font_color )
            # batch_number_group.append( batch_number_text_area )
            # data_screen.append( batch_number_group )

            # del batch_border
            # del batch_width
            # del batch_height
            # del batch_x
            # del batch_y
            # del border_color
            # del border


        if display:
            display.root_group = data_screen
            time.sleep(0.05)
            print( "display data screen" )

        try:
            from web import WebServer  # also connects to wifi
        except ConnectionError as e:
            microcontroller.reset()     # reset on ConnectionError: Unknown failure 203

        webserver = None
        if board.VFS and real_time_clock:
            webserver = WebServer(history_files,real_time_clock,units)

        if wifi.radio.ipv4_address == None:
            webserver = None

        def stop_webserver(ws):
            print("stopping webserver")
            if ws:
                ws.stop()
            time.sleep(0.05)
        atexit.register(stop_webserver,webserver)

    except (ValueError, RuntimeError) as err:
        print( "setup exception:" )
        if webserver:
            webserver.stop()
        if i2c_stemma:
            i2c_stemma.deinit()
        if i2c_local:
            i2c_local.deinit()
        print("end of setup")
        raise err

    operational = True
    print()
    print("mirror data header:")
    print( header )
    # begin loop

    sample_interval_s = 5.0

    loop_count = 0
    max_loop_count = 0
    file_error_count = 0

    stale_CO2_data = True

    current_screen = 2

    if board.SPI:
        print( "spi is good" )
    if board.SDCARD:
        print( "sd card is good" )
    if display:
        print( "display is good" )
    if touchpad:
        print( "touchpad is good" )
    if i2c_stemma:
        print( "stemma i2c bus is good" )
    if i2c_local:
        print( "local i2c bus is good" )
    if real_time_clock:
        print( "real time clock is good" )
    
    wdt = None
    wdt = microcontroller.watchdog
    wdt.feed()
    wdt.timeout=35 # seconds
    wdt.mode = watchdog.WatchDogMode.RESET
    wdt.feed()

    last_url = None
    last_line = None

    if webserver:
        print(dir(webserver.server))

    try:
        while( operational ):
            if touchpad and touchpad.is_pressed():
                current_screen = (current_screen + 1) % 5
                print( "current screen = {}".format( current_screen ))
                if current_screen == 0:
                    display.root_group = info_screen
                elif current_screen == 1:
                    display.root_group = time_screen
                elif current_screen == 2:
                    display.root_group = data_screen
                elif current_screen == 3:
                    display.root_group = qr_screen
                else:
                    display.root_group = displayio.CIRCUITPYTHON_TERMINAL
                time.sleep(0.05)

            #gc.collect()
            loop_start_time_s = time.monotonic()
            #gc.collect()
            mem_free_kB = gc.mem_free()/1000
            print( "free memory remaining = {} kB, {}%, loop {}, max {}, error count {}".format( mem_free_kB, (100* (mem_free_kB)/start_mem_free_kB ), loop_count, max_loop_count, file_error_count))
            # read clock
            if real_time_clock:
                timestamp = real_time_clock.datetime
            else:
                timestamp = null_time
            iso8601_utc = "{:04}{:02}{:02}T{:02}{:02}{:02}Z".format(
                timestamp.tm_year, timestamp.tm_mon, timestamp.tm_mday,
                timestamp.tm_hour, timestamp.tm_min, timestamp.tm_sec )
            decimal_hour = timestamp_to_decimal_hour( timestamp )
            weekday = DAYS[ timestamp.tm_wday ]
            print(1, end="")
            # read battery voltage
            main_battery_voltage = get_voltage(vbat_voltage_pin)
            #print("main battery voltage: {:.2f} V".format(main_battery_voltage))

            # read WX
            if WX_sensor:
                WX_reading = (WX_sensor.temperature, WX_sensor.relative_humidity, WX_sensor.pressure, WX_sensor.altitude)
            else:
                WX_reading = ( 0, 0, 0, 0 )
            #print( WX_reading )
            print(2, end="")
            # read CO2
            if CO2_sensor:
                if CO2_sensor.data_ready:
                    stale_CO2_data = False
                    CO2_reading = ( CO2_sensor.CO2, CO2_sensor.temperature, CO2_sensor.relative_humidity, int( stale_CO2_data ))
                    stale_CO2_data = True
                    last_CO2_reading = ( CO2_sensor.CO2, CO2_sensor.temperature, CO2_sensor.relative_humidity, int( stale_CO2_data ))
                else:
                    CO2_reading = last_CO2_reading
            else:
                CO2_reading = ( 0, 0, 0, 0 )
            CO2_tolerance = (50 + CO2_reading[0] * 0.05)
            #print( CO2_reading )
            print(3, end="")
            # read PM
            if pm25_sensor:
                if not loop_count % 3: #measure particulates only every third loop
                    try:
                        stale_pm25_data = False
                        pm25_data = (pm25_sensor.read())
                        pm25_reading = (
                            pm25_data["pm10 standard"], pm25_data["pm25 standard"], pm25_data["pm100 standard"],
                            pm25_data["pm10 env"], pm25_data["pm25 env"], pm25_data["pm100 env"],
                            pm25_data["particles 03um"], pm25_data["particles 05um"], pm25_data["particles 10um"],
                            pm25_data["particles 25um"], pm25_data["particles 50um"], pm25_data["particles 100um"],
                            int(stale_pm25_data))
                        stale_pm25_data = True
                        last_pm25_reading = (
                            pm25_data["pm10 standard"], pm25_data["pm25 standard"], pm25_data["pm100 standard"],
                            pm25_data["pm10 env"], pm25_data["pm25 env"], pm25_data["pm100 env"],
                            pm25_data["particles 03um"], pm25_data["particles 05um"], pm25_data["particles 10um"],
                            pm25_data["particles 25um"], pm25_data["particles 50um"], pm25_data["particles 100um"],
                            int(stale_pm25_data))

                    except RuntimeError:
                        pm25_reading = last_pm25_reading
                #print( pm25_reading[1], pm25_reading[2] )
                aqi = calculate_aqi( pm25_reading[1], pm25_reading[2] )
                #print("AQI = {}".format(aqi))

            else:
                aqi = 0
                pm25_reading = (0,0,0,0,0,0,0,0,0,0,0,0,0)
            #print( pm25_reading )
            print(4, end="")
            # display data
            #gc.collect()
            if display:
                if CO2_sensor:
                    CO2_value_text_area.text = str(CO2_reading[0]) + "ppm"
                if WX_sensor:
                    temperature_value_text_area.text = str(round(c_to_f(WX_reading[0]),1)) + "F"
                    humidity_value_text_area.text = str(round(WX_reading[1],1)) + "%"
                if pm25_sensor:
                    #particles10_value_text_area.text = str(round(pm25_reading[0],1)) + "ug/m^3"
                    particles25_value_text_area.text = str(round(pm25_reading[1],1)) #+ "ug/m^3"
                    particles100_value_text_area.text = str(round(pm25_reading[2],1)) # + "ug/m^3"
                    if aqi < 100:
                        aqi_text = (" " + str(aqi))
                    else:
                        aqi_text = str(aqi)
                    aqi_value_text_area.text = aqi_text

                timenow = real_time_clock.datetime
                time_text = ("{:02d}:{:02d}:{:02d}Z".format( timenow.tm_hour, timenow.tm_min, timenow.tm_sec ))
                time_text_area.text = time_text

            # build datapoint
            print(5, end="")
            history_files.append_array(
                timestamp = time.mktime(timestamp),  # seconds since 1970
                UID = UID,
                batch = batch_number,
                AQIp = aqi,
                CO2_stale_data = CO2_reading[3],
                CO2_conc = CO2_reading[0],
                CO2_tolerance = CO2_tolerance,
                CO2_air_temperature = CO2_reading[1],
                CO2_air_temperature_tolerance = CO2_sensor_air_temperature_tolerance,
                CO2_relative_humidity = CO2_reading[2],
                CO2_relative_humidity_tolerance = CO2_sensor_relative_humidity_tolerance,
                WX_air_temperature = WX_reading[0],
                WX_air_temperature_tolerance = WX_sensor_air_temperature_tolerance,
                WX_relative_humidity = WX_reading[1],
                WX_relative_humidity_tolerance = WX_sensor_relative_humidity_tolerance,
                WX_barometric_pressure = WX_reading[2],
                WX_barometric_pressure_tolerance = WX_sensor_barometric_pressure_tolerance,
                WX_altitude = WX_reading[3],
                WX_altitude_tolerance = WX_sensor_altitude_tolerance,
                concentration_1um = pm25_reading[0],
                concentration_2_5um = pm25_reading[1],
                concentration_10um = pm25_reading[2],
                particle_conc_tolerance = particle_concentration_tolerance_ug_tol,
                count_0_3um = pm25_reading[6],
                count_0_5um= pm25_reading[7],
                count_1um = pm25_reading[8],
                count_2_5um = pm25_reading[9],
                count_5um = pm25_reading[10],
                count_10um = pm25_reading[11],
                main_battery_voltage = main_battery_voltage,
                dev_free_mem = mem_free_kB,
                dev_loop_count = loop_count,
                dev_max_loop_count = max_loop_count,
                dev_file_error_count = file_error_count
            )
            print(6, end="")
            #gc.collect()
            datapoint = ("STELLA-AQ, ")
            datapoint += str ( UID )
            datapoint += str ( ", " )
            datapoint += str ( batch_number )
            datapoint += str ( ", " )
            datapoint += str ( iso8601_utc )
            datapoint += str ( ", " )
            datapoint += str ( decimal_hour )
            datapoint += str ( ", " )
            #datapoint += str ( aqi )
            #datapoint += str ( ", " )
            datapoint += str ( CO2_reading[3] )
            datapoint += str ( ", " )
            datapoint += str ( CO2_reading[0] )
            datapoint += str ( ", " )
            datapoint += str ( CO2_tolerance )
            datapoint += str ( ", " )
            datapoint += str ( CO2_reading[1] )
            datapoint += str ( ", " )
            datapoint += str ( CO2_sensor_air_temperature_tolerance )
            datapoint += str ( ", " )
            datapoint += str ( CO2_reading[2] )
            datapoint += str ( ", " )
            datapoint += str ( CO2_sensor_relative_humidity_tolerance )
            datapoint += str ( ", " )
            datapoint += str ( WX_reading[0])
            datapoint += str ( ", " )
            datapoint += str ( WX_sensor_air_temperature_tolerance )
            datapoint += str ( ", " )
            datapoint += str ( WX_reading[1] )
            datapoint += str ( ", " )
            datapoint += str ( WX_sensor_relative_humidity_tolerance )
            datapoint += str ( ", " )
            datapoint += str ( WX_reading[2] )
            datapoint += str ( ", " )
            datapoint += str ( WX_sensor_barometric_pressure_tolerance)
            datapoint += str ( ", " )
            datapoint += str ( WX_reading[3] )
            datapoint += str ( ", " )
            datapoint += str ( WX_sensor_altitude_tolerance )
            datapoint += str ( ", " )
            datapoint += str ( pm25_reading[0] )
            datapoint += str ( ", " )
            datapoint += str ( pm25_reading[1] )
            datapoint += str ( ", " )
            datapoint += str ( pm25_reading[2] )
            datapoint += str ( ", " )
            datapoint += str ( particle_concentration_tolerance_ug_tol )
            datapoint += str ( ", " )
            datapoint += str ( pm25_reading[6] )
            datapoint += str ( ", " )
            datapoint += str ( pm25_reading[7] )
            datapoint += str ( ", " )
            datapoint += str ( pm25_reading[8] )
            datapoint += str ( ", " )
            datapoint += str ( pm25_reading[9] )
            datapoint += str ( ", " )
            datapoint += str ( pm25_reading[10] )
            datapoint += str ( ", " )
            datapoint += str ( pm25_reading[11] )
            datapoint += str ( ", " )
            datapoint += str ( main_battery_voltage )
            print(7, end="")
            # record datapoint
            #gc.collect()
            loop_count, file_error_count = write_data_to_file( datapoint, pixels, loop_count, file_error_count )
            if loop_count > max_loop_count:
                max_loop_count = loop_count
            # mirror data to usb
            #gc.collect()
            print(8)
            print( datapoint )

            # Feed watchdog
            if wdt:
                wdt.feed()

            if webserver:
                url = "http://" + webserver.server.host + ":" + str(webserver.server.port) + "/graph2.html"
                line = webserver.server.host + ":" + str(webserver.server.port)
            else:
                url = "http://buildingpulse.org"
                line = "buildingPULSE.org"
            if last_url != url or last_line != line:
                qr_screen = qr_group(url,line,scale=4,display_width=display.width,display_height=display.height)

            gc.collect()

            # wait to end of sample interval
            #gc.collect()
            time_now_s = time.monotonic()
            if ( time_now_s - loop_start_time_s ) < sample_interval_s:
                interval_wait = True
            else:
                interval_wait = False

            while( interval_wait ):
                time_now_s = time.monotonic()
                if ( time_now_s - loop_start_time_s ) < sample_interval_s:
                    interval_wait = True
                else:
                    interval_wait = False
                time.sleep(0.05)
                if webserver:
                    webserver.poll()
                    gc.collect()
                #print( "waiting")
                    
                if touchpad and touchpad.is_pressed():
                    current_screen = (current_screen + 1) % 5
                    print( "current screen = {}".format( current_screen ))
                    if current_screen == 0:
                        display.root_group = info_screen
                    elif current_screen == 1:
                        display.root_group = time_screen
                    elif current_screen == 2:
                        display.root_group = data_screen
                    elif current_screen == 3:
                        display.root_group = qr_screen
                    else:
                        display.root_group = displayio.CIRCUITPYTHON_TERMINAL


    except watchdog.WatchDogTimeout:
        print( "watchdog timeout" )
        time.sleep(1.0)
        microcontroller.reset()
    finally:
        print( "loop finally clause:" )
        if webserver:
            webserver.stop()
            del webserver
        displayio.release_displays()
        print( "displayio displays released" )
        if i2c_stemma:
            i2c_stemma.deinit()
        if i2c_local:
            i2c_local.deinit()
        print( "i2c_buses and SPI bus deinitialized" )
        print("code exit: max loop count == {}, file error count == {}".format(max_loop_count, file_error_count))
        #microcontroller.reset()

def stall():
    print("intentionally stalled, press return to continue")
    input_string = False
    while input_string == False:
        input_string = input().strip()

def c_to_f( celsius ):
    return (celsius * 9/5) + 32

def initialize_data_file(header, DATA_FILE):
    try:
        os.stat( DATA_FILE ) # fail if data.csv file is not already there
        #raise OSError # uncomment to force header everytime
        print( "data file already exists, does not need header" )
        return False
    except OSError:
        # setup the header for first time
        #gc.collect()
        try:
            with open( DATA_FILE, "w" ) as f:
                f.write( header )
            print( "header written" )
        except OSError as err:
            print( err )
            pass
        return True

def write_data_to_file( datapoint, pixels, loop_count, file_error_count):
    try:
        with open( DATA_FILE, "a" ) as f:
            if pixels:
                pixels.fill ( RED )
            f.write( str(datapoint ))
            f.write("\n")
            time.sleep( 0.05 )
            #f.close()
        if pixels:
            pixels.fill( OFF )
        loop_count +=1
    except OSError as err:
        # TBD: maybe show something on the display like sd_full? this will "Error" every sample pass
        # "[Errno 30] Read-only filesystem" probably means no sd_card
        print( "\nError: sd card fail: {:}\n".format(err) )
        if pixels:
            pixels.fill( ORANGE ) #  ON to show error, likely no SD card present, or SD card full.
            time.sleep( 0.2 )
            pixels.fill( OFF )
        print("loop count == {}".format(loop_count))
        loop_count = 0
        file_error_count += 1
    return loop_count, file_error_count

def calculate_aqi( p25_reading, p100_reading ):
    #gc.collect()
    p25_break_points = (0, 12, 12.1, 35.4, 35.5, 55.4, 55.5, 150.4, 150.5, 250.4, 250.5, 350.4, 350.5, 500.4)
    #print( p25_break_points )
    p100_break_points = (0, 54, 55, 154, 155, 254, 255, 354, 355, 424, 425, 504, 505, 604)
    #print( p100_break_points )
    AQI_levels = (0, 50, 51, 100, 101, 150, 151, 200, 201, 300, 301, 400, 401, 500)
    #print( AQI_levels )
    p25_index = 0
    p100_index = 0
    for i in range (len(AQI_levels)-1):
        if (p25_reading > p25_break_points[i] and p25_reading < p25_break_points[i+1]):
            p25_index = i
    #aqi = int((((ihi-ilo)/(bhi-blo))*(reading-blo))+ilo)
    aqi25 = int((((AQI_levels[p25_index+1] - AQI_levels[p25_index])/(p25_break_points[p25_index+1] - p25_break_points[p25_index]))*(p25_reading-p25_break_points[p25_index]))+AQI_levels[p25_index])
    #print(aqi25)
    for n in range (len(AQI_levels)-1):
        if (p100_reading > p100_break_points[i] and p100_reading < p100_break_points[i+1]):
            p100_index = i
    aqi100 = int((((AQI_levels[p100_index+1] - AQI_levels[p100_index])/(p100_break_points[p100_index+1] - p100_break_points[p100_index]))*(p100_reading-p25_break_points[p100_index]))+AQI_levels[p100_index])
    #print(aqi100)
    #print( p25_break_points[p25_index], p25_break_points[p25_index+1], AQI_levels[p25_index], AQI_levels[p25_index+1], p100_break_points[p100_index], p100_break_points[p100_index+1], AQI_levels[p100_index], AQI_levels[p100_index+1])
    if aqi100 > aqi25:
        return aqi100
    else:
        return aqi25

def timestamp_to_decimal_hour( timestamp ):
    try:
        decimal_hour = timestamp.tm_hour + timestamp.tm_min/60.0 + timestamp.tm_sec/3600.0
        return decimal_hour
    except ValueError as err:
        print( "Error: invalid timestamp: {:}".format(err) )
        return False

def update_batch( timestamp ):
    #gc.collect()
    datestamp = "{:04}{:02}{:02}".format( timestamp.tm_year, timestamp.tm_mon, timestamp.tm_mday)
    try:
        with open( "/sd/batch.txt", "r" ) as b:
            try:
                previous_batchfile_string = b.readline()
                previous_datestamp = previous_batchfile_string[ 0:8 ]
                previous_batch_number = int( previous_batchfile_string[ 8: ])
            # TBD: catch error when /sd doesn't exist
            except ValueError:
                previous_batch_number = 0
                # corrupted data in batch number file, setting batch to 0
            if datestamp == previous_datestamp:
                # this is the same day, so increment the batch number
                batch_number = previous_batch_number + 1
            else:
                # this is a different day, so start the batch number at 0
                batch_number = 0
    except OSError:
            print( "batch.txt file not found" )
            batch_number = 0
    batch_string = ( "{:03}".format( batch_number ))
    batch_file_string = datestamp + batch_string
    try:
        with open( "/sd/batch.txt", "w" ) as b:
            b.write( batch_file_string )
        # TBD: catch error when /sd doesn't exist
    except OSError as err:
        print("Error: writing batch.txt {:}".format(err) )
        pass
    batch_string = ( "{:}".format( batch_number ))
    return batch_number

def get_voltage(pin):
    return (pin.value * 3.3) / 65536 * 2

main()
