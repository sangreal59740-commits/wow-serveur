# Armes légendaires (ilvl 120) : 7 fragments -> quête de l'Esprit des Sept (Hurlevent, Orgrimmar), 15 choix.
# Sorties : legendaires.sql (base world) + legendaires_rows.json (lignes Spell.dbc / SpellItemEnchantment.dbc)
import sys, json, math, subprocess
sys.path.insert(0, '/home/claude/wow/fr')
from dbc import DBC

OUT = '/home/claude/wow/donjons/'

def q(sql):
    r = subprocess.run(['mysql', '-N', '-B', 'classicmangos', '-e', sql], capture_output=True, text=True, check=True)
    return [l.split('\t') for l in r.stdout.splitlines()]

def esc(s):
    return s.replace('\\', '\\\\').replace("'", "\\'")

spell = DBC('/home/claude/wow/fr/dbc_en/Spell.dbc')
SPR = {r[0]: r for r in spell.rows}
ench = DBC('/home/claude/wow/fr/dbc_en/SpellItemEnchantment.dbc')

# familles de sorts d'équipement (mêmes valeurs que les autres générateurs)
CH = json.load(open('/home/claude/wow/stats/changes.json'))['spells']
def s32(x): return x - (1 << 32) if x >= 1 << 31 else x
SP = {}
FAM = {'sp': 'Increase Spell Dam ', 'heal': 'Increase Healing ', 'ap': 'Attack Power ', 'crit': 'Increased Critical ',
       'hit': 'Increased Hit Chance '}
for r in spell.rows:
    n = spell.str(r[120])
    for k, pre in FAM.items():
        if not n.startswith(pre) or (k == 'crit' and n.startswith('Increased Critical Spell')):
            continue
        if k == 'ap' and 'Ranged' in n:
            continue
        effs = [e for e in range(3) if r[61 + e] == 6]
        if not effs:
            continue
        e = effs[0]
        c = CH.get(str(r[0]))
        v = c[str(e)][1] + 1 if (c and str(e) in c) else s32(r[76 + e]) + (1 if r[64 + e] >= 1 else 0)
        if v > 0:
            SP.setdefault(k, []).append((v, r[0]))
def pick_split(fam, target, slots):
    """1 ou 2 sorts pour atteindre la valeur (les plus gros sorts vanilla plafonnent)."""
    top = max(v for v, _ in SP[fam])
    n = 1 if target <= top * 1.05 or slots < 2 else 2
    return [min(SP[fam], key=lambda x: (abs(x[0] - target / n), x[1]))[1] for _ in range(n)]

NPC_SW, NPC_ORG = 990160, 990161
QUEST1, QUEST2 = 999200, 999201
HEART = 999150
ITEM_BASE, BOX_BASE = 999100, 999130
SPELL_BASE, ENCH_BASE = 61000, 3100
FRAG = [999000 + i for i in range(7)]

# ---------------------------------------------------------------- sorts
#   champs : nom côté serveur -> colonne Spell.dbc
COL = dict(School=1, CastingTimeIndex=18, ProcFlags=24, ProcChance=25, ProcCharges=26, DurationIndex=30, ManaCost=32,
           StackAmount=39, SpellFamilyName=160)
for i in range(3):
    n = i + 1
    COL.update({'Effect%d' % n: 61 + i, 'EffectDieSides%d' % n: 64 + i, 'EffectBasePoints%d' % n: 76 + i,
                'EffectImplicitTargetA%d' % n: 82 + i, 'EffectImplicitTargetB%d' % n: 85 + i,
                'EffectRadiusIndex%d' % n: 88 + i, 'EffectApplyAuraName%d' % n: 91 + i, 'EffectAmplitude%d' % n: 94 + i,
                'EffectChainTarget%d' % n: 100 + i, 'EffectItemType%d' % n: 103 + i, 'EffectMiscValue%d' % n: 106 + i,
                'EffectTriggerSpell%d' % n: 109 + i})
spells = []
def newspell(base, name, desc, **sets):
    sid = SPELL_BASE + len(spells)
    spells.append(dict(id=sid, base=base, name=name, desc=desc, sets=sets))
    return sid

HIT = dict(ProcChance=20, CastingTimeIndex=1)
S_THREAT = newspell(7597, "Rempart de l'Aube", "Augmente la menace que vous générez de $s1%.",
                    EffectApplyAuraName1=10, EffectMiscValue1=127, EffectBasePoints1=49)
