import time
import pulseio

#from machine import Pin, SPI, I2C
#from touchpad import TouchPad
#from Xiao_ESP32_S3_round_display import * 
#i2c = I2C(0, scl=Pin(D5), sda=Pin(D4), freq=400_000)
#tp = TouchPad(i2c,fw.display)  
#led = machine.Pin(D7, machine.Pin.OUT, drive=machine.Pin.DRIVE_0)  # 5mA 130R


# import touchpad, busio
# import qtpy_esp32s3_and_seeed_round_display as board
# i2c_round_display = busio.I2C(board.SCL, board.SDA, frequency=100_000)
# t = touchpad.TouchPad(i2c_round_display, width=240, height=240, screen_rotation=0, interrupt_pin=board.TP_INT)
# i2c_round_display.try_lock()
# i2c_round_display.readfrom_into(touchpad.TouchPad.CHSC6X_I2C_ID, t.xy_msg, start=0, end=touchpad.TouchPad.CHSC6X_READ_POINT_LEN)
# i2c_round_display.unlock()
# t.xy_msg

# chsc6x touchscreen
class TouchPad:
    CHSC6X_I2C_ID = 0x2e
    CHSC6X_MAX_POINTS_NUM = 1
    CHSC6X_READ_POINT_LEN = 5

    def __init__(self, ic2, width=240, height=240, screen_rotation=0, interrupt_pin=None):
        self.ic2 = ic2
        self.screen_rotation = screen_rotation
        self.width = width
        self.height = height
        self.xy_msg = bytearray(TouchPad.CHSC6X_READ_POINT_LEN)
        self.pressed = None
        self.x = None
        self.y = None
        self.pulses = pulseio.PulseIn(interrupt_pin)

    def __del__(self):
        self.pulses.deinit()

    def test(self):
        while True:
            if self.is_pressed():
                print(f"pressed: {self.x},{self.y}")
            time.sleep(0.1)

    def is_pressed(self):
        if len(self.pulses) > 0:
            self.pulses.clear()
            return True
        else:
            return False

    def get_xy(self):
        x,y=self.chsc6x_get_xy()
        self.x = x
        self.y = y
        return x,y  
    
    def chsc6x_get_xy(self):
        try:
            while self.i2c.try_lock():
                pass
            self.ic2.readfrom_into(TouchPad.CHSC6X_I2C_ID, self.xy_msg, start=0, end=TouchPad.CHSC6X_READ_POINT_LEN)
            self.i2c.unlock()
        except OSError:
            return None, None
        if self.xy_msg[0] == 0x01:
            x, y = self.chc6x_convert_xy(self.xy_msg[2], self.xy_msg[4])
            return x, y
        else:
            return None, None
        
    def chc6x_convert_xy(self, x, y):
        x_tmp = x
        y_tmp = y
        _end = 0
        for i in range(1, self.screen_rotation):
            x_tmp = x
            y_tmp = y
            if (i % 2) == 1:
                _end = self.width
            else:
                _end = self.height
            x = y_tmp
            y = _end - x_tmp
        return x, y


    