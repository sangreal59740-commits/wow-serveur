# Mode mythique M0 à M+10 : PNJ des donjons de haut niveau, liste des boss, objets mythiques et butin.
# Sortie : mythique.sql (base world)
import sys, json, math, re, subprocess
from collections import defaultdict
sys.path.insert(0, '/home/claude/wow/fr')
from dbc import DBC

OUT = '/home/claude/wow/donjons/'

def q(sql):
    r = subprocess.run(['mysql', '-N', '-B', 'classicmangos', '-e', sql], capture_output=True, text=True, check=True)
    return [l.split('\t') for l in r.stdout.splitlines()]

def esc(s):
    return s.replace('\\', '\\\\').replace("'", "\\'")

NPC_BASE = 990100
GOSSIP_MYTH, TEXT_MYTH = 60101, 990101
NEW = [  # idx, map, arrivée (x, y, z, o), nom
    (13, 70, (-228.9, 46.1, -46.0, 1.57), "Uldaman"),
    (14, 209, (1212.7, 842.0, 8.9, 6.28), "Zul'Farrak"),
    (15, 349, (1016.8, -458.5, -43.5, 6.28), "Maraudon"),
    (15, 349, (755.1, -617.7, -32.9, 1.57), "Maraudon"),
    (16, 109, (-315.9, 100.2, -131.8, 3.14), "Temple englouti"),
    (17, 230, (456.9, 34.1, -68.1, 4.71), "Profondeurs de Rochenoire"),
    (18, 229, (78.4, -226.8, 49.8, 4.71), "Pic Rochenoire"),
    (19, 429, (47.5, -153.7, -2.7, 5.50), "Hache-Tripes Est"),
    (20, 429, (-65.7, 159.6, -3.5, 2.36), "Hache-Tripes Ouest"),
    (21, 429, (254.9, -19.5, -2.6, 5.50), "Hache-Tripes Nord"),
    (22, 329, (3392.9, -3395.0, 143.1, 1.57), "Stratholme : quartier écarlate"),
    (23, 329, (3590.9, -3643.2, 138.5, 5.50), "Stratholme : quartier mort-vivant"),
    (24, 289, (190.8, 126.3, 137.2, 6.28), "Scholomance"),
]
MAPS = [389, 36, 43, 33, 34, 48, 90, 47, 189, 129, 70, 209, 349, 109, 230, 229, 429, 329, 289]
MYTH_ILVL = [65, 70, 74, 79, 83, 88, 92, 97, 101, 106, 110]
ITEM_BASE, REF_BASE, LOOT_BASE = 996000, 996000, 997000
POOL = 40

# ---------------------------------------------------------------- sorts d'équipement : familles et valeurs (après l'étape 1)
spell = DBC('/home/claude/wow/fr/dbc_en/Spell.dbc')
CH = json.load(open('/home/claude/wow/stats/changes.json'))['spells']
def s32(x): return x - (1 << 32) if x >= 1 << 31 else x
PCT = {'Increased Critical', 'Increased Critical Spell', 'Increased Hit Chance', 'Increased Spell Hit Chance',
       'Increased Dodge', 'Increased Parry', 'Increased Block'}
FLAT = {'Increase Spell Dam', 'Increase Healing', 'Attack Power', 'Attack Power Ranged', 'Increased Mana Regen',
        'Increased Defense', 'Block Value', 'Increase Frost Dam', 'Increase Shadow Dam', 'Increase Fire Dam',
        'Increase Nature Dam', 'Increase Arcane Dam', 'Increased Spell Penetration', 'Increased Armor'}
FAMS = defaultdict(list)    # famille -> [(valeur, id)]
SPFAM = {}                  # id -> (famille, valeur)
for r in spell.rows:
    n = spell.str(r[120])
    fam = re.sub(r'\s*\d+\s*$', '', n)
    if fam not in PCT and fam not in FLAT or not re.search(r'\d\s*$', n):
        continue
    effs = [e for e in range(3) if r[61 + e] == 6]
    if not effs:
        continue
    e = effs[0]
    c = CH.get(str(r[0]))
    v = c[str(e)][1] + 1 if (c and str(e) in c) else s32(r[76 + e]) + (1 if r[64 + e] >= 1 else 0)
    if v > 0:
        FAMS[fam].append((v, r[0]))
        SPFAM[r[0]] = (fam, v)
