# Déplace les tableaux de primes (gameobject guid 9905000+) à côté de la boîte aux lettres la plus proche de l'auberge.
# Repli : lanterne ou éclairage extérieur ; sinon le tableau reste où il est.
import math, subprocess
def q(sql):
    r = subprocess.run(['mysql', '--default-character-set=utf8mb4', '-N', '-B', 'classicmangos', '-e', sql], capture_output=True, text=True, check=True)
    return [l.split('\t') for l in r.stdout.splitlines()]
inns = [(int(g), int(m), float(x), float(y), float(z)) for g, m, x, y, z in q(
    "select c.guid, c.map, c.position_x, c.position_y, c.position_z from creature c join creature_template t on t.Entry=c.id "
    "where (t.NpcFlags & 128) and c.map in (0,1)")]
event = set(int(r[0]) for r in q("select guid from game_event_gameobject"))
anchors = {}
for kind, cond in (('boîte aux lettres', "t.type=19"), ('lanterne', "t.name in ('Lantern','Standing, Exterior, Medium - MFF','Standing, Medium, Exterior','Brazier','Dwarven Brazier')")):
    anchors[kind] = [(int(g), int(m), float(x), float(y), float(z), float(o)) for g, m, x, y, z, o in q(
        "select g.guid, g.map, g.position_x, g.position_y, g.position_z, g.orientation from gameobject g join gameobject_template t on t.entry=g.id "
        "where g.map in (0,1) and %s" % cond) if int(g) not in event]
boards = [(int(g), int(m), float(x), float(y), float(z)) for g, m, x, y, z in q(
    "select guid, map, position_x, position_y, position_z from gameobject where guid between 9905000 and 9905999")]
L = ["-- Tableaux de primes : à côté de la boîte aux lettres de l'auberge (généré par gen_tableaux.py)",
     "-- toujours cliquables (sans l'indicateur « interaction sous condition » hérité du modèle Wanted Board)",
     "UPDATE gameobject_template SET flags=0, faction=35 WHERE entry BETWEEN 990500 AND 990599 AND type=2;"]
stats = {}
RESTE = []
used = {}
for g, m, x, y, z in boards:
    inn = min((i for i in inns if i[1] == m), key=lambda i: (i[2] - x) ** 2 + (i[3] - y) ** 2)
    done = False
    for kind in ('boîte aux lettres', 'lanterne'):
        best = None
        for a in anchors[kind]:
            if a[1] != m or used.get(a[0], 0) >= 2 or abs(a[4] - inn[4]) > 8:
                continue
            dd = math.hypot(a[2] - inn[2], a[3] - inn[3])
            if dd <= (65 if kind == 'boîte aux lettres' else 30) and (best is None or dd < best[0]):
                best = (dd, a)
        if best:
            a = best[1]
            side = 1 if used.get(a[0], 0) == 0 else -1
            used[a[0]] = used.get(a[0], 0) + 1
            # 3,5 m à côté de l'objet (un tableau de chaque côté au plus), perpendiculairement à la direction de l'auberge
            ang = math.atan2(inn[3] - a[3], inn[2] - a[2])
            bx, by = a[2] + 3.5 * math.cos(ang + side * math.pi / 2), a[3] + 3.5 * math.sin(ang + side * math.pi / 2)
            o = (ang + math.pi) % (2 * math.pi)     # affiche tournée vers la rue (dos à l'auberge)
            L.append("UPDATE gameobject SET position_x=%.2f, position_y=%.2f, position_z=%.2f, orientation=%.3f, rotation0=0, rotation1=0, "
                     "rotation2=%.5f, rotation3=%.5f WHERE guid=%d;" % (bx, by, a[4], o, math.sin(o / 2), math.cos(o / 2), g))
            stats[kind] = stats.get(kind, 0) + 1
            done = True
            break
    if not done:
        stats['inchangé'] = stats.get('inchangé', 0) + 1
        RESTE.append(q("select t.Name from creature c join creature_template t on t.Entry=c.id where c.guid=%d" % inn[0])[0][0])
open('/home/claude/wow/monde/tableaux.sql', 'w', encoding='utf-8').write('\n'.join(L) + "\nSELECT 'Tableaux OK' AS resultat;\n")
print(len(boards), stats, sorted(set(RESTE)))
