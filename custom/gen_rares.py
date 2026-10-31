# Boss élites rares de donjon : un par donjon, présent à 100 %, en patrouille avec 2 monstres du donjon.
# Stats x1,25 du boss final, sorts du boss final (liste de sorts), butin : or, 1 épique du monde au niveau, monture 10 %.
# Sortie : rares.sql (base world)
import sys, json, math, subprocess
from collections import defaultdict
sys.path.insert(0, '/home/claude/wow/fr')

OUT = '/home/claude/wow/donjons/'

def q(sql):
    r = subprocess.run(['mysql', '-N', '-B', 'classicmangos', '-e', sql], capture_output=True, text=True, check=True)
    return [l.split('\t') for l in r.stdout.splitlines()]

def esc(s):
    return s.replace('\\', '\\\\').replace("'", "\\'")

# idx, map, boss final, entrée (x, y, z), nom FR, apparence (entrée modèle), échelle, escorte (entrée), sorts
#   sort = (id, cible, flags, initial min-max, répétition min-max)   cible : 1 actuelle, 2 soi, 100 joueur au hasard,
#          101 joueur au hasard hors tank, 103 zone autour du boss ; flags 2 = sort principal à distance
DONJONS = [
    (0, 389, 11520, (0.8, -8.2, -15.5), "Garde-flamme Zor'kath", 11323, 1.4, 11322,
     [(18072, 1, 0, 6000, 10000, 8000, 14000), (11970, 103, 0, 8000, 12000, 12000, 18000)]),
    (1, 36, 639, (-14.6, -385.5, 62.5), "Capitaine Grisebarbe", 657, 1.35, 657,
     [(3391, 2, 0, 3000, 6000, 8000, 14000), (8260, 100, 0, 5000, 9000, 15000, 22000)]),
    (2, 43, 3654, (-158.4, 131.6, -74.3), "Krazzak le Déviant", 3636, 1.7, 3840,
     [(7967, 100, 0, 8000, 14000, 25000, 35000), (7399, 103, 0, 15000, 20000, 20000, 26000),
      (8150, 103, 0, 4000, 9000, 10000, 15000)]),
    (3, 33, 4275, (-228.2, 2111.4, 76.9), "Lune-Sanglante", 3859, 1.5, 3853,
     [(7588, 1, 2, 0, 0, 3000, 5000), (7621, 100, 0, 10000, 15000, 20000, 30000),
      (7803, 103, 0, 6000, 10000, 12000, 18000)]),
    (4, 34, 1716, (49.0, 0.5, -16.4), "Le Geôlier déchu", 68, 1.2, 1706,
     [(7964, 1, 0, 8000, 11000, 15000, 25000), (9128, 2, 0, 1000, 2000, 30000, 30000),
      (15496, 1, 0, 4000, 7000, 7000, 11000)]),
    (5, 48, 4829, (-150.2, 106.6, -39.8), "Matriarche Ssith'ra", 4805, 1.5, 4807,
     [(3815, 103, 0, 5000, 15000, 20000, 28000), (3490, 2, 0, 10000, 20000, 25000, 30000),
      (9613, 1, 2, 0, 0, 3000, 5000)]),
    (6, 90, 7800, (-329.1, -3.2, -152.9), "Prototype XT-9", 6229, 1.4, 6222,
     [(10101, 1, 0, 6000, 10000, 10000, 15000), (11130, 103, 0, 12000, 16000, 16000, 22000)]),
    (7, 47, 4421, (1942.3, 1544.2, 83.3), "Seigneur de guerre Grogne-Épine", 4436, 1.7, 4436,
     [(8292, 1, 2, 0, 0, 3000, 6000), (8361, 2, 0, 5000, 14000, 15000, 30000),
      (6077, 2, 0, 12000, 18000, 20000, 25000)]),
    (8, 189, 4543, (1687.3, 1050.1, 18.7), "Le Croisé sans repos", 6488, 1.4, 6426,
     [(8814, 100, 0, 10000, 20000, 20000, 35000), (12470, 103, 0, 5000, 15000, 10000, 20000),
      (8053, 121, 0, 4000, 12000, 8000, 20000), (9613, 1, 2, 0, 0, 3000, 5000)]),
    (9, 189, 6487, (253.7, -206.6, 18.7), "Archiviste Valmont", 4300, 1.3, 4296,
     [(13323, 101, 0, 8000, 12000, 20000, 25000), (8988, 103, 0, 10000, 15000, 18000, 24000),
      (9433, 103, 0, 4000, 8000, 7000, 11000), (9613, 1, 2, 0, 0, 3000, 5000)]),
    (10, 189, 3975, (1608.1, -318.9, 18.7), "Maître d'armes Darnell", 4302, 1.6, 4301,
     [(15496, 1, 0, 4000, 6000, 6000, 10000), (8989, 2, 0, 10000, 14000, 16000, 22000),
      (8260, 100, 0, 6000, 10000, 15000, 20000)]),
    (11, 189, 3977, (853.2, 1319.2, 18.7), "Grand Inquisiteur Morvane", 3976, 1.25, 4302,
     [(9481, 1, 2, 0, 0, 3500, 5500), (12039, 2, 0, 15000, 20000, 25000, 30000),
      (22187, 2, 0, 8000, 12000, 30000, 35000), (9256, 103, 0, 20000, 25000, 30000, 40000)]),
    (12, 129, 7358, (2593.7, 1111.2, 51.0), "Seigneur-squelette Ossegivre", 7329, 1.7, 7343,
     [(15530, 1, 2, 0, 0, 3000, 4500), (15531, 103, 0, 10000, 15000, 15000, 20000),
      (13009, 1, 0, 8000, 8000, 12000, 15000)]),
]