def pick(fam, target):
    v, i = min(FAMS[fam], key=lambda x: (abs(x[0] - target), x[1]))
    return i, v

# ---------------------------------------------------------------- objets sources
COLS = ("entry, Quality, ItemLevel, class, subclass, InventoryType, armor, block, dmg_min1, dmg_max1, delay, "
        + ", ".join("stat_value%d" % i for i in range(1, 11)) + ", "
        + ", ".join("spellid_%d, spelltrigger_%d" % (i, i) for i in range(1, 6))
        + ", holy_res, fire_res, nature_res, frost_res, shadow_res, arcane_res, AllowableClass")
DROP = ("(i.entry in (select item from creature_loot_template where mincountOrRef>0) "
        "or i.entry in (select item from reference_loot_template where mincountOrRef>0))")
BASE_WHERE = ("i.itemset=0 and i.class in (2,4) and i.InventoryType>0 and i.InventoryType not in (18, 24, 27, 28) "
              "and i.requiredhonorrank=0 and i.RequiredReputationFaction=0 and i.name not like '%Deprecated%' "
              "and i.name not like 'Monster%' and i.name not like '%Test%' and i.entry < 990000 and " + DROP)
def load(where):
    rows = q("select %s from item_template i where %s and %s" % (COLS, BASE_WHERE, where))
    keys = COLS.replace(' ', '').split(',')
    return [dict(zip(keys, [float(x) if '.' in x else int(x) for x in r])) for r in rows]
DUNGEON = load("i.Quality in (3,4) and i.ItemLevel between 55 and 65 and i.RequiredLevel >= 50")
RAID = load("i.Quality=4 and i.ItemLevel >= 66")
print('sources donjon', len(DUNGEON), 'raid', len(RAID))

def sample(src, m, n):
    """n objets variés (type d'objet différent autant que possible), tirage stable par niveau."""
    by = defaultdict(list)
    for it in src:
        by[(it['class'], it['subclass'], it['InventoryType'])].append(it)
    keys = sorted(by)
    out, k = [], 0
    while len(out) < n and k < 50:
        for key in keys:
            lst = sorted(by[key], key=lambda it: (it['entry'] * (m + 7) * 2654435761) % 4294967296)
            if k < len(lst):
                out.append(lst[k])
                if len(out) == n:
                    break
        k += 1
    return out

def budget(q, il):
    return (il - 1.3) / 1.3 if q == 4 else (il - 1.84) / 1.6

# ---------------------------------------------------------------- génération
items = []
for m, T in enumerate(MYTH_ILVL):
    src = DUNGEON if T < 92 else RAID
    for k, it in enumerate(sample(src, m, POOL)):
        S = it['ItemLevel']
        ratio = budget(4, T) / budget(it['Quality'], S)
        wratio = (0.6 * T + 2) / (0.6 * S + 2) * (1.1 if it['Quality'] == 3 else 1.0)
        aratio = T / S * (1.1 if it['Quality'] == 3 else 1.0)
        sets = {}
        for i in range(1, 11):
            if it['stat_value%d' % i]:
                sets['stat_value%d' % i] = max(1, round(it['stat_value%d' % i] * ratio))
        if it['armor']:
            sets['armor'] = min(65535, round(it['armor'] * aratio))
        if it['block']:
            sets['block'] = round(it['block'] * ratio)
        if it['dmg_max1']:
            sets['dmg_min1'] = round(it['dmg_min1'] * wratio)
            sets['dmg_max1'] = round(it['dmg_max1'] * wratio)
        for r_ in ('holy_res', 'fire_res', 'nature_res', 'frost_res', 'shadow_res', 'arcane_res'):
            if it[r_]:
                sets[r_] = min(255, round(it[r_] * ratio))
        # sorts d'équipement : même famille, valeur ajustée (les pourcentages progressent moins vite)
        spells, free = [], []
        for i in range(1, 6):
            sid, trg = it['spellid_%d' % i], it['spelltrigger_%d' % i]
            if sid and trg == 1 and sid in SPFAM:
                fam, v = SPFAM[sid]
                target = v * (math.sqrt(ratio) if fam in PCT else ratio)
                spells.append((i, fam, target))
            elif not sid:
                free.append(i)
        newsp = {}
        for i, fam, target in spells:
            top = max(x[0] for x in FAMS[fam])
            parts = 1
            while target / parts > top * 1.05 and len(free) >= parts:
                parts += 1
            slots = [i] + free[:parts - 1]
            free = free[parts - 1:]
            for sl in slots:
                newsp[sl] = pick(fam, target / len(slots))[0]
        for sl, sid in newsp.items():
            sets['spellid_%d' % sl] = sid
            sets['spelltrigger_%d' % sl] = 1
        items.append(dict(entry=ITEM_BASE + m * 50 + k, src=it['entry'], m=m, ilvl=T, sets=sets))

