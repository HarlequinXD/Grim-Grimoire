"""Grim Grimoire - box-modelled mansion hall.
Builds geometry from boxes and tiled quads, bakes PS1-style vertex lighting (point lights with
ray-cast shadows against the furniture), and writes mansion.bin for the game:

  "MNS1" | int vcount | vcount * (pos3 uv2 col4)       col = rgb light multiplier, a = fire flicker weight
         | int nbox   | nbox * (min3 max3)              collision AABBs
         | int nlight | nlight * (pos3 rgb3 radius flicker)
         | spawn (x y z yaw)
"""
import math, struct, json
import numpy as np
exec(open('mansion_tex.py').read())          # builds atlas, RECTS, EMISSIVE
ATL = float(ATLAS)

VERTS = []   # (pos, normal, uv, emissive)
SOLIDS = []  # collision AABBs
OCC = []     # shadow occluders (AABBs)
LIGHTS = []  # (pos, rgb, radius, flicker)

# ------------------------------------------------------------------ primitives
def uvr(rect, s, t, flip_u=False):
    x, y, w, h = rect
    if flip_u: s = 1 - s
    return ((x + 0.02 + s * (w - 0.04)) / ATL, (y + 0.02 + t * (h - 0.04)) / ATL)

class Xf:
    """Yaw rotation about +y then translation (furniture groups)."""
    def __init__(self, pos=(0, 0, 0), yaw=0.0):
        self.p = np.array(pos, float); c, s = math.cos(yaw), math.sin(yaw)
        self.R = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    def pt(self, q): return self.R @ np.asarray(q, float) + self.p
    def vec(self, q): return self.R @ np.asarray(q, float)
IDENT = Xf()

def quad(o, U, V, tex, nu=1, nv=1, tile=False, xf=IDENT, double=False, flip_u=False):
    """Quad from origin o (texture top-left) along U (texture u) and V (texture v, i.e. downward).
    Subdivided nu x nv; tile=True maps the whole texture onto every sub-quad (PS1 style tiling)."""
    rect = RECTS[tex]; em = tex in EMISSIVE
    o, U, V = np.asarray(o, float), np.asarray(U, float), np.asarray(V, float)
    n = np.cross(V, U); n = n / (np.linalg.norm(n) or 1)
    nW = xf.vec(n)
    for i in range(nu):
        for j in range(nv):
            def P(a, b): return xf.pt(o + U * ((i + a) / nu) + V * ((j + b) / nv))
            if tile: T = lambda a, b: uvr(rect, a, b, flip_u)
            else: T = lambda a, b: uvr(rect, (i + a) / nu, (j + b) / nv, flip_u)
            c = [(0, 1), (1, 1), (1, 0), (0, 0)]          # bl, br, tr, tl  (CCW from the front)
            p = [P(*k) for k in c]; t = [T(*k) for k in c]
            for a, b, cc in ((0, 1, 2), (0, 2, 3)):
                for k in (a, b, cc): VERTS.append((p[k], nW, t[k], em))
                if double:
                    for k in (a, cc, b): VERTS.append((p[k], -nW, t[k], em))

def seg(L, step=1.0): return max(1, int(math.ceil(L / step - 1e-6)))

def box(x0, y0, z0, x1, y1, z1, tex, xf=IDENT, solid=True, occ=True, skip=(), step=1.0, tiles=None):
    """Axis-aligned box in local space. tex: str or dict face->tex (front back left right top bottom side).
    tiles: dict face->(nu,nv) to tile the texture instead of stretching."""
    if isinstance(tex, str): tex = {'side': tex}
    g = lambda f: tex.get(f, tex.get('side'))
    dx, dy, dz = x1 - x0, y1 - y0, z1 - z0
    F = {'front': ((x0, y1, z1), (dx, 0, 0), (0, -dy, 0), dx, dy),
         'back': ((x1, y1, z0), (-dx, 0, 0), (0, -dy, 0), dx, dy),
         'right': ((x1, y1, z1), (0, 0, -dz), (0, -dy, 0), dz, dy),
         'left': ((x0, y1, z0), (0, 0, dz), (0, -dy, 0), dz, dy),
         'top': ((x0, y1, z0), (dx, 0, 0), (0, 0, dz), dx, dz),
         'bottom': ((x0, y0, z1), (dx, 0, 0), (0, 0, -dz), dx, dz)}
    for f, (o, U, V, lu, lv) in F.items():
        if f in skip or g(f) is None: continue
        if tiles and f in tiles: quad(o, U, V, g(f), *tiles[f], tile=True, xf=xf)
        else: quad(o, U, V, g(f), seg(lu, step), seg(lv, step), xf=xf)
    cs = np.array([xf.pt((x, y, z)) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)])
    bb = (tuple(cs.min(0)), tuple(cs.max(0)))
    if solid: SOLIDS.append(bb)
    if occ: OCC.append(bb)
    return bb

