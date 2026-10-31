# Génère le SQL des modes de donjon 40 / 50 : PNJ, quêtes, crédits, objets épiques, sets.
# Sortie : donjons.sql (base world) + itemsets.json (lignes à ajouter à ItemSet.dbc)
import sys, json, math, subprocess
sys.path.insert(0, '/home/claude/wow/fr')
from dbc import DBC

OUT = '/home/claude/wow/donjons/'

def q(sql):
    r = subprocess.run(['mysql', '-N', '-B', 'classicmangos', '-e', sql], capture_output=True, text=True, check=True)
    return [l.split('\t') for l in r.stdout.splitlines()]

def esc(s):
    return s.replace('\\', '\\\\').replace("'", "\\'")

# ---------------------------------------------------------------- sorts d'équipement (valeurs après l'étape 1)
spell = DBC('/home/claude/wow/fr/dbc_en/Spell.dbc')
CH = json.load(open('/home/claude/wow/stats/changes.json'))['spells']
def s32(x): return x - (1 << 32) if x >= 1 << 31 else x
SP = {}   # famille -> [(valeur, id)]
FAM = {'sp': 'Increase Spell Dam ', 'heal': 'Increase Healing ', 'ap': 'Attack Power ',
       'crit': 'Increased Critical ', 'hit': 'Increased Hit Chance ', 'scrit': 'Increased Critical Spell',
       'sta': 'Increased Stamina ', 'int': 'Increased Intellect ', 'spi': 'Increased Spirit ',
       'str': 'Increased Strength ', 'agi': 'Increased Agility '}
for r in spell.rows:
    n = spell.str(r[120])
    for k, pre in FAM.items():
        if not n.startswith(pre):
            continue
        if k == 'crit' and n.startswith('Increased Critical Spell'):
            continue
        effs = [e for e in range(3) if r[61 + e] == 6]
        if not effs:
            continue
        e = effs[0]
        c = CH.get(str(r[0]))
        if c and str(e) in c:
            v = c[str(e)][1] + 1
        else:
            v = s32(r[76 + e]) + (1 if r[64 + e] >= 1 else 0)
        if v > 0:
            SP.setdefault(k, []).append((v, r[0]))
def pick(fam, target):
    lst = SP[fam]
    v, i = min(lst, key=lambda x: (abs(x[0] - target), x[1]))
    return i, v

# ---------------------------------------------------------------- données des donjons
#  idx, map, zone, entrée (x,y,z,o), boss, nom du boss FR, donjon FR, emplacement récompensé
DONJONS = [
    (0, 389, 2437, (0.8, -8.2, -15.5, 4.71), 11520, "Taragaman l'Affameur", "Gouffre de Ragefeu", 'neck'),
    (1, 36, 1581, (-14.6, -385.5, 62.5, 1.57), 639, "Edwin VanCleef", "Les Mortemines", 'hands'),
    (2, 43, 718, (-158.4, 131.6, -74.3, 5.85), 3654, "Mutanus le Dévoreur", "Cavernes des Lamentations", 'wrist'),
    (3, 33, 209, (-228.2, 2111.4, 76.9, 1.22), 4275, "Archimage Arugal", "Donjon d'Ombrecroc", 'waist'),
    (4, 34, 717, (49.0, 0.5, -16.4, 6.28), 1716, "Bazil Thredd", "La Prison", 'ring'),
    (5, 48, 719, (-150.2, 106.6, -39.8, 4.45), 4829, "Aku'mai", "Profondeurs de Brassenoire", 'feet'),
    (6, 90, 721, (-329.1, -3.2, -152.9, 2.97), 7800, "Mekgénieur Thermojoncteur", "Gnomeregan", 'shoulder'),
    (7, 47, 491, (1942.3, 1544.2, 83.3, 1.31), 4421, "Charlga Trancheflanc", "Kraal de Tranchebauge", 'legs'),
    (8, 189, 796, (1687.3, 1050.1, 18.7, 1.57), 4543, "Mage de sang Thalnos", "Monastère : Cimetière", 'cloak'),
    (9, 189, 796, (253.7, -206.6, 18.7, 4.71), 6487, "Arcaniste Doan", "Monastère : Bibliothèque", 'trinket'),
    (10, 189, 796, (1608.1, -318.9, 18.7, 4.71), 3975, "Hérode", "Monastère : Armurerie", 'weapon'),
    (11, 189, 796, (853.2, 1319.2, 18.7, 1.57), 3977, "Haute inquisitrice Blanchetête", "Monastère : Cathédrale", 'chest'),
    (12, 129, 722, (2593.7, 1111.2, 51.0, 4.71), 7358, "Amnennar le Porte-froid", "Souilles de Tranchebauge", 'head'),
]

