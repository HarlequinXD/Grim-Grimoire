"""Grim Grimoire - mansion texture atlas (256x256, 32px cells).
Every texture is hand-shaded pixel art: a small palette, light from the upper left baked in,
ambient occlusion in the crevices, and the shading quantised into dithered steps."""
import math, random
import numpy as np
from PIL import Image

random.seed(3); np.random.seed(3)
ATLAS = 256; C = 32
rgb = np.zeros((ATLAS, ATLAS, 3), np.float32)
alpha = np.full((ATLAS, ATLAS), 255, np.uint8)
BAYER = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], np.float32)
LEVELS = np.array([0.42, 0.56, 0.70, 0.84, 1.0, 1.16, 1.32], np.float32)
RECTS = {}   # name -> (x, y, w, h) pixels
EMISSIVE = set()

def H(c):  # hex -> float rgb
    c = c.lstrip('#'); return np.array([int(c[i:i + 2], 16) / 255 for i in (0, 2, 4)], np.float32)

def grid(w, h):
    v, u = np.mgrid[0:h, 0:w].astype(np.float32)
    return u, v, u / max(w - 1, 1), v / max(h - 1, 1)

def bayer(w, h, ox=0, oy=0):
    yy, xx = np.mgrid[0:h, 0:w]
    return (BAYER[(yy + oy) % 4, (xx + ox) % 4] + 0.5) / 16

def ramp(cols, t, w, h):
    """Dithered pick from a palette ramp by t in 0..1 (array)."""
    cols = np.array([H(c) for c in cols]); n = len(cols) - 1
    f = np.clip(t, 0, 0.9999) * n; k = np.floor(f).astype(int); fr = f - k
    k = np.where(fr > bayer(w, h), np.minimum(k + 1, n), k)
    return cols[k]

def quant_light(L, w, h):
    """Quantise a light multiplier to LEVELS with ordered dither (the hand-shaded look)."""
    L = np.clip(L, LEVELS[0], LEVELS[-1])
    idx = np.searchsorted(LEVELS, L, side='right') - 1
    idx = np.clip(idx, 0, len(LEVELS) - 2)
    lo, hi = LEVELS[idx], LEVELS[idx + 1]
    t = (L - lo) / (hi - lo)
    return np.where(t > bayer(w, h), hi, lo)

def edge_ao(un, vn, k=0.12, amt=0.25):
    d = np.minimum(np.minimum(un, 1 - un), np.minimum(vn, 1 - vn))
    return -amt * np.clip((k - d) / k, 0, 1)

def put(name, col, row, base, light=None, a=None, cw=1, ch=1, emissive=False):
    w, h = cw * C, ch * C; x, y = col * C, row * C
    if light is not None:
        base = base * quant_light(light, w, h)[..., None]
    rgb[y:y + h, x:x + w] = np.clip(base, 0, 1)
    if a is not None: alpha[y:y + h, x:x + w] = a
    RECTS[name] = (x, y, w, h)
    if emissive: EMISSIVE.add(name)

def noise(w, h, s=1.0):
    return np.random.rand(h, w).astype(np.float32) * s

def bevel_rect(L, x0, y0, x1, y1, hi=0.28, lo=0.32, width=1):
    """Raised bevel: lit top/left edge, shadowed bottom/right edge (light from upper left)."""
    for k in range(width):
        L[y0 + k, x0 + k:x1 - k] += hi; L[y0 + k:y1 - k, x0 + k] += hi
        L[y1 - 1 - k, x0 + k:x1 - k] -= lo; L[y0 + k:y1 - k, x1 - 1 - k] -= lo

def sunk_rect(L, x0, y0, x1, y1, hi=0.25, lo=0.32):
    bevel_rect(L, x0, y0, x1, y1, hi=-lo, lo=-hi)