def prism(cx, cz, y0, y1, r, sides, tex, xf=IDENT, cap=None):
    """Low-poly vertical prism (candles, vases, posts)."""
    rect = RECTS[tex]; em = tex in EMISSIVE
    for k in range(sides):
        a0, a1 = 2 * math.pi * k / sides, 2 * math.pi * (k + 1) / sides
        p = [xf.pt((cx + r * math.sin(a), y, cz + r * math.cos(a))) for a, y in ((a0, y0), (a1, y0), (a1, y1), (a0, y1))]
        n = xf.vec((math.sin((a0 + a1) / 2), 0, math.cos((a0 + a1) / 2)))
        t = [uvr(rect, k / sides, 1), uvr(rect, (k + 1) / sides, 1), uvr(rect, (k + 1) / sides, 0), uvr(rect, k / sides, 0)]
        for i in (0, 1, 2, 0, 2, 3): VERTS.append((p[i], n, t[i], em))
    if cap:
        rc = RECTS[cap]; c = xf.pt((cx, y1, cz))
        for k in range(sides):
            a0, a1 = 2 * math.pi * k / sides, 2 * math.pi * (k + 1) / sides
            for (pt, s, t) in ((c, 0.5, 0.5), (xf.pt((cx + r * math.sin(a0), y1, cz + r * math.cos(a0))), 0.5 + 0.5 * math.sin(a0), 0.5 + 0.5 * math.cos(a0)),
                               (xf.pt((cx + r * math.sin(a1), y1, cz + r * math.cos(a1))), 0.5 + 0.5 * math.sin(a1), 0.5 + 0.5 * math.cos(a1))):
                VERTS.append((pt, np.array([0, 1.0, 0]), uvr(rc, s, t), cap in EMISSIVE))

def flame(x, y, z, s=0.07, xf=IDENT):
    """Two crossed alpha quads (PS1 billboard-ish candle flame)."""
    quad((x - s, y + 2.2 * s, z), (2 * s, 0, 0), (0, -2.2 * s, 0), 'flame', xf=xf, double=True)
    quad((x, y + 2.2 * s, z - s), (0, 0, 2 * s), (0, -2.2 * s, 0), 'flame', xf=xf, double=True)

def candle(x, y, z, h=0.18, xf=IDENT, light=None):
    prism(x, z, y, y + h, 0.025, 4, 'candle', xf=xf, cap='candle')
    flame(x, y + h, z, xf=xf)
    if light:
        LIGHTS.append((tuple(xf.pt((x, y + h + 0.1, z))),) + light)

# ------------------------------------------------------------------ room shell: 18 x 14 x 5.5 m
X0, X1, Z0, Z1, YC = -9.0, 9.0, -7.0, 7.0, 5.5
WAIN, MOLD = 1.2, 5.1
quad((X0, 0, Z0), (18, 0, 0), (0, 0, 14), 'floor', 18, 14, tile=True)               # floor, 1 m planks tiles
quad((X0, YC, Z1), (18, 0, 0), (0, 0, -14), 'ceiling', 9, 7, tile=True)            # coffered ceiling (2 m)

def wall(o, along, length, openings=()):
    """Wall: wainscot (0-1.2), wallpaper (1.2-5.1), crown molding (5.1-5.5). Normal faces into the room.
    openings: list of (start, end, bottom, top) along the wall where nothing is generated (door/window holes)."""
    o, along = np.array(o, float), np.array(along, float)
    for i in range(int(length)):
        for (y0, y1, tex) in ((0, WAIN, 'wainscot'), (WAIN, MOLD, 'wallpaper'), (MOLD, YC, 'molding')):
            # split into 1 m cells vertically for wallpaper so the tiles stay square
            cells = [(y0, y1)] if tex != 'wallpaper' else [(y, min(y + 1.3, y1)) for y in np.arange(y0, y1 - 1e-6, 1.3)]
            for (a, b) in cells:
                if any(s <= i + 0.5 <= e and bot < (a + b) / 2 < top for (s, e, bot, top) in openings): continue
                quad(o + along * i + np.array([0, b, 0]), along, (0, -(b - a), 0), tex)