NPC_BASE, CREDIT_BASE, QUEST_BASE, GOSSIP_MENU, NPC_TEXT = 990100, 990200, 990300, 60100, 990100
ITEM_BASE = {40: 991000, 50: 991200}
ITEMSET_BASE = 552

# ---------------------------------------------------------------- objets
SLOTS = ['head', 'shoulder', 'chest', 'waist', 'legs', 'feet', 'wrist', 'hands']
INVTYPE = {'head': 1, 'shoulder': 3, 'chest': (5, 20), 'waist': 6, 'legs': 7, 'feet': 8, 'wrist': 9, 'hands': 10}
SLOTMOD = {'head': 1.0, 'shoulder': 0.77, 'chest': 1.0, 'waist': 0.77, 'legs': 1.0, 'feet': 0.77, 'wrist': 0.56,
           'hands': 0.77, 'neck': 0.56, 'ring': 0.56, 'cloak': 0.56, 'trinket': 0.7}
# variantes : (clé, nom du rôle, sous-classe d'armure, set source 40, set source 50, répartition)
VARIANTS = [
    ('sorts', 'Tissu (sorts)', 1, 183, 518, {'int': .40, 'sta': .25, 'spi': .10, 'sp': .25}),
    ('soins', 'Tissu (soins)', 1, 182, 514, {'int': .35, 'spi': .20, 'sta': .20, 'heal': .25}),
    ('cuir', 'Cuir (agilité)', 2, 184, 512, {'agi': .45, 'sta': .30, 'str': .10, 'ap': .15}),
    ('mailleagi', 'Maille (agilité)', 3, 186, 515, {'agi': .40, 'sta': .30, 'int': .15, 'ap': .15}),
    ('mailleint', 'Maille (intelligence)', 3, 187, 519, {'int': .35, 'sta': .30, 'str': .10, 'sp': .25}),
    ('plaques', 'Plaques (force)', 4, 189, 511, {'str': .45, 'sta': .35, 'agi': .20}),
]
SETNAMES = {
    40: ["Atours du Sombre-savoir", "Vêtements de l'Aube claire", "Armure de Crocsombre",
         "Harnais de la Traque", "Tenue du Tonnerre", "Plates du Rempart"],
    50: ["Atours de l'Abîme", "Vêtements de la Lumière sereine", "Armure du Silence",
         "Harnais du Prédateur", "Tenue de l'Ouragan", "Plates de la Citadelle"],
}
def suffix(setname):
    # "Atours du Sombre-savoir" -> "du Sombre-savoir"
    return setname.split(' ', 1)[1]
