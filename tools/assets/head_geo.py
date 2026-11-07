# ---- box-modelled head: one cube, subdivided once (3x3x3 lattice, 26 verts, 24 quads),
# lattice verts pushed into a skull with a tapered jaw. Single mesh, no separate jaw.
def head_pos(i, j, k):
    Y = {-1: 1.475, 0: 1.625, 1: 1.80}[j]
    hw = {-1: 0.080, 0: 0.145, 1: 0.135}[j]
    front = {-1: 0.125, 0: 0.150, 1: 0.125}[j]
    back = {-1: -0.065, 0: -0.160, 1: -0.150}[j]
    x = i * hw
    if k == 1:
        z = front - (0.04 if (i and j == -1) else 0.035 if i else 0)
    elif k == -1:
        z = back + (0.03 if i else 0)
    else:
        z = (front + back) / 2 + (0.035 if j == -1 else 0)
        if i: x *= 1.06                          # bulge the sides
    if j == 1:                                    # dome the cranium
        if i and k: x *= 0.82; Y -= 0.025; z *= 0.9
        elif i or k: Y += 0.015
        else: Y += 0.035
    if j == -1:
        if k == -1: Y = 1.535; x = i * 0.112      # jaw angle: kicks up and out at the hinge
        elif k == 0: Y = 1.49; x = i * 0.100
        elif i == 0: Y = 1.462; z = 0.14         # chin forward and down
    if (i, j, k) == (0, 0, 1): z += 0.018         # nose bridge
    if (i, j, k) == (0, 1, 1): z += 0.01          # forehead
    return (x, Y + 0.0, z + 0.01)

HEAD_FACES = {  # (a,b) in -1..1 -> lattice (i,j,k); uv = ((a+1)/2, (1-b)/2)
    "head_front": lambda a, b: (a, b, 1),
    "head_cran_back": lambda a, b: (-a, b, -1),
    "head_side_r": lambda a, b: (1, b, a),
    "head_side_l": lambda a, b: (-1, b, a),
    "head_cran_top": lambda a, b: (a, 1, -b),
    "head_under": lambda a, b: (a, -1, b),
}
RECT_OF = {"head_front": "head_front", "head_cran_back": "head_cran", "head_side_r": "head_side",
           "head_side_l": "head_side", "head_cran_top": "head_cran", "head_under": "head_under"}
HC = np.array([0, 1.64, 0.0])
for fname, lat in HEAD_FACES.items():
    rect = R[RECT_OF[fname]]
    for a in (-1, 0):
        for b in (-1, 0):
            cs = [(a, b), (a + 1, b), (a + 1, b + 1), (a, b + 1)]
            P = [head_pos(*lat(*c)) for c in cs]
            T = [uv_of(rect, (c[0] + 1) / 2, (1 - c[1]) / 2) for c in cs]
            n = norm(np.cross(np.subtract(P[1], P[0]), np.subtract(P[3], P[0])))
            out = np.mean(P, axis=0) - HC
            if np.dot(n, out) < 0:                # keep winding outward
                P = P[::-1]; T = T[::-1]; n = -n
            n = tuple(n)
            tri((P[0], P[1], P[2]), (n, n, n), (T[0], T[1], T[2]))
            tri((P[0], P[2], P[3]), (n, n, n), (T[0], T[2], T[3]))