wall((X0, 0, Z0), (1, 0, 0), 18, openings=[(8, 10, 2.6, 5.0)])            # north (upper door)
wall((X1, 0, Z1), (-1, 0, 0), 18, openings=[(8, 10, 0, 3.4), (3, 5, 1.0, 4.2), (13, 15, 1.0, 4.2)])  # south: door + 2 windows
wall((X0, 0, Z1), (0, 0, -1), 14)                                                       # west
wall((X1, 0, Z0), (0, 0, 1), 14, openings=[(10, 12, 1.0, 4.2)])                     # east: window
# walls are solid
for bb in (((X0 - 1, -1, Z0 - 1), (X1 + 1, 9, Z0)), ((X0 - 1, -1, Z1), (X1 + 1, 9, Z1 + 1)),
           ((X0 - 1, -1, Z0), (X0, 9, Z1)), ((X1, -1, Z0), (X1 + 1, 9, Z1))):
    SOLIDS.append(bb)

# ceiling beams across x every 3 m
for bz in (-4.5, -1.5, 1.5, 4.5):
    box(X0, YC - 0.35, bz - 0.18, X1, YC, bz + 0.18, 'beam', solid=False, occ=False, skip=('top',), step=1.0)

# ------------------------------------------------------------------ openings: frames, doors, windows
def door_frame(cx, z, w, h, facing=1, double=True, y0=0.0):
    """Door set into a north/south wall: trim + closed leaves. facing = +1 if room is at +z of the wall."""
    zf = z + 0.02 * facing
    t = 0.14
    f = {'side': 'mahogany'}
    box(cx - w / 2 - t, y0, z - 0.05, cx - w / 2, y0 + h + t, z + 0.12 * facing if facing > 0 else z + 0.05, f, solid=False, occ=False)
    box(cx + w / 2, y0, min(z, z + 0.12 * facing), cx + w / 2 + t, y0 + h + t, max(z, z + 0.12 * facing), f, solid=False, occ=False)
    box(cx - w / 2 - t, y0 + h, min(z, z + 0.12 * facing), cx + w / 2 + t, y0 + h + t * 1.6, max(z, z + 0.12 * facing), f, solid=False, occ=False)
    # leaves
    n = 2 if double else 1; lw = w / n
    for k in range(n):
        x = cx - w / 2 + k * lw
        if facing > 0: quad((x, y0 + h, zf), (lw, 0, 0), (0, -h, 0), 'door', flip_u=(k == 0 and double))
        else: quad((x + lw, y0 + h, zf), (-lw, 0, 0), (0, -h, 0), 'door', flip_u=(k == 0 and double))

def window(cx, cz, along, w=1.4, y0=1.2, y1=3.8):
    """Window in a wall: emissive moonlit glass, sill, curtains. along = unit vector along the wall (room side view)."""
    a = np.array(along, float); nrm = np.array([-a[2], 0, a[0]])            # into the room
    c = np.array([cx, 0, cz]) - nrm * 0.12
    quad(c - a * w / 2 + np.array([0, y1, 0]), a * w, (0, -(y1 - y0), 0), 'window')
    # reveal (depth) and sill
    for s_ in (-1, 1):
        p = c + a * s_ * w / 2
        quad(p + np.array([0, y1, 0]), nrm * 0.12, (0, -(y1 - y0), 0), 'wood_dark', double=True)
    sill_lo = c - a * (w / 2 + 0.1) + nrm * 0.0
    bx = [sill_lo, sill_lo + a * (w + 0.2) + nrm * 0.28]
    mn, mx = np.minimum(*bx), np.maximum(*bx)
    box(mn[0], y0 - 0.08, mn[2], mx[0], y0, mx[2], 'marble', solid=False, occ=False)
    # top reveal
    quad(c - a * w / 2 + np.array([0, y1, 0]), a * w, nrm * 0.12, 'wood_dark', double=True)
    # curtains: two folded panels each side, pelmet above
    for s in (-1, 1):
        p0 = c + nrm * 0.18 + a * s * (w / 2 + 0.05)
        pa = p0 if s < 0 else p0 - a * 0.55
        quad(pa + np.array([0, y1 + 0.35, 0]) - a * (0.5 if s < 0 else 0), a * 0.55, (0, -(y1 + 0.35 - 0.05), 0), 'curtain', 1, 3)
    pel0 = c + nrm * 0.15 - a * (w / 2 + 0.6)
    pel1 = c + nrm * 0.35 + a * (w / 2 + 0.6)
    mn, mx = np.minimum(pel0, pel1), np.maximum(pel0, pel1)
    box(mn[0], y1 + 0.2, mn[2], mx[0], y1 + 0.55, mx[2], {'side': 'mahogany'}, solid=False, occ=False)
    LIGHTS.append((tuple(c + nrm * 0.8 + np.array([0, (y0 + y1) / 2 + 0.6, 0])), (0.38, 0.48, 0.78), 7.5, 0.0))