# ------------------------------------------------------------------ floor planks (1 m tile, 4 planks)
w = h = C; u, v, un, vn = grid(w, h)
plank = (u // 8).astype(int)
off = np.array([0, 13, 5, 21])[plank]
seam = ((v + off) % 32 == 0)
grain = np.sin((u * 1.7 + np.sin(v * 0.35 + plank * 2.1) * 1.4)) * 0.5 + 0.5
tone = np.array([0.55, 0.45, 0.62, 0.5])[plank] + grain * 0.3 + noise(w, h, 0.12)
base = ramp(['3a2214', '5a3520', '7a4a2a', '93603a'], tone, w, h)
L = np.ones((h, w), np.float32) * 1.0
L[:, (u % 8 == 0)[0]] = 0.5            # gap between planks
L[:, (u % 8 == 1)[0]] += 0.22          # lit left bevel
L[:, (u % 8 == 7)[0]] -= 0.18          # shaded right bevel
L[seam] = 0.5
L += np.where((u % 8 == 3) & (np.sin(v * 0.2 + plank) > 0.6), 0.18, 0)   # varnish sheen
put('floor', 0, 0, base, L)

# ------------------------------------------------------------------ wallpaper: dark crimson damask
base = ramp(['3a0c14', '4e121c', '621a24'], 0.45 + noise(w, h, 0.25), w, h)
L = np.ones((h, w), np.float32) * 0.95
cxs = [(8, 8), (24, 24), (24, -8), (8, 40), (-8, 24), (40, 24)]
motif = np.zeros((h, w), bool)
for cx, cy in [(8, 8), (24, 24), (24, -8), (-8, 24), (8, 40), (40, 24), (-8, -8), (40, -8), (-8, 40), (40, 40)]:
    dx, dy = np.abs(u - cx + 0.5), np.abs(v - cy + 0.5)
    m = (dx / 6 + dy / 8 < 1) & ~((dx / 3 + dy / 4.5 < 1) & (dx > 0.6))
    motif |= m
base = np.where(motif[..., None], ramp(['8a5a2a', 'b07a38'], 0.4 + noise(w, h, 0.4), w, h), base)
mot_up = np.roll(motif, 1, 0); mot_l = np.roll(motif, 1, 1)
L += np.where(motif & ~mot_up, 0.3, 0) + np.where(motif & ~np.roll(motif, -1, 0), -0.3, 0)   # embossed
L += np.where(((u % 16) == 15)[...], -0.12, 0)          # faint stripes
put('wallpaper', 1, 0, base, L)

# ------------------------------------------------------------------ wainscot: raised walnut panel, chair rail
base = ramp(['2a160c', '40220f', '583118'], 0.4 + np.sin(v * 0.9 + u * 0.15) * 0.15 + noise(w, h, 0.3), w, h)
L = np.ones((h, w), np.float32)
L[0:4, :] = 1.15; L[0, :] = 1.32; L[3, :] = 0.7; L[4, :] = 0.5      # chair rail + its shadow
L[5:7, :] -= 0.12
bevel_rect(L, 4, 9, 28, 29, hi=0.3, lo=0.35, width=2)             # raised panel
L[11:27, 6:26] += 0.08
L[29:32, :] = 0.62; L[31, :] = 0.45                                # skirting shadow at the floor
put('wainscot', 2, 0, base, L)

# ------------------------------------------------------------------ coffered plaster ceiling
base = ramp(['4a4238', '625848', '7a6e5a'], 0.5 + noise(w, h, 0.3), w, h)
L = np.ones((h, w), np.float32) * 0.92
sunk_rect(L, 3, 3, 29, 29, hi=0.3, lo=0.35)
L[5:27, 5:27] -= 0.18
L[14:18, 14:18] += 0.25                                          # rosette
L += edge_ao(un, vn, 0.08, 0.2)
put('ceiling', 3, 0, base, L)

# ------------------------------------------------------------------ dark beam wood (grain along u)
base = ramp(['1e120a', '2e1c10', '432a18'], 0.45 + np.sin(v * 1.3 + np.sin(u * 0.2) * 2) * 0.25 + noise(w, h, 0.2), w, h)
L = np.ones((h, w), np.float32) + 0.2 * (1 - vn) - 0.15 * vn
L[0, :] += 0.2; L[-1, :] -= 0.3
put('beam', 4, 0, base, L)

# ------------------------------------------------------------------ crown molding strip
base = ramp(['3a2a1a', '5a4228', '7a5c38'], 0.5 + noise(w, h, 0.2), w, h)
L = np.ones((h, w), np.float32)
for y0, hh, d in ((0, 5, 0.2), (5, 3, -0.3), (8, 8, 0.25), (16, 4, -0.35), (20, 6, 0.15), (26, 6, -0.25)):
    L[y0:y0 + hh, :] += d * np.linspace(1, -0.5, hh)[:, None]
L[9:15, (u[0] % 6 < 3)] += 0.15                                    # dentil blocks
put('molding', 5, 0, base, L)

# ------------------------------------------------------------------ fireplace stone blocks
base = ramp(['3c3a40', '55525a', '6e6a72', '858088'], 0.4 + noise(w, h, 0.45), w, h)
L = np.ones((h, w), np.float32)
for r in range(4):
    y0 = r * 8; xo = 0 if r % 2 == 0 else 8
    for c in range(-1, 3):
        x0 = c * 16 + xo
        xa, xb = max(x0, 0), min(x0 + 16, 32)
        if xb <= xa: continue
        L[y0, xa:xb] = 0.45; L[y0 + 1, xa:xb] += 0.25; L[y0 + 7, xa:xb] -= 0.25
        if 0 <= x0 < 32: L[y0:y0 + 8, x0] = 0.45
        if 0 <= x0 + 1 < 32: L[y0 + 1:y0 + 8, x0 + 1] += 0.2
        if 0 <= x0 + 15 < 32: L[y0 + 1:y0 + 8, x0 + 15] -= 0.2
put('stone', 6, 0, base, L)

# ------------------------------------------------------------------ firebox (emissive): soot, embers, flames
fire_t = np.clip(1.0 - vn * 1.1 + (np.sin(u * 0.9) * 0.15 + noise(w, h, 0.25)) * (vn > 0.2) + 0.0, 0, 1)
soot = ramp(['0a0606', '1a0d08'], noise(w, h, 1), w, h)
flame_mask = (vn > 0.35 + 0.25 * np.abs(np.sin(u * 0.45)) * (1 - vn) + noise(w, h, 0.15))
flame = ramp(['5a1004', 'a83008', 'e8700c', 'ffc040', 'fff0a0'], np.clip((vn - 0.35) * 1.6 + noise(w, h, 0.25) - np.abs(un - 0.5) * 0.6, 0, 1), w, h)
embers = (vn > 0.86) & (noise(w, h) > 0.4)
base = np.where(flame_mask[..., None], flame, soot)
base = np.where(embers[..., None], H('ff6010'), base)
put('firebox', 7, 0, base, None, emissive=True)

# ------------------------------------------------------------------ woods
def wood(cols, freq=1.1):
    t = 0.45 + np.sin(u * 0.25 + np.sin(v * 0.18) * 3 + v * freq * 0.05) * 0.25 + noise(w, h, 0.22)
    return ramp(cols, t, w, h)
base = wood(['2a0e08', '45180c', '622416', '7e3420'])
L = np.ones((h, w), np.float32) + 0.25 * (1 - vn) - 0.2 * vn + edge_ao(un, vn, 0.1, 0.2)
L[0:2, :] += 0.2; L[(np.arange(32) % 11 == 3), :] += 0.12                 # polish
put('mahogany', 0, 1, base, L)
base = wood(['1c120c', '2e1e12', '45301c', '5a4026'])
put('wood_dark', 1, 1, base, np.ones((h, w), np.float32) + 0.18 * (1 - vn) - 0.15 * vn + edge_ao(un, vn, 0.1, 0.18))
base = wood(['5a3a1c', '7c5428', '9a6c36', 'b88a4a'])
put('wood_light', 2, 1, base, np.ones((h, w), np.float32) + 0.18 * (1 - vn) - 0.15 * vn + edge_ao(un, vn, 0.1, 0.18))

# ------------------------------------------------------------------ tufted velvet (red) and buttoned leather
def tufted(cols, pitch=8):
    base = ramp(cols, 0.5 + noise(w, h, 0.25), w, h)
    L = np.ones((h, w), np.float32)
    gx = (u % pitch) - pitch / 2 + 0.5; gy = ((v + (u // pitch % 2) * pitch / 2) % pitch) - pitch / 2 + 0.5
    r = np.sqrt(gx ** 2 + gy ** 2) / (pitch / 2)
    L += 0.32 * (1 - np.clip(r, 0, 1)) * (-(gx + gy) / pitch + 0.6)      # pillowed, lit top-left
    L -= 0.25 * np.clip(r - 0.7, 0, 1) * 2
    btn = (np.abs(gx) < 1) & (np.abs(gy) < 1)
    L[btn] = 0.45
    L += 0.15 * (1 - vn) - 0.15 * vn + edge_ao(un, vn, 0.08, 0.25)
    return base, L
b, L = tufted(['4a0a12', '6e1220', '921c2a'])
put('velvet', 3, 1, b, L)
b, L = tufted(['3a1c0c', '5a2e14', '7a4220'], 10)
put('leather', 4, 1, b, L)

# ------------------------------------------------------------------ persian rug (64x32)
w2, h2 = 64, 32; U2, V2, un2, vn2 = grid(w2, h2)
dx, dy = np.abs(un2 - 0.5) * 2, np.abs(vn2 - 0.5) * 2
pal = {k: H(c) for k, c in dict(r0='3c0a10', r1='6a1018', r2='8e1c22', n='182040', n1='24305a', g='b08838', g1='d8b050', c='d8c8a0').items()}
img = np.zeros((h2, w2, 3), np.float32) + pal['r1']
border = (dx > 0.86) | (dy > 0.78)
inner = (dx > 0.8) | (dy > 0.66)
img[inner & ~border] = pal['g']
img[border] = pal['n']
img[border & ((U2 + V2) % 4 < 1)] = pal['n1']
img[border & ((U2 - V2) % 6 == 0)] = pal['g1']
med = (dx * 1.4 + dy < 0.62)
img[med] = pal['n']
img[(dx * 1.4 + dy < 0.42)] = pal['r2']
img[(dx * 1.4 + dy < 0.2)] = pal['g1']
img[(np.abs(dx * 1.4 + dy - 0.62) < 0.06)] = pal['c']
field = ~inner & ~med
img[field & ((U2 % 8 == 2) & (V2 % 8 == 2))] = pal['g']
img[field & (((U2 + 4) % 8 == 2) & ((V2 + 4) % 8 == 2))] = pal['n1']
img[field & (((U2 + V2) % 8 == 0) | ((U2 - V2) % 8 == 0)) & (noise(w2, h2) > 0.5)] = pal['r0']
L = np.ones((h2, w2), np.float32) - 0.12 * dy + noise(w2, h2, 0.15) - 0.07
w, h = 64, 32
put('rug', 5, 1, img, L, cw=2)
w = h = C; u, v, un, vn = grid(w, h)

# ------------------------------------------------------------------ marble
t = 0.6 + np.sin(u * 0.3 + v * 0.2 + np.sin(v * 0.4) * 2) * 0.2 + noise(w, h, 0.15)
base = ramp(['8a8478', 'b0aa9c', 'd0cabc', 'e8e2d4'], t, w, h)
vein = np.abs(np.sin(u * 0.15 - v * 0.31 + np.sin(u * 0.4))) < 0.06
base[vein] = H('6a6458')
put('marble', 7, 1, base, np.ones((h, w), np.float32) + 0.15 * (1 - vn) + edge_ao(un, vn, 0.08, 0.15))

# ------------------------------------------------------------------ books on a shelf (one shelf section)
base = np.zeros((h, w, 3), np.float32); L = np.ones((h, w), np.float32)
spine_cols = ['5a1018', '1e3a24', '1c2848', '6a4a1c', '3a1a3a', '2a2a2a', '7a2a10', '20403e']
x = 1
base[:] = H('120a06')
while x < 31:
    bw = random.choice([2, 2, 3, 3, 4]); bh = random.randint(19, 27); col = random.choice(spine_cols)
    lean = 0
    top = 28 - bh
    for i in range(x, min(x + bw, 31)):
        base[top:28, i] = H(col)
        L[top:28, i] = 1.0 + (0.22 if i == x else -0.22 if i == x + bw - 1 else 0)
    for band in (top + 3, 24):
        base[band, x:min(x + bw, 31)] = H('c8a040')
    if random.random() < 0.4:
        base[top + 8:top + 11, x:min(x + bw, 31)] = H('d8c8a0')        # title label
    x += bw + (1 if random.random() < 0.15 else 0)
L[0:8, :] -= 0.35 * (1 - np.arange(8) / 8)[:, None]                   # shadow under the shelf above
base[28:32, :] = H('45301c'); L[28, :] = 1.3; L[29:31, :] = 1.0; L[31, :] = 0.55   # shelf plank
put('books', 0, 2, base, L)

# ------------------------------------------------------------------ clock face
cx, cy = 15.5, 15.5; r = np.sqrt((u - cx) ** 2 + (v - cy) ** 2)
base = ramp(['1c120c', '2e1e12'], noise(w, h), w, h)
base[r < 15] = H('b08838'); base[r < 13.5] = H('e0d4b0')
L = np.ones((h, w), np.float32) - 0.2 * vn + 0.1 * (1 - un)
for k in range(12):
    a = k * math.pi / 6; px, py = int(round(cx + math.sin(a) * 11)), int(round(cy - math.cos(a) * 11))
    base[py, px] = H('1a1010')
    if k % 3 == 0: base[py, px + (1 if px < 16 else -1)] = H('1a1010')
for a, ln in ((math.radians(-60), 7), (math.radians(80), 10)):     # hands: ~ 10 to 3
    for s in range(ln):
        base[int(round(cy - math.cos(a) * s)), int(round(cx + math.sin(a) * s))] = H('101010')
L[(r > 13.5) & (r < 15)] += np.where(((u - cx) + (v - cy) < 0)[(r > 13.5) & (r < 15)], 0.25, -0.25)
put('clock_face', 1, 2, base, L)

# ------------------------------------------------------------------ clock body front: panel + pendulum window
base = wood(['1c0e08', '30180c', '4a2414', '62301c'])
L = np.ones((h, w), np.float32) + 0.15 * (1 - vn) + edge_ao(un, vn, 0.1, 0.25)
sunk_rect(L, 6, 3, 26, 29, 0.25, 0.35)
base[5:27, 8:24] = ramp(['060404', '140c08'], noise(16, 22) if False else np.random.rand(22, 16), 16, 22)
for yy in range(5, 20): base[yy, 15:17] = H('9a7428')                # pendulum rod
pr = np.sqrt((u - 15.5) ** 2 + (v - 21) ** 2) < 3.2
base[pr] = H('d8b050'); L[pr & (u < 15) & (v < 21)] += 0.25
put('clock_body', 2, 2, base, L)

# ------------------------------------------------------------------ paintings (generic, invented)
def oil_bg(cols):
    return ramp(cols, 0.3 + vn * 0.3 + noise(w, h, 0.4), w, h)
# stern ancestor portrait: dark background, pale face oval, dark coat, white collar
base = oil_bg(['0e0a08', '1e1610', '2e2216'])
face = ((u - 15.5) / 5.2) ** 2 + ((v - 11) / 6.8) ** 2 < 1
hair = ((u - 15.5) / 6.6) ** 2 + ((v - 9) / 7) ** 2 < 1
body = (v > 18) & (np.abs(u - 15.5) < 4 + (v - 18) * 0.9)
collar = (v > 17) & (v < 21) & (np.abs(u - 15.5) < 3 + (v - 17) * 0.6)
base[hair] = H('1a1210'); base[body] = H('141418'); base[collar] = H('c8c0a8')
base[face] = ramp(['8a6a50', 'b89070', 'd8b090'], np.clip(0.8 - (u - 11) / 12, 0, 1), w, h)[face]
base[(np.abs(u - 13) < 1) & (np.abs(v - 10) < 0.6)] = H('1a0e0a'); base[(np.abs(u - 18) < 1) & (np.abs(v - 10) < 0.6)] = H('1a0e0a')
base[(v == 15) & (np.abs(u - 15.5) < 2)] = H('5a3428')
L = np.ones((h, w), np.float32) + 0.2 * (1 - un) - 0.1 * vn
put('portrait', 3, 2, base, L)
# lady in a high-necked dress, veil
base = oil_bg(['10141a', '1a2028', '28303a'])
face = ((u - 15.5) / 4.6) ** 2 + ((v - 10.5) / 6) ** 2 < 1
veil = ((u - 15.5) / 7.5) ** 2 + ((v - 12) / 9) ** 2 < 1
body = (v > 17) & (np.abs(u - 15.5) < 5 + (v - 17) * 0.8)
base[veil] = H('1c1820'); base[body] = H('3a1a30'); base[face] = ramp(['9a8a80', 'c8b8a8', 'e0d4c8'], np.clip(0.8 - (u - 11) / 10, 0, 1), w, h)[face]
base[(np.abs(u - 13.5) < 1) & (np.abs(v - 10) < 0.6)] = H('201418'); base[(np.abs(u - 17.5) < 1) & (np.abs(v - 10) < 0.6)] = H('201418')
base[(v > 19) & (v < 21) & (np.abs(u - 15.5) < 2)] = H('d8b050')    # brooch
put('portrait2', 2, 5, base, L)
# moonlit hills landscape
sky = ramp(['0a1020', '182848', '28406a'], 1 - vn * 1.3 + noise(w, h, 0.2), w, h)
base = sky.copy()
moon = (u - 22) ** 2 + (v - 7) ** 2 < 10
base[moon] = H('e8e4c8')
hill1 = v > 17 + 3 * np.sin(u * 0.2 + 1)
hill2 = v > 21 + 2 * np.sin(u * 0.33)
base[hill1] = ramp(['0e1a14', '1a2a1e'], noise(w, h), w, h)[hill1]
base[hill2] = ramp(['080e0a', '101a12'], noise(w, h), w, h)[hill2]
tree = (np.abs(u - 8) < 1) & (v > 11) & (v < 20) | (((u - 8) / 3.5) ** 2 + ((v - 11) / 3) ** 2 < 1)
base[tree] = H('06080a')
put('landscape', 4, 2, base, np.ones((h, w), np.float32) + 0.1 * (1 - un))

# ------------------------------------------------------------------ gilded frame, brass
base = ramp(['5a3e10', '8a6420', 'b88a30', 'e0b850'], 0.5 + noise(w, h, 0.4), w, h)
L = np.ones((h, w), np.float32)
for k in range(4):                                   # stepped ornate profile
    bevel_rect(L, k * 3, k * 3, 32 - k * 3, 32 - k * 3, hi=0.25, lo=0.3)
L[(u + v) % 5 == 0] += 0.12
put('frame', 5, 2, base, L)
base = ramp(['5a4010', '9a7428', 'd0a840', 'f0d070'], 0.5 + (1 - vn) * 0.3 + noise(w, h, 0.3), w, h)
L = np.ones((h, w), np.float32) + 0.3 * (1 - vn) - 0.2 * vn; L[:, 6:8] += 0.3
put('brass', 6, 2, base, L)

# ------------------------------------------------------------------ door leaf (32x64)
w, h = 32, 64; u, v, un, vn = grid(w, h)
base = wood(['24100a', '3a1c10', '552a18', '6a3820'])
L = np.ones((h, w), np.float32) + 0.12 * (1 - vn) + edge_ao(un, vn, 0.05, 0.25)
for (y0, y1) in ((4, 26), (32, 60)):
    bevel_rect(L, 5, y0, 27, y1, 0.3, 0.38, 2)
    L[y0 + 3:y1 - 3, 8:24] += 0.06
kn = (u - 26) ** 2 + (v - 30) ** 2 < 4
base[kn] = H('d0a840'); L[kn] = 1.15; L[(u - 25.5) ** 2 + (v - 29.5) ** 2 < 1] = 1.32
put('door', 7, 2, base, L, ch=2)

# ------------------------------------------------------------------ moonlit window (32x64), leaded panes
sky = ramp(['101c34', '1c3058', '2a4878', '4a6a98'], np.clip(1 - vn * 1.1 + noise(w, h, 0.18), 0, 1), w, h)
base = sky.copy()
moon = (u - 21) ** 2 + (v - 14) ** 2 < 26
base[moon] = ramp(['c8c8b0', 'f0f0dc'], np.clip(1 - ((u - 21) ** 2 + (v - 14) ** 2) / 26 + 0.3, 0, 1), w, h)[moon]
for sx_, sy_ in ((4, 6), (9, 22), (26, 34), (6, 40), (14, 3), (28, 5)):
    base[sy_, sx_] = H('d0d8f0')
treeline = v > 50 + 3 * np.sin(u * 0.5) + 2 * np.sin(u * 1.3)
base[treeline] = H('060a10')
lead = (u % 8 == 0) | (v % 10 == 0) | (u >= 30) | (v >= 62)
base[lead] = H('101014')
frame = (u < 2) | (u > 29) | (v < 2) | (v > 61) | ((v >= 30) & (v <= 33))
base[frame] = H('2e1e12')
put('window', 0, 3, base, None, ch=2, emissive=True)

# ------------------------------------------------------------------ velvet curtain (32x64): vertical folds + tie-back
fold = np.sin(u / 32 * math.pi * 5 + 0.3)
base = ramp(['3a0610', '5e0c18', '82142a'], 0.5 + noise(w, h, 0.2), w, h)
L = np.ones((h, w), np.float32) + 0.32 * fold - 0.15 * vn + 0.12 * (1 - vn)
tie = (v >= 38) & (v < 42)
base[tie] = H('c8a040'); L[tie] = 1.0 + 0.2 * (v[tie] == 38)
L[42:46] -= 0.2
put('curtain', 1, 3, base, L, ch=2)

w = h = C; u, v, un, vn = grid(w, h)
# ------------------------------------------------------------------ stair tread (carpet runner + wood ends) & riser
base = wood(['3a2212', '553018', '6e4020'])
car = (u >= 6) & (u < 26)
base[car] = ramp(['4a0a12', '6e1220', '8a1a28'], 0.5 + noise(w, h, 0.3), w, h)[car]
base[(u == 6) | (u == 25)] = H('c8a040')
L = np.ones((h, w), np.float32) - 0.18 * vn; L[0:3, :] += 0.28       # nosing highlight at the front edge (v=0)
put('tread', 2, 3, base, L)
base = wood(['24140a', '361e10', '4a2a16'])
base[car] = ramp(['3a0810', '560e1a'], 0.5 + noise(w, h, 0.3), w, h)[car]
L = np.ones((h, w), np.float32) * 0.8; L[0:6, :] -= 0.3 * (1 - np.arange(6) / 6)[:, None]   # shadow under nosing
put('riser', 3, 3, base, L)

# ------------------------------------------------------------------ balusters (alpha cut-out railing)
base = wood(['2a160c', '45240f', '5e3418'])
a = np.zeros((h, w), np.uint8)
L = np.ones((h, w), np.float32)
a[0:4, :] = 255; L[0, :] = 1.3; L[3, :] = 0.6                         # hand rail
a[29:32, :] = 255; L[29, :] = 1.15
for bx in (3, 11, 19, 27):
    prof = 1.2 + 0.6 * np.sin((v[:, 0] - 4) / 25 * math.pi * 3)
    for yy in range(4, 29):
        hw_ = prof[yy]
        for xx in range(int(bx - hw_), int(bx + hw_ + 1)):
            if 0 <= xx < 32:
                a[yy, xx] = 255; L[yy, xx] = 1.25 if xx < bx else 0.7
put('balusters', 4, 3, base, L, a=a)

# ------------------------------------------------------------------ upright piano front & keys
base = ramp(['060608', '101014', '1c1c22'], 0.4 + noise(w, h, 0.3), w, h)
L = np.ones((h, w), np.float32) + edge_ao(un, vn, 0.08, 0.2)
bevel_rect(L, 3, 3, 29, 15, 0.45, 0.3); bevel_rect(L, 3, 18, 15, 30, 0.45, 0.3); bevel_rect(L, 17, 18, 29, 30, 0.45, 0.3)
L[4:14, 6] += 0.5                                                     # lacquer streak
base[8, 12:20] = H('b08838')                                          # gilt maker's line
put('piano_front', 5, 3, base, L)
base = np.zeros((h, w, 3), np.float32) + H('e8e0cc')
L = np.ones((h, w), np.float32)
for kx in range(0, 32, 3): base[:, kx] = H('6a6458')
for kx in (2, 5, 11, 14, 17, 23, 26, 29):
    base[0:19, kx - 1:kx + 1] = H('0c0c0e'); L[18, kx - 1:kx + 1] = 0.5
L[:, :] -= 0.2 * vn; L[0:2, :] -= 0.3
put('piano_keys', 6, 3, base, L)

# ------------------------------------------------------------------ candle wax, flame (alpha, emissive), cobweb (alpha)
base = ramp(['a89a78', 'd8ccaa', 'f0e8d0'], 0.5 + noise(w, h, 0.25), w, h)
L = np.ones((h, w), np.float32) + 0.3 * (1 - un) - 0.3 * un
for dxp in (6, 19, 27): L[0:6 + dxp % 7, dxp] += 0.2                  # drips
put('candle', 2, 4, base, L)
r = np.sqrt(((u - 15.5) / 7) ** 2 + ((v - 20) / 11) ** 2 * (1 + (v < 20) * 0.6))
a = np.where(r + noise(w, h, 0.15) < 1.0, 255, 0).astype(np.uint8)
base = ramp(['c83808', 'f08018', 'ffd060', 'fff8d0'], np.clip(1.2 - r, 0, 1), w, h)
put('flame', 3, 4, base, None, a=a, emissive=True)
a = np.zeros((h, w), np.uint8); base = np.zeros((h, w, 3), np.float32) + H('c8c8cc')
for k in range(7):                                                    # radial strands from the corner (0,0)
    ang = k / 6 * math.pi / 2
    for s in range(40):
        xx, yy = int(s * math.cos(ang)), int(s * math.sin(ang))
        if xx < 32 and yy < 32: a[yy, xx] = 255
for rr in (6, 11, 17, 23, 29):                                        # sagging spiral threads
    for t_ in np.linspace(0, math.pi / 2, 60):
        sag = 1.0 - 0.12 * math.sin(t_ * 2) ** 2
        xx, yy = int(rr * sag * math.cos(t_)), int(rr * sag * math.sin(t_))
        if xx < 32 and yy < 32: a[yy, xx] = 255
put('cobweb', 4, 4, base, np.ones((h, w), np.float32) * (1.1 - 0.4 * vn), a=a)

# ------------------------------------------------------------------ sideboard front: two drawers over two doors
base = wood(['2a0e08', '45180c', '622416'])
L = np.ones((h, w), np.float32) + 0.15 * (1 - vn) + edge_ao(un, vn, 0.06, 0.25)
for (x0, y0, x1, y1) in ((2, 2, 15, 10), (17, 2, 30, 10), (2, 12, 15, 30), (17, 12, 30, 30)):
    bevel_rect(L, x0, y0, x1, y1, 0.28, 0.36)
for (kx, ky) in ((8, 6), (23, 6), (13, 21), (19, 21)):
    base[ky - 1:ky + 1, kx - 1:kx + 1] = H('d0a840'); L[ky - 1, kx - 1] = 1.32
put('sideboard', 5, 4, base, L)

# ------------------------------------------------------------------ hall runner (tiles along v), table top
base = ramp(['4a0a12', '6e1220', '8a1a28'], 0.5 + noise(w, h, 0.25), w, h)
bd = (u < 4) | (u > 27)
base[bd] = H('1c2448'); base[(u == 4) | (u == 27)] = H('c8a040')
base[bd & ((v % 8) < 2)] = H('c8a040')
dia = (np.abs(u - 15.5) + np.abs((v % 16) - 7.5) < 6) & (np.abs(u - 15.5) + np.abs((v % 16) - 7.5) > 4)
base[dia] = H('c8a040')
put('runner', 6, 4, base, np.ones((h, w), np.float32) - 0.05 + noise(w, h, 0.12))
base = wood(['220a06', '3a140a', '561e10', '702a18'])
L = np.ones((h, w), np.float32) + edge_ao(un, vn, 0.05, 0.2)
L += 0.35 * np.exp(-((un - vn * 0.6 - 0.25) ** 2) / 0.004)            # polished reflection streak
put('table_top', 7, 4, base, L)

# ------------------------------------------------------------------ dining chair back, pillar, blob shadow, logs, vase
base = wood(['2a0e08', '45180c', '622416'])
L = np.ones((h, w), np.float32) + 0.15 * (1 - vn) + edge_ao(un, vn, 0.08, 0.25)
pad = (u > 6) & (u < 25) & (v > 6) & (v < 26)
tb, tL = tufted(['4a0a12', '6e1220', '921c2a'], 6)
base[pad] = tb[pad]; L[pad] = tL[pad]
L[6, 6:25] = 0.55; L[6:26, 6] = 0.55; L[25, 6:25] = 1.25; L[6:26, 24] = 1.25
L[0:3, :] += 0.2                                                       # carved crest rail
put('chair_back', 0, 5, base, L)
base = wood(['24100a', '3a1c10', '552a18'])
L = np.ones((h, w), np.float32) + 0.35 * np.cos((un - 0.3) * math.pi) - 0.2
for fx in range(3, 32, 6): L[:, fx] -= 0.25; L[:, fx + 1] += 0.12      # fluting
L[0:3, :] += 0.25; L[29:32, :] -= 0.25
put('pillar', 1, 5, base, L)
r = np.sqrt((un - 0.5) ** 2 + (vn - 0.5) ** 2) * 2
a = (np.clip(1.0 - r, 0, 1) ** 0.7 * 170).astype(np.uint8)
put('blob', 3, 5, np.zeros((h, w, 3), np.float32), None, a=a)
base = ramp(['1a0e08', '2e1a0c', '42261a'], 0.5 + np.sin(u * 0.8) * 0.25 + noise(w, h, 0.3), w, h)
L = np.ones((h, w), np.float32) + 0.3 * (1 - vn) - 0.3 * vn
emb = (vn > 0.7) & (noise(w, h) > 0.6); base[emb] = H('d04010')
put('logs', 4, 5, base, L)
base = np.zeros((h, w, 3), np.float32) + H('e0e4ec')
pat = (np.sin(u * 0.8) * np.sin(v * 0.6) > 0.45) | (np.abs(v - 4) < 1) | (np.abs(v - 27) < 1)
base[pat] = H('2a4a9a')
L = np.ones((h, w), np.float32) + 0.35 * np.cos((un - 0.3) * math.pi) - 0.25
put('vase', 5, 5, base, L)

# ------------------------------------------------------------------ write atlas
out = np.zeros((ATLAS, ATLAS, 4), np.uint8)
out[..., :3] = (np.clip(rgb, 0, 1) * 255 + 0.5).astype(np.uint8)
out[..., 3] = alpha
Image.fromarray(out, 'RGBA').save('mansion_tex.png')
if __name__ == '__main__':
    Image.fromarray(out, 'RGBA').resize((768, 768), Image.NEAREST).save('mansion_tex_preview.png')
    print(len(RECTS), 'textures')
