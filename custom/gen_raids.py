# Raids à 10 ou 20 joueurs : PNJ d'entrée, butin des boss selon la taille, boss légendaires, fragments.
# Sortie : raids.sql (base world)
import sys, math, subprocess
from collections import defaultdict

OUT = '/home/claude/wow/donjons/'

def q(sql):
    r = subprocess.run(['mysql', '-N', '-B', 'classicmangos', '-e', sql], capture_output=True, text=True, check=True)
    return [l.split('\t') for l in r.stdout.splitlines()]

def esc(s):
    return s.replace('\\', '\\\\').replace("'", "\\'")

NPC_BASE, LEG_BASE, FRAG_BASE = 990150, 990450, 999000
GOSSIP, TEXT = 60102, 990102
LOOT10, LOOT20, POOLREF, LEGLOOT10, LEGLOOT20, RAIDREF = 998000, 998300, 998600, 998900, 998920, 998950

# idx, map, nom, arrivée (x, y, z, o), boss final, 1er et 2e boss, légendaire, apparence (entrée), échelle, fragment,
# modèle du fragment (objet), sorts (id, cible, flags, initial min-max, répétition min-max)
#   cible : 0 aucune (zone autour du boss), 1 cible actuelle, 2 soi, 100 joueur au hasard, 101 joueur au hasard hors tank
RAIDS = [
    (0, 309, "Zul'Gurub", (-11916.6, -1243.5, 92.5, 4.71), 14834, "Jin'zakh, Avatar du Sang", 11380, 2.0,
     "Fragment du Sang d'Hakkar", 19802,
     [(23918, 1, 0, 8000, 10000, 8000, 13000), (22911, 100, 0, 15000, 20000, 20000, 30000),
      (22644, 1, 0, 20000, 25000, 15000, 30000), (23860, 100, 0, 10000, 12000, 20000, 30000),
      (23979, 1, 0, 25000, 30000, 15000, 25000), (23858, 0, 0, 15000, 18000, 12000, 18000),
      (23895, 2, 0, 30000, 35000, 25000, 35000)]),
    (1, 509, "Ruines d'Ahn'Qiraj", (-8436.5, 1519.2, 31.9, 2.62), 15339, "Zer'akh, Seigneur des Sables", 15387, 2.0,
     "Fragment des Sables d'Ossirian", 21220,
     [(25814, 1, 0, 6000, 9000, 10000, 15000), (25646, 1, 0, 8000, 12000, 8000, 12000),
      (3391, 2, 0, 4000, 6000, 10000, 20000), (25599, 0, 0, 12000, 15000, 16000, 21000),
      (6713, 100, 0, 7000, 9000, 15000, 20000)]),
    (2, 409, "Cœur du Magma", (1091.9, -467.0, -105.1, 3.14), 11502, "Pyrion, Fils de Ragnaros", 11668, 2.2,
     "Fragment du Cœur du Magma", 17010,
     [(19460, 1, 0, 6000, 8000, 6000, 9000), (19702, 0, 0, 10000, 15000, 20000, 25000),
      (19703, 0, 0, 20000, 25000, 20000, 25000), (19408, 0, 0, 25000, 30000, 30000, 35000),
      (19449, 2, 0, 1000, 2000, 30000, 30000), (19451, 2, 0, 15000, 20000, 15000, 20000)]),
    (3, 249, "Repaire d'Onyxia", (30.9, -54.1, -5.0, 4.71), 10184, "Matriarche Noirflamme", 10184, 1.3,
     "Fragment d'Onyxia", 18423,
     [(18435, 1, 0, 10000, 15000, 15000, 20000), (18500, 0, 0, 20000, 25000, 25000, 30000),
      (19983, 1, 0, 5000, 8000, 7000, 10000), (15847, 0, 0, 10000, 12000, 12000, 16000),
      (18392, 100, 0, 6000, 10000, 8000, 12000), (19633, 1, 0, 15000, 20000, 20000, 25000),
      (20203, 0, 0, 12000, 16000, 14000, 18000)]),
    (4, 469, "Repaire de l'Aile noire", (-7672.3, -1107.1, 396.7, 0.79), 11583, "Chromatus l'Ultime", 14020, 1.2,
     "Fragment de l'Aile noire", 19003,
     [(19632, 1, 0, 5000, 8000, 7000, 10000), (24375, 0, 0, 15000, 20000, 18000, 24000),
      (22425, 0, 0, 10000, 14000, 12000, 16000), (23023, 1, 0, 12000, 16000, 15000, 20000),
      (23461, 1, 0, 8000, 12000, 10000, 14000), (23462, 0, 0, 20000, 25000, 20000, 25000),
      (15847, 0, 0, 10000, 12000, 12000, 16000)]),
    (5, 531, "Temple d'Ahn'Qiraj", (-8221.4, 2014.3, 129.1, 0.87), 15727, "Zhar'thul, Gardien du Vide", 15277, 2.0,
     "Fragment de l'Œil de C'Thun", 21221,
     [(26192, 0, 0, 10000, 14000, 10000, 14000), (26194, 1, 0, 5000, 8000, 6000, 9000),
      (25174, 1, 0, 6000, 9000, 8000, 12000), (26083, 2, 0, 20000, 25000, 30000, 35000),
      (785, 101, 0, 40000, 50000, 45000, 60000)]),
    (6, 533, "Naxxramas", (3498.3, -5349.9, 145.0, 1.31), 15990, "Mal'gorath la Liche", 15990, 1.4,
     "Fragment de la Nécropole", 22682,
     [(28783, 100, 0, 12000, 15000, 12000, 18000), (28785, 2, 0, 60000, 80000, 90000, 90000),
      (28796, 1, 0, 8000, 11000, 11000, 11000), (28794, 100, 0, 16000, 18000, 16000, 20000)]),
]
EXTRA_BOSSES = {409: [11502], 469: [11583], 309: [14515, 15114, 15082, 15083, 15084, 15085], 531: [15517, 15727],
                533: [15989]}