door_frame(0.0, Z1, 2.0, 3.6, facing=-1)                      # front entrance (south)
window(-5.0, Z1, (-1, 0, 0), w=2.0); window(5.0, Z1, (-1, 0, 0), w=2.0)     # south windows
window(X1, 4.0, (0, 0, 1), w=2.0)                      # east window

# ------------------------------------------------------------------ grand staircase to the north landing
LAND_Y = 2.6; NSTEP = 13; RISE = LAND_Y / NSTEP; RUN = 0.30
SZ0 = -5.0                                                    # landing front edge
for k in range(NSTEP):
    za = SZ0 + (NSTEP - k) * RUN; zb = za - RUN               # step k occupies z in [zb, za]
    top = (k + 1) * RISE
    box(-1.5, 0, zb, 1.5, top, za, {'top': 'tread', 'front': 'riser', 'side': 'wood_dark'}, skip=('bottom', 'back'),
        tiles={'top': (3, 1), 'front': (3, 1)})
# side stringers (sloped): drawn as a sloped quad each side
for sx in (-1, 1):
    x = 1.5 * sx + 0.0
    zs, ze = SZ0 + NSTEP * RUN, SZ0
    p0 = np.array([x + 0.08 * sx, 0.0, zs + 0.05]); p1 = np.array([x + 0.08 * sx, LAND_Y, ze])
    if sx > 0: quad(p0 + (0, 0.25, 0), p1 - p0, (0, -0.25, 0), 'wood_dark', 6, 1)
    else: quad(p1 + (0, 0.25, 0), p0 - p1, (0, -0.25, 0), 'wood_dark', 6, 1)
    # sloped baluster railing (alpha) + hand rail
    rh = 1.0
    if sx > 0: quad(p0 + (0, rh + 0.2, 0), p1 - p0, (0, -rh, 0), 'balusters', 6, 1, tile=True, double=True)
    else: quad(p1 + (0, rh + 0.2, 0), p0 - p1, (0, -rh, 0), 'balusters', 6, 1, tile=True, double=True)
    # newel post at the bottom + cap
    box(x - 0.1 + 0.08 * sx, 0, zs - 0.12, x + 0.1 + 0.08 * sx, 1.35, zs + 0.08, 'pillar')
    box(x - 0.13 + 0.08 * sx, 1.35, zs - 0.15, x + 0.13 + 0.08 * sx, 1.45, zs + 0.11, 'mahogany', solid=False)
    # rail collision per step so you can't walk off the stair sides
    for k in range(NSTEP):
        za = SZ0 + (NSTEP - k) * RUN; zb = za - RUN
        SOLIDS.append(((x + 0.03 * sx - 0.06, (k + 1) * RISE, zb), (x + 0.03 * sx + 0.06, (k + 1) * RISE + 1.2, za)))

# landing (gallery) across the north wall
box(X0, LAND_Y - 0.3, Z0, X1, LAND_Y, SZ0, {'top': 'floor', 'side': 'mahogany', 'bottom': 'ceiling'},
    tiles={'top': (18, 2), 'bottom': (9, 1)})
for px in (-8.85, -5.0, -1.75, 1.75, 5.0, 8.85):              # supporting columns
    if abs(px) < 2: continue
    box(px - 0.15, 0, SZ0 - 0.3, px + 0.15, LAND_Y - 0.3, SZ0, 'pillar')
# gallery balustrade (front edge), gap for the stairs
for (xa, xb) in ((X0, -1.5), (1.5, X1)):
    L = xb - xa
    quad((xa, LAND_Y + 1.0, SZ0 + 0.04), (L, 0, 0), (0, -1.0, 0), 'balusters', int(round(L)), 1, tile=True, double=True)
    box(xa, LAND_Y + 1.0, SZ0 - 0.02, xb, LAND_Y + 1.08, SZ0 + 0.1, 'mahogany', solid=False, occ=False)
    SOLIDS.append(((xa, LAND_Y, SZ0 - 0.05), (xb, LAND_Y + 1.3, SZ0 + 0.12)))