S_AEGIS = newspell(9800, "Égide des Sept", "Absorbe $s1 points de dégâts.", EffectBasePoints1=1499, DurationIndex=9,
                   SpellFamilyName=0)
S_AEGIS_P = newspell(19409, "Égide des Sept", "Quand vous êtes frappé, 10 % de chance de vous entourer d'un bouclier "
                     "qui absorbe 1500 points de dégâts pendant 30 s.", ProcChance=10, EffectTriggerSpell1=S_AEGIS)
S_SHADOWFIRE = newspell(18138, "Décharge d'ombre et de feu", "Inflige $s1 points de dégâts d'Ombre et de Feu.",
                        EffectBasePoints1=449, EffectDieSides1=101, **HIT)
S_EXTRA = newspell(15601, "Brise-Monde", "Frappe une seconde fois.", **HIT)
S_WAVE = newspell(20549, "Onde du Crépuscule", "Étourdit les ennemis proches pendant 2 s et leur inflige $s2 points de dégâts.",
                  Effect2=2, EffectBasePoints2=249, EffectDieSides2=101, EffectImplicitTargetA2=SPR[20549][82],
                  EffectImplicitTargetB2=SPR[20549][85], EffectRadiusIndex2=SPR[20549][88], SpellFamilyName=0, **HIT)
S_POISON = newspell(2818, "Poison du Néant", "$s1 points de dégâts d'Ombre toutes les 3 s pendant 12 s. Cumulable 5 fois.",
                    School=5, EffectBasePoints1=59, StackAmount=5, SpellFamilyName=0, **HIT)
S_HASTE = newspell(21165, "Éclipse", "Augmente votre vitesse d'attaque de $s1% pendant 10 s.", EffectBasePoints1=29, **HIT)
S_BLEED = newspell(772, "Saignement de Rage", "$s1 points de dégâts toutes les 3 s pendant 12 s. Cumulable 5 fois.",
                   EffectBasePoints1=39, DurationIndex=29, StackAmount=5, SpellFamilyName=0, **HIT)
S_DRAIN = newspell(20004, "Dévorer", "Vole $s1 points de vie à la cible.", EffectBasePoints1=199, EffectDieSides1=51, **HIT)
S_EXPLO = newspell(18392, "Balle explosive", "Inflige $s1 points de dégâts de Feu aux ennemis autour de la cible.",
                   EffectBasePoints1=399, EffectDieSides1=201, EffectRadiusIndex1=13, **HIT)
S_MULTI = newspell(18651, "Souffle des Sept Vents", "Tire 3 flèches d'un coup.", EffectBasePoints1=149, EffectChainTarget1=3, **HIT)
S_PIERCE = newspell(14287, "Carreau du Jugement", "Inflige $s1 points de dégâts d'Arcanes, sans tenir compte de l'armure.",
                    EffectBasePoints1=599, EffectDieSides1=1, **HIT)
S_SOULS = newspell(21165, "Sept Âmes", "Vos sorts sont presque instantanés et ne coûtent rien.",
                   EffectApplyAuraName1=65, EffectBasePoints1=899, Effect2=6, EffectApplyAuraName2=72, EffectMiscValue2=127,
                   EffectBasePoints2=-101, EffectDieSides2=1, EffectImplicitTargetA2=1, DurationIndex=35, ProcChance=101)
S_SOULS_P = newspell(25906, "Sept Âmes", "Vos sorts offensifs ont 20 % de chance de rendre vos sorts presque instantanés "
                     "et gratuits pendant 4 s.", ProcChance=20, ProcFlags=0x10000, EffectTriggerSpell1=S_SOULS)
S_ARC = newspell(21165, "Éclat d'Arcane", "Les dégâts de vos sorts sont augmentés de $s1%.", EffectApplyAuraName1=79,
                 EffectMiscValue1=126, EffectBasePoints1=99, DurationIndex=27, ProcChance=101)
S_ARC_P = newspell(25906, "Éclat d'Arcane", "Vos sorts offensifs ont 20 % de chance d'augmenter les dégâts de vos sorts "
                   "de 100 % pendant 3 s.", ProcChance=20, ProcFlags=0x10000, EffectTriggerSpell1=S_ARC)
S_BOUNCE = newspell(1064, "Aube éternelle", "Rend $s1 points de vie, puis rebondit sur les alliés blessés proches.",
                    EffectBasePoints1=499, EffectDieSides1=101, CastingTimeIndex=1, ManaCost=0, SpellFamilyName=0, ProcChance=101)
