# Monde extérieur : tableaux de primes (10 quêtes par zone), boss élite de zone, boss rare en patrouille.
# Données calculées depuis la base world locale (copie de SPP). Les noms (FR) sont pris dans la base du PC
# au moment de l'installation (UPDATE ... JOIN), le script ne contient que des numéros.
import sys, struct, json, math, subprocess, random
from collections import defaultdict
sys.path.insert(0, '/home/claude/wow/fr')
from dbc import DBC

random.seed(1912)
OUT = '/home/claude/wow/monde/'

def q(sql):
    r = subprocess.run(['mysql', '-N', '-B', 'classicmangos', '-e', sql], capture_output=True, text=True, check=True)
    return [l.split('\t') for l in r.stdout.splitlines()]

def esc(s):
    return s.replace('\\', '\\\\').replace("'", "\\'")

def f32(x):
    return struct.unpack('<f', struct.pack('<I', x))[0]

# ------------------------------------------------------------------ zones (WorldMapArea)
VILLES = {1519, 1637, 1537, 1638, 1657, 1497}
wma = DBC('/home/claude/wow/fr/dbc_en/WorldMapArea.dbc')
at = DBC('/home/claude/wow/fr/dbc_en/AreaTable.dbc')
T = {}
import glob
for fn in glob.glob('/home/claude/wow/fr/out/*.json'):
    if 'ranks' not in fn:
        T.update(json.load(open(fn, encoding='utf-8')))
areaname = {r[0]: at.str(r[11]) for r in at.rows}
ZONES = []
for r in wma.rows:
    if r[1] in (0, 1) and r[2] and r[2] not in VILLES:
        left, right, top, bottom = (f32(x) for x in r[4:8])   # left/right = Y max/min, top/bottom = X max/min
        en = areaname.get(r[2], '')
        ZONES.append(dict(id=r[2], map=r[1], ymax=left, ymin=right, xmax=top, xmin=bottom,
                          nom=T.get(en, en), area=(left - right) * (top - bottom)))

ZBYID = {z['id']: z for z in ZONES}
# Points étiquetés : PNJ qui donnent/rendent des quêtes d'une zone + créatures à tuer pour ces quêtes
# Zone exacte de chaque spawn, calculée par le serveur (Spawns.ZoneArea) et exportée du PC
ZONE_OF_GUID = {int(g): int(zid) for g, zid in q("select Guid, ZoneId from creature_zone")}
def zone_of_guid(g):
    return ZBYID.get(ZONE_OF_GUID.get(g))

# ------------------------------------------------------------------ factions
ft = DBC('/mnt/user-data/uploads/SPP_Classics V2/SPP_Classics_V2/SPP_Server/Server/Modules/vanilla/dbc/FactionTemplate.dbc')
FT = {r[0]: r for r in ft.rows}
def amical(fac):
    r = FT.get(fac)
    if not r:
        return False
    return bool((r[3] | r[4]) & 6)

# ------------------------------------------------------------------ créatures
rows = q("select c.guid, c.id, c.map, c.position_x, c.position_y, c.position_z, c.orientation, t.MinLevel, t.MaxLevel, t.Rank, "
         "t.CreatureType, t.Faction, t.NpcFlags, t.LootId, t.UnitFlags, t.ExtraFlags from creature c join creature_template t on t.Entry=c.id "
         "where c.map in (0,1) and c.guid not in (select guid from game_event_creature)")      # hors spawns d'événement (Invasion du Fléau...)
spawns = defaultdict(list)       # zone -> liste de spawns de monstres
hubs = defaultdict(list)         # zone -> aubergistes
fly = defaultdict(list)
templ = {}
for g, e, m, x, y, z, o, mn, mx, rk, ct, fac, npc, loot, uf, xf in rows:
    g, e, m = int(g), int(e), int(m)
    x, y, z, o = float(x), float(y), float(z), float(o)
    zo = zone_of_guid(g)
    if not zo:
        continue
    npc = int(npc)
    if npc & 128:
        hubs[zo['id']].append((g, e, m, x, y, z, o))
    if npc & 8:
        fly[zo['id']].append((g, e, m, x, y, z, o))
    if npc or amical(int(fac)) or int(loot) == 0 or int(rk) not in (0, 1):
        continue
    if int(uf) & (2 | 256 | 33554432):     # non attaquable / non sélectionnable
        continue
    templ[e] = dict(min=int(mn), max=int(mx), rank=int(rk), type=int(ct), loot=int(loot))
    spawns[zo['id']].append(dict(guid=g, e=e, map=m, x=x, y=y, z=z, o=o, lvl=int(mx), rank=int(rk), type=int(ct)))