door_frame(0.0, Z0, 2.0, 2.4, facing=1, y0=LAND_Y)           # upper gallery door
candle(-1.4, LAND_Y + 1.7, Z0 + 0.12, light=((1.0, 0.62, 0.3), 3.2, 0.4))
candle(1.4, LAND_Y + 1.7, Z0 + 0.12, light=((1.0, 0.62, 0.3), 3.2, 0.4))
for sx in (-1.4, 1.4):
    box(sx - 0.08, LAND_Y + 1.55, Z0, sx + 0.08, LAND_Y + 1.7, Z0 + 0.16, 'brass', solid=False, occ=False)

def painting(cx, cy, cz, along, w, h, tex):
    a = np.array(along, float); nrm = np.array([-a[2], 0, a[0]])
    c = np.array([cx, cy, cz]) + nrm * 0.03
    fr = 0.1
    quad(c - a * (w / 2 + fr) + np.array([0, h / 2 + fr, 0]), a * (w + 2 * fr), (0, -(h + 2 * fr), 0), 'frame')
    quad(c + nrm * 0.03 - a * w / 2 + np.array([0, h / 2, 0]), a * w, (0, -h, 0), tex)
painting(-3.6, LAND_Y + 1.9, Z0, (1, 0, 0), 1.1, 1.4, 'portrait')
painting(3.6, LAND_Y + 1.9, Z0, (1, 0, 0), 1.1, 1.4, 'portrait2')

# ------------------------------------------------------------------ west: fireplace + sitting room
FX = X0
box(FX, 0, -1.5, FX + 0.75, 0.25, 1.5, 'stone')                         # plinth
box(FX, 0.25, -1.5, FX + 0.75, 1.45, -0.75, 'stone')                    # left jamb
box(FX, 0.25, 0.75, FX + 0.75, 1.45, 1.5, 'stone')                      # right jamb
box(FX, 1.15, -0.75, FX + 0.75, 1.45, 0.75, 'stone', solid=False)       # lintel
box(FX, 1.45, -1.7, FX + 0.9, 1.6, 1.7, {'side': 'mahogany', 'top': 'marble'})   # mantel shelf
box(FX, 1.6, -1.2, FX + 0.5, YC, 1.2, 'stone', skip=('top',))          # chimney breast
quad((FX + 0.25, 1.15, -0.75), (0, 0, 1.5), (0, -0.9, 0), 'firebox')   # fire back (emissive)
quad((FX + 0.25, 1.15, 0.75), (0.5, 0, 0), (0, -0.9, 0), 'firebox')    # fire sides
quad((FX + 0.75, 1.15, -0.75), (-0.5, 0, 0), (0, -0.9, 0), 'firebox')
box(FX + 0.75, 0, -1.7, FX + 1.35, 0.06, 1.7, 'marble', solid=False, occ=False)  # hearth
SOLIDS.append(((FX, 0.25, -0.75), (FX + 0.75, 1.15, 0.75)))                   # keep out of the fire
for lz in (-0.3, 0.2):                                                  # logs
    box(FX + 0.32, 0.25, lz - 0.32, FX + 0.5, 0.4, lz + 0.32, 'logs', solid=False, occ=False)
for fz in (-0.45, -0.1, 0.25, 0.5):
    flame(FX + 0.45, 0.32, fz, s=0.16 if abs(fz) < 0.3 else 0.11)
LIGHTS.append(((FX + 1.25, 0.75, 0.0), (1.55, 0.72, 0.28), 10.0, 1.0))
painting(FX + 0.5, 3.0, 0.0, (0, 0, -1), 1.6, 1.1, 'landscape')
for sz in (-1.1, 1.1):                                                  # mantel candlesticks
    box(FX + 0.55, 1.6, sz - 0.06, FX + 0.67, 1.66, sz + 0.06, 'brass', solid=False, occ=False)
    candle(FX + 0.61, 1.66, sz, h=0.24, light=((1.0, 0.62, 0.3), 2.6, 0.5))
# mantel clock (small)
box(FX + 0.55, 1.6, -0.22, FX + 0.8, 1.92, 0.22, {'right': 'clock_face', 'side': 'mahogany'}, solid=False, occ=False)

# rug
quad((-8.0, 0.012, -2.0), (4.4, 0, 0), (0, 0, 4.0), 'rug', 3, 3)

