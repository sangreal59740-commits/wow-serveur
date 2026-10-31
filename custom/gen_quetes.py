# 2 quêtes par donjon (mode normal), données par le Gardien des épreuves, une fois par personnage :
#   - vaincre le boss final : XP x2, or, un bleu au choix (6 types d'objet)
#   - tuer 10 monstres du donjon : XP x2, or
# Sortie : quetes_donjons.sql
import math, random, subprocess
from collections import defaultdict

OUT = '/home/claude/wow/donjons/'

def q(sql):
    r = subprocess.run(['mysql', '-N', '-B', 'classicmangos', '-e', sql], capture_output=True, text=True, check=True)
    return [l.split('\t') for l in r.stdout.splitlines()]

def esc(s):
    return s.replace('\\', '\\\\').replace("'", "\\'")

NPC_BASE, QUEST_BASE = 990100, 990330
# idx, map, entrée, boss final, position de repli du boss (entrée d'un PNJ voisin), nom, zone
D = [
    (0, 389, (0.8, -8.2, -15.5), 11520, None, "Gouffre de Ragefeu", 2437),
    (1, 36, (-14.6, -385.5, 62.5), 639, None, "Les Mortemines", 1581),
    (2, 43, (-158.4, 131.6, -74.3), 3654, 3679, "Cavernes des Lamentations", 718),
    (3, 33, (-228.2, 2111.4, 76.9), 4275, None, "Donjon d'Ombrecroc", 209),
    (4, 34, (49.0, 0.5, -16.4), 1716, None, "La Prison", 717),
    (5, 48, (-150.2, 106.6, -39.8), 4829, None, "Profondeurs de Brassenoire", 719),
    (6, 90, (-329.1, -3.2, -152.9), 7800, None, "Gnomeregan", 721),
    (7, 47, (1942.3, 1544.2, 83.3), 4421, None, "Kraal de Tranchebauge", 491),
    (8, 189, (1687.3, 1050.1, 18.7), 4543, None, "Monastère : Cimetière", 796),
    (9, 189, (253.7, -206.6, 18.7), 6487, None, "Monastère : Bibliothèque", 796),
    (10, 189, (1608.1, -318.9, 18.7), 3975, None, "Monastère : Armurerie", 796),
    (11, 189, (853.2, 1319.2, 18.7), 3977, None, "Monastère : Cathédrale", 796),
    (12, 129, (2593.7, 1111.2, 51.0), 7358, None, "Souilles de Tranchebauge", 722),
    (13, 70, (-228.9, 46.1, -46.0), 2748, None, "Uldaman", 1337),
    (14, 209, (1212.7, 842.0, 8.9), 7267, None, "Zul'Farrak", 1176),
    (15, 349, (1016.8, -458.5, -43.5), 12201, None, "Maraudon", 2100),
    (16, 109, (-315.9, 100.2, -131.8), 5709, None, "Temple englouti", 1477),
    (17, 230, (456.9, 34.1, -68.1), 9019, None, "Profondeurs de Rochenoire", 1584),
    (18, 229, (78.4, -226.8, 49.8), 9568, None, "Pic Rochenoire", 1583),
    (19, 429, (47.5, -153.7, -2.7), 11492, None, "Hache-Tripes Est", 2557),
    (20, 429, (-65.7, 159.6, -3.5), 11486, None, "Hache-Tripes Ouest", 2557),
    (21, 429, (254.9, -19.5, -2.6), 11501, None, "Hache-Tripes Nord", 2557),
    (22, 329, (3392.9, -3395.0, 143.1), 10813, 10812, "Stratholme : quartier écarlate", 2017),
    (23, 329, (3590.9, -3643.2, 138.5), 10440, None, "Stratholme : quartier mort-vivant", 2017),
    (24, 289, (190.8, 126.3, 137.2), 1853, None, "Scholomance", 2057),
]

TPL = {}
for e, n, mn, mx, rank, nf, hm in q("select Entry, Name, MinLevel, MaxLevel, Rank, NpcFlags, HealthMultiplier from creature_template"):
    TPL[int(e)] = dict(name=n, min=int(mn), max=int(mx), rank=int(rank), npc=int(nf), hm=float(hm))
spawns = defaultdict(list)
for i, m, x, y, z in q("select id, map, position_x, position_y, position_z from creature where map in (%s) and spawnMask>0"
                       % ",".join(str(m) for m in set(d[1] for d in D))):
    spawns[int(m)].append((int(i), float(x), float(y), float(z)))

def dist(a, b):
    return math.sqrt(sum((a[k] - b[k]) ** 2 for k in range(3)))

bosspos = {}
for d in D:
    ref = d[4] or d[3]
    p = [s[1:] for s in spawns[d[1]] if s[0] == ref]
    bosspos[d[0]] = p[0] if p else d[2]

def owner(mapid, pos):
    same = [d for d in D if d[1] == mapid]
    return min(same, key=lambda d: min(dist(pos, d[2]), dist(pos, bosspos[d[0]])))[0]

# monstre le plus courant du donjon (ou de l'aile)
trash = {}
for d in D:
    cnt = defaultdict(int)
    for i, x, y, z in spawns[d[1]]:
        t = TPL.get(i)
        if not t or t['npc'] or t['max'] <= 5 or t['hm'] >= 4 or t['rank'] >= 2:
            continue
        if owner(d[1], (x, y, z)) != d[0]:
            continue
        cnt[i] += 1
    elites = {e: c for e, c in cnt.items() if TPL[e]['rank'] == 1 and c >= 5}
    pool = elites or cnt
    trash[d[0]] = max(pool, key=lambda e: (pool[e], -e)) if pool else None

