"""Procedural PS1-style skeleton in a suit and top hat.
Outputs: skeleton.obj / skeleton.mtl / skeleton_tex.png (128x128) and model.json for the viewer."""
import math, json, random
import numpy as np
from PIL import Image

TEX = 128
random.seed(7)

# ---------------------------------------------------------------- texture
img = Image.new("RGB", (TEX, TEX), (14, 12, 18))
px = img.load()

PAL = {
    "bone0": (92, 80, 62), "bone1": (150, 136, 104), "bone2": (204, 192, 156), "bone3": (238, 232, 206),
    "dark": (14, 12, 18), "sock": (40, 10, 14),
    "suit0": (16, 16, 24), "suit1": (30, 30, 44), "suit2": (48, 48, 66), "suit3": (70, 70, 94),
    "shirt0": (150, 154, 160), "shirt1": (214, 218, 222), "shirt2": (246, 248, 250),
    "red0": (80, 8, 16), "red1": (150, 20, 30), "red2": (210, 48, 52),
    "gold": (214, 168, 60), "gold0": (130, 92, 30),
    "shoe0": (8, 8, 10), "shoe1": (28, 26, 30), "shoe2": (90, 88, 96),
}
BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]

def fill(x, y, w, h, c):
    for j in range(y, y + h):
        for i in range(x, x + w):
            if 0 <= i < TEX and 0 <= j < TEX:
                px[i, j] = PAL[c] if isinstance(c, str) else c

def put(i, j, c):
    if 0 <= i < TEX and 0 <= j < TEX:
        px[i, j] = PAL[c]

def grad_fill(x, y, w, h, cols, vertical=True, noise=0.0):
    """Ordered-dither gradient across a list of palette colours."""
    n = len(cols) - 1
    for j in range(h):
        for i in range(w):
            t = (j / max(h - 1, 1)) if vertical else (i / max(w - 1, 1))
            t = min(max(t + (random.random() - 0.5) * noise, 0), 0.999)
            f = t * n
            k = int(f)
            frac = f - k
            thr = (BAYER[j % 4][i % 4] + 0.5) / 16
            put(x + i, y + j, cols[min(k + (frac > thr), n)])

def speckle(x, y, w, h, c, amount):
    for _ in range(int(w * h * amount)):
        put(x + random.randrange(w), y + random.randrange(h), c)

R = {}  # named rects in pixels

exec(open("head_paint.py").read())
# --- generic bone 16x16 & hand 16x16
R["bone"] = (96, 0, 16, 16)
grad_fill(96, 0, 16, 16, ["bone1", "bone3", "bone2", "bone1"], vertical=False)
speckle(96, 0, 16, 16, "bone1", 0.06)
R["hand"] = (112, 0, 16, 16)
fill(112, 0, 16, 16, "dark")
for f in range(4):  # 4 bony fingers, knuckle dots
    x0 = 112 + 1 + f * 4
    for j in range(16):
        put(x0, j, "bone2"); put(x0 + 1, j, "bone3" if j % 5 else "bone1"); put(x0 + 2, j, "bone1")
R["hand_side"] = (96, 16, 32, 16)
grad_fill(96, 16, 32, 16, ["bone3", "bone2", "bone1"], noise=0.2)
for j in range(16, 32, 5):
    for i in range(96, 128): put(i, j, "bone0")

