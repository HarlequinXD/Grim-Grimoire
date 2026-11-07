"""Touch-control atlas (128x128 pixel art) + launcher icons for Grim Grimoire."""
import math
import numpy as np
from PIL import Image, ImageDraw

S = 128
img = Image.new('RGBA', (S, S), (0, 0, 0, 0))
px = img.load()
BONE = (226, 214, 176, 255); BONE_D = (150, 136, 104, 255); DARK = (16, 12, 20, 255)
RED = (170, 30, 40, 255); GOLD = (214, 168, 60, 255)

def disc(cx, cy, r, col, ring=None):
    for y in range(S):
        for x in range(S):
            d = math.hypot(x + 0.5 - cx, y + 0.5 - cy)
            if (ring is None and d <= r) or (ring is not None and r - ring <= d <= r):
                px[x, y] = col

# stick base (0,0,64,64): dark translucent disc with bone ring and tick marks
disc(32, 32, 31, (10, 8, 14, 110)); disc(32, 32, 31, BONE_D, ring=3); disc(32, 32, 29, BONE, ring=1)
for k in range(8):
    a = k * math.pi / 4
    for s in range(22, 26):
        px[int(32 + math.cos(a) * s), int(32 + math.sin(a) * s)] = BONE_D
# knob (64,0,32,32): skull-ish bone knob with bevel
for y in range(32):
    for x in range(32):
        d = math.hypot(x + 0.5 - 16, y + 0.5 - 16)
        if d <= 14:
            lit = ((16 - x) + (16 - y)) / 28
            c = BONE if lit > 0.15 else BONE_D if lit > -0.35 else (110, 98, 74, 255)
            if d > 12.5: c = (60, 50, 40, 255)
            px[64 + x, y] = c
# button base (96,0,32,32): dark disc, gold rim, lit top-left
for y in range(32):
    for x in range(32):
        d = math.hypot(x + 0.5 - 16, y + 0.5 - 16)
        if d <= 15:
            if d > 13.5: px[96 + x, y] = GOLD if (x + y) < 30 else (120, 86, 30, 255)
            else:
                lit = ((16 - x) + (16 - y)) / 30
                v = int(34 + 22 * lit)
                px[96 + x, y] = (v, int(v * 0.8), int(v * 1.1), 200)

def icon(slot, draw_fn):
    """Draw an aliased 32x32 icon with a dark outline into row 1/2 slots."""
    ic = Image.new('L', (32, 32), 0)
    d = ImageDraw.Draw(ic); draw_fn(d)
    a = np.array(ic) > 0
    ox, oy = (slot % 4) * 32, 64 + (slot // 4) * 32
    out = np.zeros_like(a)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            out |= np.roll(np.roll(a, dy, 0), dx, 1)
    for y in range(32):
        for x in range(32):
            if a[y, x]: px[ox + x, oy + y] = BONE if (x + y) < 34 else BONE_D
            elif out[y, x]: px[ox + x, oy + y] = DARK

# 0 attack: a bone club
icon(0, lambda d: (d.line([(9, 23), (23, 9)], fill=255, width=4), d.ellipse([5, 21, 11, 27], fill=255), d.ellipse([9, 24, 14, 29], fill=255),
                   d.ellipse([21, 4, 27, 10], fill=255), d.ellipse([24, 8, 29, 13], fill=255)))
# 1 jump: up arrow
icon(1, lambda d: (d.polygon([(16, 4), (27, 16), (20, 16), (20, 27), (12, 27), (12, 16), (5, 16)], fill=255)))
# 2 block: shield
icon(2, lambda d: (d.polygon([(6, 6), (26, 6), (26, 15), (16, 28), (6, 15)], fill=255), d.line([(16, 8), (16, 24)], fill=0, width=2)))
# 3 strafe: left-right arrows
icon(3, lambda d: (d.polygon([(3, 16), (11, 9), (11, 13), (21, 13), (21, 9), (29, 16), (21, 23), (21, 19), (11, 19), (11, 23)], fill=255)))
# 4 cam left: curved arrow  5 cam right
def cam(d, flip):
    pts = []
    for k in range(0, 141, 10):
        a = math.radians(200 + k)
        pts.append((15 + 9 * math.cos(a), 21 + 9 * math.sin(a)))
    if flip: pts = [(32 - x, y) for x, y in pts]
    d.line(pts, fill=255, width=4)
    tip = pts[-1]; s = -1 if flip else 1
    d.polygon([(tip[0] + 5 * s, tip[1] + 6), (tip[0] - 5 * s, tip[1] + 3), (tip[0] + 2 * s, tip[1] - 4)], fill=255)
icon(4, lambda d: cam(d, False)); icon(5, lambda d: cam(d, True))
# 6 recentre ("Dan cam"): an eye
icon(6, lambda d: (d.ellipse([3, 9, 29, 23], fill=255), d.ellipse([11, 10, 21, 22], fill=0), d.ellipse([14, 13, 18, 19], fill=255)))
# 7 pause bars
icon(7, lambda d: (d.rectangle([9, 7, 13, 25], fill=255), d.rectangle([19, 7, 23, 25], fill=255)))
img.save('ui.png')
Image.open('ui.png').resize((512, 512), Image.NEAREST).save('ui_preview.png')

# launcher icon from the head close-up render
src = Image.open('../head0.png').convert('RGB')
w, h = src.size; side = min(w, h)
crop = src.crop(((w - side) // 2, 0, (w - side) // 2 + side, side)).resize((96, 96), Image.NEAREST)
for name, size in (('mdpi', 48), ('hdpi', 72), ('xhdpi', 96), ('xxhdpi', 144), ('xxxhdpi', 192)):
    crop.resize((size, size), Image.NEAREST).save(f'ic_launcher_{name}.png')