RARE_BASE = 990400            # entrée du boss rare = 990400 + index
LOOT_MODE = {0: 0, 40: 20, 50: 40}   # butin : entrée + décalage selon le mode
GUID_BASE = 9902000           # boss rare : + index*3, escortes + 1 et + 2
REF_EPIC, REF_MOUNT = 993400, 993399
SUBLIME_BASE = 995000

TPL = {e: dict(zip(['name', 'minl', 'maxl', 'hp', 'dmg', 'cls', 'disp'], r)) for e, *r in
       q("select Entry, Name, MinLevel, MaxLevel, HealthMultiplier, DamageMultiplier, UnitClass, DisplayId1 from creature_template")}
TPL = {int(k): v for k, v in TPL.items()}

def dist(a, b):
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))

# ---------------------------------------------------------------- positions
spawns = defaultdict(list)
for g, i, m, x, y, z in q("select c.guid, c.id, c.map, c.position_x, c.position_y, c.position_z from creature c "
                          "where c.map in (389,36,43,33,34,48,90,47,189,129) and c.spawnMask>0"):
    spawns[int(m)].append((int(g), int(i), float(x), float(y), float(z)))
bosspos = {}
for d in DONJONS:
    ref = {3654: 3679}.get(d[2], d[2])     # Mutanus apparaît par script : position de Naralex
    p = [s for s in spawns[d[1]] if s[1] == ref]
    assert p, d[4]
    bosspos[d[0]] = p[0][2:]
SM = [d for d in DONJONS if d[1] == 189]

def wing_of(d, pos):
    """Monastère : aile la plus proche (entrée ou boss)."""
    best = min(SM, key=lambda w: min(dist(pos, w[3]), dist(pos, bosspos[w[0]])))
    return best[0] == d[0]

BOSSES = set(d[2] for d in DONJONS)
placement = {}
for d in DONJONS:
    idx, mapid, boss, entr = d[0], d[1], d[2], d[3]
    bp = bosspos[idx]
    D = dist(entr, bp)
    cand = []
    for g, i, x, y, z in spawns[mapid]:
        p = (x, y, z)
        t = TPL.get(i)
        if i in BOSSES or (t and int(t['maxl']) <= 5):
            continue
        if mapid == 189 and not wing_of(d, p):
            continue
        de, db = dist(p, entr), dist(p, bp)
        if de < 0.3 * D or db < 0.3 * D:
            continue
        cand.append((abs(de - db), g, p))
    cand.sort()
    g0, p0 = cand[0][1], cand[0][2]
    # patrouille : 2 autres emplacements de monstres proches (même étage)
    near = sorted((dist(p0, (x, y, z)), (x, y, z)) for g, i, x, y, z in spawns[mapid]
                  if 6 < dist(p0, (x, y, z)) < 30 and abs(z - p0[2]) < 4)
    pts = [p0]
    for dd, p in near:
        if all(dist(p, o) > 6 for o in pts):
            pts.append(p)
        if len(pts) == 3:
            break
    placement[idx] = pts