S_BOUNCE_P = newspell(25906, "Aube éternelle", "Vos soins ont 20 % de chance de rebondir sur les alliés blessés proches "
                      "et de leur rendre 500 à 600 points de vie.", ProcChance=20, ProcFlags=0x4000, EffectTriggerSpell1=S_BOUNCE)
S_LUMEN = newspell(10901, "Lumière brisée", "Absorbe $s1 points de dégâts et rend $s2 points de mana au soigneur.",
                   EffectBasePoints1=799, Effect2=30, EffectBasePoints2=299, EffectDieSides2=1, EffectImplicitTargetA2=1,
                   EffectMiscValue2=0, ManaCost=0, SpellFamilyName=0, ProcChance=101)
S_LUMEN_P = newspell(25906, "Lumière brisée", "Vos soins ont 20 % de chance d'entourer la cible d'un bouclier absorbant "
                     "800 points de dégâts et de vous rendre 300 points de mana.", ProcChance=20, ProcFlags=0x4000,
                     EffectTriggerSpell1=S_LUMEN)

# ---------------------------------------------------------------- effets visuels (enchantement permanent posé à la création)
VISUALS = {}
def visual(name, itemvisual):
    if (name, itemvisual) not in VISUALS:
        VISUALS[(name, itemvisual)] = ENCH_BASE + len(VISUALS)
    return VISUALS[(name, itemvisual)]
V_GOLD, V_SHADOW, V_FIRE, V_BLUE, V_POISON, V_BLOOD, V_ICE, V_ARCANE = 103, 1, 25, 33, 26, 125, 126, 107

# ---------------------------------------------------------------- armes
STATID = {'agi': 3, 'str': 4, 'int': 5, 'spi': 6, 'sta': 7}
COST = {'ap': 0.5, 'crit': 14, 'hit': 10}
def stats_for(slotmod, dist):
    P = (120 - 1.3) / 1.3 * slotmod * 1.25 * 1.5      # légendaire ilvl 120, +50 % compris
    st, bonus = {}, {}
    for k, f in dist.items():
        if k in STATID:
            st[k] = round(P * f)
        else:
            bonus[k] = P * f / COST[k]
    return st, bonus
D_TANK = {'sta': .45, 'str': .30, 'agi': .15, 'hit': .10}
D_STR = {'str': .45, 'sta': .25, 'agi': .10, 'crit': .10, 'ap': .10}
D_AGI = {'agi': .40, 'sta': .25, 'str': .10, 'crit': .10, 'ap': .15}
D_RNG = {'agi': .50, 'sta': .25, 'crit': .10, 'ap': .15}
D_CAST = {'int': .45, 'sta': .35, 'spi': .20}
D_HEAL = {'int': .40, 'spi': .30, 'sta': .30}