def armchair(x, z, yaw):
    xf = Xf((x, 0, z), yaw)                          # local: faces +z
    v = {'side': 'velvet'}
    box(-0.42, 0.0, -0.4, 0.42, 0.42, 0.4, {'side': 'velvet', 'top': 'velvet'}, xf=xf)       # seat base
    box(-0.42, 0.42, -0.45, 0.42, 1.2, -0.25, v, xf=xf)                                   # back
    for sx in (-1, 1):
        xa, xb = (0.3, 0.46) if sx > 0 else (-0.46, -0.3)
        box(xa, 0.42, -0.4, xb, 0.7, 0.42, v, xf=xf, solid=False)                           # arms
        box(xa - 0.02, 1.0, -0.45, xb + 0.02, 1.25, -0.2, v, xf=xf, solid=False)            # wings
    for lx, lz in ((-0.36, 0.34), (0.36, 0.34), (-0.36, -0.34), (0.36, -0.34)):
        box(lx - 0.04, -0.0, lz - 0.04, lx + 0.04, 0.08, lz + 0.04, 'mahogany', xf=xf, solid=False, occ=False)

def sofa(x, z, yaw):
    xf = Xf((x, 0, z), yaw)
    box(-1.1, 0.0, -0.45, 1.1, 0.45, 0.45, 'leather', xf=xf)
    box(-1.1, 0.45, -0.5, 1.1, 0.95, -0.28, 'leather', xf=xf)
    for sx in (-1, 1):
        xa, xb = (1.0, 1.25) if sx > 0 else (-1.25, -1.0)
        box(xa, 0.0, -0.5, xb, 0.8, 0.5, 'leather', xf=xf)

armchair(-6.6, 2.2, math.radians(-150))
armchair(-6.6, -2.2, math.radians(-30))
sofa(-4.0, 0.0, math.radians(-90))
# coffee table + candle
xf = Xf((-5.7, 0, 0))
box(-0.5, 0.36, -0.75, 0.5, 0.44, 0.75, {'top': 'table_top', 'side': 'mahogany'}, xf=xf)
for lx, lz in ((-0.42, 0.67), (0.42, 0.67), (-0.42, -0.67), (0.42, -0.67)):
    box(lx - 0.04, 0, lz - 0.04, lx + 0.04, 0.36, lz + 0.04, 'mahogany', xf=xf, solid=False, occ=False)
prism(-5.7, 0.25, 0.44, 0.7, 0.09, 6, 'vase', cap='vase')
candle(-5.7, 0.44, -0.3, light=((1.0, 0.62, 0.3), 2.6, 0.5))

# bookshelves on the west wall, either side of the fireplace (deeper than tall stretch, tiled books)
for bz in (-4.3, 4.3):
    x0, x1 = X0, X0 + 0.45; z0, z1 = bz - 0.9, bz + 0.9
    box(x0, 0, z0, x1, 2.7, z1, {'right': None, 'side': 'wood_dark'}, skip=('right',))
    quad((x1, 2.6, z1), (0, 0, -1.8), (0, -2.5, 0), 'books', 1, 4, tile=True)
    box(x1 - 0.02, 2.6, z0 - 0.05, x1 + 0.06, 2.8, z1 + 0.05, 'mahogany', solid=False, occ=False)   # cornice
    candle(x1 - 0.12, 2.8, bz, light=None)
# cobwebs in the corners
quad((X0 + 0.01, YC - 0.36, Z1 - 1.2), (0, 0, 1.19), (0, -1.0, 0), 'cobweb', double=True, flip_u=True)
quad((X1 - 1.2, YC - 0.36, Z1 - 0.01), (1.19, 0, 0), (0, -1.0, 0), 'cobweb', double=True)
quad((X0 + 0.01, LAND_Y - 0.31, SZ0 - 1.2), (0, 0, 1.19), (0, -0.9, 0), 'cobweb', double=True)
quad((X1 - 0.01, 2.2, 6.2), (0, 0, 0.8), (0, -0.9, 0), 'cobweb', double=True, flip_u=True)

# ------------------------------------------------------------------ east: dining
TX, TZ = 5.2, 0.6
xf = Xf((TX, 0, TZ))
box(-0.6, 0.72, -1.7, 0.6, 0.8, 1.7, {'top': 'table_top', 'side': 'mahogany'}, xf=xf)
for lx, lz in ((-0.5, 1.6), (0.5, 1.6), (-0.5, -1.6), (0.5, -1.6)):
    box(lx - 0.06, 0, lz - 0.06, lx + 0.06, 0.72, lz + 0.06, 'mahogany', xf=xf, solid=False)
SOLIDS.append(((TX - 0.6, 0, TZ - 1.7), (TX + 0.6, 0.8, TZ + 1.7)))
# candelabra
box(TX - 0.06, 0.8, TZ - 0.06, TX + 0.06, 1.15, TZ + 0.06, 'brass', solid=False, occ=False)
box(TX - 0.05, 1.12, TZ - 0.35, TX + 0.05, 1.17, TZ + 0.35, 'brass', solid=False, occ=False)
for dz in (-0.33, 0, 0.33):
    candle(TX, 1.17 + (0.05 if dz == 0 else 0), TZ + dz)