# ---------------------------------------------------------------- épiques : pools par niveau (+ épiques « sublimes » créés)
pool_rows = q("select i.entry, i.Quality, i.ItemLevel, i.class, i.subclass, i.InventoryType from item_template i "
              "where i.Quality in (3,4) and i.class in (2,4) and i.InventoryType>0 and i.requiredhonorrank=0 "
              "and i.RequiredReputationFaction=0 and i.bonding in (0,1,2) and i.name not like '%Deprecated%' "
              "and i.name not like 'Monster%' and i.name not like '%Test%' "
              "and (i.entry in (select item from creature_loot_template where mincountOrRef>0) "
              "or i.entry in (select item from reference_loot_template where mincountOrRef>0)) and i.entry < 990000")
BLUES, EPICS = defaultdict(list), defaultdict(list)
for e, qu, il, cl, sc, it in pool_rows:
    (BLUES if qu == '3' else EPICS)[int(il)].append((int(e), int(cl), int(sc), int(it)))

levels = sorted(set(int(TPL[d[2]]['maxl']) for d in DONJONS) | {41, 51})
pools, sublimes = {}, []
nsub = [SUBLIME_BASE]
for L in levels:
    ep = [x for il in range(L, L + 9) for x in EPICS.get(il, [])]
    if len(ep) >= 6:
        pools[L] = sorted(set(x[0] for x in ep))
        continue
    # pas assez d'épiques vanilla à ce niveau : bleus du niveau passés en épique (stats x1,2)
    bl = [x for il in range(L + 2, L + 8) for x in BLUES.get(il, [])]
    seen, pick = set(), []
    for x in sorted(bl, key=lambda x: (x[0] * 7919) % 1000):
        k = (x[1], x[2], x[3])
        if k in seen:
            continue
        seen.add(k)
        pick.append(x[0])
        if len(pick) == 10:
            break
    out = [x[0] for x in ep]
    for src in pick:
        sublimes.append((nsub[0], src))
        out.append(nsub[0])
        nsub[0] += 1
    pools[L] = sorted(set(out))

def gold(L):
    # 50 pa au niveau 16, 15 po au niveau 60 (progression géométrique)
    return round(5000 * (30 ** ((L - 16) / 44.0)))

# ---------------------------------------------------------------- SQL
L_ = []
w = L_.append
w("-- Boss élites rares de donjon (généré)")
w("SET NAMES utf8mb4;")
w("DELETE FROM creature_linking WHERE guid BETWEEN %d AND %d;" % (GUID_BASE, GUID_BASE + 99))
w("DELETE FROM creature_movement WHERE Id BETWEEN %d AND %d;" % (GUID_BASE, GUID_BASE + 99))
w("DELETE FROM creature WHERE guid BETWEEN %d AND %d;" % (GUID_BASE, GUID_BASE + 99))
w("DELETE FROM creature_template WHERE Entry BETWEEN %d AND %d;" % (RARE_BASE, RARE_BASE + 19))
w("DELETE FROM creature_loot_template WHERE entry BETWEEN %d AND %d;" % (RARE_BASE, RARE_BASE + 59))
w("DELETE FROM creature_spell_list WHERE Id BETWEEN %d AND %d;" % (RARE_BASE, RARE_BASE + 19))
w("DELETE FROM creature_spell_list_entry WHERE Id BETWEEN %d AND %d;" % (RARE_BASE, RARE_BASE + 19))
w("DELETE FROM reference_loot_template WHERE entry BETWEEN %d AND %d;" % (REF_MOUNT, REF_EPIC + 99))
w("DELETE FROM item_template WHERE entry BETWEEN %d AND %d;" % (SUBLIME_BASE, SUBLIME_BASE + 999))
w("")
w("-- Épiques « sublimes » : bleus du monde passés en épique (stats x1,2) pour les bas niveaux")
w("DROP TEMPORARY TABLE IF EXISTS tmp_it;")
w("CREATE TEMPORARY TABLE tmp_it LIKE item_template;")
for e, src in sublimes:
    w("INSERT INTO tmp_it SELECT * FROM item_template WHERE entry=%d;" % src)
    w("UPDATE tmp_it SET entry=%d, name=CONCAT(name, ' sublime'), Quality=4, ItemLevel=ItemLevel+3, "
      "stat_value1=ROUND(stat_value1*1.2), stat_value2=ROUND(stat_value2*1.2), stat_value3=ROUND(stat_value3*1.2), "
      "stat_value4=ROUND(stat_value4*1.2), stat_value5=ROUND(stat_value5*1.2), stat_value6=ROUND(stat_value6*1.2), "
      "armor=ROUND(armor*1.05), dmg_min1=dmg_min1*1.1, dmg_max1=dmg_max1*1.1, SellPrice=SellPrice*2, BuyPrice=BuyPrice*2 "
      "WHERE entry=%d;" % (e, src))
