# Sorts des classes custom (document Classes_custom_conception), partie données.
# Sorties : sorts.sql (base world), sorts_rows.json (lignes Spell.dbc, SkillLineAbility.dbc, SkillLine.dbc pour build.py)
import json, sys
sys.path.insert(0, '/home/claude/wow/fr')
sys.path.insert(0, '/home/claude/wow/classes')
from spellgen import Gen, q, esc, icon, visual, rank_levels, rank_value, DUR, CAST, RADIUS, RANGE, SPR

OUT = '/home/claude/wow/classes/'
NECRO, SNIPER, META = 6, 10, 11
CBIT = {c: 1 << (c - 1) for c in range(1, 12)}

BASEMANA = {}
for c, lv, m in q("select class, level, basemana from player_classlevelstats where class in (9, 3, 7)"):
    BASEMANA[(int(c), int(lv))] = int(m)

def mana(cls_base, pct, level):
    # croissant avec le niveau ; environ pct % du mana de base au niveau 60, plus cher en proportion à bas niveau (comme vanilla)
    return int(round(pct / 100.0 * BASEMANA[(cls_base, 60)] * (0.12 + 0.88 * (level / 60.0) ** 1.2)))

def eff_index(base, effect=None, aura=None):
    r = SPR[base]
    for i in range(3):
        if effect is not None and r[61 + i] == effect:
            return i + 1
        if aura is not None and r[61 + i] in (6, 27, 35) and r[91 + i] == aura:
            return i + 1
    raise ValueError((base, effect, aura))

ECOLE = {0: "physiques", 1: "Sacré", 2: "Feu", 3: "Nature", 4: "Givre", 5: "Ombre", 6: "Arcanes"}
def ecole(s):
    n = ECOLE[s]
    return "de " + n if n[0] not in "AEIOUÉ" else "d'" + n

# ======================================================================== Nécromancien
NG = Gen(5, range(34, 64))          # famille démoniste (classe de sorts du Nécromancien côté serveur)
NID = [62000]
def nid():
    NID[0] += 1
    return NID[0] - 1
NSKILL = {'inv': 900, 'mal': 901, 'mag': 902}
NSLA = []                           # (skill, sort)

def common(lv, cd, cast, mpct, icon_sid=None, base_cls=9):
    s = {'SpellLevel': lv, 'BaseLevel': lv, 'MaxLevel': 0, 'CastingTimeIndex': CAST[cast], 'RecoveryTime': cd,
         'CategoryRecoveryTime': 0, 'Category': 0, 'ManaCost': mana(base_cls, mpct, lv) if mpct else 0,
         'ManaCostPercentage': 0, 'ManaCostPerlevel': 0, 'ManaPerSecond': 0, 'ManaPerSecondPerLevel': 0}
    if icon_sid:
        s['SpellIconID'] = icon(icon_sid)
    return s

def n_direct(key, tree, base, lv0, nranks, name, school, vmin, vmax, coef, cast, cd, mpct, icon_sid=None, extra=None,
             desc_extra='', drop_effects=()):
    ids = []
    di = eff_index(base, effect=2)
    for k, L in enumerate(rank_levels(lv0, nranks)):
        lo, hi = round(rank_value(vmin, L)), round(rank_value(vmax, L))
        sets = common(L, cd, cast, mpct, icon_sid)
        sets.update({'School': school, 'EffectBasePoints%d' % di: lo - 1, 'EffectDieSides%d' % di: max(1, hi - lo + 1),
                     'EffectRealPointsPerLevel%d' % di: 0, 'EffectBonusCoefficient%d' % di: coef})
        for e in drop_effects:
            sets.update({'Effect%d' % e: 0, 'EffectApplyAuraName%d' % e: 0, 'EffectBonusCoefficient%d' % e: 0})
        if extra:
            sets.update(extra(L))
        desc = "Inflige %d à %d points de dégâts %s à l'ennemi.%s" % (lo, hi, ecole(school), desc_extra(L) if callable(desc_extra) else desc_extra)
        ids.append(NG.add(nid(), base, name, desc, "Rang %d" % (k + 1), key=key, sets=sets))
        NSLA.append((NSKILL[tree], ids[-1]))
    NG.chain_ranks(ids)
    return ids