NOUNS = {
    1: {'head': 'Capuche', 'shoulder': 'Mantelet', 'chest': 'Robe', 'waist': 'Ceinture', 'legs': 'Jambières',
        'feet': 'Sandales', 'wrist': 'Brassards', 'hands': 'Gants'},
    2: {'head': 'Coiffe', 'shoulder': 'Épaulières', 'chest': 'Tunique', 'waist': 'Ceinturon', 'legs': 'Pantalon',
        'feet': 'Bottes', 'wrist': 'Brassards', 'hands': 'Gants'},
    3: {'head': 'Camail', 'shoulder': 'Spallières', 'chest': 'Haubert', 'waist': 'Ceinture', 'legs': 'Jambières',
        'feet': 'Bottes', 'wrist': 'Manchettes', 'hands': 'Gantelets'},
    4: {'head': 'Heaume', 'shoulder': 'Épaulières', 'chest': 'Cuirasse', 'waist': 'Ceinture', 'legs': 'Cuissards',
        'feet': 'Solerets', 'wrist': 'Brassards', 'hands': 'Gantelets'},
}
OFFNOUN = {'neck': 'Pendentif', 'ring': 'Anneau', 'cloak': 'Cape', 'trinket': 'Talisman'}
WEAPONS = {  # variante -> (nom, classe, sous-classe, invtype, vitesse ms, type dps, slotmod stats)
    'sorts': ('Bâton', 2, 10, 17, 3000, '2h', 1.0),
    'soins': ('Masse', 2, 4, 21, 2600, '1h', 0.6),
    'cuir': ('Dague', 2, 15, 13, 1800, '1h', 0.42),
    'mailleagi': ('Arc', 2, 2, 15, 2800, 'bow', 0.3),
    'mailleint': ('Marteau', 2, 4, 21, 2400, '1h', 0.6),
    'plaques': ('Grande épée', 2, 8, 17, 3500, '2h', 0.8),
}
STATID = {'agi': 3, 'str': 4, 'int': 5, 'spi': 6, 'sta': 7}
COST = {'sp': 0.86, 'heal': 0.45, 'ap': 0.5}

def budget(ilvl, slotmod):
    return (ilvl - 1.3) / 1.3 * slotmod * 1.25

def make_stats(ilvl, slotmod, dist):
    P = budget(ilvl, slotmod)
    stats, bonus = {}, {}
    for k, f in dist.items():
        if k in STATID:
            stats[k] = max(1, round(P * f * 1.5))
        else:
            bonus[k] = P * f / COST[k] * 1.5
    return stats, bonus

def dps(kind, ilvl):
    return {'1h': 0.62 * ilvl + 6, '2h': 0.8 * ilvl + 8, 'bow': 0.45 * ilvl + 7.5}[kind]

# objets sources (apparence, matériau, durabilité...)
setrows = {}
for sid in set(v[3] for v in VARIANTS) | set(v[4] for v in VARIANTS):
    for e, it, il, armor in q("select entry, InventoryType, ItemLevel, armor from bak_q1_item_template where itemset=%d" % sid):
        setrows[(sid, int(it))] = (int(e), int(il), int(armor))
def setsource(sid, slot):
    it = INVTYPE[slot]
    for t in (it if isinstance(it, tuple) else (it,)):
        if (sid, t) in setrows:
            return setrows[(sid, t)]
    raise KeyError((sid, slot))

def candidates(where, n):
    return [(int(a), int(b), int(c)) for a, b, c in q(
        "select entry, ItemLevel, armor from bak_q1_item_template where %s and name not like '%%Monster%%' "
        "and name not like '%%DEPRECATED%%' and name not like '%%Test%%' and name not like '%%OLD%%' order by Quality desc, ItemLevel limit %d" % (where, n))]
OFFSRC = {
    'neck': candidates("class=4 and InventoryType=2 and Quality in (3,4) and ItemLevel between 45 and 65", 12),
    'ring': candidates("class=4 and InventoryType=11 and Quality in (3,4) and ItemLevel between 45 and 65", 12),
    'cloak': candidates("class=4 and InventoryType=16 and Quality in (3,4) and ItemLevel between 45 and 65", 12),
    'trinket': candidates("class=4 and InventoryType=12 and Quality in (3,4) and ItemLevel between 45 and 65 and spellid_1>0", 12),
}
WSRC = {}
for key, (nom, cl, sc, it, spd, kind, sm) in WEAPONS.items():
    WSRC[key] = candidates("class=%d and subclass=%d and InventoryType=%d and Quality=4 and ItemLevel between 40 and 70" % (cl, sc, it), 2)
    if len(WSRC[key]) < 2:
        WSRC[key] += candidates("class=%d and subclass=%d and InventoryType=%d and Quality=3 and ItemLevel between 45 and 65" % (cl, sc, it), 2 - len(WSRC[key]))