# boss de donjon : rang élite, beaucoup de PV, une seule apparition (ou script de boss)
bosses = q("select t.Entry from creature_template t join creature c on c.id=t.Entry where c.map in (%s) "
           "and t.Rank>=1 and (t.HealthMultiplier>=4 or t.Rank>=2 or t.ScriptName like 'boss%%') and t.NpcFlags=0 "
           "group by t.Entry having count(*) <= 2" % ",".join(map(str, MAPS)))
bosses = sorted(set(int(b[0]) for b in bosses))

# ---------------------------------------------------------------- SQL
L = []
w = L.append
w("-- Mode mythique M0 à M+10 (généré)")
w("SET NAMES utf8mb4;")
w("DELETE FROM creature WHERE id BETWEEN %d AND %d;" % (NPC_BASE + 13, NPC_BASE + 24))
w("DELETE FROM creature_template WHERE Entry BETWEEN %d AND %d;" % (NPC_BASE + 13, NPC_BASE + 24))
w("DELETE FROM gossip_menu WHERE entry=%d;" % GOSSIP_MYTH)
w("DELETE FROM npc_text WHERE ID=%d;" % TEXT_MYTH)
w("DELETE FROM item_template WHERE entry BETWEEN %d AND %d;" % (ITEM_BASE, ITEM_BASE + 999))
w("DELETE FROM reference_loot_template WHERE entry BETWEEN %d AND %d;" % (REF_BASE, REF_BASE + 99))
w("DELETE FROM creature_loot_template WHERE entry BETWEEN %d AND %d;" % (LOOT_BASE, LOOT_BASE + 199))
w("CREATE TABLE IF NOT EXISTS custom_mythic_boss (entry INT UNSIGNED NOT NULL PRIMARY KEY) ENGINE=InnoDB;")
w("DELETE FROM custom_mythic_boss;")
w("")
w("-- Textes des PNJ")
txt_myth = ("Ce donjon peut être affronté en mode mythique.$B$BTous les ennemis passent au niveau 60, plus nombreux "
            "et plus puissants à chaque niveau, de M0 à M+10. Réussir un niveau (boss final vaincu) débloque le suivant. "
            "Les boss y laissent des objets mythiques.$B$BChoisissez avant d'engager le combat : le mode est verrouillé "
            "dès le premier ennemi abattu.")
w("INSERT INTO npc_text (ID, text0_0, text0_1, prob0) VALUES (%d, '%s', '%s', 1);" % (TEXT_MYTH, esc(txt_myth), esc(txt_myth)))
w("INSERT INTO gossip_menu (entry, text_id, script_id, condition_id) VALUES (%d, %d, 0, 0);" % (GOSSIP_MYTH, TEXT_MYTH))
txt = ("Ce donjon peut être affronté dans une version bien plus redoutable.$B$B"
       "Mode niveau 40 : ennemis niveau 40, boss niveau 41. Mode niveau 50 : ennemis niveau 50, boss niveau 51.$B"
       "Mode mythique M0 à M+10 : ennemis niveau 60, plus nombreux et plus puissants ; réussir un niveau débloque le suivant.$B$B"
       "Choisissez avant d'engager le combat : le mode est verrouillé dès le premier ennemi abattu.")