# butin "à collecter" : objets gris / commerce, hors quête, chance >= 25 %
lootrows = q("select l.entry, l.item, l.ChanceOrQuestChance, i.class, i.Quality from creature_loot_template l join item_template i on i.entry=l.item "
             "where l.mincountOrRef>0 and l.ChanceOrQuestChance>=25 and l.groupid=0 and i.class in (7,15) and i.Quality<=1 and i.bonding=0 "
             "and i.startquest=0 and i.name not like '%Deprecated%'")
loot_of = defaultdict(list)
for le, it, ch, cl, qu in lootrows:
    loot_of[int(le)].append((int(it), float(ch)))

# XP / or moyens des quêtes normales par niveau
xpl = {}
for lv, rmm, money in q("select QuestLevel, avg(RewMoneyMaxLevel), avg(greatest(RewOrReqMoney,0)) from quest_template "
                        "where Type=0 and QuestLevel between 1 and 60 and RewMoneyMaxLevel>0 group by QuestLevel"):
    xpl[int(lv)] = (float(rmm), float(money))
def rmm_money(lv):
    lv = max(1, min(60, lv))
    for d in range(0, 10):
        for c in (lv - d, lv + d):
            if c in xpl:
                return xpl[c]
    return (lv * 40.0, lv * 50.0)

# pools d'objets (bleus et épiques du monde, montures)
pool_rows = q("select i.entry, i.Quality, i.ItemLevel, i.class, i.subclass, i.InventoryType, i.AllowableClass from item_template i "
              "where i.Quality in (3,4) and i.class in (2,4) and i.InventoryType>0 and i.requiredhonorrank=0 and i.RequiredReputationFaction=0 "
              "and i.bonding in (0,1,2) and i.name not like '%Deprecated%' and i.name not like 'Monster%' and i.name not like '%Test%' "
              "and (i.entry in (select item from creature_loot_template where mincountOrRef>0) or i.entry in (select item from reference_loot_template where mincountOrRef>0)) "
              "and i.entry < 990000")
BLUES, EPICS = defaultdict(list), defaultdict(list)
for e, qu, il, cl, sc, it, ac in pool_rows:
    (BLUES if qu == '3' else EPICS)[int(il)].append((int(e), int(cl), int(sc), int(it), int(ac)))
def pool(d, lo, hi, minimum=8):
    while True:
        out = [x for il in range(lo, hi + 1) for x in d.get(il, [])]
        if len(out) >= minimum or hi > 80:
            return out
        lo, hi = max(1, lo - 2), hi + 3

spell = DBC('/home/claude/wow/fr/dbc_en/Spell.dbc')
mount_spells = set(r[0] for r in spell.rows if any(r[61 + k] == 6 and r[91 + k] == 78 for k in range(3)))
MOUNTS = [int(e) for e, s, t in q("select entry, spellid_2, spelltrigger_2 from item_template where class=15 and spellid_2>0")
          if int(s) in mount_spells]
MOUNTS += [int(e) for e, s in q("select entry, spellid_1 from item_template where spellid_1>0 and spelltrigger_1=0 and class in (15,0)")
           if int(s) in mount_spells and int(e) not in MOUNTS]

# ------------------------------------------------------------------ génération par zone
QBASE, GOBASE, BOSSBASE, RAREBASE = 991400, 990500, 992000, 992100
REF_BLUE, REF_EPIC, REF_MOUNT = 993000, 993100, 993200    # + niveau
L = []
w = L.append
quests, boards, bosses, rares, refs = [], [], [], [], {}
SLOTS = [(4, 1), (4, 2), (4, 3), (4, 4), (2, None), (4, 0)]   # tissu, cuir, maille, plaques, arme, bijou/cape

def choice_blues(lv):
    p = pool(BLUES, lv - 2, lv + 3, 12)
    out = []
    for cl, sc in SLOTS:
        cands = [x for x in p if x[1] == cl and (sc is None or x[2] == sc) and x[4] in (-1, 0, 32767) and x[0] not in out]
        if cands:
            out.append(random.choice(cands)[0])
    while len(out) < 6 and p:
        c = random.choice(p)[0]
        if c not in out:
            out.append(c)
    return out[:6]