# (clé, nom, objet modèle, type d'objet, vitesse ms, dps, répartition, part de stats, sorts [(id, déclencheur)],
#  bonus fixe (famille, valeur), visuel)
W = [
    ('tank_epee', "Rempart de l'Aube", 19019, 13, 2400, 125, D_TANK, 0.42, [(S_THREAT, 1)], None, V_GOLD),
    ('tank_bouclier', "Égide des Sept", 18168, 14, 0, 0, {'sta': .7, 'str': .3}, 0.56, [(S_AEGIS_P, 1)], None, None),
    ('epee2m', "Lame des Sept Fragments", 22691, 17, 3600, 165, D_STR, 0.8, [(S_SHADOWFIRE, 2)], None, V_SHADOW),
    ('hache2m', "Brise-Monde", 22815, 17, 3600, 165, D_STR, 0.8, [(S_EXTRA, 2)], None, V_BLUE),
    ('masse2m', "Marteau du Crépuscule", 22798, 17, 3800, 165, D_STR, 0.8, [(S_WAVE, 2)], None, V_SHADOW),
    ('dague1', "Croc Jumeau du Néant", 22802, 13, 1800, 125, D_AGI, 0.42, [(S_POISON, 2)], None, V_POISON),
    ('dague2', "Croc Jumeau du Néant", 22802, 13, 1800, 125, D_AGI, 0.42, [(S_POISON, 2)], None, V_POISON),
    ('epee1', "Lame de l'Éclipse", 23577, 13, 2600, 125, D_AGI, 0.42, [(S_HASTE, 2)], None, V_BLUE),
    ('epee2', "Lame de l'Éclipse", 23577, 13, 2600, 125, D_AGI, 0.42, [(S_HASTE, 2)], None, V_BLUE),
    ('hache1', "Fendeuse de Rage", 19363, 13, 2600, 125, D_AGI, 0.42, [(S_BLEED, 2)], None, V_BLOOD),
    ('hache2', "Fendeuse de Rage", 19363, 13, 2600, 125, D_AGI, 0.42, [(S_BLEED, 2)], None, V_BLOOD),
    ('griffe1', "Griffe du Dévoreur", 23242, 13, 2000, 125, D_AGI, 0.42, [(S_DRAIN, 2)], None, V_SHADOW),
    ('griffe2', "Griffe du Dévoreur", 23242, 13, 2000, 125, D_AGI, 0.42, [(S_DRAIN, 2)], None, V_SHADOW),
    ('fusil', "Le Dernier Mot", 17072, 26, 3000, 120, D_RNG, 0.3, [(S_EXPLO, 2)], None, V_FIRE),
    ('arc', "Souffle des Sept Vents", 17069, 15, 3000, 120, D_RNG, 0.3, [(S_MULTI, 2)], None, V_ICE),
    ('arbalete', "Carreau du Jugement", 19361, 26, 3400, 120, D_RNG, 0.3, [(S_PIERCE, 2)], None, V_GOLD),
    ('baton_sorts', "Bâton des Sept Âmes", 22589, 17, 3000, 90, D_CAST, 0.8, [(S_SOULS_P, 1)], ('sp', 230), V_ARCANE),
    ('dague_sorts', "Éclat d'Arcane", 22803, 13, 1800, 70, D_CAST, 0.42, [(S_ARC_P, 1)], ('sp', 140), V_ARCANE),
    ('orbe', "Orbe des Fragments", 23049, 23, 0, 0, D_CAST, 0.42, [], ('sp', 60), None),
    ('baton_soins', "Bâton de l'Aube éternelle", 22631, 17, 3000, 90, D_HEAL, 0.8, [(S_BOUNCE_P, 1)], ('heal', 440), V_GOLD),
    ('masse_soins', "Marteau de la Lumière brisée", 23056, 13, 2400, 70, D_HEAL, 0.42, [(S_LUMEN_P, 1)], ('heal', 260), V_GOLD),
    ('lumen', "Lumen", 23048, 23, 0, 0, D_HEAL, 0.42, [], ('heal', 110), None),
]
WID = {k: ITEM_BASE + i for i, (k, *_) in enumerate(W)}
VISUAL_OF = {}
for i, w in enumerate(W):
    if w[10] is not None:
        VISUAL_OF[ITEM_BASE + i] = visual("Puissance légendaire", w[10])

# coffrets (paires) et choix des 4 voies
BOXES = [
    ('box_tank', "Coffret du Rempart de l'Aube", ['tank_epee', 'tank_bouclier']),
    ('box_dagues', "Coffret des Crocs Jumeaux du Néant", ['dague1', 'dague2']),
    ('box_epees', "Coffret des Lames de l'Éclipse", ['epee1', 'epee2']),
    ('box_haches', "Coffret des Fendeuses de Rage", ['hache1', 'hache2']),
    ('box_griffes', "Coffret des Griffes du Dévoreur", ['griffe1', 'griffe2']),
    ('box_arcane', "Coffret de l'Éclat d'Arcane", ['dague_sorts', 'orbe']),
    ('box_lumiere', "Coffret de la Lumière brisée", ['masse_soins', 'lumen']),
]
BID = {k: BOX_BASE + i for i, (k, *_) in enumerate(BOXES)}
VOIES = [
    (QUEST2, "La voie de l'acier", "un tank ou un combattant à deux mains", ['box_tank', 'epee2m', 'hache2m', 'masse2m']),
    (QUEST2 + 1, "La voie des lames jumelles", "un combattant à deux armes", ['box_dagues', 'box_epees', 'box_haches', 'box_griffes']),
    (QUEST2 + 2, "La voie du tireur", "un tireur", ['fusil', 'arc', 'arbalete']),
    (QUEST2 + 3, "La voie des arcanes et de la lumière", "un lanceur de sorts ou un soigneur",
     ['baton_sorts', 'box_arcane', 'baton_soins', 'box_lumiere']),
]
def rid(k): return WID.get(k) or BID[k]

