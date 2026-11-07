# Hand-painted style baked lighting pass. Executed inside build_skeleton.py (shares px, R, PAL, BAYER).
# Key light: upper-left-front. Shading is quantised into dithered steps so it stays pixel art.
LEVELS = [0.50, 0.66, 0.82, 1.0, 1.16]

def shade_px(i, j, f):
    """Multiply pixel by brightness f, quantised to LEVELS with 4x4 ordered dither."""
    if not (0 <= i < TEX and 0 <= j < TEX): return
    f = max(LEVELS[0], min(LEVELS[-1], f))
    k = 0
    while k < len(LEVELS) - 2 and LEVELS[k + 1] <= f: k += 1
    lo, hi = LEVELS[k], LEVELS[k + 1]
    t = (f - lo) / (hi - lo)
    m = hi if t > (BAYER[j % 4][i % 4] + 0.5) / 16 else lo
    r, g, b = px[i, j]
    px[i, j] = (min(255, int(r * m + (8 if m > 1 else 0))), min(255, int(g * m + (6 if m > 1 else 0))), min(255, int(b * m + (4 if m > 1 else 0))))

def light_map(rect, fn):
    x, y, w, h = rect
    for j in range(h):
        for i in range(w):
            shade_px(x + i, y + j, fn(i / max(w - 1, 1), j / max(h - 1, 1)))

def edge_ao(u, v, k=0.12, amt=0.22):
    d = min(u, 1 - u, v, 1 - v)
    return -amt * max(0, (k - d) / k)

def face_light(u, v):              # front-facing box face: brighter top-left, darker bottom, AO edges
    return 1.0 + 0.16 * (1 - v) - 0.10 * v + 0.08 * (0.5 - u) + edge_ao(u, v)

def wrap_light(u, v):              # wrapped strip, front at u=0.5, key light slightly to viewer's left
    import math
    a = (u - 0.5) * 2 * math.pi
    lam = max(0, math.cos(a - 0.6))
    return 0.62 + 0.48 * lam + 0.10 * (1 - v)

exec(open("head_bake.py").read())
light_map(R["bone"], lambda u, v: 1.0 + 0.18 * (0.5 - abs(u - 0.35)) - 0.15 * abs(u - 0.35) * 2)
light_map(R["hand"], lambda u, v: 1.05 - 0.3 * v)          # fingertips fall into shade
light_map(R["hand_side"], lambda u, v: 0.85 - 0.25 * v)

# --- jacket: top lit, lapel drop shadows, bow-tie shadow on shirt, waist folds
x0, y0 = R["jacket_front"][:2]
light_map(R["jacket_front"], lambda u, v: face_light(u, v) + 0.05)
for j in range(8, 11):            # bow tie casts shadow onto the shirt
    for i in range(10, 22): shade_px(x0 + i, y0 + j, 0.68 if j < 10 else 0.82)
for j in range(24):               # lapel edges: lit left edge, shadowed right edge
    half = max(0, 9 - j * 9 // 20); lap = half + 4
    shade_px(x0 + 16 - lap, y0 + j, 1.18); shade_px(x0 + 16 + lap, y0 + j, 0.58)
    shade_px(x0 + 16 + lap + 1, y0 + j, 0.72)
for (fx, fy) in ((6, 26), (24, 25)):  # horizontal pull folds near buttons
    for k in range(5):
        shade_px(x0 + fx + k, y0 + fy - k // 2, 1.16); shade_px(x0 + fx + k, y0 + fy - k // 2 + 1, 0.6)
light_map(R["jacket_side"], lambda u, v: 0.9 + 0.14 * (1 - v) - 0.18 * u + edge_ao(u, v))
xs, ys = R["jacket_side"][:2]
for j in range(18, 32):           # armpit / side crease shadow
    shade_px(xs + 4, ys + j, 0.6); shade_px(xs + 27, ys + j, 0.6)
light_map(R["coat_front"], lambda u, v: 0.92 - 0.25 * v + edge_ao(u, v, amt=0.15))
light_map(R["coat_side"], lambda u, v: 0.82 - 0.22 * v + edge_ao(u, v))

# sleeves: cylindrical lighting + elbow creases + cuff shadow
light_map(R["sleeve"], lambda u, v: 1.08 - 0.42 * abs(u - 0.3) * 2 - 0.1 * v)
xs, ys = R["sleeve"][:2]
for k in range(3):
    for i in range(6, 26, 2):
        shade_px(xs + i, ys + 3 + k * 4 + (i % 4) // 2, 0.62)
        shade_px(xs + i, ys + 2 + k * 4 + (i % 4) // 2, 1.16)
for i in range(32): shade_px(xs + i, ys + 27, 0.55)   # sleeve shadow on cuff

# pants: cylinder lighting + knee folds
light_map(R["pants"], lambda u, v: 1.06 - 0.45 * abs(u - 0.3) * 2 - 0.08 * v)
xs, ys = R["pants"][:2]
for (fy, fx) in ((4, 8), (10, 14), (22, 10), (26, 18)):
    for k in range(7):
        shade_px(xs + fx + k, ys + fy + k // 3, 1.18); shade_px(xs + fx + k, ys + fy + 1 + k // 3, 0.58)
light_map(R["sock"], lambda u, v: 0.9)

# shoes: glossy - sharp specular streak + floor occlusion
light_map(R["shoe"], lambda u, v: 1.0 - 0.3 * v)
xs, ys = R["shoe"][:2]
for i in range(6, 14): put(xs + i, ys + 3, "shoe2"); put(xs + i + 1, ys + 2, "shirt0")
light_map(R["shoe_top"], lambda u, v: 1.1 - 0.35 * u)
xs, ys = R["shoe_top"][:2]
fill(xs + 3, ys + 3, 3, 2, "shirt0"); put(xs + 4, ys + 6, "shoe2")

# hat: wrap lighting, sheen streak on lit side, band occlusion, top & brim AO
light_map(R["hat_crown"], lambda u, v: wrap_light(u, v) + 0.1 - 0.12 * v)
xs, ys = R["hat_crown"][:2]
for j in range(2, 21):            # vertical satin highlight on the lit side
    put(xs + 22, ys + j, "suit3");
    if j % 2: put(xs + 23, ys + j, "shoe2")
for i in range(64): shade_px(xs + i, ys + 21, 0.55)   # crease above band
light_map(R["hat_top"], lambda u, v: 1.05 + 0.15 * (0.5 - u) + 0.15 * (0.5 - v) + edge_ao(u, v, 0.2, 0.25))
import math as _m
def brim(u, v):                   # radial UV: centre is under the crown -> deep AO ring
    r = _m.hypot(u - 0.5, v - 0.5) * 2
    return (0.55 if r < 0.62 else 0.75 if r < 0.72 else 1.0) + 0.12 * (0.5 - u) - 0.1 * (r > 0.95)
light_map(R["hat_brim"], brim)