SIZE = {309: 20, 509: 20, 409: 40, 249: 40, 469: 40, 531: 40, 533: 40}

# ---------------------------------------------------------------- boss et butin
MAPRAID = {r[1]: r[0] for r in RAIDS}
FINAL = {r[4]: r[0] for r in RAIDS}
bosses = {}
for m, e in q("select c.map, t.Entry from creature c join creature_template t on t.Entry=c.id where c.map in (%s) "
              "and t.Rank=3 and t.LootId>0 group by t.Entry" % ",".join(map(str, MAPRAID))):
    bosses[int(e)] = MAPRAID[int(m)]
for m, lst in EXTRA_BOSSES.items():
    for e in lst:
        bosses[e] = MAPRAID[m]
bosses.pop(12018, None)

ITEM = {int(e): (int(qu), int(cl), int(st)) for e, qu, cl, st in q("select entry, Quality, class, itemset from item_template")}
CLT = defaultdict(list)
for row in q("select entry, item, ChanceOrQuestChance, groupid, mincountOrRef, maxcount, condition_id from creature_loot_template"):
    CLT[int(row[0])].append(row)
RLT = defaultdict(list)
for row in q("select entry, item, ChanceOrQuestChance, groupid, mincountOrRef, maxcount, condition_id from reference_loot_template"):
    RLT[int(row[0])].append(row)
LOOTID = {int(e): int(l) for e, l in q("select Entry, LootId from creature_template where Rank=3")}

def is_pool(item, chance):
    it = ITEM.get(item)
    if not it or float(chance) < 0:
        return False
    qu, cl, st = it
    return 3 <= qu <= 4 and (cl in (2, 4) or st or cl in (12, 15))

def expand(rows, depth=0):
    pool, keep = set(), []
    for row in rows:
        entry, item, chance, grp, mc, mx, cond = row
        mc = int(mc)
        if mc < 0:
            sub, _ = expand(RLT[-mc], depth + 1)
            pool |= sub
            if not sub and depth == 0:
                keep.append(row)
        elif is_pool(int(item), chance) and cond == '0':
            pool.add(int(item))
        elif depth == 0:
            keep.append(row)
    return pool, keep