# ---------------------------------------------------------------- SQL
L = []
w_ = L.append
w_("-- Armes légendaires (généré)")
w_("SET NAMES utf8mb4;")
w_("DELETE FROM item_template WHERE entry BETWEEN %d AND %d;" % (ITEM_BASE, HEART))
w_("DELETE FROM item_loot_template WHERE entry BETWEEN %d AND %d;" % (BOX_BASE, BOX_BASE + 19))
w_("DELETE FROM spell_template WHERE Id BETWEEN %d AND %d;" % (SPELL_BASE, SPELL_BASE + 99))
w_("DELETE FROM quest_template WHERE entry BETWEEN %d AND %d;" % (QUEST1, QUEST1 + 9))
w_("DELETE FROM creature_questrelation WHERE id IN (%d, %d);" % (NPC_SW, NPC_ORG))
w_("DELETE FROM creature_involvedrelation WHERE id IN (%d, %d);" % (NPC_SW, NPC_ORG))
w_("DELETE FROM creature WHERE id IN (%d, %d);" % (NPC_SW, NPC_ORG))
w_("DELETE FROM creature_template WHERE Entry IN (%d, %d);" % (NPC_SW, NPC_ORG))
w_("")
w_("-- Sorts des armes")
w_("DROP TEMPORARY TABLE IF EXISTS tmp_sp;")
w_("CREATE TEMPORARY TABLE tmp_sp LIKE spell_template;")
for s in spells:
    w_("INSERT INTO tmp_sp SELECT * FROM spell_template WHERE Id=%d;" % s['base'])
    sets = ["Id=%d" % s['id'], "SpellName='%s'" % esc(s['name']), "Rank1=''"] + ["%s=%d" % kv for kv in s['sets'].items()]
    if s['sets'].get('SpellFamilyName') == 0:
        sets.append("SpellFamilyFlags=0")
    w_("UPDATE tmp_sp SET %s WHERE Id=%d;" % (", ".join(sets), s['base']))
w_("INSERT INTO spell_template SELECT * FROM tmp_sp;")
w_("DROP TEMPORARY TABLE tmp_sp;")
w_("")
w_("-- Armes")
w_("DROP TEMPORARY TABLE IF EXISTS tmp_it;")
w_("CREATE TEMPORARY TABLE tmp_it LIKE item_template;")
for i, (k, nom, src, inv, spd, dps, dist, sm, sps, fixe, vis) in enumerate(W):
    e = ITEM_BASE + i
    st, bonus = stats_for(sm, dist)
    sl = []
    for fam, v in bonus.items():
        sl += pick_split(fam, v, 1)
    if fixe:
        sl += pick_split(fixe[0], fixe[1] * 1.0, 2)
    allsp = [(sid, trg) for sid, trg in sps] + [(x, 1) for x in sl]
    allsp = allsp[:5]
    sets = ["entry=%d" % e, "name='%s'" % esc(nom), "Quality=5", "ItemLevel=120", "RequiredLevel=60", "bonding=1",
            "InventoryType=%d" % inv, "AllowableClass=-1", "AllowableRace=-1", "RandomProperty=0", "itemset=0",
            "Flags=0", "maxcount=1", "description='Forgée avec les sept fragments.'", "SellPrice=250000", "BuyPrice=1000000",
            "RequiredReputationFaction=0", "RequiredReputationRank=0", "requiredhonorrank=0", "RequiredSkill=0",
            "RequiredSkillRank=0", "requiredspell=0", "ScriptName=''", "startquest=0", "MaxDurability=GREATEST(MaxDurability, 120)"]
    stl = list(st.items())
    for n in range(10):
        if n < len(stl):
            sets += ["stat_type%d=%d" % (n + 1, STATID[stl[n][0]]), "stat_value%d=%d" % (n + 1, stl[n][1])]
        else:
            sets += ["stat_type%d=0" % (n + 1), "stat_value%d=0" % (n + 1)]
    if spd:
        avg = dps * spd / 1000.0
        sets += ["dmg_min1=%d" % round(avg * 0.8), "dmg_max1=%d" % round(avg * 1.2), "delay=%d" % spd, "armor=0"]
        for n in range(2, 6):
            sets += ["dmg_min%d=0" % n, "dmg_max%d=0" % n]
    if k == 'tank_bouclier':
        sets += ["armor=6000", "block=150"]
    for n in range(5):
        sid, trg = allsp[n] if n < len(allsp) else (0, 0)
        sets += ["spellid_%d=%d" % (n + 1, sid), "spelltrigger_%d=%d" % (n + 1, trg), "spellppmRate_%d=0" % (n + 1),
                 "spellcharges_%d=0" % (n + 1), "spellcooldown_%d=-1" % (n + 1), "spellcategory_%d=0" % (n + 1),
                 "spellcategorycooldown_%d=-1" % (n + 1)]
    w_("INSERT INTO tmp_it SELECT * FROM item_template WHERE entry=%d;" % src)
    w_("UPDATE tmp_it SET %s WHERE entry=%d;" % (", ".join(sets), src))