# --- jacket front 32x32: lapels, white shirt V, red bow tie, gold buttons
R["jacket_front"] = (0, 32, 32, 32)
x0, y0 = 0, 32
grad_fill(x0, y0, 32, 32, ["suit2", "suit1", "suit1", "suit0"], noise=0.1)
for j in range(32):
    half = max(0, 9 - j * 9 // 20)          # shirt V narrows downward
    for i in range(16 - half, 16 + half):
        put(x0 + i, y0 + j, "shirt2" if abs(i - 15.5) < half - 1 else "shirt1")
    lap = half + 4 if j < 24 else 0         # lapel band
    for i in list(range(16 - lap, 16 - half)) + list(range(16 + half, 16 + lap)):
        put(x0 + i, y0 + j, "suit3" if (i + j) % 3 else "suit2")
    if half > 0:
        put(x0 + 16 - half - 1, y0 + j, "suit0"); put(x0 + 16 + half, y0 + j, "suit0")
# shirt buttons / tie line
for j in range(10, 20, 3): put(x0 + 15, y0 + j, "shirt0")
# bow tie
for j in range(2, 8):
    for i in range(0, 12):
        d = abs(i - 5.5)
        if abs(j - 4.5) <= d * 0.55 + 0.6:
            put(x0 + 10 + i, y0 + j, "red2" if j < 5 else "red1")
fill(x0 + 15, y0 + 3, 2, 3, "red0")
# gold buttons
for j in (22, 27):
    put(x0 + 12, y0 + j, "gold"); put(x0 + 19, y0 + j, "gold")
    put(x0 + 12, y0 + j + 1, "gold0"); put(x0 + 19, y0 + j + 1, "gold0")
# pocket square
fill(x0 + 22, y0 + 13, 4, 2, "red2"); put(x0 + 23, y0 + 12, "red1")
for i in range(21, 28): put(x0 + i, y0 + 15, "suit0")

R["jacket_side"] = (32, 32, 32, 32)
grad_fill(32, 32, 32, 32, ["suit2", "suit1", "suit0"], noise=0.15)
for j in range(32): put(32 + 15, 32 + j, "suit0")      # centre seam
speckle(32, 32, 32, 32, "suit3", 0.02)

R["coat_front"] = (64, 32, 32, 16)   # lower jacket: opening + button
grad_fill(64, 32, 32, 16, ["suit1", "suit0"], noise=0.1)
for j in range(16):
    w = j // 3
    for i in range(16 - w, 16 + w): put(64 + i, 32 + j, "suit0" if i in (16 - w, 15 + w) else "shirt0" if j < 3 else "suit0")
    put(64 + 15 - w - 1, 32 + j, "suit3"); put(64 + 16 + w, 32 + j, "suit3")
put(64 + 12, 33, "gold"); put(64 + 19, 33, "gold")
R["coat_side"] = (64, 48, 32, 16)
grad_fill(64, 48, 32, 16, ["suit1", "suit0", "suit0"], noise=0.15)

R["sleeve"] = (96, 32, 32, 32)  # cuff at bottom (v high)
grad_fill(96, 32, 32, 28, ["suit2", "suit1", "suit0"], vertical=False, noise=0.15)
fill(96, 60, 32, 4, "shirt2")
for i in range(96, 128): put(i, 60, "shirt0")
for i in range(96, 128, 8): put(i + 3, 62, "gold")

# --- pants with pinstripes
R["pants"] = (0, 64, 32, 28)
grad_fill(0, 64, 32, 28, ["suit1", "suit1", "suit0"], vertical=False, noise=0.1)
for i in range(2, 32, 6):
    for j in range(64, 92):
        if j % 2: put(i, j, "suit3")
R["sock"] = (0, 92, 32, 4)
fill(0, 92, 32, 4, "sock")

# --- shoes
R["shoe"] = (32, 64, 32, 16)
grad_fill(32, 64, 32, 16, ["shoe2", "shoe1", "shoe0", "shoe0"])
for i in range(32, 64): put(i, 79, "dark")
R["shoe_top"] = (32, 80, 32, 16)
grad_fill(32, 80, 32, 16, ["shoe1", "shoe0"], vertical=False)
for j in range(84, 92, 2): fill(44, j, 8, 1, "shoe2")   # laces
put(36, 82, "shoe2"); put(37, 82, "shoe2")             # shine

# --- top hat
R["hat_crown"] = (64, 64, 64, 32)
grad_fill(64, 64, 64, 32, ["suit2", "suit1", "suit0", "dark"], noise=0.1)
for i in range(64, 128, 8):                    # sheen streaks
    for j in range(66, 84):
        if (j + i) % 4 == 0: put(i + 2, j, "suit3")
fill(64, 86, 64, 6, "red1")                    # band
for i in range(64, 128): put(i, 86, "red2"); put(i, 91, "red0")
fill(64 + 28, 86, 8, 6, "gold"); fill(64 + 30, 88, 4, 2, "gold0")  # buckle (front)
R["hat_top"] = (0, 96, 32, 32)
grad_fill(0, 96, 32, 32, ["suit2", "suit1", "suit0"], noise=0.2)
R["hat_brim"] = (32, 96, 32, 32)
grad_fill(32, 96, 32, 32, ["suit1", "suit0", "dark"], noise=0.2)
R["neck"] = R["bone"]

exec(open("bake_light.py").read())
img.save("skeleton_tex.png")

# ---------------------------------------------------------------- geometry
V, N, UV, TRI = [], [], [], []  # unindexed per-corner lists -> we'll index later

def uv_of(rect, u, v):
    x, y, w, h = rect
    # inset half a texel to avoid bleeding
    return ((x + 0.5 + u * (w - 1)) / TEX, 1.0 - (y + 0.5 + v * (h - 1)) / TEX)

PART = []
CUR = ['torso']
def tri(p, n, t):
    TRI.append((p, n, t)); PART.append(CUR[0])

def quad(a, b, c, d, n, rect, flip=False):
    """a b c d counter-clockwise seen from outside; a=bottom-left."""
    ua, ub, uc, ud = uv_of(rect, 0, 1), uv_of(rect, 1, 1), uv_of(rect, 1, 0), uv_of(rect, 0, 0)
    tri((a, b, c), (n, n, n), (ua, ub, uc))
    tri((a, c, d), (n, n, n), (ua, uc, ud))

def norm(v):
    v = np.asarray(v, float); l = np.linalg.norm(v); return v / l if l else v

def box(center, size, faces, rot_basis=None, taper=1.0):
    """Box with per-face rects. faces keys: front back left right top bottom (fallback 'side').
    taper scales the top face (x,z) for tapered torsos."""
    cx, cy, cz = center; sx, sy, sz = [s / 2 for s in size]
    def P(x, y, z):
        k = taper if y > 0 else 1.0
        p = np.array([x * k, y, z * (1 + (k - 1) * 0.5) if y > 0 else z])
        if rot_basis is not None: p = rot_basis @ p
        return tuple(p + np.array(center))
    c = {}
    for xs in (-1, 1):
        for ys in (-1, 1):
            for zs in (-1, 1):
                c[(xs, ys, zs)] = P(xs * sx, ys * sy, zs * sz)
    g = lambda k: faces.get(k, faces.get("side"))
    def F(a, b, cc, d, key):
        if key in faces and faces[key] is None: return
        n = norm(np.cross(np.subtract(b, a), np.subtract(d, a)))
        quad(a, b, cc, d, tuple(n), g(key))
    F(c[(-1,-1,1)], c[(1,-1,1)], c[(1,1,1)], c[(-1,1,1)], "front")
    F(c[(1,-1,-1)], c[(-1,-1,-1)], c[(-1,1,-1)], c[(1,1,-1)], "back")
    F(c[(1,-1,1)], c[(1,-1,-1)], c[(1,1,-1)], c[(1,1,1)], "right")
    F(c[(-1,-1,-1)], c[(-1,-1,1)], c[(-1,1,1)], c[(-1,1,-1)], "left")
    F(c[(-1,1,1)], c[(1,1,1)], c[(1,1,-1)], c[(-1,1,-1)], "top")
    if True:
        F(c[(-1,-1,-1)], c[(1,-1,-1)], c[(1,-1,1)], c[(-1,-1,1)], "bottom")

def limb(a, b, w, d, faces, twist_out=0.0):
    a, b = np.array(a, float), np.array(b, float)
    yax = norm(b - a)
    zax = norm(np.cross(np.array([1.0, 0, 0]), yax))
    if np.linalg.norm(zax) < 1e-6: zax = np.array([0, 0, 1.0])
    xax = norm(np.cross(yax, zax))
    basis = np.column_stack([xax, yax, zax])
    L = np.linalg.norm(b - a)
    box(tuple((a + b) / 2), (w, L, d), faces, rot_basis=basis)

def lathe(cy_list, r_list, sides, rect, cap_top=None, cap_bot=None, zscale=1.0, center=(0, 0, 0), u_off=0.5, smooth=True):
    """Vertical surface of revolution. front (+z) maps to u=u_off of rect."""
    cx, _, cz = center
    def ring(i, k):
        ang = 2 * math.pi * k / sides
        return (cx + r_list[i] * math.sin(ang), cy_list[i], cz + r_list[i] * math.cos(ang) * zscale)
    nrm = lambda k: tuple(norm((math.sin(2*math.pi*k/sides), 0, math.cos(2*math.pi*k/sides) * zscale)))
    for i in range(len(cy_list) - 1):
        v0 = 1 - i / (len(cy_list) - 1); v1 = 1 - (i + 1) / (len(cy_list) - 1)
        for k in range(sides):
            u0 = ((k / sides) + u_off) % 1.0; u1 = u0 + 1 / sides
            a, b = ring(i, k), ring(i, k + 1); c, dd = ring(i + 1, k + 1), ring(i + 1, k)
            if smooth: na, nb = nrm(k), nrm(k + 1)
            else:
                na = nb = tuple(norm(np.cross(np.subtract(b, a), np.subtract(dd, a))))
            ta, tb, tc, td = uv_of(rect, u0, v0), uv_of(rect, u1, v0), uv_of(rect, u1, v1), uv_of(rect, u0, v1)
            tri((a, b, c), (na, nb, nb), (ta, tb, tc))
            tri((a, c, dd), (na, nb, na), (ta, tc, td))
    for cap, i, up in ((cap_top, len(cy_list) - 1, 1), (cap_bot, 0, -1)):
        if cap is None: continue
        pts = [ring(i, k) for k in range(sides)]
        uvs = [uv_of(cap, 0.5 + 0.5 * math.sin(2*math.pi*k/sides), 0.5 + 0.5 * math.cos(2*math.pi*k/sides)) for k in range(sides)]
        n = (0, up, 0)
        for k in range(1, sides - 1):  # triangle fan, sides-2 tris
            if up > 0: tri((pts[0], pts[k], pts[k+1]), (n, n, n), (uvs[0], uvs[k], uvs[k+1]))
            else:      tri((pts[0], pts[k+1], pts[k]), (n, n, n), (uvs[0], uvs[k+1], uvs[k]))

S = lambda r: {"side": R[r]}

# ---- legs & shoes
for sx in (-1, 1):
    x = sx * 0.105
    side = "L" if sx > 0 else "R"
    CUR[0] = "thigh_" + side
    limb((x, 0.52, 0), (x, 0.92, 0.0), 0.13, 0.14, S("pants"))
    CUR[0] = "shin_" + side
    limb((x, 0.10, -0.01), (x, 0.52, 0), 0.115, 0.12, {"side": R["pants"], "bottom": R["sock"]})
    box((x, 0.055, 0.035), (0.12, 0.11, 0.26), {"side": R["shoe"], "top": R["shoe_top"], "bottom": R["shoe"]}, taper=0.9)

# ---- hips / coat tails / torso
CUR[0] = "torso"
box((0, 0.93, 0), (0.40, 0.20, 0.235), {"front": R["coat_front"], "side": R["coat_side"], "bottom": R["coat_side"]}, taper=1.0)
box((0, 1.24, 0), (0.38, 0.42, 0.24), {"front": R["jacket_front"], "side": R["jacket_side"], "top": R["jacket_side"], "bottom": None}, taper=1.28)

# ---- arms (shoulder -> elbow -> wrist), slightly out from body
for sx in (-1, 1):
    sh = (sx * 0.27, 1.40, 0.0); el = (sx * 0.33, 1.13, -0.02); wr = (sx * 0.36, 0.88, 0.04)
    side = "L" if sx > 0 else "R"
    CUR[0] = "uarm_" + side
    limb(sh, el, 0.12, 0.13, S("jacket_side"))
    CUR[0] = "farm_" + side
    limb(el, wr, 0.11, 0.12, {"side": R["sleeve"], "bottom": R["bone"]})
    hd = (sx * 0.375, 0.76, 0.06)
    limb(wr, hd, 0.075, 0.035, {"front": R["hand"], "back": R["hand"], "side": R["hand_side"], "top": R["bone"], "bottom": R["bone"]})

# ---- neck + box-modelled head
CUR[0] = "head"
limb((0, 1.42, -0.02), (0, 1.53, -0.02), 0.06, 0.06, S("neck"))
exec(open("head_geo.py").read())

# ---- top hat (slightly cocked)
CUR[0] = "hat"
hat_start = len(TRI)
lathe([1.795, 1.82], [0.24, 0.24], 10, R["hat_brim"], cap_top=R["hat_brim"], cap_bot=R["hat_brim"], smooth=False)
lathe([1.81, 1.92, 2.06], [0.135, 0.14, 0.15], 8, R["hat_crown"], cap_top=R["hat_top"], u_off=0.5)
ang = math.radians(-8)
Rz = np.array([[math.cos(ang), -math.sin(ang), 0], [math.sin(ang), math.cos(ang), 0], [0, 0, 1]])
pivot = np.array([0, 1.80, 0])
for i in range(hat_start, len(TRI)):
    p, n, t = TRI[i]
    p = tuple(tuple(Rz @ (np.array(q) - pivot) + pivot + np.array([0.012, 0.0, 0])) for q in p)
    n = tuple(tuple(Rz @ np.array(q)) for q in n)
    TRI[i] = (p, n, t)

ntri = len(TRI)
print("triangles:", ntri)
assert ntri <= 500

# ---------------------------------------------------------------- index + export
vmap, verts, idx = {}, [], []
for p, n, t in TRI:
    for k in range(3):
        key = (tuple(round(c, 5) for c in p[k]), tuple(round(c, 4) for c in n[k]), tuple(round(c, 5) for c in t[k]))
        if key not in vmap:
            vmap[key] = len(verts); verts.append(key)
        idx.append(vmap[key])
print("vertices:", len(verts))

with open("skeleton.mtl", "w") as f:
    f.write("newmtl skeleton\nKd 1 1 1\nmap_Kd skeleton_tex.png\n")
with open("skeleton.obj", "w") as f:
    f.write(f"# PS1-style suited skeleton - {ntri} triangles\nmtllib skeleton.mtl\no Skeleton\n")
    for p, n, t in verts: f.write("v %.5f %.5f %.5f\n" % p)
    for p, n, t in verts: f.write("vt %.5f %.5f\n" % t)
    for p, n, t in verts: f.write("vn %.4f %.4f %.4f\n" % n)
    f.write("usemtl skeleton\ns off\n")
    for i in range(0, len(idx), 3):
        a, b, c = idx[i] + 1, idx[i+1] + 1, idx[i+2] + 1
        f.write(f"f {a}/{a}/{a} {b}/{b}/{b} {c}/{c}/{c}\n")

json.dump({"pos": [c for v in verts for c in v[0]], "nrm": [c for v in verts for c in v[1]],
           "uv": [c for v in verts for c in v[2]], "idx": idx, "tris": ntri}, open("model.json", "w"))

# ---------------------------------------------------------------- segmented export for the game (grim.bin)
import struct
from collections import Counter
print(Counter(PART))
PARTS = [  # name, parent, pivot (model space)
    ("torso", -1, (0, 0.93, 0)), ("head", 0, (0, 1.45, -0.02)), ("hat", 1, (0, 1.80, 0)),
    ("uarm_L", 0, (0.27, 1.40, 0)), ("farm_L", 3, (0.33, 1.13, -0.02)),
    ("uarm_R", 0, (-0.27, 1.40, 0)), ("farm_R", 5, (-0.33, 1.13, -0.02)),
    ("thigh_L", -1, (0.105, 0.92, 0)), ("shin_L", 7, (0.105, 0.52, 0)),
    ("thigh_R", -1, (-0.105, 0.92, 0)), ("shin_R", 9, (-0.105, 0.52, 0)),
]
with open("grim.bin", "wb") as f:
    f.write(b"GRM1"); f.write(struct.pack("<i", len(PARTS)))
    body = bytearray(); start = 0
    for name, parent, piv in PARTS:
        tris = [TRI[i] for i in range(len(TRI)) if PART[i] == name]
        nb = name.encode()
        f.write(struct.pack("<i", len(nb))); f.write(nb)
        f.write(struct.pack("<i3fii", parent, *piv, start, len(tris) * 3))
        for p, n, t in tris:
            for k in range(3):
                body += struct.pack("<8f", *p[k], *n[k], t[k][0], 1.0 - t[k][1])  # top-left UV origin for Android
        start += len(tris) * 3
    f.write(struct.pack("<i", start)); f.write(body)
print("grim.bin verts", start)