w("INSERT INTO item_template SELECT * FROM tmp_it;")
w("DROP TEMPORARY TABLE tmp_it;")
w("")
w("-- Pools : épiques par niveau, montures")
for L, items in sorted(pools.items()):
    vals = ", ".join("(%d, %d, 0, 1, 1, 1, 0, 'Custom rare donjon')" % (REF_EPIC + L, it) for it in items)
    w("INSERT INTO reference_loot_template (entry, item, ChanceOrQuestChance, groupid, mincountOrRef, maxcount, condition_id, comments) VALUES %s;" % vals)
w("INSERT INTO reference_loot_template (entry, item, ChanceOrQuestChance, groupid, mincountOrRef, maxcount, condition_id, comments) "
  "SELECT %d, item, 0, 1, 1, 1, 0, 'Custom montures' FROM reference_loot_template WHERE entry=993200;" % REF_MOUNT)
w("")
w("-- Boss rares : copie du boss final, stats x1,25, IA par liste de sorts")
w("DROP TEMPORARY TABLE IF EXISTS tmp_ct;")
w("CREATE TEMPORARY TABLE tmp_ct LIKE creature_template;")
for d in DONJONS:
    idx, mapid, boss, entr, nom, model, scale, escort, sorts = d
    e = RARE_BASE + idx
    lv = int(TPL[boss]['maxl'])
    disp = int(TPL[model]['disp'])
    g = gold(lv)
    w("INSERT INTO tmp_ct SELECT * FROM creature_template WHERE Entry=%d;" % boss)
    w("UPDATE tmp_ct SET Entry=%d, Name='%s', SubName='', MinLevel=%d, MaxLevel=%d, Rank=2, "
      "HealthMultiplier=HealthMultiplier*1.25, DamageMultiplier=DamageMultiplier*1.25, "
      "DisplayId1=%d, DisplayId2=0, DisplayId3=0, DisplayId4=0, DisplayIdProbability1=100, DisplayIdProbability2=0, "
      "DisplayIdProbability3=0, DisplayIdProbability4=0, Scale=%.2f, AIName='', ScriptName='', SpellList=%d, "
      "LootId=%d, MinLootGold=%d, MaxLootGold=%d, GossipMenuId=0, NpcFlags=0, ExtraFlags=0, EquipmentTemplateId=(SELECT EquipmentTemplateId FROM creature_template WHERE Entry=%d) "
      "WHERE Entry=%d;" % (e, esc(nom), lv, lv, disp, scale, e, e, round(g * 0.8), round(g * 1.2), model, boss))
w("INSERT INTO creature_template SELECT * FROM tmp_ct;")
w("DROP TEMPORARY TABLE tmp_ct;")
w("")
w("-- Listes de sorts")
for d in DONJONS:
    idx, mapid, boss, entr, nom, model, scale, escort, sorts = d
    e = RARE_BASE + idx
    caster = any(s[2] == 2 for s in sorts)
    w("INSERT INTO creature_spell_list_entry (Id, Name, ChanceSupportAction, ChanceRangedAttack) VALUES (%d, '%s', 0, %d);"
      % (e, esc('Custom - rare - ' + nom), 75 if caster else 0))
    for pos, (sid, tgt, fl, imin, imax, rmin, rmax) in enumerate(sorts):
        w("INSERT INTO creature_spell_list (Id, Position, SpellId, Flags, CombatCondition, TargetId, ScriptId, Availability, "
          "Probability, InitialMin, InitialMax, RepeatMin, RepeatMax, Comments) VALUES (%d, %d, %d, %d, -1, %d, 0, 100, %d, %d, %d, %d, %d, '%s');"
          % (e, pos, sid, fl, tgt, 1 if fl == 2 else 3, imin, imax, rmin, rmax, esc('Custom - ' + nom)))