w("UPDATE npc_text SET text0_0='%s', text0_1='%s' WHERE ID=990100;" % (esc(txt), esc(txt)))
w("")
w("-- PNJ des donjons de haut niveau (copie du Gardien des épreuves)")
w("DROP TEMPORARY TABLE IF EXISTS tmp_ct;")
w("CREATE TEMPORARY TABLE tmp_ct LIKE creature_template;")
done = set()
for idx, mapid, pos, nom in NEW:
    if idx in done:
        continue
    done.add(idx)
    w("INSERT INTO tmp_ct SELECT * FROM creature_template WHERE Entry=10667;")
    w("UPDATE tmp_ct SET Entry=%d, Name='Gardien des épreuves', SubName='%s', DisplayId1=7591, DisplayId2=0, DisplayId3=0, "
      "DisplayId4=0, DisplayIdProbability1=100, DisplayIdProbability2=0, DisplayIdProbability3=0, DisplayIdProbability4=0, "
      "MinLevel=60, MaxLevel=60, Faction=35, NpcFlags=3, GossipMenuId=%d, ScriptName='', AIName='', EquipmentTemplateId=0, "
      "LootId=0, PickpocketLootId=0, SkinningLootId=0, ExperienceMultiplier=1 WHERE Entry=10667;"
      % (NPC_BASE + idx, esc(nom), GOSSIP_MYTH))
w("INSERT INTO creature_template SELECT * FROM tmp_ct;")
w("DROP TEMPORARY TABLE tmp_ct;")
for n, (idx, mapid, (x, y, z, o), nom) in enumerate(NEW):
    nx, ny = x + 5 * math.cos(o), y + 5 * math.sin(o)
    w("INSERT INTO creature (guid, id, map, spawnMask, position_x, position_y, position_z, orientation, spawntimesecsmin, "
      "spawntimesecsmax, spawndist, MovementType) VALUES (%d, %d, %d, 1, %.2f, %.2f, %.2f, %.3f, 300, 300, 0, 0);"
      % (9901013 + n, NPC_BASE + idx, mapid, nx, ny, z + 0.2, (o + math.pi) % (2 * math.pi)))
w("")
w("-- Boss de donjon (butin mythique)")
w("INSERT INTO custom_mythic_boss (entry) VALUES %s;" % ", ".join("(%d)" % b for b in bosses))
w("")
w("-- Objets mythiques : objets hors set existants, ilvl et stats ajustés au niveau M (objets de raid à partir de l'ilvl 92)")
w("DROP TEMPORARY TABLE IF EXISTS tmp_it;")
w("CREATE TEMPORARY TABLE tmp_it LIKE item_template;")
for it in items:
    w("INSERT INTO tmp_it SELECT * FROM item_template WHERE entry=%d;" % it['src'])
    s = ["entry=%d" % it['entry'], "name=CONCAT(name, ' mythique')", "Quality=4", "ItemLevel=%d" % it['ilvl'],
         "RequiredLevel=60", "bonding=1", "RandomProperty=0", "SellPrice=%d" % (it['ilvl'] ** 2 * 6),
         "BuyPrice=%d" % (it['ilvl'] ** 2 * 24)] + ["%s=%d" % kv for kv in it['sets'].items()]
    w("UPDATE tmp_it SET %s WHERE entry=%d;" % (", ".join(s), it['src']))
w("INSERT INTO item_template SELECT * FROM tmp_it;")
w("DROP TEMPORARY TABLE tmp_it;")
w("")
w("-- Butin : pool par niveau M, 2 objets par boss, 3 pour le boss final")
for m in range(len(MYTH_ILVL)):
    lst = [it['entry'] for it in items if it['m'] == m]
    w("INSERT INTO reference_loot_template (entry, item, ChanceOrQuestChance, groupid, mincountOrRef, maxcount, condition_id, comments) VALUES %s;"
      % ", ".join("(%d, %d, 0, 1, 1, 1, 0, 'Custom mythique')" % (REF_BASE + m, e) for e in lst))
    for off, n in ((0, 2), (100, 3)):
        w("INSERT INTO creature_loot_template (entry, item, ChanceOrQuestChance, groupid, mincountOrRef, maxcount, condition_id, comments) "
          "VALUES (%d, %d, 100, 0, -%d, %d, 0, 'Custom mythique');" % (LOOT_BASE + off + m, REF_BASE + m, REF_BASE + m, n))
w("")
w("SELECT 'Mythique OK' AS resultat;")
open(OUT + 'mythique.sql', 'w', encoding='utf-8').write("\n".join(L) + "\n")
print('objets', len(items), 'boss', len(bosses))