order = sorted(bosses)
bossdata = []
for n, e in enumerate(order):
    pool, keep = expand(CLT[LOOTID.get(e, e)])
    if not pool:
        continue
    bossdata.append(dict(n=n, entry=e, raid=bosses[e], final=e in FINAL, pool=sorted(pool), keep=keep))
raidpool = defaultdict(set)
for b in bossdata:
    raidpool[b['raid']] |= set(b['pool'])

TPL = {int(r[0]): r for r in q("select Entry, MaxLevel, DisplayId1, MinLootGold, MaxLootGold from creature_template")}

# ---------------------------------------------------------------- SQL
L = []
w = L.append
w("-- Raids à 10 ou 20 joueurs, boss légendaires, fragments (généré)")
w("SET NAMES utf8mb4;")
w("DELETE FROM creature WHERE id BETWEEN %d AND %d;" % (NPC_BASE, NPC_BASE + 9))
w("DELETE FROM creature_template WHERE Entry BETWEEN %d AND %d OR Entry BETWEEN %d AND %d;" % (NPC_BASE, NPC_BASE + 9, LEG_BASE, LEG_BASE + 9))
w("DELETE FROM creature_spell_list WHERE Id BETWEEN %d AND %d;" % (LEG_BASE, LEG_BASE + 9))
w("DELETE FROM creature_spell_list_entry WHERE Id BETWEEN %d AND %d;" % (LEG_BASE, LEG_BASE + 9))
w("DELETE FROM creature_loot_template WHERE entry BETWEEN %d AND %d;" % (LOOT10, RAIDREF + 49))
w("DELETE FROM reference_loot_template WHERE entry BETWEEN %d AND %d;" % (LOOT10, RAIDREF + 49))
w("DELETE FROM item_template WHERE entry BETWEEN %d AND %d;" % (FRAG_BASE, FRAG_BASE + 9))
w("DELETE FROM gossip_menu WHERE entry=%d;" % GOSSIP)
w("DELETE FROM npc_text WHERE ID=%d;" % TEXT)
w("CREATE TABLE IF NOT EXISTS custom_raid_boss (entry INT UNSIGNED NOT NULL PRIMARY KEY, raid INT NOT NULL, "
  "loot10 INT UNSIGNED NOT NULL, loot20 INT UNSIGNED NOT NULL, final TINYINT NOT NULL DEFAULT 0) ENGINE=InnoDB;")
w("DELETE FROM custom_raid_boss;")
w("")
w("-- PNJ d'entrée")
txt = ("Ce raid se fait à 10 ou à 20 joueurs : les ennemis sont ajustés à la taille choisie, et le butin aussi "
       "(boss : 2 objets à 10, 3 à 20 ; boss final et boss légendaire : 3 à 10, 4 à 20).$B$B"
       "Trente secondes après la chute du boss final, un boss légendaire surgit. Il donne à chacun un fragment, "
       "une seule fois par personnage.$B$BLe chef de groupe choisit la taille avant le premier combat ; "
       "par défaut, le raid est à 20 joueurs.")
w("INSERT INTO npc_text (ID, text0_0, text0_1, prob0) VALUES (%d, '%s', '%s', 1);" % (TEXT, esc(txt), esc(txt)))
w("INSERT INTO gossip_menu (entry, text_id, script_id, condition_id) VALUES (%d, %d, 0, 0);" % (GOSSIP, TEXT))
w("DROP TEMPORARY TABLE IF EXISTS tmp_ct;")
w("CREATE TEMPORARY TABLE tmp_ct LIKE creature_template;")
for r in RAIDS:
    idx, mapid, nom = r[0], r[1], r[2]
    w("INSERT INTO tmp_ct SELECT * FROM creature_template WHERE Entry=10667;")
    w("UPDATE tmp_ct SET Entry=%d, Name='Gardien des raids', SubName='%s', DisplayId1=7591, DisplayId2=0, DisplayId3=0, "
      "DisplayId4=0, DisplayIdProbability1=100, DisplayIdProbability2=0, DisplayIdProbability3=0, DisplayIdProbability4=0, "
      "MinLevel=63, MaxLevel=63, Faction=35, NpcFlags=3, GossipMenuId=%d, ScriptName='', AIName='', EquipmentTemplateId=0, "
      "LootId=0, PickpocketLootId=0, SkinningLootId=0, ExperienceMultiplier=1 WHERE Entry=10667;" % (NPC_BASE + idx, esc(nom), GOSSIP))
