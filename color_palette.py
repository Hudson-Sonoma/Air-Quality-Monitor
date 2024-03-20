

# Convert r, g, b in range 0-255 to a 16 bit colour value RGB565
#  acceptable to hardware: rrrrrggggggbbbbb
def rgb(r, g, b):
    return ((r & 0xf8) << 5) | ((g & 0x1c) << 11) | (b & 0xf8) | ((g & 0xe0) >> 5)

def rgb888(r, g, b):
    return (r << 16) | (g << 8) | b

PALETTE = []
# 24bit
# https://colorswall.com/palette/105557
#PALETTE.append(ssd.rgb_to_565(244, 67, 54))
PALETTE.append(rgb888(0, 0, 0))
PALETTE.append(rgb888(232, 30, 99))
PALETTE.append(rgb888(156, 39, 176))
PALETTE.append(rgb888(103, 58, 183))
PALETTE.append(rgb888(63, 81, 181))
PALETTE.append(rgb888(33, 150, 243))
PALETTE.append(rgb888(3, 169, 244))
PALETTE.append(rgb888(0, 188, 212))
PALETTE.append(rgb888(0, 150, 136))
PALETTE.append(rgb888(76, 175, 80))
PALETTE.append(rgb888(139, 195, 74))
PALETTE.append(rgb888(205, 220, 57))
PALETTE.append(rgb888(255, 235, 59))
PALETTE.append(rgb888(255, 193, 7))
PALETTE.append(rgb888(255, 152, 0))
PALETTE.append(rgb888(255, 87, 34))