items = []      # dict par objet
itemsets = []   # lignes ItemSet.dbc
for lvl in (40, 50):
    ilvl, req = (50, 40) if lvl == 40 else (60, 50)
    base = ITEM_BASE[lvl]
    for v, (key, role, armorsub, src40, src50, dist) in enumerate(VARIANTS):
        sid = src40 if lvl == 40 else src50
        setname = SETNAMES[lvl][v]
        setid = ITEMSET_BASE + (0 if lvl == 40 else 6) + v
        setitems = []
        for s, slot in enumerate(SLOTS):
            srcentry, srcil, srcarmor = setsource(sid, slot)
            stats, bonus = make_stats(ilvl, SLOTMOD[slot], dist)
            entry = base + v * 8 + s
            items.append(dict(entry=entry, src=srcentry, name="%s %s" % (NOUNS[armorsub][slot], suffix(setname)),
                              ilvl=ilvl, req=req, stats=stats, bonus=bonus, itemset=setid,
                              armor=round(srcarmor * ilvl / srcil * 1.08 * 1.5)))
            setitems.append(entry)
        # bonus de set : 2 endurance / 3 rôle A / 4 caractéristique principale / 5 rôle B
        k = 1.0 if lvl == 40 else 1.3
        main = max((x for x in dist if x in STATID and x != 'sta'), key=lambda x: dist[x])
        roleA = {'sorts': ('sp', 12), 'soins': ('heal', 22), 'cuir': ('ap', 24), 'mailleagi': ('ap', 24),
                 'mailleint': ('sp', 10), 'plaques': ('ap', 24)}[key]
        roleB = {'sorts': ('scrit', 1), 'soins': ('spi', 10), 'cuir': ('crit', 1), 'mailleagi': ('hit', 1),
                 'mailleint': ('int', 10), 'plaques': ('hit', 1)}[key]
        def tgt(fam, val):
            if fam in ('crit', 'hit', 'scrit'):
                return pick(fam, 2)[0]       # +1 % devenu +2 % avec l'étape 1
            return pick(fam, val * k * 1.5)[0]
        spells = [tgt('sta', 8), tgt(*roleA), tgt(main, 8), tgt(*roleB)]
        itemsets.append(dict(id=setid, name=setname, items=setitems, spells=spells, thresholds=[2, 3, 4, 5]))
    # hors set : collier, anneau, cape, bijou, arme
    for o, slot in enumerate(['neck', 'ring', 'cloak', 'trinket', 'weapon']):
        for v, (key, role, armorsub, src40, src50, dist) in enumerate(VARIANTS):
            entry = base + 50 + o * 6 + v
            sx = suffix(SETNAMES[lvl][v])
            if slot == 'weapon':
                nom, cl, sc, it, spd, kind, sm = WEAPONS[key]
                src = WSRC[key][0 if lvl == 40 else min(1, len(WSRC[key]) - 1)][0]
                stats, bonus = make_stats(ilvl, sm, dist)
                d = dps(kind, ilvl) * 1.5
                avg = d * spd / 1000
                items.append(dict(entry=entry, src=src, name="%s %s" % (nom, sx), ilvl=ilvl, req=req, stats=stats,
                                  bonus=bonus, itemset=0, armor=0, weapon=(round(avg * 0.75), round(avg * 1.25), spd, kind)))
            else:
                cands = OFFSRC[slot]
                srcentry, srcil, srcarmor = cands[(v + (0 if lvl == 40 else 6)) % len(cands)]
                stats, bonus = make_stats(ilvl, SLOTMOD[slot], dist)
                armor = round(srcarmor * ilvl / max(srcil, 1) * 1.08 * 1.5) if slot == 'cloak' else 0
                items.append(dict(entry=entry, src=srcentry, name="%s %s" % (OFFNOUN[slot], sx), ilvl=ilvl, req=req,
                                  stats=stats, bonus=bonus, itemset=0, armor=armor))