w_("-- Coffrets (paires d'armes) et Cœur des Sept")
for i, (k, nom, contenu) in enumerate(BOXES):
    e = BOX_BASE + i
    w_("INSERT INTO tmp_it SELECT * FROM item_template WHERE entry=20367;")
    w_("UPDATE tmp_it SET entry=%d, name='%s', class=15, subclass=0, Quality=5, Flags=4, InventoryType=0, ItemLevel=120, "
       "RequiredLevel=0, maxcount=1, stackable=1, bonding=1, description='Clic droit pour ouvrir.', BuyPrice=0, SellPrice=0, "
       "spellid_1=0, spelltrigger_1=0, startquest=0, lockid=0, ScriptName='' "
       "WHERE entry=20367;" % (e, esc(nom)))
w_("INSERT INTO tmp_it SELECT * FROM item_template WHERE entry=%d;" % FRAG[0])
w_("UPDATE tmp_it SET entry=%d, name='Cœur des Sept (inachevé)', description='Quatre fragments réunis. Il en manque trois.' "
   "WHERE entry=%d;" % (HEART, FRAG[0]))
w_("INSERT INTO item_template SELECT * FROM tmp_it;")
w_("DROP TEMPORARY TABLE tmp_it;")
for i, (k, nom, contenu) in enumerate(BOXES):
    for item in contenu:
        w_("INSERT INTO item_loot_template (entry, item, ChanceOrQuestChance, groupid, mincountOrRef, maxcount, condition_id, comments) "
           "VALUES (%d, %d, 100, 0, 1, 1, 0, 'Custom légendaire');" % (BOX_BASE + i, WID[item]))
w_("")
w_("-- L'Esprit des Sept (Hurlevent et Orgrimmar)")
w_("DROP TEMPORARY TABLE IF EXISTS tmp_ct;")
w_("CREATE TEMPORARY TABLE tmp_ct LIKE creature_template;")
for e in (NPC_SW, NPC_ORG):
    w_("INSERT INTO tmp_ct SELECT * FROM creature_template WHERE Entry=10667;")
    w_("UPDATE tmp_ct SET Entry=%d, Name='Esprit des Sept', SubName='Gardien des fragments', DisplayId1=5233, DisplayId2=0, "
       "DisplayId3=0, DisplayId4=0, DisplayIdProbability1=100, DisplayIdProbability2=0, DisplayIdProbability3=0, "
       "DisplayIdProbability4=0, MinLevel=63, MaxLevel=63, Faction=35, NpcFlags=2, GossipMenuId=0, ScriptName='', AIName='', "
       "EquipmentTemplateId=0, LootId=0 WHERE Entry=10667;" % e)
w_("INSERT INTO creature_template SELECT * FROM tmp_ct;")
w_("DROP TEMPORARY TABLE tmp_ct;")
for g, e, m, (x, y, z, o) in ((9903100, NPC_SW, 0, (-8439.98, 329.39, 122.58, 2.29)), (9903101, NPC_ORG, 1, (1920.07, -4125.69, 43.00, 4.80))):
    nx, ny = x + 4 * math.cos(o + 1.2), y + 4 * math.sin(o + 1.2)
    w_("INSERT INTO creature (guid, id, map, spawnMask, position_x, position_y, position_z, orientation, spawntimesecsmin, "
       "spawntimesecsmax, spawndist, MovementType) VALUES (%d, %d, %d, 1, %.2f, %.2f, %.2f, %.3f, 60, 60, 0, 0);" % (g, e, m, nx, ny, z, o))
