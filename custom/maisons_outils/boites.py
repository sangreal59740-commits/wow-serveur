# Boîte intérieure de chaque maison retenue (groupes intérieurs des modèles qui contiennent le point repéré en jeu)
import sys, json, math, csv
sys.path.insert(0, '/tmp/claude-0/maisons')
import vmo
MID = 32 * 533.3333333
S = json.load(open('/tmp/claude-0/maisons/spawns.json'))
def rotm(rx, ry, rz):
    a, b, c = map(math.radians, (ry, rx, rz))
    Rz = [[math.cos(a), -math.sin(a), 0], [math.sin(a), math.cos(a), 0], [0, 0, 1]]
    Ry = [[math.cos(b), 0, math.sin(b)], [0, 1, 0], [-math.sin(b), 0, math.cos(b)]]
    Rx = [[1, 0, 0], [0, math.cos(c), -math.sin(c)], [0, math.sin(c), math.cos(c)]]
    mm = lambda A, B: [[sum(A[i][k] * B[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
    return mm(Rz, mm(Ry, Rx))
cache = {}
def boxes_near(m, x, y, r=250):
    out = []
    for s in S:
        if s['m'] != m or s['flags'] & 1:
            continue
        wx = MID - s['pos'][0]; wy = MID - s['pos'][1]
        if (wx - x) ** 2 + (wy - y) ** 2 > (r + 400) ** 2:
            continue
        if s['name'] not in cache:
            try: cache[s['name']] = vmo.load(s['name'])
            except Exception: cache[s['name']] = []
        R = rotm(*s['rot']); sc = s['sc']
        for g in cache[s['name']]:
            fl = g['fl']
            if not (fl & 0x2000) or (fl & 0x40) or (fl & 0x8):
                continue
            lo = g['b'][:3]; hi = g['b'][3:]
            pts = []
            for cx in (lo[0], hi[0]):
                for cy in (lo[1], hi[1]):
                    for cz in (lo[2], hi[2]):
                        v = [cx * sc, cy * sc, cz * sc]
                        w = [sum(R[i][k] * v[k] for k in range(3)) + s['pos'][i] for i in range(3)]
                        pts.append((MID - w[0], MID - w[1], w[2]))
            xs = [p[0] for p in pts]; ys = [p[1] for p in pts]; zs = [p[2] for p in pts]
            if max(xs) - min(xs) > 60 or max(ys) - min(ys) > 60:
                continue
            out.append((min(xs), min(ys), min(zs), max(xs), max(ys), max(zs)))
    return out
def boite(m, x, y, z):
    bs = [b for b in boxes_near(m, x, y) if b[0] - 1 <= x <= b[3] + 1 and b[1] - 1 <= y <= b[4] + 1 and b[2] - 3 <= z <= b[5] + 1]
    if not bs:
        return (x - 7, y - 7, z - 2, x + 7, y + 7, z + 8), False
    b = (min(b[0] for b in bs), min(b[1] for b in bs), min(b[2] for b in bs), max(b[3] for b in bs), max(b[4] for b in bs), max(b[5] for b in bs))
    # bornée à 20 m autour du point (plusieurs maisons peuvent partager un même bloc)
    b = (max(b[0], x - 20), max(b[1], y - 20), max(b[2], z - 4), min(b[3], x + 20), min(b[4], y + 20), min(b[5], z + 15))
    return b, True