w("-- Boss légendaires : copie du boss final, PV et dégâts x1,2, sorts des 1er et 2e boss")
for r in RAIDS:
    idx, mapid, nom, pos, final, leg, model, scale, frag, fragmodel, sorts = r
    e = LEG_BASE + idx
    disp = int(TPL[model][2])
    w("INSERT INTO tmp_ct SELECT * FROM creature_template WHERE Entry=%d;" % final)
    w("UPDATE tmp_ct SET Entry=%d, Name='%s', SubName='Boss légendaire', HealthMultiplier=HealthMultiplier*1.2, "
      "DamageMultiplier=DamageMultiplier*1.2, DisplayId1=%d, DisplayId2=0, DisplayId3=0, DisplayId4=0, DisplayIdProbability1=100, "
      "DisplayIdProbability2=0, DisplayIdProbability3=0, DisplayIdProbability4=0, Scale=%.2f, AIName='', ScriptName='', "
      "SpellList=%d, LootId=%d, UnitFlags=0, ExtraFlags=0, StaticFlags1=0, StaticFlags2=0, StaticFlags3=0, StaticFlags4=0, "
      "InhabitType=1, MovementType=0, GossipMenuId=0, NpcFlags=0, MinLootGold=500000, MaxLootGold=800000, "
      "EquipmentTemplateId=0, SpeedWalk=1, SpeedRun=1.14286 WHERE Entry=%d;"
      % (e, esc(leg), disp, scale, e, LEGLOOT10 + idx, final))
w("INSERT INTO creature_template SELECT * FROM tmp_ct;")
w("DROP TEMPORARY TABLE tmp_ct;")
for n, r in enumerate(RAIDS):
    idx, mapid, nom, (x, y, z, o) = r[0], r[1], r[2], r[3]
    nx, ny = x + 5 * math.cos(o), y + 5 * math.sin(o)
    w("INSERT INTO creature (guid, id, map, spawnMask, position_x, position_y, position_z, orientation, spawntimesecsmin, "
      "spawntimesecsmax, spawndist, MovementType) VALUES (%d, %d, %d, 1, %.2f, %.2f, %.2f, %.3f, 300, 300, 0, 0);"
      % (9903000 + idx, NPC_BASE + idx, mapid, nx, ny, z + 0.2, (o + math.pi) % (2 * math.pi)))
w("")
w("-- Listes de sorts des boss légendaires")
for r in RAIDS:
    idx, leg, sorts = r[0], r[5], r[10]
    e = LEG_BASE + idx
    w("INSERT INTO creature_spell_list_entry (Id, Name, ChanceSupportAction, ChanceRangedAttack) VALUES (%d, '%s', 0, 0);"
      % (e, esc('Custom - légendaire - ' + leg)))
    for p, (sid, tgt, fl, imin, imax, rmin, rmax) in enumerate(sorts):
        w("INSERT INTO creature_spell_list (Id, Position, SpellId, Flags, CombatCondition, TargetId, ScriptId, Availability, "
          "Probability, InitialMin, InitialMax, RepeatMin, RepeatMax, Comments) VALUES (%d, %d, %d, %d, -1, %d, 0, 100, 3, %d, %d, %d, %d, '%s');"
          % (e, p, sid, fl, tgt, imin, imax, rmin, rmax, esc('Custom - ' + leg)))