LIGHTS.append(((TX, 1.55, TZ), (1.1, 0.68, 0.32), 4.5, 0.35))

def chair(x, z, yaw):
    xf = Xf((x, 0, z), yaw)
    box(-0.24, 0.42, -0.22, 0.24, 0.5, 0.24, {'top': 'velvet', 'side': 'mahogany'}, xf=xf)
    for lx, lz in ((-0.2, 0.2), (0.2, 0.2), (-0.2, -0.18), (0.2, -0.18)):
        box(lx - 0.03, 0, lz - 0.03, lx + 0.03, 0.42, lz + 0.03, 'mahogany', xf=xf, solid=False, occ=False)
    box(-0.24, 0.5, -0.24, 0.24, 1.15, -0.18, {'front': 'chair_back', 'side': 'mahogany'}, xf=xf)

for dz in (-1.1, 0.0, 1.1):
    chair(TX - 0.85, TZ + dz, math.radians(90))
    chair(TX + 0.85, TZ + dz, math.radians(-90))
chair(TX, TZ + 2.05, math.radians(180))

# sideboard on the east wall + painting + vases
xf = Xf((X1 - 0.28, 0, -1.6), math.radians(-90))
box(-0.9, 0.05, -0.27, 0.9, 0.95, 0.27, {'front': 'sideboard', 'top': 'marble', 'side': 'mahogany'}, xf=xf)
prism(X1 - 0.3, -2.2, 0.95, 1.35, 0.1, 6, 'vase', cap='vase')
prism(X1 - 0.3, -1.0, 0.95, 1.2, 0.08, 6, 'vase', cap='vase')
candle(X1 - 0.3, 0.95, -1.6, h=0.22, light=((1.0, 0.62, 0.3), 2.8, 0.5))
painting(X1, 2.6, -1.6, (0, 0, 1), 1.2, 1.5, 'portrait')

# ------------------------------------------------------------------ under the gallery: grandfather clock, piano
xf = Xf((3.3, 0, Z0 + 0.25))
box(-0.3, 0, -0.22, 0.3, 0.5, 0.22, 'mahogany', xf=xf)
box(-0.25, 0.5, -0.18, 0.25, 1.55, 0.18, {'front': 'clock_body', 'side': 'mahogany'}, xf=xf)
box(-0.3, 1.55, -0.22, 0.3, 2.1, 0.22, {'front': 'clock_face', 'side': 'mahogany'}, xf=xf)
box(-0.33, 2.1, -0.24, 0.33, 2.2, 0.24, 'mahogany', xf=xf, solid=False)

xf = Xf((-3.4, 0, Z0 + 0.32))
box(-0.75, 0.0, -0.3, 0.75, 1.3, 0.3, {'front': 'piano_front', 'side': 'wood_dark', 'top': 'wood_dark'}, xf=xf)
box(-0.72, 0.72, 0.3, 0.72, 0.78, 0.55, {'top': 'piano_keys', 'side': 'wood_dark'}, xf=xf)
box(-0.3, 0.0, 0.85, 0.3, 0.48, 1.15, {'top': 'velvet', 'side': 'wood_dark'}, xf=xf)   # stool
candle(-0.55, 1.3, -0.05, xf=xf, light=((1.0, 0.62, 0.3), 2.6, 0.5))
candle(0.55, 1.3, -0.05, xf=xf)

# side tables with vases by the front door + wall sconces
for sx in (-1, 1):
    x = sx * 2.4
    box(x - 0.3, 0.75, Z1 - 0.55, x + 0.3, 0.82, Z1 - 0.1, {'top': 'marble', 'side': 'mahogany'})
    box(x - 0.05, 0, Z1 - 0.38, x + 0.05, 0.75, Z1 - 0.28, 'mahogany', solid=False, occ=False)
    prism(x, Z1 - 0.33, 0.82, 1.25, 0.1, 6, 'vase', cap='vase')
    box(sx * 1.55 - 0.08, 2.3, Z1 - 0.16, sx * 1.55 + 0.08, 2.45, Z1, 'brass', solid=False, occ=False)
    candle(sx * 1.55, 2.45, Z1 - 0.08, light=((1.0, 0.62, 0.3), 3.4, 0.4))

# runner from the door to the stairs
quad((-0.7, 0.014, SZ0 + NSTEP * RUN + 0.1), (1.4, 0, 0), (0, 0, Z1 - (SZ0 + NSTEP * RUN + 0.1)), 'runner', 1, 7, tile=True)