def n_dot(key, tree, base, lv0, nranks, name, school, total, dur, coef_total, cd, mpct, aura=3, icon_sid=None, extra=None,
          verb="Inflige", tip=None):
    ids = []
    ai = eff_index(base, aura=aura)
    ticks = dur // 1000
    for k, L in enumerate(rank_levels(lv0, nranks)):
        tot = round(rank_value(total, L))
        tick = max(1, round(tot / ticks))
        sets = common(L, cd, 0, mpct, icon_sid)
        sets.update({'School': school, 'EffectBasePoints%d' % ai: tick - 1, 'EffectDieSides%d' % ai: 1,
                     'EffectRealPointsPerLevel%d' % ai: 0, 'EffectAmplitude%d' % ai: 1000, 'DurationIndex': DUR[dur],
                     'EffectBonusCoefficient%d' % ai: round(coef_total / ticks, 4)})
        if extra:
            sets.update(extra(L))
        desc = "%s %d points de dégâts %s en %d s." % (verb, tick * ticks, ecole(school), ticks)
        if aura == 53:
            desc += " Vous rend autant de points de vie."
        tooltip = tip(tick) if tip else "%d points de dégâts %s par seconde." % (tick, ecole(school))
        ids.append(NG.add(nid(), base, name, desc, "Rang %d" % (k + 1), tooltip=tooltip, key=key, sets=sets))
        NSLA.append((NSKILL[tree], ids[-1]))
    NG.chain_ranks(ids)
    return ids

def n_single(key, tree, base, lv, name, desc, cd, cast, mpct, icon_sid=None, tooltip='', **sets):
    s = common(lv, cd, cast, mpct, icon_sid)
    s.update(sets)
    sid = NG.add(nid(), base, name, desc, "", tooltip=tooltip, key=key, sets=s)
    NSLA.append((NSKILL[tree], sid))
    return sid

N = {}
# Armure : armure x1,2 permanente
N['armure'] = n_single('armure', 'inv', 687, 1, "Armure", "Augmente votre armure de 20 %. Dure jusqu'à annulation.", 0, 0, 8,
                       icon_sid=706, tooltip="Armure augmentée de 20 %.",
                       Effect1=6, EffectApplyAuraName1=101, EffectMiscValue1=1, EffectBasePoints1=19, EffectDieSides1=1,
                       Effect2=0, EffectApplyAuraName2=0, DurationIndex=DUR[-1])
N['trait'] = n_direct('trait', 'mag', 686, 1, 9, "Trait d'ombre", 5, 300, 340, 0.57, 2000, 2000, 17)
N['mot'] = n_dot('mot', 'mal', 172, 2, 9, "Mot de l'ombre", 5, 470, 10000, 0.67, 1000, 14, icon_sid=589)
N['corruption'] = n_dot('corruption', 'mal', 172, 10, 8, "Corruption", 5, 460, 10000, 0.67, 1000, 14,
                        extra=lambda L: {'CastingTimeIndex': CAST[0]})
# Bouclier : absorbe 15 x niveau
N['bouclier'] = n_single('bouclier', 'inv', 11426, 12, "Bouclier",
                         "Absorbe 15 points de dégâts par niveau du lanceur (900 au niveau 60). Dure 1 min.", 30000, 0, 15,
                         icon_sid=6229, tooltip="Absorbe des dégâts.",
                         EffectBasePoints1=15 * 12 - 1, EffectDieSides1=1, EffectRealPointsPerLevel1=15.0, MaxLevel=60,
                         EffectMiscValue1=127, EffectBonusCoefficient1=0.10, DurationIndex=DUR[60000])
N['eclair'] = n_direct('eclair', 'mag', 116, 14, 7, "Éclair de givre", 4, 260, 300, 0.57, 2000, 2000, 16,
                       extra=lambda L: {'EffectBasePoints1': -21, 'EffectDieSides1': 1, 'DurationIndex': DUR[3000]},
                       desc_extra=" Ralentit la cible de 20 % pendant 3 s.")
N['vol'] = n_dot('vol', 'mal', 18265, 18, 7, "Vol de vie", 5, 300, 10000, 0.50, 10000, 16, aura=53,
                 tip=lambda t: "Perd %d points de vie par seconde, au profit du Nécromancien." % t)
N['resu'] = n_single('resu', 'inv', 20770, 20, "Résurrection",
                     "Ramène un allié mort à la vie avec 35 % de ses points de vie et de son mana. Hors combat.",
                     0, 4000, 25, icon_sid=2006)