w_("")
w_("-- Quêtes : 4 fragments -> Cœur des Sept ; Cœur + 3 fragments -> arme (une seule voie par personnage)")
cols = ("entry, Method, ZoneOrSort, MinLevel, QuestLevel, Type, QuestFlags, PrevQuestId, ExclusiveGroup, Title, Details, Objectives, "
        "OfferRewardText, RequestItemsText, ReqItemId1, ReqItemId2, ReqItemId3, ReqItemId4, ReqItemCount1, ReqItemCount2, "
        "ReqItemCount3, ReqItemCount4")
det1 = ("Sept puissances ont été vaincues dans les raids de ce monde, et de chacune un éclat est resté entre vos mains.$B$B"
        "Apportez-moi d'abord les fragments du Sang d'Hakkar, des Sables d'Ossirian, du Cœur du Magma et d'Onyxia. "
        "Je les fondrai en un cœur.")
w_("INSERT INTO quest_template (%s, RewItemId1, RewItemCount1) VALUES (%d, 2, -344, 60, 60, 0, 0, 0, 0, '%s', '%s', '%s', '%s', '%s', "
   "%d, %d, %d, %d, 1, 1, 1, 1, %d, 1);" % (cols, QUEST1, esc("Les Sept Fragments"), esc(det1),
   esc("Rapporter les fragments du Sang d'Hakkar, des Sables d'Ossirian, du Cœur du Magma et d'Onyxia."),
   esc("Le cœur bat déjà. Il lui manque encore trois fragments."), esc("Les fragments, $N ?"),
   FRAG[0], FRAG[1], FRAG[2], FRAG[3], HEART))
for qid, titre, qui, choix in VOIES:
    det = ("Le cœur est prêt à devenir une arme. Celle-ci convient à %s.$B$BApportez-moi le Cœur des Sept et les fragments "
           "de l'Aile noire, de l'Œil de C'Thun et de la Nécropole. Choisissez bien : une seule arme légendaire par personne." % qui)
    rew = ", ".join(str(rid(c)) for c in choix)
    n = len(choix)
    w_("INSERT INTO quest_template (%s, %s, %s) VALUES (%d, 2, -344, 60, 60, 0, 0, %d, %d, '%s', '%s', '%s', '%s', '%s', "
       "%d, %d, %d, %d, 1, 1, 1, 1, %s, %s);" % (
           cols, ", ".join("RewChoiceItemId%d" % (j + 1) for j in range(n)), ", ".join("RewChoiceItemCount%d" % (j + 1) for j in range(n)),
           qid, QUEST1, QUEST2, esc(titre), esc(det),
           esc("Rapporter le Cœur des Sept et les fragments de l'Aile noire, de l'Œil de C'Thun et de la Nécropole."),
           esc("Les sept puissances ne font plus qu'une. Elle est à vous."), esc("Le cœur attend, $N."),
           HEART, FRAG[4], FRAG[5], FRAG[6], rew, ", ".join("1" for _ in range(n))))
for e in (NPC_SW, NPC_ORG):
    for qid in [QUEST1] + [v[0] for v in VOIES]:
        w_("INSERT INTO creature_questrelation (id, quest) VALUES (%d, %d);" % (e, qid))
        w_("INSERT INTO creature_involvedrelation (id, quest) VALUES (%d, %d);" % (e, qid))
w_("")
w_("SELECT 'Armes legendaires OK' AS resultat;")
open(OUT + 'legendaires.sql', 'w', encoding='utf-8').write("\n".join(L) + "\n")

# ---------------------------------------------------------------- lignes DBC client
spellrows = []
for s in spells:
    r = list(SPR[s['base']])
    r[0] = s['id']
    for kk, v in s['sets'].items():
        r[COL[kk]] = v
    if s['sets'].get('SpellFamilyName') == 0:
        r[161] = r[162] = 0
    for c in range(120, 156):
        if c not in (128, 137, 146, 155):
            r[c] = 0
    r[120] = s['name']
    r[138] = s['desc']
    spellrows.append(r)
enchrows = []
for (nom, iv), eid in sorted(VISUALS.items(), key=lambda x: x[1]):
    enchrows.append([eid, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, nom] + [0] * 7 + [ench.rows[0][21], iv, 0])
json.dump(dict(spell=spellrows, ench=enchrows, visual_of=VISUAL_OF), open(OUT + 'legendaires_rows.json', 'w', encoding='utf-8'),
          ensure_ascii=False)
print('sorts', len(spells), 'armes', len(W), 'coffrets', len(BOXES), 'visuels', len(VISUALS))
print('visuels par arme', VISUAL_OF)