w("")
w("-- Butin : 1 épique du monde au niveau (normal / mode 40 / mode 50), monture 10 %")
for d in DONJONS:
    idx, boss = d[0], d[2]
    e = RARE_BASE + idx
    for mode, off in LOOT_MODE.items():
        lv = int(TPL[boss]['maxl']) if mode == 0 else mode + 1
        w("INSERT INTO creature_loot_template (entry, item, ChanceOrQuestChance, groupid, mincountOrRef, maxcount, condition_id, comments) VALUES "
          "(%d, %d, 100, 0, -%d, 1, 0, 'Custom : 1 epique'), (%d, %d, 10, 0, -%d, 1, 0, 'Custom : monture 10 %%');"
          % (e + off, REF_EPIC + lv, REF_EPIC + lv, e + off, REF_MOUNT, REF_MOUNT))
w("")
w("-- Apparition (toujours là) + patrouille + 2 escortes qui suivent")
for d in DONJONS:
    idx, mapid, boss, entr, nom, model, scale, escort, sorts = d
    pts = placement[idx]
    g = GUID_BASE + idx * 3
    p0 = pts[0]
    o = math.atan2(pts[1][1] - p0[1], pts[1][0] - p0[0]) % (2 * math.pi) if len(pts) > 1 else 0
    mv = 2 if len(pts) >= 2 else 1
    w("INSERT INTO creature (guid, id, map, spawnMask, position_x, position_y, position_z, orientation, spawntimesecsmin, "
      "spawntimesecsmax, spawndist, MovementType) VALUES (%d, %d, %d, 1, %.2f, %.2f, %.2f, %.3f, 604800, 604800, %d, %d);"
      % (g, RARE_BASE + idx, mapid, p0[0], p0[1], p0[2], o, 0 if mv == 2 else 5, mv))
    if mv == 2:
        loop = pts
        for n, p in enumerate(loop):
            w("INSERT INTO creature_movement (Id, Point, PositionX, PositionY, PositionZ, Orientation, WaitTime, ScriptId, Comment) "
              "VALUES (%d, %d, %.2f, %.2f, %.2f, 100, %d, 0, 'Custom rare');" % (g, n + 1, p[0], p[1], p[2], 4000))
    for k in (1, 2):
        a = o + math.pi + (0.6 if k == 1 else -0.6)
        w("INSERT INTO creature (guid, id, map, spawnMask, position_x, position_y, position_z, orientation, spawntimesecsmin, "
          "spawntimesecsmax, spawndist, MovementType) VALUES (%d, %d, %d, 1, %.2f, %.2f, %.2f, %.3f, 604800, 604800, 0, 0);"
          % (g + k, escort, mapid, p0[0] + 2.5 * math.cos(a), p0[1] + 2.5 * math.sin(a), p0[2], o))
        # suit le chef, entre en combat avec lui, réapparaît avec lui
        w("INSERT INTO creature_linking (guid, master_guid, flag) VALUES (%d, %d, %d);" % (g + k, g, 0x0001 | 0x0002 | 0x0080 | 0x0200))
w("")
w("SELECT 'Rares de donjon OK' AS resultat;")
open(OUT + 'rares.sql', 'w', encoding='utf-8').write("\n".join(L_) + "\n")
for d in DONJONS:
    p = placement[d[0]]
    print(d[4], int(TPL[d[2]]['maxl']), 'pts', len(p), ['%.0f,%.0f,%.0f' % x for x in p], 'gold', gold(int(TPL[d[2]]['maxl'])))
print('pools', {k: len(v) for k, v in pools.items()}, 'sublimes', len(sublimes))