N['boule'] = n_direct('boule', 'mag', 133, 22, 6, "Boule de feu", 2, 350, 410, 0.57, 2000, 10000, 20,
                      extra=lambda L: {'EffectChainTarget1': 3, 'EffectChainTarget2': 3,
                                       'EffectBasePoints2': max(1, round(rank_value(60, L) / 5)) - 1, 'EffectDieSides2': 1,
                                       'EffectAmplitude2': 1000, 'DurationIndex': DUR[5000], 'EffectBonusCoefficient2': 0.03},
                      desc_extra=lambda L: " Touche aussi 2 ennemis proches, et inflige %d points de dégâts de Feu supplémentaires en 5 s." % (max(1, round(rank_value(60, L) / 5)) * 5))
N['peur'] = n_single('peur', 'inv', 8122, 32, "Peur",
                     "Fait fuir de terreur les ennemis à moins de 8 mètres pendant 6 s.", 15000, 0, 12, icon_sid=5484,
                     tooltip="Fuit de terreur.", DurationIndex=DUR[6000], EffectRadiusIndex1=RADIUS[8], EffectRadiusIndex2=RADIUS[8])
N['camouflage'] = n_single('camouflage', 'inv', 3680, 36, "Camouflage",
                           "Vous rend invisible, même en mouvement. Toute attaque ou tout sort met fin à l'effet.",
                           1000, 0, 5, tooltip="Invisible.", DurationIndex=DUR[-1])
N['meteorite'] = []
_ids = []
for k, L in enumerate(rank_levels(40, 4)):
    tick = round(rank_value(140, L))
    s = common(L, 10000, 0, 22)
    s.update({'Effect1': 0, 'EffectBonusCoefficient1': 0, 'EffectBasePoints2': tick - 1, 'EffectDieSides2': 1,
              'EffectAmplitude2': 1000, 'DurationIndex': DUR[6000], 'EffectRadiusIndex1': RADIUS[8],
              'EffectRadiusIndex2': RADIUS[8], 'EffectBonusCoefficient2': 0.055, 'SpellIconID': icon(5740)})
    _ids.append(NG.add(nid(), 2120, "Météorite", "Une pluie de météores frappe la zone ciblée : %d points de dégâts de Feu "
                       "par seconde pendant 6 s aux ennemis dans un rayon de 8 mètres." % tick, "Rang %d" % (k + 1), key='meteorite', sets=s))
    NSLA.append((NSKILL['mag'], _ids[-1]))
NG.chain_ranks(_ids)
N['meteorite'] = _ids
N['malediction'] = n_dot('malediction', 'mal', 980, 44, 3, "Malédiction", 5, 460, 10000, 0.67, 1000, 14,
                         tip=lambda t: "Maudit : %d points de dégâts d'Ombre par seconde." % t)
N['javelot'] = n_direct('javelot', 'mag', 116, 46, 3, "Javelot de glace", 4, 160, 190, 0.43, 0, 2000, 10, icon_sid=8056,
                        drop_effects=(1,))
N['tirombre'] = n_direct('tirombre', 'mag', 686, 52, 2, "Tir d'ombre", 5, 375, 425, 0.86, 3000, 5000, 24, icon_sid=17877)
N['peste'] = n_dot('peste', 'mal', 2944 if False else 172, 56, 2, "Peste", 5, 500, 10000, 0.67, 1000, 15, icon_sid=2944)
N['releve'] = n_single('releve', 'inv', 20770, 60, "Relève-toi",
                       "Ramène un allié mort à la vie avec 30 % de ses points de vie et de son mana. Utilisable en combat.",
                       180000, 2000, 30, icon_sid=20707,
                       Attributes=SPR[20770][6] & ~0x10000000)
# Tempête du néant : instantanés, recharges -50 %, dégâts +20 % (modificateurs de sorts, masque 64 bits via spell_affect)
N['tempete'] = n_single('tempete', 'mag', 12042, 60, "Tempête du néant",
                        "Pendant 15 s, Trait d'ombre, Éclair de givre, Boule de feu et Tir d'ombre sont instantanés, "
                        "leur temps de recharge est réduit de 50 % et les dégâts de vos sorts sont augmentés de 20 %.",
                        300000, 0, 10, tooltip="Sorts instantanés, recharges réduites, dégâts augmentés.",
                        EffectApplyAuraName1=108, EffectMiscValue1=10, EffectBasePoints1=-101, EffectDieSides1=1,
                        EffectApplyAuraName2=108, EffectMiscValue2=11, EffectBasePoints2=-51, EffectDieSides2=1,
                        EffectApplyAuraName3=79, EffectMiscValue3=126, EffectBasePoints3=19, EffectDieSides3=1,
                        DurationIndex=DUR[15000])
