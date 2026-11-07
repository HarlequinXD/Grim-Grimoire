# --- head: baked light from upper-left-front, brim shadow over the top rows
def brim_shadow(v): return -0.30 if v < 0.10 else -0.14 if v < 0.18 else 0
light_map(R["head_front"], lambda u, v: face_light(u, v) + brim_shadow(v) - 0.14 * max(0, v - 0.6))
x0, y0 = R["head_front"][:2]
for ex in (10, 21):                       # socket rims: lit lower-right, shadowed upper-left (light from top-left)
    for j in range(7, 15):
        shade_px(x0 + ex + 5, y0 + j, 1.2); shade_px(x0 + ex - 5, y0 + j, 0.68)
for i in range(3):                        # cheekbone highlights + cast shadow below
    shade_px(x0 + 3 + i, y0 + 16, 1.2); shade_px(x0 + 26 + i, y0 + 16, 1.1)
    shade_px(x0 + 3 + i, y0 + 18, 0.6); shade_px(x0 + 26 + i, y0 + 18, 0.6)
for i in range(8, 24): shade_px(x0 + i, y0 + 27, 0.62)   # shadow under lower teeth
light_map(R["head_side"], lambda u, v: 0.78 + 0.22 * u + brim_shadow(v) - 0.2 * max(0, v - 0.55) + edge_ao(u, v, 0.1, 0.15))
light_map(R["head_cran"], lambda u, v: 0.75 - 0.2 * v + edge_ao(u, v, 0.15, 0.2))   # mostly under the hat
light_map(R["head_under"], lambda u, v: 0.7)