# ---------------------------------------------------------------- SQL
L = []
w = L.append
w("-- Modes de donjon niveau 40 / 50 : PNJ, quêtes, crédits, objets épiques (généré)")
w("SET NAMES utf8mb4;")
w("DELETE FROM creature WHERE id BETWEEN %d AND %d;" % (NPC_BASE, NPC_BASE + 12))
w("DELETE FROM creature_template WHERE Entry BETWEEN %d AND %d;" % (NPC_BASE, CREDIT_BASE + 25))
w("DELETE FROM creature_questrelation WHERE id BETWEEN %d AND %d;" % (NPC_BASE, NPC_BASE + 12))
w("DELETE FROM creature_involvedrelation WHERE id BETWEEN %d AND %d;" % (NPC_BASE, NPC_BASE + 12))
w("DELETE FROM quest_template WHERE entry BETWEEN %d AND %d;" % (QUEST_BASE, QUEST_BASE + 25))
w("DELETE FROM item_template WHERE entry BETWEEN 991000 AND 991399;")
w("DELETE FROM gossip_menu WHERE entry=%d;" % GOSSIP_MENU)
w("DELETE FROM npc_text WHERE ID=%d;" % NPC_TEXT)
w("")
w("-- Texte du PNJ")
txt = ("Ce donjon peut être affronté dans une version bien plus redoutable.$B$B"
       "Choisissez le mode avant d'engager le combat : une fois le premier ennemi abattu, il est verrouillé jusqu'à la "
       "réinitialisation du donjon.$B$BMode niveau 40 : ennemis niveau 40, boss niveau 41.$B"
       "Mode niveau 50 : ennemis niveau 50, boss niveau 51.")
w("INSERT INTO npc_text (ID, text0_0, text0_1, prob0) VALUES (%d, '%s', '%s', 1);" % (NPC_TEXT, esc(txt), esc(txt)))
w("INSERT INTO gossip_menu (entry, text_id, script_id, condition_id) VALUES (%d, %d, 0, 0);" % (GOSSIP_MENU, NPC_TEXT))
w("")
w("-- PNJ (un par donjon, copie de Chromie, apparence d'archimage)")
w("DROP TEMPORARY TABLE IF EXISTS tmp_ct;")
w("CREATE TEMPORARY TABLE tmp_ct LIKE creature_template;")
for d in DONJONS:
    idx = d[0]
    e = NPC_BASE + idx
    w("INSERT INTO tmp_ct SELECT * FROM creature_template WHERE Entry=10667;")
    w("UPDATE tmp_ct SET Entry=%d, Name='Gardien des épreuves', SubName='%s', DisplayId1=7591, DisplayId2=0, DisplayId3=0, "
      "DisplayId4=0, DisplayIdProbability1=100, DisplayIdProbability2=0, DisplayIdProbability3=0, DisplayIdProbability4=0, "
      "MinLevel=60, MaxLevel=60, Faction=35, NpcFlags=3, GossipMenuId=%d, ScriptName='', AIName='', EquipmentTemplateId=0, "
      "LootId=0, PickpocketLootId=0, SkinningLootId=0, ExperienceMultiplier=1 WHERE Entry=10667;"
      % (e, esc(d[6]), GOSSIP_MENU))
w("-- Entrées de crédit (boss final vaincu dans un mode)")
for d in DONJONS:
    idx = d[0]
    for m, lv in enumerate((40, 50)):
        e = CREDIT_BASE + idx * 2 + m
        w("INSERT INTO tmp_ct SELECT * FROM creature_template WHERE Entry=10667;")
        w("UPDATE tmp_ct SET Entry=%d, Name='%s vaincu (mode %d)', SubName='', NpcFlags=0, GossipMenuId=0, ScriptName='', "
          "AIName='', LootId=0 WHERE Entry=10667;" % (e, esc(d[5]), lv))
