# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

import qtpy_esp32s3_and_seeed_round_display as board
import displayio
import adafruit_miniqr

def bitmap_QR(matrix):
    # monochome (2 color) palette
    BORDER_PIXELS = 2

    # bitmap the size of the screen, monochrome (2 colors)
    bitmap = displayio.Bitmap(
        matrix.width + 2 * BORDER_PIXELS, matrix.height + 2 * BORDER_PIXELS, 2
    )
    # raster the QR code
    for y in range(matrix.height):  # each scanline in the height
        for x in range(matrix.width):
            if matrix[x, y]:
                bitmap[x + BORDER_PIXELS, y + BORDER_PIXELS] = 1
            else:
                bitmap[x + BORDER_PIXELS, y + BORDER_PIXELS] = 0
    return bitmap

from color_palette import PALETTE
from adafruit_display_text import label
import terminalio

def qr_group(url,line1, fg_color=PALETTE[8], bg_color=PALETTE[13],scale=2,display_width=240,display_height=240):

    qr = adafruit_miniqr.QRCode(qr_type=3, error_correct=adafruit_miniqr.L)
    qr.add_data(url)
    qr.make()

    # generate the 1-pixel-per-bit bitmap
    qr_bitmap = bitmap_QR(qr.matrix)
    # We'll draw with a classic black/white palette
    palette = displayio.Palette(2)
    palette[0] = fg_color
    palette[1] = bg_color
    # # we'll scale the QR code as big as the display can handle
    # scale = min(
    #     board.DISPLAY.width // qr_bitmap.width, board.DISPLAY.height // qr_bitmap.height
    # )
    # then center it!
    pos_x = int(((display_width / scale) - qr_bitmap.width) / 2)
    pos_y = int(((display_height / scale) - qr_bitmap.height) / 2)
    qr_img = displayio.TileGrid(qr_bitmap, pixel_shader=palette, x=pos_x, y=pos_y)

    splash = displayio.Group(scale=scale)
    splash.append(qr_img)

    fontscale = 1
    lbl_x = pos_x * (scale//fontscale)
    lbl_y = (pos_y + qr_bitmap.height + 4) * (scale//fontscale)
    subname_text_area = label.Label( terminalio.FONT, text=line1, color=fg_color, x=lbl_x, y=lbl_y)
    text_group = displayio.Group(scale=fontscale)
    text_group.append(subname_text_area)

    container = displayio.Group()
    container.append(splash)
    container.append(text_group)
    return container



# board.DISPLAY.root_group = qr_group(b"https://www.adafruit.com/circuitpython","line1",scale=4,display_width=board.DISPLAY.width,display_height=board.DISPLAY.height)[0]
