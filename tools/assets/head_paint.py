# --- box-modelled head textures. Front/side/cranium/under, 32x32 each.
# Front face: lattice row j=0 (cheekbone line) sits at v=0.5 -> pixel row ~15.5
R["head_front"] = (0, 0, 32, 32)
R["head_side"] = (32, 0, 32, 32)
R["head_cran"] = (64, 0, 32, 32)
R["head_under"] = (64, 96, 32, 32)

x0, y0 = R["head_front"][:2]
grad_fill(x0, y0, 32, 32, ["bone3", "bone2", "bone2", "bone1"], noise=0.15)
speckle(x0, y0, 32, 32, "bone1", 0.05)
# eye sockets: centred at px 10 / 21, rows 7-15
for ex in (10, 21):
    for j in range(5, 17):
        for i in range(-6, 7):
            d = (i / 5.0) ** 2 + ((j - 10.5) / 5.0) ** 2
            if d < 1.0: put(x0 + ex + i, y0 + j, "dark")
            elif d < 1.5: put(x0 + ex + i, y0 + j, "bone1")
    put(x0 + ex, y0 + 11, "red2"); put(x0 + ex, y0 + 12, "red1")   # glowing pupils
for i in range(4, 28): put(x0 + i, y0 + 4, "bone3")              # brow ridge
# nose cavity (rows 15-20)
for j in range(15, 21):
    w = 1 + (j - 15) // 2
    for i in range(-w, w): put(x0 + 16 + i, y0 + j, "dark")
put(x0 + 15, y0 + 15, "bone1"); put(x0 + 16, y0 + 15, "bone1")
# hollow cheeks under the cheekbones (outer lower quads)
for j in range(18, 24):
    for i in list(range(0, 5)) + list(range(27, 32)):
        if (i + j) % 2 == 0: put(x0 + i, y0 + j, "bone0")
        else: put(x0 + i, y0 + j, "bone1")
# teeth: upper rows 21-23, bite line 24, lower 25-26 (across px 7..24)
for i in range(7, 25):
    gap = (i % 3 == 0)
    for j in range(21, 24): put(x0 + i, y0 + j, "dark" if gap else ("bone3" if j < 23 else "bone2"))
    put(x0 + i, y0 + 24, "dark")
    for j in range(25, 27): put(x0 + i, y0 + j, "dark" if gap else ("bone2" if j == 25 else "bone1"))
for i in range(7, 25): put(x0 + i, y0 + 20, "bone1")             # gum line
# chin highlight
for i in range(12, 20): put(x0 + i, y0 + 29, "bone3")

# side: u=0 back, u=1 front ; v=0 top (crown), v=1 jaw bottom
x0, y0 = R["head_side"][:2]
grad_fill(x0, y0, 32, 32, ["bone3", "bone2", "bone2", "bone1"], noise=0.15)
speckle(x0, y0, 32, 32, "bone1", 0.05)
for j in range(7, 15):                                             # temple hollow near the front
    for i in range(21, 30):
        if ((i - 25.5) / 4.5) ** 2 + ((j - 11) / 4) ** 2 < 1: put(x0 + i, y0 + j, "bone1")
for i in range(15, 32):                                            # zygomatic arch
    put(x0 + i, y0 + 15, "bone3"); put(x0 + i, y0 + 16, "bone2")
for i in range(15, 30):                                            # notch under the arch
    put(x0 + i, y0 + 17, "bone1"); put(x0 + i, y0 + 18, "bone0" if 20 < i < 26 else "bone1")
fill(x0 + 11, y0 + 15, 3, 3, "dark"); put(x0 + 12, y0 + 14, "bone0")   # ear hole
for j in range(18, 32):                                            # back edge of the jaw (ramus)
    put(x0 + 10 + (j - 18) // 4, y0 + j, "bone0")
for j in range(21, 27):                                            # side of teeth at the front edge
    for i in range(28, 32):
        put(x0 + i, y0 + j, "dark" if (i + j) % 3 == 0 or j == 24 else "bone3")
for i in range(12, 32): put(x0 + i, y0 + 30, "bone1")              # jaw line

# cranium (top + back)
x0, y0 = R["head_cran"][:2]
grad_fill(x0, y0, 32, 32, ["bone3", "bone2", "bone2", "bone1"], noise=0.2)
speckle(x0, y0, 32, 32, "bone1", 0.06)
for j in range(32):                                                # sagittal suture
    put(x0 + 16 + int(1.5 * math.sin(j * 1.1)), y0 + j, "bone0")
for i in range(32):                                                # lambdoid suture
    put(x0 + i, y0 + 20 + int(1.2 * math.sin(i * 1.3)) - abs(i - 16) // 4, "bone0")

x0, y0 = R["head_under"][:2]
grad_fill(x0, y0, 32, 32, ["bone1", "bone0"], noise=0.2)