AFFECT = []        # (sort, effet, masque)
_m = NG.masks['trait'] | NG.masks['eclair'] | NG.masks['boule'] | NG.masks['tirombre']
AFFECT += [(N['tempete'], 0, _m), (N['tempete'], 1, _m)]

# ======================================================================== maîtres de classe (étape 2)
import math
TEACH_BASE = 1296                   # sort d'apprentissage vanilla (effet 36) servant de modèle
TEACH = [64500]
TEACH_ROWS = []                     # sorts d'apprentissage (Gen dédié, sans famille)
TG = Gen(0, [])
TRAINER_SPELLS = {}                 # gabarit -> [(sort d'apprentissage, coût, niveau)]
START_SPELLS = {}                   # classe -> sorts donnés à la création

def teach_all(gen, template, skip):
    for sp in gen.spells:
        if sp['id'] in skip:
            continue
        lv = sp['sets'].get('SpellLevel', 1)
        tid = TEACH[0]; TEACH[0] += 1
        TG.add(tid, TEACH_BASE, sp['name'], sp['desc'], sp['rank'], family=False,
               sets={'EffectTriggerSpell1': sp['id'], 'SpellLevel': lv, 'BaseLevel': lv, 'MaxLevel': 0,
                     'SpellIconID': sp['sets'].get('SpellIconID', SPR[sp['base']][117])})
        TRAINER_SPELLS.setdefault(template, []).append((tid, max(10, 9 * lv * lv), lv))

START_SPELLS[NECRO] = [N['armure'], N['trait'][0]]
teach_all(NG, 900, set(START_SPELLS[NECRO]))

# (gabarit, entrée, nom, sous-titre, PNJ modèle, décalage, modèle 3D ou 0)
TRAINERS = [
    (900, 990170, "Mortis Valcendre", "Maître nécromancien", 459, 0, 10427),       # Comté du Nord
    (900, 990171, "Séraphine Noirsuaire", "Maître nécromancien", 461, 0, 10427),   # Hurlevent, l'Agneau égorgé
    (900, 990172, "Zul'gash", "Maître nécromancien", 3156, 0, 0),                    # Vallée des Épreuves
    (900, 990173, "Vol'kesh", "Maître nécromancien", 3324, 0, 0),                    # Orgrimmar, la Faille de l'ombre
]

def trainer_sql():
    L = ["-- Maîtres de classe des classes custom",
         "DELETE FROM npc_trainer_template WHERE entry BETWEEN 900 AND 909;",
         "DELETE FROM creature WHERE guid BETWEEN 9903000 AND 9903099;",
         "DELETE FROM creature_template WHERE Entry BETWEEN 990170 AND 990199;"]
    for tpl, lst in sorted(TRAINER_SPELLS.items()):
        for tid, cost, lv in lst:
            L.append("INSERT INTO npc_trainer_template (entry, spell, spellcost, reqskill, reqskillvalue, reqlevel) VALUES (%d, %d, %d, 0, 0, %d);" % (tpl, tid, cost, lv))
    L.append("DROP TEMPORARY TABLE IF EXISTS tmp_ct;")
    L.append("CREATE TEMPORARY TABLE tmp_ct LIKE creature_template;")
    guid = 9903000
    for tpl, entry, nom, sous, src, _, disp in TRAINERS:
        cls = {900: NECRO, 901: SNIPER, 902: META}[tpl]
        L.append("INSERT INTO tmp_ct SELECT * FROM creature_template WHERE Entry=%d;" % src)
        sets = ["Entry=%d" % entry, "Name='%s'" % esc(nom), "SubName='%s'" % esc(sous), "TrainerType=0", "TrainerClass=%d" % cls,
                "TrainerTemplateId=%d" % tpl, "NpcFlags=17", "GossipMenuId=0", "ScriptName=''"]
        if disp:
            sets += ["DisplayId1=%d" % disp, "DisplayId2=0", "DisplayId3=0", "DisplayId4=0", "DisplayIdProbability1=100",
                     "DisplayIdProbability2=0", "DisplayIdProbability3=0", "DisplayIdProbability4=0"]
        L.append("UPDATE tmp_ct SET %s WHERE Entry=%d;" % (", ".join(sets), src))
        # placé à côté du PNJ modèle, à 2 m sur sa gauche
        L.append("INSERT INTO creature (guid, id, map, spawnMask, position_x, position_y, position_z, orientation, spawntimesecsmin, "
                 "spawntimesecsmax, spawndist, MovementType) SELECT %d, %d, map, spawnMask, position_x + 2 * COS(orientation + PI() / 2), "
                 "position_y + 2 * SIN(orientation + PI() / 2), position_z + 0.3, orientation, 300, 300, 0, 0 FROM creature WHERE id=%d LIMIT 1;"
                 % (guid, entry, src))
        guid += 1
    L.append("INSERT INTO creature_template SELECT * FROM tmp_ct;")
    L.append("DROP TEMPORARY TABLE tmp_ct;")
    return L