w("INSERT INTO creature_template SELECT * FROM tmp_ct;")
w("DROP TEMPORARY TABLE tmp_ct;")
w("")
w("-- Placement : 5 m devant l'arrivée dans l'instance, tourné vers les joueurs")
for d in DONJONS:
    idx, mapid = d[0], d[1]
    x, y, z, o = d[3]
    nx, ny = x + 5 * math.cos(o), y + 5 * math.sin(o)
    no = (o + math.pi) % (2 * math.pi)
    w("INSERT INTO creature (guid, id, map, spawnMask, position_x, position_y, position_z, orientation, spawntimesecsmin, "
      "spawntimesecsmax, spawndist, MovementType) VALUES (%d, %d, %d, 1, %.2f, %.2f, %.2f, %.3f, 300, 300, 0, 0);"
      % (9901000 + idx, NPC_BASE + idx, mapid, nx, ny, z + 0.2, no))
w("")
w("-- Objets épiques (stats déjà +50 %, comme le reste du monde)")
w("DROP TEMPORARY TABLE IF EXISTS tmp_it;")
w("CREATE TEMPORARY TABLE tmp_it LIKE item_template;")
for it in items:
    w("INSERT INTO tmp_it SELECT * FROM item_template WHERE entry=%d;" % it['src'])
    sets = ["entry=%d" % it['entry'], "name='%s'" % esc(it['name']), "Quality=4", "Flags=0", "ItemLevel=%d" % it['ilvl'],
            "RequiredLevel=%d" % it['req'], "AllowableClass=-1", "AllowableRace=-1", "RequiredSkill=0",
            "RequiredSkillRank=0", "requiredspell=0", "requiredhonorrank=0", "RequiredCityRank=0",
            "RequiredReputationFaction=0", "RequiredReputationRank=0", "maxcount=0", "stackable=1", "bonding=1",
            "description=''", "PageText=0", "startquest=0", "lockid=0", "RandomProperty=0", "itemset=%d" % it['itemset'],
            "area=0", "Map=0", "ScriptName=''", "holy_res=0", "fire_res=0", "nature_res=0", "frost_res=0",
            "shadow_res=0", "arcane_res=0", "SellPrice=%d" % (it['ilvl'] ** 2 * 6), "BuyPrice=%d" % (it['ilvl'] ** 2 * 24)]
    st = list(it['stats'].items())
    for n in range(10):
        if n < len(st):
            sets += ["stat_type%d=%d" % (n + 1, STATID[st[n][0]]), "stat_value%d=%d" % (n + 1, st[n][1])]
        else:
            sets += ["stat_type%d=0" % (n + 1), "stat_value%d=0" % (n + 1)]
    if 'weapon' in it:
        mn, mx, spd, kind = it['weapon']
        sets += ["dmg_min1=%d" % mn, "dmg_max1=%d" % mx, "dmg_type1=0", "delay=%d" % spd, "armor=0"]
    else:
        sets += ["armor=%d" % it['armor']]
    for n in range(2, 6):
        sets += ["dmg_min%d=0" % n, "dmg_max%d=0" % n]
    spells = []
    for fam, val in it['bonus'].items():
        spells.append(pick(fam, val)[0])
    for n in range(5):
        sid = spells[n] if n < len(spells) else 0
        sets += ["spellid_%d=%d" % (n + 1, sid), "spelltrigger_%d=%d" % (n + 1, 1 if sid else 0),
                 "spellcharges_%d=0" % (n + 1), "spellcooldown_%d=-1" % (n + 1), "spellcategory_%d=0" % (n + 1),
                 "spellcategorycooldown_%d=-1" % (n + 1)]
    w("UPDATE tmp_it SET %s WHERE entry=%d;" % (", ".join(sets), it['src']))