# ------------------------------------------------------------------ chandelier (centre)
CY = 3.9; CZ = 1.6
box(-0.03, CY + 0.1, CZ - 0.03, 0.03, YC, CZ + 0.03, 'brass', solid=False, occ=False)          # chain
prism(0, CZ, CY - 0.15, CY + 0.15, 0.12, 6, 'brass', cap='brass')
for k in range(8):
    a = k * math.pi / 4
    x, z = math.sin(a) * 0.75, CZ + math.cos(a) * 0.75
    box(min(0, x) - 0.02, CY - 0.02, min(CZ, z) - 0.02, max(0, x) + 0.02, CY + 0.02, max(CZ, z) + 0.02, 'brass', solid=False, occ=False)
    candle(x, CY, z)
LIGHTS.append(((0.0, CY - 0.3, CZ), (1.15, 0.78, 0.42), 9.0, 0.15))

SPAWN = (0.0, 0.0, 3.4, math.pi)    # by the front door facing into the hall (-z)

# ------------------------------------------------------------------ bake vertex lighting
P = np.array([v[0] for v in VERTS], np.float32)
N = np.array([v[1] for v in VERTS], np.float32)
EM = np.array([v[3] for v in VERTS])
occ = np.array([list(a) + list(b) for a, b in OCC], np.float32)
amb = np.array([0.24, 0.21, 0.30], np.float32)
col = np.tile(amb, (len(P), 1)) + np.clip(N[:, 1:2], 0, 1) * np.array([0.04, 0.04, 0.06])
fire = np.zeros(len(P), np.float32)

def shadowed(org, dst):
    """Segment org->dst (N,3) vs occluder boxes; returns visibility in [0.2,1]."""
    d = dst - org
    vis = np.ones(len(org), np.float32)
    inv = 1.0 / np.where(np.abs(d) < 1e-9, 1e-9, d)
    for b in occ:
        t1 = (b[None, :3] - org) * inv; t2 = (b[None, 3:] - org) * inv
        tmin = np.max(np.minimum(t1, t2), axis=1); tmax = np.min(np.maximum(t1, t2), axis=1)
        hit = (tmax >= np.maximum(tmin, 0.0)) & (tmin < 0.98) & (tmax > 0.02)
        vis = np.where(hit, 0.22, vis)
    return vis

for (lp, lc, lr, fl) in LIGHTS:
    lp = np.array(lp, np.float32); lc = np.array(lc, np.float32)
    d = lp[None] - P; dist = np.linalg.norm(d, axis=1) + 1e-6
    ndl = np.clip((N * d).sum(1) / dist, 0, 1) * 0.85 + 0.15 * (dist < lr)
    att = np.clip(1 - dist / lr, 0, 1) ** 2
    m = att > 0.003
    vis = np.ones(len(P), np.float32)
    vis[m] = shadowed(P[m] + N[m] * 0.04, np.repeat(lp[None], m.sum(), 0))
    contrib = (ndl * att * vis)[:, None] * lc[None]
    col += contrib
    fire += contrib.sum(1) * fl

tot = col.sum(1) + 1e-6
flick = np.clip(fire / tot, 0, 1)
col = np.clip(col, 0, 1.7)
col[EM] = 1.0; flick[EM] = 0.0

UV = np.array([v[2] for v in VERTS], np.float32)
print('triangles:', len(VERTS) // 3, ' solids:', len(SOLIDS), ' occluders:', len(OCC), ' lights:', len(LIGHTS))

with open('mansion.bin', 'wb') as f:
    f.write(b'MNS1'); f.write(struct.pack('<i', len(VERTS)))
    data = np.concatenate([P, UV, col, flick[:, None]], axis=1).astype('<f4')
    f.write(data.tobytes())
    f.write(struct.pack('<i', len(SOLIDS)))
    for a, b in SOLIDS: f.write(struct.pack('<6f', *a, *b))
    f.write(struct.pack('<i', len(LIGHTS)))
    for (lp, lc, lr, fl) in LIGHTS: f.write(struct.pack('<8f', *lp, *lc, lr, fl))
    f.write(struct.pack('<4f', *SPAWN))
json.dump({'pos': P.round(3).flatten().tolist(), 'uv': UV.round(5).flatten().tolist(),
           'col': np.concatenate([col, flick[:, None]], 1).round(3).flatten().tolist(),
           'spawn': SPAWN, 'lights': [list(l[0]) + list(l[1]) + [l[2], l[3]] for l in LIGHTS],
           'solids': [list(a) + list(b) for a, b in SOLIDS]}, open('mansion.json', 'w'))