w("")
w("-- Fragments (objets de quête légendaires, un par raid)")
w("DROP TEMPORARY TABLE IF EXISTS tmp_it;")
w("CREATE TEMPORARY TABLE tmp_it LIKE item_template;")
for r in RAIDS:
    idx, nom, frag, fragmodel = r[0], r[2], r[8], r[9]
    w("INSERT INTO tmp_it SELECT * FROM item_template WHERE entry=%d;" % fragmodel)
    w("UPDATE tmp_it SET entry=%d, name='%s', class=12, subclass=0, Quality=5, Flags=0, BuyPrice=0, SellPrice=0, "
      "InventoryType=0, AllowableClass=-1, AllowableRace=-1, ItemLevel=60, RequiredLevel=0, RequiredSkill=0, RequiredSkillRank=0, "
      "maxcount=1, stackable=1, ContainerSlots=0, bonding=4, description='%s', startquest=0, spellid_1=0, spelltrigger_1=0, "
      "spellid_2=0, spellid_3=0, spellid_4=0, spellid_5=0, itemset=0, RandomProperty=0, ScriptName='' WHERE entry=%d;"
      % (FRAG_BASE + idx, esc(frag), esc("Arraché au boss légendaire de %s. Les sept fragments réunis forgent une arme légendaire." % nom), fragmodel))
w("INSERT INTO item_template SELECT * FROM tmp_it;")
w("DROP TEMPORARY TABLE tmp_it;")
w("")
w("-- Butin des boss selon la taille (lot du boss : 2 ou 3 objets, boss final 3 ou 4) ; le reste du butin d'origine est gardé")
for b in bossdata:
    n, e = b['n'], b['entry']
    ref = POOLREF + n
    w("INSERT INTO reference_loot_template (entry, item, ChanceOrQuestChance, groupid, mincountOrRef, maxcount, condition_id, comments) VALUES %s;"
      % ", ".join("(%d, %d, 0, 1, 1, 1, 0, 'Custom raid')" % (ref, it) for it in b['pool']))
    for base, cnt in ((LOOT10, 3 if b['final'] else 2), (LOOT20, 4 if b['final'] else 3)):
        rows = ["(%d, %d, 100, 0, -%d, %d, 0, 'Custom raid')" % (base + n, ref, ref, cnt)]
        for _, item, chance, grp, mc, mx, cond in b['keep']:
            rows.append("(%d, %s, %s, %s, %s, %s, %s, 'Custom raid (origine)')" % (base + n, item, chance, grp, mc, mx, cond))
        w("INSERT INTO creature_loot_template (entry, item, ChanceOrQuestChance, groupid, mincountOrRef, maxcount, condition_id, comments) VALUES %s;"
          % ", ".join(rows))
    w("INSERT INTO custom_raid_boss (entry, raid, loot10, loot20, final) VALUES (%d, %d, %d, %d, %d);"
      % (e, b['raid'], LOOT10 + n, LOOT20 + n, 1 if b['final'] else 0))
w("")
w("-- Boss légendaires : 3 ou 4 objets pris dans tout le butin du raid")
for r in RAIDS:
    idx = r[0]
    ref = RAIDREF + idx
    w("INSERT INTO reference_loot_template (entry, item, ChanceOrQuestChance, groupid, mincountOrRef, maxcount, condition_id, comments) VALUES %s;"
      % ", ".join("(%d, %d, 0, 1, 1, 1, 0, 'Custom raid légendaire')" % (ref, it) for it in sorted(raidpool[idx])))
    for base, cnt in ((LEGLOOT10, 3), (LEGLOOT20, 4)):
        w("INSERT INTO creature_loot_template (entry, item, ChanceOrQuestChance, groupid, mincountOrRef, maxcount, condition_id, comments) "
          "VALUES (%d, %d, 100, 0, -%d, %d, 0, 'Custom raid légendaire');" % (base + idx, ref, ref, cnt))
w("")
w("SELECT 'Raids OK' AS resultat;")
open(OUT + 'raids.sql', 'w', encoding='utf-8').write("\n".join(L) + "\n")
print('boss', len(bossdata), {r[2]: len(raidpool[r[0]]) for r in RAIDS})
missing = [e for e in order if e not in [b['entry'] for b in bossdata]]
print('boss sans lot', missing)