w("INSERT INTO item_template SELECT * FROM tmp_it;")
w("DROP TEMPORARY TABLE tmp_it;")
w("")
w("-- Quêtes : tuer le boss final en mode 40 / 50 (une fois par personnage), récompense au choix (6 variantes)")
SLOTIDX = {s: i for i, s in enumerate(SLOTS)}
OFFIDX = {'neck': 0, 'ring': 1, 'cloak': 2, 'trinket': 3, 'weapon': 4}
for d in DONJONS:
    idx, mapid, zone, pos, boss, bossfr, nomfr, slot = d
    for m, lv in enumerate((40, 50)):
        qid = QUEST_BASE + idx * 2 + m
        base = ITEM_BASE[lv]
        if slot in SLOTIDX:
            rewards = [base + v * 8 + SLOTIDX[slot] for v in range(6)]
        else:
            rewards = [base + 50 + OFFIDX[slot] * 6 + v for v in range(6)]
        title = "%s : l'épreuve du niveau %d" % (nomfr, lv)
        details = ("Ce lieu peut révéler une puissance bien plus grande. Parlez-moi pour activer le mode niveau %d, "
                   "puis abattez %s. Seuls les plus aguerris en reviendront.$B$BRapportez-moi la preuve de votre victoire "
                   "et vous choisirez une pièce d'équipement épique adaptée à votre armure." % (lv, bossfr))
        objectives = "Vaincre %s en mode niveau %d." % (bossfr, lv)
        offer = "Vous l'avez fait. Votre réputation va vous précéder, $N. Choisissez votre récompense."
        req_txt = "Le mode niveau %d vous attend, $N." % lv
        qlevel, minlevel = (41, 38) if lv == 40 else (51, 48)
        rmm, money = (3600, 15000) if lv == 40 else (6600, 30000)
        cols = ("entry, Method, ZoneOrSort, MinLevel, QuestLevel, Type, SuggestedPlayers, QuestFlags, Title, Details, "
                "Objectives, OfferRewardText, RequestItemsText, EndText, ObjectiveText1, ReqCreatureOrGOId1, "
                "ReqCreatureOrGOCount1, RewChoiceItemId1, RewChoiceItemId2, RewChoiceItemId3, RewChoiceItemId4, "
                "RewChoiceItemId5, RewChoiceItemId6, RewChoiceItemCount1, RewChoiceItemCount2, RewChoiceItemCount3, "
                "RewChoiceItemCount4, RewChoiceItemCount5, RewChoiceItemCount6, RewOrReqMoney, RewMoneyMaxLevel")
        vals = [str(qid), '2', str(zone), str(minlevel), str(qlevel), '81', '5', '8', "'%s'" % esc(title),
                "'%s'" % esc(details), "'%s'" % esc(objectives), "'%s'" % esc(offer), "'%s'" % esc(req_txt), "''",
                "'%s'" % esc("%s vaincu (mode %d)" % (bossfr, lv)), str(CREDIT_BASE + idx * 2 + m), '1'] + \
               [str(r) for r in rewards] + ['1'] * 6 + [str(money), str(rmm)]
        w("INSERT INTO quest_template (%s) VALUES (%s);" % (cols, ", ".join(vals)))
        w("INSERT INTO creature_questrelation (id, quest) VALUES (%d, %d);" % (NPC_BASE + idx, qid))
        w("INSERT INTO creature_involvedrelation (id, quest) VALUES (%d, %d);" % (NPC_BASE + idx, qid))
w("")
w("SELECT 'Donjons 40/50 OK' AS resultat;")
open(OUT + 'donjons.sql', 'w', encoding='utf-8').write("\n".join(L) + "\n")
json.dump(itemsets, open(OUT + 'itemsets.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
json.dump(items, open(OUT + 'items.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('objets', len(items), 'sets', len(itemsets))