# objets bleus du monde
BLUES = defaultdict(list)
for e, il, cl, sc, it, ac in q("select entry, ItemLevel, class, subclass, InventoryType, AllowableClass from item_template "
                               "where Quality=3 and class in (2,4) and InventoryType>0 and requiredhonorrank=0 and RequiredReputationFaction=0 "
                               "and bonding in (1,2) and name not like '%Deprecated%' and name not like 'Monster%' and name not like '%Test%' "
                               "and entry < 990000 and (entry in (select item from creature_loot_template where mincountOrRef>0) "
                               "or entry in (select item from reference_loot_template where mincountOrRef>0))"):
    BLUES[int(il)].append((int(e), int(cl), int(sc), int(it), int(ac)))
SLOTS = [(4, 1), (4, 2), (4, 3), (4, 4), (2, None), (4, 0)]
def choice_blues(lv, seed):
    rnd = random.Random(seed)
    lo, hi = lv + 1, lv + 6
    while True:
        p = [x for il in range(lo, hi + 1) for x in BLUES.get(il, [])]
        if len(p) >= 12 or hi > 80:
            break
        lo, hi = lo - 2, hi + 2
    out = []
    for cl, sc in SLOTS:
        c = [x for x in p if x[1] == cl and (sc is None or x[2] == sc) and x[4] in (-1, 0, 32767) and x[0] not in out]
        if c:
            out.append(rnd.choice(sorted(c))[0])
    while len(out) < 6 and p:
        c = rnd.choice(sorted(p))[0]
        if c not in out:
            out.append(c)
    return out[:6]

def xp_money(L):
    rmml = round((40 * L + 0.6 * L * L) * 2)      # expérience : quête de donjon x2
    money = 12 * L * L
    return rmml, money

L_ = []
w = L_.append
w("-- 2 quêtes par donjon en mode normal (généré)")
w("SET NAMES utf8mb4;")
w("DELETE FROM creature_questrelation WHERE quest BETWEEN %d AND %d;" % (QUEST_BASE, QUEST_BASE + 59))
w("DELETE FROM creature_involvedrelation WHERE quest BETWEEN %d AND %d;" % (QUEST_BASE, QUEST_BASE + 59))
w("DELETE FROM quest_template WHERE entry BETWEEN %d AND %d;" % (QUEST_BASE, QUEST_BASE + 59))
cols = ("entry, Method, ZoneOrSort, MinLevel, QuestLevel, Type, SuggestedPlayers, QuestFlags, Title, Details, Objectives, "
        "OfferRewardText, RequestItemsText, ObjectiveText1, ReqCreatureOrGOId1, ReqCreatureOrGOCount1, RewOrReqMoney, RewMoneyMaxLevel")
recap = []
for idx, mapid, entr, boss, _, nom, zone in D:
    L = TPL[boss]['max']
    rmml, money = xp_money(L)
    minl = max(1, L - 6)
    npc = NPC_BASE + idx
    bossnom = "'%s'" % esc(TPL[boss]['name'])
    # quête 1 : boss final
    q1 = QUEST_BASE + idx * 2
    blues = choice_blues(L, idx)
    det = ("La menace qui règne au fond de ce lieu doit être abattue.$B$BVainquez son maître et revenez me voir : "
           "vous choisirez une pièce d'équipement digne de votre exploit.")
    w("INSERT INTO quest_template (%s, %s, %s) VALUES (%d, 2, %d, %d, %d, 81, 5, 8, '%s', '%s', CONCAT('Vaincre ', (SELECT Name FROM creature_template WHERE Entry=%d), '.'), '%s', '%s', '', %d, 1, %d, %d, %s, %s);"
      % (cols, ", ".join("RewChoiceItemId%d" % (j + 1) for j in range(len(blues))),
         ", ".join("RewChoiceItemCount%d" % (j + 1) for j in range(len(blues))),
         q1, zone, minl, L, esc("%s : le maître des lieux" % nom), esc(det), boss,
         esc("Bien joué, $N. Choisissez votre récompense."), esc("Alors, $N ?"),
         boss, money * 2, rmml, ", ".join(map(str, blues)), ", ".join("1" for _ in blues)))
    w("INSERT INTO creature_questrelation (id, quest) VALUES (%d, %d);" % (npc, q1))
    w("INSERT INTO creature_involvedrelation (id, quest) VALUES (%d, %d);" % (npc, q1))
    # quête 2 : 10 monstres du donjon
    t = trash[idx]
    if t:
        q2 = q1 + 1
        det2 = ("Les lieux grouillent d'ennemis. Faites le ménage : abattez-en dix et revenez me voir.")
        w("INSERT INTO quest_template (%s) VALUES (%d, 2, %d, %d, %d, 81, 5, 0, '%s', '%s', CONCAT('Tuer 10 ', (SELECT Name FROM creature_template WHERE Entry=%d), '.'), '%s', '%s', '', %d, 10, %d, %d);"
          % (cols, q2, zone, minl, L, esc("%s : faire le ménage" % nom), esc(det2), t,
             esc("Le chemin est plus sûr grâce à vous, $N."), esc("Alors, $N ?"), t, money, rmml))
        w("INSERT INTO creature_questrelation (id, quest) VALUES (%d, %d);" % (npc, q2))
        w("INSERT INTO creature_involvedrelation (id, quest) VALUES (%d, %d);" % (npc, q2))
    recap.append((nom, L, TPL[boss]['name'], TPL[t]['name'] if t else '-'))
w("")
w("SELECT 'Quetes de donjon OK' AS resultat;")
open(OUT + 'quetes_donjons.sql', 'w', encoding='utf-8').write("\n".join(L_) + "\n")
for r in recap:
    print(*r, sep=' | ')