# ======================================================================== sorties
def all_ids(d):
    out = []
    for v in d.values():
        out += v if isinstance(v, list) else [v]
    return out

L = ["-- Sorts des classes custom (généré par gen_sorts.py)", "SET NAMES utf8mb4;"]
L += NG.sql(62000, 62499)
L += TG.sql(64500, 65499)
L += trainer_sql()
# sorts de départ du Nécromancien (remplacent Trait de l'ombre et Peau de démon)
L.append("DELETE FROM playercreateinfo_spell WHERE class=%d AND Spell IN (686, 687);" % NECRO)
for race in (1, 8):
    for sp in START_SPELLS[NECRO]:
        L.append("INSERT IGNORE INTO playercreateinfo_spell (race, class, Spell, Note) VALUES (%d, %d, %d, 'Necromancien');" % (race, NECRO, sp))
L.append("UPDATE playercreateinfo_action SET action=%d WHERE class=%d AND type=0 AND action=686;" % (N['trait'][0], NECRO))
L.append("UPDATE playercreateinfo_action SET action=%d WHERE class=%d AND type=0 AND action=687;" % (N['armure'], NECRO))
L.append("DELETE FROM spell_affect WHERE entry BETWEEN 62000 AND 64499;")
for sid, e, m in AFFECT:
    L.append("INSERT INTO spell_affect (entry, effectId, SpellFamilyMask) VALUES (%d, %d, %d);" % (sid, e, m))

# lignes de compétence (onglets du grimoire)
SKILLLINES = [(900, "Invocateur", 354), (901, "Malédiction", 355), (902, "Magicien", 593),
              (903, "Tireur d'élite", 163), (904, "Bestial", 50), (905, "Mécanisme", 51)]
RENAME_SKILL = {573: "Totémique", 134: "Druidique", 574: "Angélique"}
SLA_ROWS = []
sla_id = 21000
for skill, sid in NSLA:
    SLA_ROWS.append([sla_id, skill, sid, 0, CBIT[NECRO], 0, 0, 1, 0, 0, 0, 0, 0, 0, 0])
    sla_id += 1

# DBC serveur : SkillLine (nouvelles lignes + Métamorphe) et SkillLineAbility (base + métiers + sorts custom)
import struct
from dbc import DBC, append_rows, rebuild
sk = DBC(OUT + 'srv/SkillLine.dbc')
SKROWS = {r[0]: r for r in sk.rows}
sk_new = []
for sid_, nom, src in SKILLLINES:
    r = list(SKROWS[src]); r[0] = sid_; r[3] = nom
    for c in range(4, 11): r[c] = 0
    for c in range(12, 20): r[c] = 0
    sk_new.append(r)
data, _ = rebuild(sk, {}, {(i, 3): RENAME_SKILL[r[0]] for i, r in enumerate(sk.rows) if r[0] in RENAME_SKILL})
open(OUT + 'out/SkillLine.dbc', 'wb').write(append_rows(data, sk_new))
MET = json.load(open('/home/claude/wow/metiers/metiers_rows.json', encoding='utf-8'))
open(OUT + 'out/SkillLineAbility.dbc', 'wb').write(
    append_rows(open('/home/claude/wow/dbc_extra/SkillLineAbility.dbc', 'rb').read(), MET['sla'] + SLA_ROWS))

json.dump({'spell': NG.dbc_rows() + TG.dbc_rows(), 'sla': SLA_ROWS, 'skilllines': sk_new, 'rename_skill': RENAME_SKILL,
           'masks': {'necro': {k: v for k, v in NG.masks.items()}}, 'ids': {'necro': N}},
          open(OUT + 'sorts_rows.json', 'w', encoding='utf-8'), ensure_ascii=False)
open(OUT + 'sorts.sql', 'w', encoding='utf-8').write("\n".join(L) + "\n")
print('necro', len(NG.spells), 'sorts', 'sla', len(SLA_ROWS))