summary = []
for zi, z in enumerate(sorted(ZONES, key=lambda z: z['id'])):
    sp = spawns.get(z['id'], [])
    if len(sp) < 30:
        continue
    lv = sorted(s['lvl'] for s in sp)
    q1, q3 = lv[len(lv) // 4], lv[(len(lv) * 3) // 4]
    sp = [s for s in sp if q1 - 4 <= s['lvl'] <= q3 + 4]
    lv = sorted(s['lvl'] for s in sp)
    lmin, lmax = lv[len(lv) // 20], lv[(len(lv) * 19) // 20]
    hub = hubs.get(z['id']) or fly.get(z['id'])
    if not hub:
        continue
    per_e = defaultdict(list)
    for s in sp:
        per_e[s['e']].append(s)
    normals = sorted([e for e, l in per_e.items() if templ[e]['rank'] == 0 and len(l) >= 6], key=lambda e: templ[e]['max'])
    elites = sorted([e for e, l in per_e.items() if templ[e]['rank'] == 1 and len(l) >= 1], key=lambda e: -len(per_e[e]))
    if len(normals) < 5:
        continue
    # 5 tuer : répartis sur la plage de niveaux
    kill = [normals[int(i * (len(normals) - 1) / 4)] for i in range(5)]
    kill = list(dict.fromkeys(kill))
    for e in normals:
        if len(kill) >= 5:
            break
        if e not in kill:
            kill.append(e)
    # 4 récupérer
    collect = []
    for e in sorted(normals, key=lambda e: -len(per_e[e])):
        if len(collect) >= 4:
            break
        items = [it for it, ch in loot_of.get(templ[e]['loot'], []) if it not in [c[1] for c in collect]]
        if items:
            collect.append((e, items[0]))
    zq = []
    for e in kill:
        n = max(6, min(12, len(per_e[e])))
        zq.append(dict(kind='kill', e=e, n=n, lvl=templ[e]['max'], mult=0.8))
    for e, it in collect:
        zq.append(dict(kind='item', e=e, item=it, n=8, lvl=templ[e]['max'], mult=0.8))
    if elites:
        e = elites[0]
        zq.append(dict(kind='kill', e=e, n=min(3, len(per_e[e])), lvl=templ[e]['max'], mult=1.5, elite=True))

    # boss élite : centre du camp d'humanoïdes le plus dense
    hum = [s for s in sp if s['type'] == 7] or sp
    def voisins(s, lst):
        return sum(1 for t in lst if (t['x'] - s['x']) ** 2 + (t['y'] - s['y']) ** 2 < 35 * 35)
    camp = max(hum, key=lambda s: (voisins(s, hum), s['lvl']))
    blvl = min(62, lmax + 2)
    boss = dict(entry=BOSSBASE + zi, src=camp['e'], spawn=camp, lvl=blvl, zone=z)
    # boss rare : bête (sinon autre) du plus haut niveau, en patrouille
    cand = [s for s in sp if s['type'] == 1 and s['lvl'] >= lmax - 2] or [s for s in sp if s['lvl'] >= lmax - 2] or sp
    rs = random.choice(cand)
    rlvl = min(63, lmax + 3)
    rare = dict(entry=RAREBASE + zi, src=rs['e'], spawn=rs, lvl=rlvl, zone=z)
    zq.append(dict(kind='boss', e=boss['entry'], n=1, lvl=blvl, mult=2.0, blues=choice_blues(blvl)))
    zq.append(dict(kind='rare', e=rare['entry'], n=1, lvl=rlvl, mult=2.0, blues=choice_blues(rlvl)))
    for qq in zq:
        qq['zone'] = z
        qq['id'] = QBASE + len(quests)
        quests.append(qq)
    boards.append(dict(entry=GOBASE + zi, zone=z, hubs=hub, quests=[qq['id'] for qq in zq]))
    bosses.append(boss)
    rares.append(rare)
    refs[blvl] = True
    refs[rlvl] = True
    summary.append((z['nom'], lmin, lmax, len(zq), len(hub)))

# ------------------------------------------------------------------ SQL
w("-- Monde extérieur : tableaux de primes, boss élite de zone, boss rare (généré)")
w("SET NAMES utf8mb4;")
w("DELETE FROM gameobject WHERE id BETWEEN %d AND %d;" % (GOBASE, GOBASE + 99))
w("DELETE FROM gameobject_template WHERE entry BETWEEN %d AND %d;" % (GOBASE, GOBASE + 99))
w("DELETE FROM gameobject_questrelation WHERE id BETWEEN %d AND %d;" % (GOBASE, GOBASE + 99))
w("DELETE FROM gameobject_involvedrelation WHERE id BETWEEN %d AND %d;" % (GOBASE, GOBASE + 99))
w("DELETE FROM quest_template WHERE entry BETWEEN %d AND %d;" % (QBASE, QBASE + 599))
w("DELETE FROM creature WHERE id BETWEEN %d AND %d;" % (BOSSBASE, RAREBASE + 99))
w("DELETE FROM creature_template WHERE Entry BETWEEN %d AND %d;" % (BOSSBASE, RAREBASE + 99))
w("DELETE FROM creature_loot_template WHERE entry BETWEEN %d AND %d;" % (BOSSBASE, RAREBASE + 99))
w("DELETE FROM reference_loot_template WHERE entry BETWEEN %d AND %d;" % (REF_BLUE, REF_MOUNT + 99))
w("")
w("-- Pools de butin : bleus et épiques du monde par niveau, montures")
for lv in sorted(refs):
    for ref, d, lo, hi in ((REF_BLUE + lv, BLUES, lv - 2, lv + 3), (REF_EPIC + lv, EPICS, lv - 3, lv + 6)):
        items = sorted(set(x[0] for x in pool(d, lo, hi, 8)))
        vals = ", ".join("(%d, %d, 0, 1, 1, 1, 0, 'Custom monde')" % (ref, it) for it in items)
        w("INSERT INTO reference_loot_template (entry, item, ChanceOrQuestChance, groupid, mincountOrRef, maxcount, condition_id, comments) VALUES %s;" % vals)
vals = ", ".join("(%d, %d, 0, 1, 1, 1, 0, 'Custom montures')" % (REF_MOUNT, it) for it in sorted(set(MOUNTS)))
w("INSERT INTO reference_loot_template (entry, item, ChanceOrQuestChance, groupid, mincountOrRef, maxcount, condition_id, comments) VALUES %s;" % vals)
w("")
w("-- Tableaux de primes (copie du « Wanted Board » 2713)")
w("DROP TEMPORARY TABLE IF EXISTS tmp_go;")
w("CREATE TEMPORARY TABLE tmp_go LIKE gameobject_template;")
for b in boards:
    w("INSERT INTO tmp_go SELECT * FROM gameobject_template WHERE entry=2713;")
    w("UPDATE tmp_go SET entry=%d, name='Tableau de primes', size=1.2 WHERE entry=2713;" % b['entry'])
w("INSERT INTO gameobject_template SELECT * FROM tmp_go;")
w("DROP TEMPORARY TABLE tmp_go;")
gguid = 9905000
for b in boards:
    for (g, e, m, x, y, z, o) in b['hubs']:
        bx, by = x + 3.0 * math.cos(o + 1.2), y + 3.0 * math.sin(o + 1.2)
        rot2, rot3 = math.sin(o / 2), math.cos(o / 2)
        w("INSERT INTO gameobject (guid, id, map, spawnMask, position_x, position_y, position_z, orientation, rotation0, rotation1, rotation2, rotation3, "
          "spawntimesecsmin, spawntimesecsmax) VALUES (%d, %d, %d, 1, %.2f, %.2f, %.2f, %.3f, 0, 0, %.5f, %.5f, 120, 120);"
          % (gguid, b['entry'], m, bx, by, z, o, rot2, rot3))
        gguid += 1
    for qid in b['quests']:
        w("INSERT INTO gameobject_questrelation (id, quest) VALUES (%d, %d);" % (b['entry'], qid))
        w("INSERT INTO gameobject_involvedrelation (id, quest) VALUES (%d, %d);" % (b['entry'], qid))
w("")
w("-- Boss élite de zone et boss rare (copies de monstres de la zone)")
w("DROP TEMPORARY TABLE IF EXISTS tmp_ct;")
w("CREATE TEMPORARY TABLE tmp_ct LIKE creature_template;")
for kind, lst in (('boss', bosses), ('rare', rares)):
    for bo in lst:
        lv = bo['lvl']
        if kind == 'boss':
            sets = ("Rank=1, HealthMultiplier=8, DamageMultiplier=2.2, "
                    "Scale=IF(Scale>0,Scale,1)*1.3, SubName='Boss de zone', ExperienceMultiplier=4, MinLootGold=%d, MaxLootGold=%d"
                    % (lv * lv * 20, lv * lv * 30))
        else:
            sets = ("Rank=2, HealthMultiplier=14, DamageMultiplier=2.5, "
                    "Scale=IF(Scale>0,Scale,1)*1.4, SubName='Rare élite', ExperienceMultiplier=6, MinLootGold=%d, MaxLootGold=%d"
                    % (lv * lv * 35, lv * lv * 45))
        w("INSERT INTO tmp_ct SELECT * FROM creature_template WHERE Entry=%d;" % bo['src'])
        w("UPDATE tmp_ct SET Entry=%d, MinLevel=%d, MaxLevel=%d, LootId=%d, PickpocketLootId=0, SkinningLootId=0, KillCredit1=0, KillCredit2=0, "
          "StringId1=0, StringId2=0, %s WHERE Entry=%d;" % (bo['entry'], lv, lv, bo['entry'], sets, bo['src']))
w("INSERT INTO creature_template SELECT * FROM tmp_ct;")
w("DROP TEMPORARY TABLE tmp_ct;")
w("UPDATE creature_template SET Name=CONCAT('Chef ', Name) WHERE Entry BETWEEN %d AND %d;" % (BOSSBASE, BOSSBASE + 99))
w("UPDATE creature_template SET Name=CONCAT(Name, ' alpha') WHERE Entry BETWEEN %d AND %d;" % (RAREBASE, RAREBASE + 99))
cguid = 9920000
for bo in bosses:
    s = bo['spawn']
    w("INSERT INTO creature (guid, id, map, spawnMask, position_x, position_y, position_z, orientation, spawntimesecsmin, spawntimesecsmax, spawndist, MovementType) "
      "VALUES (%d, %d, %d, 1, %.2f, %.2f, %.2f, %.3f, 1800, 3600, 0, 0);" % (cguid, bo['entry'], s['map'], s['x'] + 1.5, s['y'] + 1.5, s['z'], s['o']))
    cguid += 1
    w("INSERT INTO creature_loot_template (entry, item, ChanceOrQuestChance, groupid, mincountOrRef, maxcount, condition_id, comments) VALUES "
      "(%d, %d, 100, 0, -%d, 1, 0, 'Custom : 1 bleu');" % (bo['entry'], REF_BLUE + bo['lvl'], REF_BLUE + bo['lvl']))
for bo in rares:
    s = bo['spawn']
    w("INSERT INTO creature (guid, id, map, spawnMask, position_x, position_y, position_z, orientation, spawntimesecsmin, spawntimesecsmax, spawndist, MovementType) "
      "VALUES (%d, %d, %d, 1, %.2f, %.2f, %.2f, %.3f, 3600, 7200, 40, 1);" % (cguid, bo['entry'], s['map'], s['x'], s['y'], s['z'], s['o']))
    cguid += 1
    w("INSERT INTO creature_loot_template (entry, item, ChanceOrQuestChance, groupid, mincountOrRef, maxcount, condition_id, comments) VALUES "
      "(%d, %d, 100, 0, -%d, 1, 0, 'Custom : 1 epique'), (%d, %d, 5, 0, -%d, 1, 0, 'Custom : monture 5 %%');"
      % (bo['entry'], REF_EPIC + bo['lvl'], REF_EPIC + bo['lvl'], bo['entry'], REF_MOUNT, REF_MOUNT))
w("")
w("-- Quêtes des tableaux (textes complétés plus bas avec les noms de la base)")
for qq in quests:
    lv = max(1, min(60, qq['lvl']))
    rmm, money = rmm_money(lv)
    rmm, money = int(rmm * qq['mult']), int(max(money, lv * 30) * qq['mult'])
    minl = max(1, lv - 6)
    cols = ["entry", "Method", "ZoneOrSort", "MinLevel", "QuestLevel", "Type", "QuestFlags", "SuggestedPlayers", "Title", "Details",
            "Objectives", "OfferRewardText", "RequestItemsText", "EndText", "RewOrReqMoney", "RewMoneyMaxLevel"]
    vals = [str(qq['id']), '2', str(qq['zone']['id']), str(minl), str(lv),
            '1' if qq['kind'] in ('boss', 'rare') or qq.get('elite') else '0', '8',
            '3' if qq['kind'] == 'boss' else ('5' if qq['kind'] == 'rare' else ('3' if qq.get('elite') else '0')),
            "''", "''", "''", "'Bon travail, $N. La prime est à vous.'", "'Alors, ce contrat ?'", "''", str(money), str(rmm)]
    if qq['kind'] == 'item':
        cols += ["ReqItemId1", "ReqItemCount1"]
        vals += [str(qq['item']), str(qq['n'])]
    else:
        cols += ["ReqCreatureOrGOId1", "ReqCreatureOrGOCount1"]
        vals += [str(qq['e']), str(qq['n'])]
    if qq.get('blues'):
        for i, it in enumerate(qq['blues']):
            cols += ["RewChoiceItemId%d" % (i + 1), "RewChoiceItemCount%d" % (i + 1)]
            vals += [str(it), '1']
    w("INSERT INTO quest_template (%s) VALUES (%s);" % (", ".join(cols), ", ".join(vals)))
w("")
w("-- Textes en français avec les noms de la base")
Z = "CONCAT(' (', z.n, ')')"
w("DROP TEMPORARY TABLE IF EXISTS tmp_zn;")
w("CREATE TEMPORARY TABLE tmp_zn (id INT PRIMARY KEY, n VARCHAR(100)) CHARACTER SET utf8mb4;")
w("INSERT INTO tmp_zn VALUES %s;" % ", ".join("(%d, '%s')" % (z['id'], esc(z['nom'])) for z in ZONES))
w("UPDATE quest_template q JOIN creature_template c ON c.Entry=q.ReqCreatureOrGOId1 JOIN tmp_zn z ON z.id=q.ZoneOrSort "
  "SET q.Title=CONCAT('Prime : ', c.Name), "
  "q.Objectives=CONCAT('Tuez ', q.ReqCreatureOrGOCount1, ' x ', c.Name, '.'), "
  "q.Details=CONCAT('Avis aux aventuriers de la région de ', z.n, ' : les ', c.Name, ' deviennent trop nombreux. ',"
  "'Une prime est offerte à qui en éliminera ', q.ReqCreatureOrGOCount1, '.$B$BRevenez au tableau une fois le travail fait.') "
  "WHERE q.entry BETWEEN %d AND %d AND q.ReqCreatureOrGOId1>0;" % (QBASE, QBASE + 599))
w("UPDATE quest_template q JOIN item_template i ON i.entry=q.ReqItemId1 JOIN tmp_zn z ON z.id=q.ZoneOrSort "
  "SET q.Title=CONCAT('Récolte : ', i.name), "
  "q.Objectives=CONCAT('Rapportez ', q.ReqItemCount1, ' x ', i.name, '.'), "
  "q.Details=CONCAT('Un marchand de ', z.n, ' paie bien pour ', q.ReqItemCount1, ' x ', i.name, '. ',"
  "'On en trouve sur les créatures des environs.$B$BRapportez-les au tableau de primes.') "
  "WHERE q.entry BETWEEN %d AND %d AND q.ReqItemId1>0;" % (QBASE, QBASE + 599))
w("UPDATE quest_template q JOIN creature_template c ON c.Entry=q.ReqCreatureOrGOId1 JOIN tmp_zn z ON z.id=q.ZoneOrSort "
  "SET q.Title=CONCAT('Avis de recherche : ', c.Name), q.Objectives=CONCAT('Abattez ', c.Name, '.'), "
  "q.Details=CONCAT(c.Name, ' terrorise la région de ', z.n, '. Il est redoutable : partez à plusieurs.$B$B',"
  "'Rapportez la preuve de sa mort au tableau et choisissez votre récompense.') "
  "WHERE q.entry BETWEEN %d AND %d AND q.ReqCreatureOrGOId1 BETWEEN %d AND %d;" % (QBASE, QBASE + 599, BOSSBASE, RAREBASE + 99))
w("DROP TEMPORARY TABLE tmp_zn;")
w("")
w("SELECT 'Monde exterieur OK' AS resultat;")
open(OUT + 'monde.sql', 'w', encoding='utf-8').write("\n".join(L) + "\n")
json.dump(summary, open(OUT + 'resume.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
print('zones', len(boards), 'quetes', len(quests), 'tableaux', sum(len(b['hubs']) for b in boards), 'montures', len(set(MOUNTS)))
for s in summary:
    print(s)
