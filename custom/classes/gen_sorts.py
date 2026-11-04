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
for c, lv, m in q("select class, level, basemana from player_classlevelstats"):
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
    s = {'SpellLevel': lv, 'BaseLevel': lv, 'MaxLevel': 0, 'CastingTimeIndex': CAST[cast], 'RecoveryTime': cd, 'PowerType': 0,
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
N['trait'] = n_direct('trait', 'mag', 686, 1, 9, "Trait d'ombre", 5, 300, 340, 0.57, 2000, 0, 10)   # recharge retirée, mana -40 % (Alexis, 01/11)
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
_m = NG.mask('trait') | NG.mask('eclair') | NG.mask('boule') | NG.mask('tirombre')
AFFECT_N = [(N['tempete'], 0, _m), (N['tempete'], 1, _m)]

# ======================================================================== outils communs Sniper / Métamorphe
TRIGGERED = set()                   # sorts déclenchés (ni grimoire, ni maître de classe)
NOTEACH = set()                     # sorts appris par talent (grimoire oui, maître de classe non)
GROUPS = {}                         # groupe d'exclusivité -> [sorts]

class Ctx:
    def __init__(self, gen, first, skills, mcls, cls):
        self.g, self.next, self.skills, self.mcls, self.cls, self.sla = gen, first, skills, mcls, cls, []
    def nid(self):
        self.next += 1
        return self.next - 1
    def ranked(self, key, tree, base, lv0, nranks, name, mpct, cd, cast, per_rank, icon_sid=None):
        ids = []
        for k, L in enumerate(rank_levels(lv0, nranks)):
            sets = common(L, cd, cast, mpct, icon_sid, base_cls=self.mcls)
            extra, desc, tip = per_rank(L, k)
            sets.update(extra)
            ids.append(self.g.add(self.nid(), base, name, desc, "Rang %d" % (k + 1), tooltip=tip, key=key, sets=sets))
            self.sla.append((self.skills[tree], ids[-1]))
        self.g.chain_ranks(ids)
        return ids
    def single(self, key, tree, base, lv, name, desc, cd, cast, mpct, icon_sid=None, tooltip='', **sets):
        s = common(lv, cd, cast, mpct, icon_sid, base_cls=self.mcls)
        s.update(sets)
        sid = self.g.add(self.nid(), base, name, desc, "", tooltip=tooltip, key=key, sets=s)
        self.sla.append((self.skills[tree], sid))
        return sid
    def trig(self, key, base, name, desc, tooltip='', **sets):
        sid = self.g.add(self.nid(), base, name, desc, "", tooltip=tooltip, key=key, sets=sets)
        TRIGGERED.add(sid)
        return sid

def rv(v, L):
    return max(1, round(rank_value(v, L)))

PROC_RANGED = 0x40 | 0x100          # tir automatique et tirs à distance réussis

# ======================================================================== Sniper
SG = Gen(9, range(32, 64))          # famille chasseur
SC = Ctx(SG, 62500, {'tir': 903, 'bes': 904, 'mec': 905}, 3, SNIPER)
S = {}
RANGED = {'RangeIndex': 114}

S['arcanes'] = SC.ranked('arcanes', 'tir', 3044, 1, 9, "Tir des arcanes", 6, 5000, 0, lambda L, k: (
    {'EffectBasePoints1': rv(170, L) - 1, 'EffectDieSides1': 1, 'EffectBonusCoefficient1': 0, 'EffectBonusCoefficientFromAP1': 0.15},
    "Un tir instantané qui inflige %d points de dégâts d'Arcanes." % rv(170, L), ''))
S['marque'] = SC.ranked('marque', 'tir', 1130, 2, 9, "Marque", 4, 1000, 0, lambda L, k: (
    {'EffectBasePoints2': rv(110, L) - 1, 'EffectDieSides2': 1, 'DurationIndex': DUR[120000]},
    "Marque la cible pendant 2 min : les attaques à distance contre elle gagnent %d points de puissance d'attaque." % rv(110, L),
    "Marqué."), icon_sid=1130)
S['saignant'] = SC.ranked('saignant', 'tir', 1978, 4, 8, "Tir saignant", 5, 6000, 0, lambda L, k: (
    dict(RANGED, EffectBasePoints1=49, EffectApplyAuraName2=3, School=0, EffectBasePoints2=rv(180, L) // 5 - 1, EffectDieSides2=1,
         EffectAmplitude2=1000, DurationIndex=DUR[5000], EffectMechanic2=15, Mechanic=0, EffectBonusCoefficientFromAP2=0.01),
    "Inflige 50 %% des dégâts de l'arme et fait saigner la cible : %d points de dégâts en 5 s." % (rv(180, L) // 5 * 5),
    "Saigne."), icon_sid=1978)
S['fauve'] = SC.single('fauve', 'tir', 13165, 8, "Aspect du fauve",
    "Augmente votre puissance d'attaque et vos dégâts physiques de 10 %. Un seul aspect actif à la fois.", 1000, 0, 5,
    tooltip="Puissance d'attaque et dégâts physiques augmentés de 10 %.",
    Effect1=6, EffectApplyAuraName1=166, EffectBasePoints1=9, EffectDieSides1=1, EffectImplicitTargetA1=1,
    Effect2=6, EffectApplyAuraName2=167, EffectBasePoints2=9, EffectDieSides2=1, EffectImplicitTargetA2=1, EffectTriggerSpell2=0,
    Effect3=6, EffectApplyAuraName3=79, EffectMiscValue3=1, EffectBasePoints3=9, EffectDieSides3=1, EffectImplicitTargetA3=1,
    ProcFlags=0, ProcChance=101, DurationIndex=DUR[-1])
GROUPS.setdefault('aspect', []).append(S['fauve'])
S['glace'] = SC.single('glace', 'mec', 853, 14, "Piège de glace",
    "Gèle instantanément la cible pendant 1 s. Les dégâts ne brisent pas la glace.", 10000, 0, 4, icon_sid=13809,
    tooltip="Gelé.", DurationIndex=DUR[1000], RangeIndex=114)
S['long'] = SC.ranked('long', 'tir', 19434, 18, 7, "Tir long", 8, 10000, 4000, lambda L, k: (
    dict(RANGED, Effect1=31, EffectBasePoints1=119, EffectDieSides1=1,
         Effect2=2, EffectBasePoints2=rv(550, L) - 1, EffectDieSides2=1, EffectImplicitTargetA2=6, School=0,
         EffectBonusCoefficientFromAP2=0.15,
         Effect3=6, EffectApplyAuraName3=3, EffectBasePoints3=rv(200, L) // 5 - 1, EffectDieSides3=1, EffectImplicitTargetA3=6,
         EffectAmplitude3=1000, DurationIndex=DUR[5000], EffectBonusCoefficientFromAP3=0.01),
    "Un tir puissant : 120 %% des dégâts de l'arme plus %d, puis %d points de dégâts en 5 s." % (rv(550, L), rv(200, L) // 5 * 5),
    "Blessure profonde."))

# balles : buff de 10 s, recharge partagée de 30 s, une seule active (groupe exclusif)
BULLET_CAT = 1250
def bullet(key, lv0, nranks, name, icon_sid, dmg_pct, dot_name, dot_base, dot_school, dot60, dot_extra, desc_fn, proc_chance=100):
    def per(L, k):
        tick = max(1, rv(dot60, L) // 5)
        ds = dict(SpellLevel=L, School=dot_school, Effect1=6, EffectApplyAuraName1=3,
                  EffectBasePoints1=tick - 1, EffectDieSides1=1, EffectAmplitude1=1000, EffectImplicitTargetA1=6,
                  DurationIndex=DUR[5000], ManaCost=0, RecoveryTime=0, CastingTimeIndex=1, EffectBonusCoefficientFromAP1=0.01,
                  EffectBonusCoefficient1=0, Category=0, CategoryRecoveryTime=0,
                  Effect2=0, EffectApplyAuraName2=0, Effect3=0, EffectApplyAuraName3=0)
        ds.update(dot_extra)
        d = SC.trig(key + '_dot', dot_base, dot_name, "", tooltip="%d points de dégâts %s par seconde." % (tick, ecole(dot_school)), **ds)
        sets = {'Effect1': 6, 'EffectApplyAuraName1': 79, 'EffectMiscValue1': 1, 'EffectBasePoints1': dmg_pct - 1,
                'EffectDieSides1': 1, 'EffectImplicitTargetA1': 1,
                'Effect2': 6, 'EffectApplyAuraName2': 42, 'EffectTriggerSpell2': d, 'EffectImplicitTargetA2': 1,
                'EffectBasePoints2': 0, 'EffectDieSides2': 1, 'Effect3': 0, 'EffectApplyAuraName3': 0,
                'ProcFlags': PROC_RANGED, 'ProcChance': proc_chance, 'ProcCharges': 0, 'DurationIndex': DUR[10000],
                'Category': BULLET_CAT, 'CategoryRecoveryTime': 30000, 'RecoveryTime': 0}
        if dmg_pct <= 0:
            sets.update({'Effect1': 0, 'EffectApplyAuraName1': 0})
        return sets, desc_fn(L, tick), name + " chargée."
    ids = SC.ranked(key, 'tir', 13165, lv0, nranks, name, 6, 0, 0, per, icon_sid=icon_sid)
    GROUPS.setdefault('balle', []).extend(ids)
    return ids

S['feu'] = bullet('feu', 10, 8, "Balle de feu", 13795, 25, "Brûlure", 133, 2, 60, {'StackAmount': 3},
    lambda L, t: "Pendant 10 s, vos dégâts physiques sont augmentés de 25 %% et chaque tir brûle la cible : %d points de "
                 "dégâts de Feu par seconde pendant 5 s, cumulable 3 fois. Recharge partagée avec les autres balles." % t)
S['eau'] = bullet('eau', 20, 6, "Balle d'eau", 10497, 0, "Drain aqueux", 18265, 3, 120, {'EffectApplyAuraName1': 53},
    lambda L, t: "Pendant 10 s, chaque tir draine la vie de la cible : %d points de dégâts de Nature par seconde pendant 5 s, "
                 "qui vous soignent. Recharge partagée avec les autres balles." % t)
S['givre'] = bullet('givre', 30, 5, "Balle de givre", 116, 0, "Morsure du givre", 116, 4, 50,
    {'StackAmount': 3, 'Effect2': 6, 'EffectApplyAuraName2': 33, 'EffectBasePoints2': -31, 'EffectDieSides2': 1,
     'EffectImplicitTargetA2': 6, 'EffectAmplitude2': 0},
    lambda L, t: "Pendant 10 s, chaque tir ralentit la cible de 30 %% et lui inflige %d points de dégâts de Givre par seconde "
                 "pendant 5 s, cumulable 3 fois. Recharge partagée avec les autres balles." % t)
S['roche'] = bullet('roche', 50, 3, "Balle de roche", 8071, 10, "Éclat de roche", 853, 3, 100,
    {'StackAmount': 3, 'Effect2': 6, 'EffectApplyAuraName2': 12, 'EffectBasePoints2': 0, 'EffectDieSides2': 1,
     'EffectImplicitTargetA2': 6, 'EffectAmplitude2': 0, 'DurationIndex': DUR[5000]},
    lambda L, t: "Pendant 10 s, vos dégâts physiques sont augmentés de 10 %% et chaque tir a 25 %% de chance d'étourdir la "
                 "cible et de lui infliger %d points de dégâts de Nature par seconde pendant 5 s, cumulable 3 fois." % t,
    proc_chance=25)

S['bombe'] = SC.ranked('bombe', 'mec', 2120, 34, 5, "Bombe méca", 12, 10000, 1000, lambda L, k: (
    {'Effect2': 0, 'EffectApplyAuraName2': 0, 'EffectBasePoints1': rv(220, L) - 1, 'EffectDieSides1': rv(280, L) - rv(220, L) + 1,
     'EffectRadiusIndex1': RADIUS[20], 'EffectBonusCoefficient1': 0, 'EffectBonusCoefficient2': 0,
     'EffectBonusCoefficientFromAP1': 0.10, 'School': 2},
    "Lance une bombe qui explose dans la zone ciblée : %d à %d points de dégâts de Feu dans un rayon de 20 mètres." % (rv(220, L), rv(280, L)),
    ''), icon_sid=4068)
S['multiple'] = SC.ranked('multiple', 'tir', 2643, 36, 4, "Tir multiple", 9, 6000, 0, lambda L, k: (
    dict(RANGED, Effect1=31, EffectBasePoints1=69, EffectDieSides1=1, EffectImplicitTargetA1=24, EffectRadiusIndex1=RADIUS[20],
         EffectChainTarget1=0, Effect2=6, EffectApplyAuraName2=3, EffectBasePoints2=rv(80, L) // 5 - 1, EffectDieSides2=1,
         EffectImplicitTargetA2=24, EffectRadiusIndex2=RADIUS[20], EffectAmplitude2=1000, DurationIndex=DUR[5000],
         EffectBonusCoefficientFromAP2=0.01, School=0),
    "Tire sur tous les ennemis devant vous à moins de 20 mètres : 70 %% des dégâts de l'arme plus %d points de dégâts en 5 s." % (rv(80, L) // 5 * 5),
    "Blessé."))
S['cri'] = SC.ranked('cri', 'bes', 1160, 38, 4, "Cri bestial", 10, 10000, 0, lambda L, k: (
    {'EffectApplyAuraName1': 101, 'EffectMiscValue1': 1, 'EffectBasePoints1': -16, 'EffectDieSides1': 1,
     'EffectRadiusIndex1': RADIUS[20],
     'Effect2': 2, 'EffectBasePoints2': rv(150, L) - 1, 'EffectDieSides2': rv(180, L) - rv(150, L) + 1,
     'EffectImplicitTargetA2': 22, 'EffectImplicitTargetB2': 15, 'EffectRadiusIndex2': RADIUS[20], 'EffectBonusCoefficientFromAP2': 0.10,
     'Effect3': 6, 'EffectApplyAuraName3': 3, 'EffectBasePoints3': rv(80, L) // 6 - 1, 'EffectDieSides3': 1,
     'EffectImplicitTargetA3': 22, 'EffectImplicitTargetB3': 15, 'EffectRadiusIndex3': RADIUS[20], 'EffectAmplitude3': 1000,
     'EffectBonusCoefficientFromAP3': 0.005, 'DurationIndex': DUR[6000], 'School': 0},
    "Un cri terrifiant : les ennemis à moins de 20 mètres subissent %d à %d points de dégâts et %d points de dégâts en 6 s, "
    "et leur armure est réduite de 15 %% pendant 6 s." % (rv(150, L), rv(180, L), rv(80, L) // 6 * 6),
    "Armure réduite."), icon_sid=1160)
S['precision'] = SC.ranked('precision', 'tir', 19434, 42, 4, "Tir de précision", 9, 15000, 3000, lambda L, k: (
    dict(RANGED, Effect1=31, EffectBasePoints1=139, EffectDieSides1=1,
         Effect2=6, EffectApplyAuraName2=3, EffectBasePoints2=rv(200, L) // 5 - 1, EffectDieSides2=1, EffectImplicitTargetA2=6,
         EffectAmplitude2=1000, DurationIndex=DUR[5000], EffectMechanic2=15, School=0, EffectBonusCoefficientFromAP2=0.01),
    "Un tir précis : 140 %% des dégâts de l'arme et %d points de dégâts de saignement en 5 s." % (rv(200, L) // 5 * 5),
    "Saigne."), icon_sid=19434)
S['bestial'] = SC.ranked('bestial', 'bes', 1978, 46, 3, "Tir bestial", 7, 5000, 0, lambda L, k: (
    dict(RANGED, EffectBasePoints1=69, EffectApplyAuraName2=3, School=3, EffectBasePoints2=rv(60, L) // 5 - 1,
         EffectDieSides2=1, EffectAmplitude2=1000, DurationIndex=DUR[5000], StackAmount=3, Mechanic=0, EffectMechanic2=0,
         EffectBonusCoefficientFromAP2=0.01),
    "Inflige 70 %% des dégâts de l'arme et %d points de dégâts de Nature en 5 s, cumulable 3 fois." % (rv(60, L) // 5 * 5),
    "Empoisonné."), icon_sid=19574)
S['explosif'] = SC.ranked('explosif', 'tir', 2643, 52, 2, "Tir explosif", 10, 10000, 0, lambda L, k: (
    dict(RANGED, Effect1=31, EffectBasePoints1=99, EffectDieSides1=1, EffectChainTarget1=0, EffectImplicitTargetA1=6,
         Effect2=2, EffectBasePoints2=rv(120, L) - 1, EffectDieSides2=rv(150, L) - rv(120, L) + 1, EffectImplicitTargetA2=6,
         EffectChainTarget2=6, EffectBonusCoefficientFromAP2=0.10,
         Effect3=6, EffectApplyAuraName3=3, EffectBasePoints3=rv(100, L) // 5 - 1, EffectDieSides3=1, EffectImplicitTargetA3=6,
         EffectChainTarget3=6, EffectAmplitude3=1000, DurationIndex=DUR[5000], EffectBonusCoefficientFromAP3=0.01, School=2),
    "Inflige 100 %% des dégâts de l'arme, puis la charge explose : %d à %d points de dégâts de Feu et %d en 5 s à la cible "
    "et aux ennemis proches." % (rv(120, L), rv(150, L), rv(100, L) // 5 * 5), "Brûle."), icon_sid=13813)
S['dynamite'] = SC.ranked('dynamite', 'mec', 2120, 54, 2, "Dynamite", 12, 30000, 2000, lambda L, k: (
    {'Effect1': 31, 'EffectBasePoints1': 99, 'EffectDieSides1': 1, 'DmgClass': 3, 'EffectRadiusIndex1': RADIUS[8],
     'Effect2': 6, 'EffectApplyAuraName2': 3, 'EffectBasePoints2': rv(100, L) // 5 - 1, 'EffectDieSides2': 1,
     'EffectImplicitTargetA2': 16, 'EffectImplicitTargetB2': 0, 'EffectRadiusIndex2': RADIUS[8], 'EffectAmplitude2': 1000,
     'DurationIndex': DUR[5000], 'EffectBonusCoefficient1': 0, 'EffectBonusCoefficient2': 0, 'EffectBonusCoefficientFromAP2': 0.01,
     'EquippedItemClass': 2, 'EquippedItemSubClassMask': 1 << 3, 'School': 2},
    "Lance un bâton de dynamite : 100 %% des dégâts de l'arme à tous les ennemis de la zone et %d points de dégâts de Feu en 5 s." % (rv(100, L) // 5 * 5),
    "Brûle."), icon_sid=4062)
S['meca'] = SC.single('meca', 'mec', 13165, 22, "Aspect méca",
    "Augmente votre armure de 25 % et réduit le temps d'incantation de vos sorts de 0,5 s. Un seul aspect actif à la fois.",
    1000, 0, 5, icon_sid=12749, tooltip="Armure augmentée, incantations accélérées.",
    Effect1=6, EffectApplyAuraName1=101, EffectMiscValue1=1, EffectBasePoints1=24, EffectDieSides1=1, EffectImplicitTargetA1=1,
    Effect2=6, EffectApplyAuraName2=107, EffectMiscValue2=10, EffectBasePoints2=-501, EffectDieSides2=1, EffectImplicitTargetA2=1,
    EffectTriggerSpell2=0, ProcFlags=0, ProcChance=101, DurationIndex=DUR[-1])
GROUPS['aspect'].append(S['meca'])
S['animal'] = SC.single('animal', 'bes', 13165, 28, "Aspect animal",
    "Votre familier inflige 15 % de dégâts en plus et son armure est augmentée de 25 %. Un seul aspect actif à la fois.",
    1000, 0, 5, icon_sid=13161, tooltip="Familier renforcé.",
    Effect1=6, EffectApplyAuraName1=4, EffectMiscValue1=0, EffectBasePoints1=0, EffectDieSides1=1, EffectImplicitTargetA1=1,
    Effect2=0, EffectApplyAuraName2=0, EffectTriggerSpell2=0, ProcFlags=0, ProcChance=101, DurationIndex=DUR[-1])
GROUPS['aspect'].append(S['animal'])
AFFECT = []
AFFECT.append((S['meca'], 1, SG.mask('long') | SG.mask('precision') | SG.mask('bombe') | SG.mask('dynamite')))

# sorts vanilla du chasseur ouverts au Sniper (familier, Feindre la mort) : (sort, niveau, onglet)
SNIPER_VANILLA = [(1515, 10, 'bes'), (883, 10, 'bes'), (2641, 10, 'bes'), (982, 10, 'bes'), (6991, 10, 'bes'),
                  (5149, 10, 'bes'), (5384, 22, 'tir')]

# ======================================================================== Métamorphe
MG = Gen(7, range(36, 64))          # famille druide
MC = Ctx(MG, 63000, {'tot': 573, 'dru': 134, 'ang': 574}, 7, META)
M = {}
NOFORM = {'Stances': 0, 'StancesNot': 0, 'PowerType': 0}
SHOCK_CAT = 1260

def mr(key, tree, base, lv0, n, name, mpct, cd, cast, per, icon_sid=None):
    def per2(L, k):
        sets, d, t = per(L, k)
        out = dict(NOFORM); out.update(sets)
        return out, d, t
    return MC.ranked(key, tree, base, lv0, n, name, mpct, cd, cast, per2, icon_sid=icon_sid)

def ms(key, tree, base, lv, name, desc, cd, cast, mpct, icon_sid=None, tooltip='', **sets):
    out = dict(NOFORM); out.update(sets)
    return MC.single(key, tree, base, lv, name, desc, cd, cast, mpct, icon_sid=icon_sid, tooltip=tooltip, **out)

def lohi(a, b, L):
    lo, hi = rv(a, L), rv(b, L)
    return lo, hi, lo - 1, hi - lo + 1

def _terre(L, k):
    lo, hi, bp, ds = lohi(480, 510, L)
    return ({'EffectBasePoints1': bp, 'EffectDieSides1': ds, 'EffectBonusCoefficient1': 0.43, 'EffectBonusCoefficientFromAP1': 0.15,
             'Category': SHOCK_CAT, 'CategoryRecoveryTime': 10000, 'RecoveryTime': 0, 'DurationIndex': DUR[2000]},
            "Inflige %d à %d points de dégâts de Nature et interrompt l'incantation de la cible pendant 2 s. "
            "Recharge partagée avec Horion de feu." % (lo, hi), '')
M['terre'] = mr('terre', 'tot', 8042, 1, 9, "Horion de terre", 9, 0, 0, _terre)
M['remous'] = mr('remous', 'tot', 774, 1, 9, "Remous", 8, 3000, 0, lambda L, k: (
    {'EffectBasePoints1': rv(250, L) // 10 - 1, 'EffectDieSides1': 1, 'EffectAmplitude1': 1000, 'DurationIndex': DUR[10000],
     'EffectBonusCoefficient1': 0.067},
    "Rend %d points de vie à la cible en 10 s." % (rv(250, L) // 10 * 10), "Récupère des points de vie."), icon_sid=774)
M['lien'] = mr('lien', 'tot', 21562, 2, 9, "Lien spirituel", 12, 0, 0, lambda L, k: (
    {'EffectBasePoints1': rv(54, L) - 1, 'EffectDieSides1': 1, 'Reagent1': 0, 'ReagentCount1': 0, 'DurationIndex': DUR[7200000]},
    "Augmente l'Endurance de tous les membres du groupe de %d pendant 2 h." % rv(54, L), "Endurance augmentée."), icon_sid=21562)
M['tonnerre'] = mr('tonnerre', 'tot', 8921, 4, 8, "Tonnerre", 10, 1000, 0, lambda L, k: (
    {'Effect1': 6, 'EffectApplyAuraName1': 101, 'EffectMiscValue1': 1, 'EffectBasePoints1': -11, 'EffectDieSides1': 1,
     'Effect2': 6, 'EffectApplyAuraName2': 3, 'EffectBasePoints2': rv(300, L) // 10 - 1, 'EffectDieSides2': 1,
     'EffectAmplitude2': 1000, 'DurationIndex': DUR[10000], 'School': 3, 'EffectBonusCoefficient2': 0.067,
     'EffectBonusCoefficientFromAP2': 0.02, 'EffectBonusCoefficient1': 0},
    "Inflige %d points de dégâts de Nature en 10 s et réduit l'armure de la cible de 10 %%." % (rv(300, L) // 10 * 10),
    "Armure réduite, subit des dégâts de Nature."), icon_sid=403)
M['feu'] = mr('hfeu', 'dru', 8050, 6, 8, "Horion de feu", 9, 0, 0, lambda L, k: (
    {'EffectBasePoints1': rv(280, L) - 1, 'EffectDieSides1': rv(300, L) - rv(280, L) + 1,
     'EffectBasePoints2': rv(200, L) // 10 - 1, 'EffectDieSides2': 1, 'EffectAmplitude2': 1000, 'DurationIndex': DUR[10000],
     'EffectBonusCoefficient1': 0.43, 'EffectBonusCoefficientFromAP1': 0.15, 'EffectBonusCoefficient2': 0.067,
     'EffectBonusCoefficientFromAP2': 0.02, 'Category': SHOCK_CAT, 'CategoryRecoveryTime': 10000, 'RecoveryTime': 0},
    "Inflige %d à %d points de dégâts de Feu puis %d en 10 s. Recharge partagée avec Horion de terre." % (rv(280, L), rv(300, L), rv(200, L) // 10 * 10),
    "Brûle."))
M['perçant'] = ms('percant', 'ang', 355, 8, "Cri perçant", "Provoque la cible, qui vous attaque pendant 3 s.", 3000, 0, 3,
                  icon_sid=355, tooltip="Provoqué.", Category=0, CategoryRecoveryTime=0, RangeIndex=RANGE[20])
M['appel'] = ms('appel', 'ang', 1160, 10, "Cri d'appel",
                "Réduit de 10 % la puissance d'attaque des ennemis à moins de 20 mètres pendant 6 s.", 15000, 0, 5,
                tooltip="Puissance d'attaque réduite.", EffectApplyAuraName1=166, EffectBasePoints1=-11, EffectDieSides1=1,
                EffectRadiusIndex1=RADIUS[20], DurationIndex=DUR[6000])
M['recup'] = mr('recup', 'tot', 8936, 12, 7, "Récupération", 14, 3000, 2000, lambda L, k: (
    {'EffectBasePoints1': rv(320, L) - 1, 'EffectDieSides1': rv(360, L) - rv(320, L) + 1, 'EffectBonusCoefficient1': 0.57,
     'EffectBasePoints2': rv(85, L) // 5 - 1, 'EffectDieSides2': 1, 'EffectAmplitude2': 1000, 'DurationIndex': DUR[5000],
     'EffectBonusCoefficient2': 0.066},
    "Rend %d à %d points de vie à la cible, puis %d en 5 s." % (rv(320, L), rv(360, L), rv(85, L) // 5 * 5), "Récupère."))
M['massive'] = ms('massive', 'ang', 25780, 14, "Armure massive",
                  "Double la menace que vous générez et augmente votre armure de 10 %. Buff de spé, exclusif.", 1000, 0, 5,
                  tooltip="Menace doublée, armure augmentée.", EffectBasePoints1=99, EffectDieSides1=1, EffectMiscValue1=127,
                  Effect2=6, EffectApplyAuraName2=101, EffectMiscValue2=1, EffectBasePoints2=9, EffectDieSides2=1, EffectImplicitTargetA2=1,
                  DurationIndex=DUR[-1])
M['lunaire'] = mr('lunaire', 'dru', 8921, 16, 7, "Éclair lunaire", 7, 3000, 0, lambda L, k: (
    {'School': 6, 'Effect1': 2, 'EffectApplyAuraName1': 0, 'EffectImplicitTargetA1': 6,
     'EffectBasePoints1': rv(100, L) - 1, 'EffectDieSides1': rv(115, L) - rv(100, L) + 1,
     'EffectBonusCoefficient1': 0, 'EffectBonusCoefficientFromAP1': 0.075,
     'Effect2': 6, 'EffectApplyAuraName2': 3, 'EffectBasePoints2': rv(100, L) // 10 - 1, 'EffectDieSides2': 1,
     'EffectAmplitude2': 1000, 'DurationIndex': DUR[10000], 'StackAmount': 2, 'EffectBonusCoefficient2': 0,
     'EffectBonusCoefficientFromAP2': 0.02},
    "Inflige %d à %d points de dégâts d'Arcanes puis %d en 10 s, cumulable 2 fois. Basé sur la puissance d'attaque." % (rv(100, L), rv(115, L), rv(100, L) // 10 * 10),
    "Brûlure lunaire."))
M['renfo'] = ms('renfo', 'dru', 12042, 18, "Renforcement",
                "Augmente de 20 % votre puissance d'attaque, votre vitesse d'attaque et les dégâts de vos sorts. Buff de spé, exclusif.",
                1000, 0, 5, icon_sid=12880, tooltip="Puissance, vitesse et dégâts augmentés de 20 %.",
                EffectApplyAuraName1=166, EffectBasePoints1=19, EffectDieSides1=1, EffectMiscValue1=0,
                EffectApplyAuraName2=138, EffectBasePoints2=19, EffectDieSides2=1, EffectMiscValue2=0,
                EffectApplyAuraName3=79, EffectBasePoints3=19, EffectDieSides3=1, EffectMiscValue3=126, DurationIndex=DUR[-1])
M['bouclier_eau'] = ms('beau', 'tot', 12042, 22, "Bouclier d'eau",
                       "Augmente de 25 % votre Intelligence et vos soins, et vous permet de conserver 25 % de votre régénération "
                       "de mana pendant les incantations. Buff de spé, exclusif.", 1000, 0, 5, icon_sid=24398,
                       tooltip="Intelligence, soins et régénération augmentés.",
                       EffectApplyAuraName1=137, EffectMiscValue1=3, EffectBasePoints1=24, EffectDieSides1=1,
                       EffectApplyAuraName2=134, EffectMiscValue2=0, EffectBasePoints2=24, EffectDieSides2=1,
                       EffectApplyAuraName3=136, EffectMiscValue3=127, EffectBasePoints3=24, EffectDieSides3=1, DurationIndex=DUR[-1])
GROUPS['meta'] = [M['massive'], M['renfo'], M['bouclier_eau']]
M['epuration'] = ms('epuration', 'tot', 4987, 22, "Épuration",
                    "Dissipe un effet de magie, une malédiction et un poison de la cible.", 0, 0, 6,
                    EffectMiscValue1=1, EffectMiscValue2=2, EffectMiscValue3=4)
M['stellaire'] = mr('stellaire', 'dru', 2912, 24, 6, "Feu stellaire", 11, 12000, 0, lambda L, k: (
    {'EffectBasePoints1': rv(384, L) - 1, 'EffectDieSides1': rv(432, L) - rv(384, L) + 1, 'EffectBonusCoefficient1': 0,
     'EffectBonusCoefficientFromAP1': 0.15,
     'Effect2': 6, 'EffectApplyAuraName2': 3, 'EffectImplicitTargetA2': 6, 'EffectBasePoints2': rv(156, L) // 5 - 1,
     'EffectDieSides2': 1, 'EffectAmplitude2': 1000, 'DurationIndex': DUR[5000], 'EffectBonusCoefficientFromAP2': 0.03},
    "Inflige %d à %d points de dégâts d'Arcanes puis %d en 5 s. Basé sur la puissance d'attaque." % (rv(384, L), rv(432, L), rv(156, L) // 5 * 5),
    "Brûlure stellaire."))
M['coup_bouclier'] = mr('cbouclier', 'ang', 23922, 26, 6, "Coup de bouclier", 8, 6000, 0, lambda L, k: (
    {'Effect1': 2, 'EffectImplicitTargetA1': 24, 'EffectRadiusIndex1': RADIUS[8], 'EffectMiscValue1': 0,
     'EffectBasePoints1': rv(280, L) - 1, 'EffectDieSides1': rv(320, L) - rv(280, L) + 1, 'EffectBonusCoefficientFromAP1': 0.15,
     'Effect2': 0, 'EffectBonusCoefficient1': 0, 'School': 0, 'Category': 0, 'CategoryRecoveryTime': 0},
    "Frappe de votre bouclier tous les ennemis devant vous : %d à %d points de dégâts et une menace élevée. Nécessite un bouclier." % (rv(280, L), rv(320, L)),
    ''))
M['coup_tonnerre'] = mr('ctonnerre', 'ang', 6343, 26, 6, "Coup de tonnerre", 8, 12000, 0, lambda L, k: (
    {'EffectBasePoints1': rv(180, L) - 1, 'EffectDieSides1': rv(210, L) - rv(180, L) + 1, 'EffectRadiusIndex1': RADIUS[10],
     'Effect2': 0, 'EffectApplyAuraName2': 0, 'School': 3, 'EffectBonusCoefficientFromAP1': 0.10, 'EffectBonusCoefficient1': 0,
     'Category': 0, 'CategoryRecoveryTime': 0},
    "Inflige %d à %d points de dégâts de Nature aux ennemis à moins de 10 mètres." % (rv(180, L), rv(210, L)), ''))
M['salve'] = mr('salve', 'tot', 1064, 32, 5, "Salve de guérison", 14, 18000, 3500, lambda L, k: (
    {'EffectBasePoints1': rv(215, L) - 1, 'EffectDieSides1': rv(240, L) - rv(215, L) + 1, 'EffectChainTarget1': 4,
     'DmgMultiplier1': 0.75, 'EffectBonusCoefficient1': 1.0},
    "Rend %d à %d points de vie à la cible, puis rebondit sur 3 autres alliés (75, 50 et 25 %%)." % (rv(215, L), rv(240, L)), ''))
M['enrage'] = ms('enrage', 'dru', 12042, 34, "Enragé", "Augmente vos dégâts de mêlée de 20 % pendant 15 s.", 300000, 0, 5,
                 icon_sid=12292, tooltip="Dégâts de mêlée augmentés de 20 %.",
                 EffectApplyAuraName1=79, EffectMiscValue1=1, EffectBasePoints1=19, EffectDieSides1=1,
                 Effect2=0, EffectApplyAuraName2=0, Effect3=0, EffectApplyAuraName3=0, DurationIndex=DUR[15000])
M['bouclier_elem'] = mr('belem', 'tot', 17, 36, 4, "Bouclier élémentaire", 12, 6000, 0, lambda L, k: (
    {'EffectBasePoints1': rv(335, L) - 1, 'EffectDieSides1': 1, 'DurationIndex': DUR[8000], 'EffectBonusCoefficient1': 0.10,
     'Category': 0, 'CategoryRecoveryTime': 0},
    "Entoure la cible d'un bouclier qui absorbe %d points de dégâts pendant 8 s." % rv(335, L), "Absorbe des dégâts."))
M['courroux'] = ms('courroux', 'ang', 12042, 38, "Courroux protecteur",
                   "Pendant 15 s, augmente vos points de vie maximum et votre armure de 30 %, et vos résistances de 60.",
                   180000, 0, 5, icon_sid=498, tooltip="Vie, armure et résistances augmentées.",
                   EffectApplyAuraName1=133, EffectBasePoints1=29, EffectDieSides1=1, EffectMiscValue1=0,
                   EffectApplyAuraName2=101, EffectMiscValue2=1, EffectBasePoints2=29, EffectDieSides2=1,
                   EffectApplyAuraName3=22, EffectMiscValue3=126, EffectBasePoints3=59, EffectDieSides3=1, DurationIndex=DUR[15000])
M['colere'] = mr('colere', 'dru', 78, 42, 4, "Colère", 8, 6000, 0, lambda L, k: (
    {'Effect1': 31, 'EffectBasePoints1': 49, 'EffectDieSides1': 1,
     'Effect2': 2, 'EffectImplicitTargetA2': 6, 'EffectBasePoints2': rv(150, L) - 1, 'EffectDieSides2': 1,
     'EffectBonusCoefficientFromAP2': 0.10,
     'Effect3': 6, 'EffectApplyAuraName3': 33, 'EffectImplicitTargetA3': 6, 'EffectBasePoints3': -21, 'EffectDieSides3': 1,
     'DurationIndex': DUR[6000], 'School': 3, 'PowerType': 0},
    "Un coup d'arme électrique : 50 %% des dégâts de l'arme plus %d points de dégâts de Nature, et ralentit la cible de 20 %% pendant 6 s." % rv(150, L),
    "Ralenti."), icon_sid=8042)
M['entrave'] = ms('entrave', 'ang', 853, 42, "Entrave", "Étourdit la cible pendant 3 s.", 15000, 0, 5, icon_sid=853,
                  tooltip="Étourdi.", DurationIndex=DUR[3000], Category=0, CategoryRecoveryTime=0)
M['jugement'] = mr('jugement', 'ang', 585, 44, 3, "Jugement", 8, 15000, 0, lambda L, k: (
    {'EffectBasePoints1': rv(350, L) - 1, 'EffectDieSides1': rv(400, L) - rv(350, L) + 1, 'EffectBonusCoefficient1': 0.43,
     'EffectBonusCoefficientFromAP1': 0.15},
    "Inflige %d à %d points de dégâts du Sacré à la cible." % (rv(350, L), rv(400, L)), ''), icon_sid=20271)
M['pluie'] = mr('pluie', 'tot', 596, 46, 3, "Pluie de guérison", 20, 60000, 2000, lambda L, k: (
    {'EffectBasePoints1': rv(160, L) - 1, 'EffectDieSides1': rv(175, L) - rv(160, L) + 1, 'EffectBonusCoefficient1': 0.75,
     'Effect2': 6, 'EffectApplyAuraName2': 8, 'EffectImplicitTargetA2': 20, 'EffectBasePoints2': rv(85, L) // 5 - 1,
     'EffectDieSides2': 1, 'EffectAmplitude2': 1000, 'DurationIndex': DUR[5000], 'EffectBonusCoefficient2': 0.03,
     'EffectRadiusIndex1': RADIUS[20], 'EffectRadiusIndex2': RADIUS[20]},
    "Rend %d à %d points de vie aux membres du groupe à moins de 20 mètres, puis %d en 5 s." % (rv(160, L), rv(175, L), rv(85, L) // 5 * 5),
    "Récupère."), icon_sid=10460)
M['massacre'] = ms('massacre', 'dru', 78, 52, "Massacre",
                   "Frappe avec les deux armes : 150 % des dégâts de l'arme principale et 150 % de l'arme en main gauche. "
                   "Avec un bouclier, la deuxième frappe se fait avec l'arme principale.", 12000, 0, 8, icon_sid=12294,
                   Effect1=31, EffectBasePoints1=149, EffectDieSides1=1, PowerType=0)
M['consecration'] = mr('consecration', 'ang', 20924, 56, 2, "Consécration", 12, 8000, 0, lambda L, k: (
    {'EffectBasePoints1': rv(384, L) // 8 - 1, 'EffectDieSides1': 1, 'Category': 0, 'CategoryRecoveryTime': 0},
    "Consacre le sol sous vous : %d points de dégâts du Sacré en 8 s aux ennemis qui s'y trouvent." % (rv(384, L) // 8 * 8), ''))
M['don'] = ms('don', 'tot', 21562, 60, "Don des esprits",
              "Augmente toutes les caractéristiques des membres du groupe de 30 pendant 2 h.", 0, 0, 20, icon_sid=21849,
              tooltip="Caractéristiques augmentées.", EffectMiscValue1=-1, EffectBasePoints1=29, EffectDieSides1=1,
              Reagent1=0, ReagentCount1=0, DurationIndex=DUR[7200000])

# ======================================================================== invocations, totems et sorts gérés par le module (étapes 3, 4, 5, 7)
CREATURES = []        # (entrée, nom, modèle, échelle, classe, PV, dégâts, armure, type, [(sort, cible, initial, répétition)])
NC = Ctx(NG, 62300, NSKILL, 9, NECRO)    # sorts cachés du Nécromancien (62300+)
MODULE = {}           # constantes exportées vers le module C++

def lin(v60):
    """valeur qui croît avec le niveau du lanceur (créatures) : (points de base, points par niveau)"""
    return int(round(v60 * 0.05)) - 1, v60 * 0.95 / 60.0

def cspell(ctx, key, base, name, cast=0, **sets):
    out = {'SpellLevel': 0, 'BaseLevel': 0, 'MaxLevel': 60, 'ManaCost': 0, 'PowerType': 0, 'Stances': 0, 'StancesNot': 0,
           'RecoveryTime': 0, 'Category': 0, 'CategoryRecoveryTime': 0, 'CastingTimeIndex': CAST[cast], 'Reagent1': 0,
           'ReagentCount1': 0, 'EquippedItemClass': -1, 'EquippedItemSubClassMask': 0, 'StartRecoveryTime': 0}
    out.update(sets)
    return ctx.trig(key, base, name, "", **out)

def dmg(n, v60, spread=0, school_eff=2, target=6):
    b, pl = lin(v60)
    d = {'Effect%d' % n: school_eff, 'EffectBasePoints%d' % n: b, 'EffectDieSides%d' % n: max(1, int(spread)),
         'EffectRealPointsPerLevel%d' % n: pl, 'EffectImplicitTargetA%d' % n: target, 'EffectApplyAuraName%d' % n: 0}
    return d

def per(n, v60_tick, aura=3, target=6, amp=1000):
    b, pl = lin(v60_tick)
    return {'Effect%d' % n: 6, 'EffectApplyAuraName%d' % n: aura, 'EffectBasePoints%d' % n: b, 'EffectDieSides%d' % n: 1,
            'EffectRealPointsPerLevel%d' % n: pl, 'EffectImplicitTargetA%d' % n: target, 'EffectAmplitude%d' % n: amp}

def none(n):
    return {'Effect%d' % n: 0, 'EffectApplyAuraName%d' % n: 0}

def weapon(n, pct, target=6):
    return {'Effect%d' % n: 31, 'EffectBasePoints%d' % n: pct - 1, 'EffectDieSides%d' % n: 1, 'EffectImplicitTargetA%d' % n: target,
            'EffectApplyAuraName%d' % n: 0}

def auraf(n, aura, misc, val, target=1):
    return {'Effect%d' % n: 6, 'EffectApplyAuraName%d' % n: aura, 'EffectMiscValue%d' % n: misc, 'EffectBasePoints%d' % n: val - 1,
            'EffectDieSides%d' % n: 1, 'EffectImplicitTargetA%d' % n: target}

def merge(*ds):
    out = {}
    for d in ds:
        out.update(d)
    return out

# ---------------------------------------------------------------- créatures du Nécromancien
C_SQ, C_GOULE, C_ABO, C_GIVRE, C_CHIEN, C_CK, C_WYRM = range(990500, 990507)
a = {}
a['sq_coup'] = cspell(NC, 'k_sq', 11976, "Coup d'épée", **merge(weapon(1, 100), dmg(2, 15, target=6)))
a['sq_saign'] = cspell(NC, 'k_sq', 172, "Saignement", School=0, DurationIndex=DUR[10000], Mechanic=15, **merge(per(1, 15), none(2), none(3)))
a['gh_croc'] = cspell(NC, 'k_goule', 11976, "Croc", **merge(weapon(1, 100), dmg(2, 25)))
a['gh_renov'] = cspell(NC, 'k_goule', 774, "Rénovation", DurationIndex=DUR[5000], **merge(per(1, 50, aura=8, target=21), none(2), none(3)))
a['abo_crochet'] = cspell(NC, 'k_abo', 11976, "Crochet", **merge(weapon(1, 110), none(2)))
a['abo_provoc'] = cspell(NC, 'k_abo', 1161, "Provocation de masse", EffectRadiusIndex1=RADIUS[10], DurationIndex=DUR[6000])
a['abo_vomi'] = cspell(NC, 'k_abo', 585, "Vomi", School=3, **merge(dmg(1, 200, 40, target=24), {'EffectRadiusIndex1': RADIUS[10]}))
a['gv_eclair'] = cspell(NC, 'k_givre', 585, "Éclair de givre", cast=1500, School=4, SpellVisual=visual(116), **dmg(1, 190, 20))
a['gv_bouclier'] = cspell(NC, 'k_givre', 11426, "Bouclier de givre", DurationIndex=DUR[15000],
                          **merge(per(1, 150, aura=69, target=1, amp=0), {'EffectMiscValue1': 127},
                                  per(2, 150, aura=69, target=27, amp=0), {'Effect2': 6, 'EffectMiscValue2': 127}))
a['gv_blizzard'] = cspell(NC, 'k_givre', 172, "Blizzard", School=4, DurationIndex=DUR[4000], SpellVisual=visual(10),
                          **merge(per(1, 60), {'EffectChainTarget1': 3}, none(2), none(3)))
a['ch_morsure'] = cspell(NC, 'k_chien', 11976, "Morsure", DurationIndex=DUR[5000], **merge(weapon(1, 100), per(2, 20)))
a['ch_cri'] = cspell(NC, 'k_chien', 13730, "Cri", DurationIndex=DUR[10000],
                     **merge(auraf(1, 101, 1, -15, target=22), {'EffectImplicitTargetB1': 15, 'EffectRadiusIndex1': RADIUS[10]},
                             auraf(2, 166, 0, -15, target=22), {'EffectImplicitTargetB2': 15, 'EffectRadiusIndex2': RADIUS[10]}))
a['ch_charge'] = cspell(NC, 'k_chien', 853, "Charge", DurationIndex=DUR[2000])
a['ck_frappe'] = cspell(NC, 'k_ck', 11976, "Frappe impie", DurationIndex=DUR[6000], StackAmount=2,
                        **merge(weapon(1, 120), per(2, 25), {'School': 5}))
a['ck_givre'] = cspell(NC, 'k_ck', 116, "Givre", DurationIndex=DUR[5000], **merge(auraf(1, 33, 0, -50, target=6), none(2)))
a['ck_buff'] = cspell(NC, 'k_ck', 21562, "Aura du chevalier", DurationIndex=DUR[3600000], Reagent1=0,
                      **merge(auraf(1, 137, -1, 10, target=37)))
a['ck_dnd'] = cspell(NC, 'k_ck', 26573, "Mort et décomposition", School=5, DurationIndex=DUR[5000],
                     **merge(per(1, 80, aura=3, target=18), {'Effect1': 27, 'EffectRadiusIndex1': RADIUS[8]}))
a['wy_givrefeu'] = cspell(NC, 'k_wyrm', 133, "Givrefeu", cast=1500, School=4, DurationIndex=DUR[4000],
                          **merge(dmg(1, 375, 50), per(2, 20)))
a['wy_souffle'] = cspell(NC, 'k_wyrm', 585, "Souffle de givre", School=4, **merge(dmg(1, 325, 50, target=24), {'EffectRadiusIndex1': RADIUS[10]}))
a['wy_buff'] = cspell(NC, 'k_wyrm', 12042, "Aura du wyrm", DurationIndex=DUR[3600000],
                      **merge(auraf(1, 79, 126, 10, target=27), none(2), none(3)))

def creature(entry, name, disp, scale, ucls, hp, dm, arm, ctype, spells, ranged=False):
    CREATURES.append((entry, name, disp, scale, ucls, hp, dm, arm, ctype, spells, ranged))

creature(C_SQ, "Squelette", 200, 1.0, 1, 0.35, 0.45, 1.0, 6, [(a['sq_coup'], 1, 1000, 2000), (a['sq_saign'], 1, 2000, 10000)])
creature(C_GOULE, "Goule", 646, 1.0, 1, 0.35, 0.45, 1.0, 6, [(a['gh_croc'], 1, 1000, 3000), (a['gh_renov'], 206, 3000, 5000)])
creature(C_ABO, "Abomination", 1693, 0.8, 1, 0.7, 0.6, 2.0, 6, [(a['abo_crochet'], 1, 1000, 2000), (a['abo_provoc'], 2, 500, 5000), (a['abo_vomi'], 1, 3000, 6000)])
creature(C_GIVRE, "Squelette de givre", 9783, 1.0, 8, 0.3, 0.35, 0.8, 6, [(a['gv_eclair'], 1, 0, 2000), (a['gv_bouclier'], 2, 1000, 15000), (a['gv_blizzard'], 1, 3000, 5000)], ranged=True)
creature(C_CHIEN, "Chien squelettique", 850, 0.9, 1, 0.35, 0.45, 1.0, 6, [(a['ch_morsure'], 1, 1000, 3000), (a['ch_cri'], 2, 2000, 10000), (a['ch_charge'], 1, 0, 25000)])
creature(C_CK, "Chevalier de la mort", 14591, 0.8, 1, 0.7, 0.7, 1.5, 6, [(a['ck_frappe'], 1, 1000, 3000), (a['ck_givre'], 1, 2000, 15000), (a['ck_buff'], 2, 0, 3600000), (a['ck_dnd'], 2, 3000, 8000)])
creature(C_WYRM, "Wyrm de givre", 16033, 0.12, 8, 0.6, 0.6, 1.0, 6, [(a['wy_givrefeu'], 1, 0, 2000), (a['wy_souffle'], 1, 3000, 10000), (a['wy_buff'], 2, 0, 3600000)], ranged=True)

# sorts d'invocation : sort visible (effet factice, le module invoque) + sort caché (invocation réelle)
NSUM = [('inv_squelette', 1, "Invocation : Squelette", C_SQ, 1, 200), ('inv_goule', 10, "Invocation : Goule", C_GOULE, 1, 646),
        ('inv_abo', 20, "Invocation : Abomination", C_ABO, 2, 1693), ('inv_givre', 30, "Invocation : Squelette de givre", C_GIVRE, 1, 9783),
        ('inv_chien', 40, "Invocation : Chien squelettique", C_CHIEN, 1, 850),
        ('inv_chevalier', 30, "Invocation : Chevalier de la mort", C_CK, 2, 14591), ('inv_wyrm', 40, "Invocation : Wyrm de givre", C_WYRM, 2, 16033)]
SUMMON_TABLE = []     # (sort visible, sort caché, sort caché 5 s Annihilation, entrée, coût)
ANNI_COUNT = {C_SQ: 6, C_GOULE: 5, C_CHIEN: 6, C_GIVRE: 5, C_ABO: 2, C_CK: 1, C_WYRM: 1}
for key, lv, name, entry, cost, disp in NSUM:
    front = n_single('invocation', 'inv', 688, lv, name, "Invoque un %s qui combat à vos côtés. Coûte %d point%s d'invocation." % (name.split(' : ')[1].lower(), cost, 's' if cost > 1 else ''),
                     0, 3000, 20, icon_sid=688 if cost == 1 else 712, Effect1=3, EffectImplicitTargetA1=1, EffectMiscValue1=entry,
                     DurationIndex=0, Category=0)
    hidden = cspell(NC, 'invocation', 12740, name, EffectMiscValue1=entry, DurationIndex=DUR[-1], EffectBasePoints1=0, EffectDieSides1=1,
                    EffectImplicitTargetA1=1, CastingTimeIndex=1)
    anni = cspell(NC, 'annihilation', 12740, "Annihilation", EffectMiscValue1=entry, DurationIndex=DUR[5000],
                  EffectBasePoints1=ANNI_COUNT[entry] - 1, EffectDieSides1=1, EffectImplicitTargetA1=1, EffectRadiusIndex1=RADIUS[5])
    N[key] = front
    SUMMON_TABLE.append((front, hidden, anni, entry, cost))
NOTEACH.update([N['inv_chevalier'], N['inv_wyrm']])

# sorts du Nécromancien qui agissent sur l'armée (effet factice, le module fait le reste)
def n_dummy(key, tree, lv0, nranks, name, mpct, cd, cast, desc_fn, v60=0, icon_sid=None, target=1, extra=None):
    def per_rank(L, k):
        v = rv(v60, L) if v60 else 0
        sets = {'Effect1': 3, 'EffectImplicitTargetA1': target, 'EffectBasePoints1': max(0, v - 1), 'EffectDieSides1': 1,
                'Effect2': 0, 'EffectApplyAuraName2': 0, 'Effect3': 0, 'EffectApplyAuraName3': 0, 'DurationIndex': 0,
                'EffectApplyAuraName1': 0}
        if extra:
            sets.update(extra)
        return sets, desc_fn(v), ''
    ctx = NCX
    ids = ctx.ranked(key, tree, 688, lv0, nranks, name, mpct, cd, cast, per_rank, icon_sid=icon_sid)
    return ids
NCX = Ctx(NG, 62400, NSKILL, 9, NECRO)
NSLA_EXTRA = NCX.sla
N['peste_explo'] = n_dummy('peste_explo', 'inv', 6, 8, "Explosion de peste", 12, 10000, 0,
                           lambda v: "Chacune de vos invocations explose de peste : %d points de dégâts de Nature aux ennemis à moins de 8 mètres." % v,
                           v60=130, icon_sid=2944)
N['berserk'] = n_dummy('berserk', 'inv', 24, 1, "Berserk", 8, 30000, 0,
                       lambda v: "Vos invocations gagnent 25 % de hâte, de dégâts et de puissance pendant 10 s.", icon_sid=19574)
N['mortexplo'] = n_dummy('mortexplo', 'inv', 28, 1, "Explosion de la mort", 10, 60000, 0,
                         lambda v: "Chaque invocation sacrifie 10 % de ses points de vie maximum et inflige autant de dégâts d'Ombre autour d'elle.",
                         icon_sid=17877)
N['renovation'] = n_dummy('renovation', 'inv', 30, 5, "Rénovation", 12, 1000, 0,
                          lambda v: "Rend %d points de vie en 10 s à chacune de vos invocations et à votre familier." % (v // 10 * 10),
                          v60=650, icon_sid=774)
N['sang'] = n_dummy('sang', 'inv', 48, 3, "Sang enflammé", 14, 10000, 0,
                    lambda v: "Enflamme vos invocations : chacune inflige %d points de dégâts de Feu aux ennemis à moins de 5 mètres, plus 120 en 5 s." % v,
                    v60=60, icon_sid=2894 if 2894 in SPR else 13795)
N['chevalier_renf'] = n_dummy('chevalier_renf', 'inv', 50, 1, "Chevalier renforcé", 15, 600000, 0,
                              lambda v: "Nécessite un Chevalier de la mort. Pendant 5 s, votre groupe ne subit plus de dégâts et le chevalier devient insensible.",
                              icon_sid=642)
N['annihilation'] = n_dummy('annihilation', 'inv', 60, 1, "Annihilation", 30, 300000, 0,
                            lambda v: "Invoque pendant 5 s une armée de squelettes, goules, chiens, squelettes de givre, abominations et chevaliers à 50 % de leur puissance.",
                            icon_sid=18540)
N['mort'] = n_dummy('mort', 'mal', 42, 1, "Trait de la mort", 15, 60000, 2000,
                    lambda v: "Applique à la cible toutes vos DoT apprises, à leur rang maximum.", target=6, icon_sid=17877,
                    extra={'RangeIndex': RANGE[30], 'EffectImplicitTargetA1': 6})
N['malefice'] = NCX.single('malefice', 'mal', 12042, 60, "Maléfice",
                           "Pendant 15 s, vos DoT infligent leurs dégâts deux fois plus vite et votre puissance des sorts est augmentée de 25 %.",
                           300000, 0, 20, icon_sid=603, tooltip="DoT accélérées.",
                           **merge(auraf(1, 79, 126, 25), none(2), none(3), {'DurationIndex': DUR[15000]}))
NOTEACH.update([])
# sorts cachés lancés par le module
h = {}
h['peste'] = cspell(NC, 'peste_explo', 585, "Explosion de peste", School=3, **merge(dmg(1, 130, target=22), {'EffectImplicitTargetB1': 15, 'EffectRadiusIndex1': RADIUS[8]}))
h['berserk'] = cspell(NC, 'berserk', 12042, "Berserk", DurationIndex=DUR[10000], **merge(auraf(1, 138, 0, 25, target=1), auraf(2, 79, 127, 25, target=1), none(3)))
h['mortexplo'] = cspell(NC, 'mortexplo', 585, "Explosion de la mort", School=5, **merge(dmg(1, 100, target=22), {'EffectImplicitTargetB1': 15, 'EffectRadiusIndex1': RADIUS[8]}))
h['renov'] = cspell(NC, 'renovation', 774, "Rénovation", DurationIndex=DUR[10000], **merge(per(1, 65, aura=8, target=1), none(2), none(3)))
h['sang'] = cspell(NC, 'sang', 585, "Sang enflammé", School=2, DurationIndex=DUR[5000],
                   **merge(dmg(1, 60, target=22), {'EffectImplicitTargetB1': 15, 'EffectRadiusIndex1': RADIUS[5]},
                           per(2, 24, target=22), {'EffectImplicitTargetB2': 15, 'EffectRadiusIndex2': RADIUS[5]}))
h['bulle'] = cspell(NC, 'chevalier_renf', 642, "Chevalier renforcé", DurationIndex=DUR[5000])
h['absorbe'] = cspell(NC, 'chevalier_renf', 12042, "Protection du chevalier", DurationIndex=DUR[5000],
                      **merge(auraf(1, 87, 127, -100, target=1), none(2), none(3)))
h['affaibli'] = cspell(NC, 'annihilation', 12042, "Puissance réduite", DurationIndex=DUR[-1],
                       **merge(auraf(1, 79, 127, -50, target=1), none(2), none(3)))
h['camou'] = cspell(NC, 'camouflage', 3680, "Camouflage", DurationIndex=DUR[-1])
h['malefice_tick'] = cspell(NC, 'malefice', 585, "Maléfice", School=5, **dmg(1, 1))
for _k in ('peste', 'mortexplo', 'sang', 'renov', 'malefice_tick'):
    for _sp in NG.spells:
        if _sp['id'] == h[_k]:
            for _e in (1, 2, 3):
                _sp['sets']['EffectRealPointsPerLevel%d' % _e] = 0
MODULE['necro'] = dict(summons=SUMMON_TABLE, hidden=h, dots=['mot', 'corruption', 'vol', 'malediction', 'peste', 'maudit'])

# ---------------------------------------------------------------- Sniper : bêtes, tourelle, canon, robots, sorts gérés par le module
SCX = Ctx(SG, 62800, SC.skills, 3, SNIPER)
C_SANG, C_TIGRE, C_OURS, C_DINO, C_TOUR, C_CANON, C_ROBOT = range(990510, 990517)
b = {}
b['sa_charge'] = cspell(SCX, 'sa_charge', 853, "Charge", DurationIndex=DUR[1000])
b['sa_morsure'] = cspell(SCX, 'sa_morsure', 11976, "Morsure", **merge(weapon(1, 100), none(2)))
b['ti_griffe'] = cspell(SCX, 'ti_griffe', 11976, "Griffe", **merge(weapon(1, 100), none(2)))
b['ti_cri'] = cspell(SCX, 'ti_cri', 12042, "Cri félin", DurationIndex=DUR[10000], **merge(auraf(1, 138, 0, 25, target=1), auraf(2, 138, 0, 25, target=27), none(3)))
b['ou_morsure'] = cspell(SCX, 'ou_morsure', 11976, "Morsure", **merge(weapon(1, 100), none(2)))
b['ou_cri'] = cspell(SCX, 'ou_cri', 1161, "Cri d'ours", DurationIndex=DUR[4000],
                     **merge({'EffectRadiusIndex1': RADIUS[20]}, auraf(2, 166, 0, -20, target=22), {'EffectImplicitTargetB2': 15, 'EffectRadiusIndex2': RADIUS[20]}))
b['di_arrach'] = cspell(SCX, 'di_arrach', 11976, "Arrachage", DurationIndex=DUR[5000], **merge(weapon(1, 100), per(2, 20)))
b['di_cri'] = cspell(SCX, 'di_cri', 12042, "Cri du dinosaure", DurationIndex=DUR[10000], **merge(auraf(1, 166, 0, 25, target=1), auraf(2, 166, 0, 25, target=27), none(3)))
b['to_tir'] = cspell(SCX, 'tourelle', 585, "Tir de tourelle", School=0, SpellVisual=visual(6660), **dmg(1, 45, 10))
b['ca_tir'] = cspell(SCX, 'canon', 133, "Boulet", School=0, DurationIndex=DUR[5000], StackAmount=5, **merge(dmg(1, 140), per(2, 10)))
b['ro_elec'] = cspell(SCX, 'tirmeca', 116, "Électrocution", School=3, DurationIndex=DUR[3000], StackAmount=3,
                      **merge(auraf(1, 33, 0, -20, target=6), dmg(2, 20)))
creature(C_SANG, "Sanglier", 607, 1.0, 1, 0.5, 0.6, 1.0, 1, [(b['sa_charge'], 1, 0, 10000), (b['sa_morsure'], 1, 1000, 2000)])
creature(C_TIGRE, "Tigre blanc", 9953, 1.0, 1, 0.5, 0.6, 1.0, 1, [(b['ti_griffe'], 1, 500, 1500), (b['ti_cri'], 2, 0, 10000)])
creature(C_OURS, "Ours brun", 3201, 1.0, 1, 0.7, 0.5, 1.5, 1, [(b['ou_morsure'], 1, 1000, 2000), (b['ou_cri'], 2, 0, 8000)])
creature(C_DINO, "Dinosaure", 5239, 0.45, 1, 0.6, 0.7, 1.0, 1, [(b['di_arrach'], 1, 500, 1500), (b['di_cri'], 2, 0, 10000)])
creature(C_TOUR, "Tourelle", 6978, 0.6, 1, 0.3, 0.1, 1.0, 9, [(b['to_tir'], 1, 0, 500)], ranged=True)
creature(C_CANON, "Canon à boulets", 10753, 0.8, 1, 0.4, 0.1, 1.0, 9, [(b['ca_tir'], 1, 0, 2000)], ranged=True)
creature(C_ROBOT, "Robot", 5926, 0.4, 1, 0.2, 0.35, 1.0, 9, [(b['ro_elec'], 1, 1000, 3000)])
BEAST_CAT = 1270
BEASTS = [('inv_sanglier', 12, "Sanglier", C_SANG, 607), ('inv_tigre', 26, "Tigre blanc", C_TIGRE, 9953),
          ('inv_ours', 44, "Ours brun", C_OURS, 3201), ('inv_dino', 60, "Dinosaure", C_DINO, 5239)]
BEAST_HIDDEN = []
for key, lv, name, entry, disp in BEASTS:
    S[key] = SC.single(key, 'bes', 12740, lv, name, "Invoque un %s de votre niveau pendant 10 s. Recharge partagée de 60 s entre les bêtes." % name.lower(),
                       0, 2000 if lv < 60 else 0, 8, icon_sid=883, EffectMiscValue1=entry, DurationIndex=DUR[10000], EffectBasePoints1=0,
                       EffectDieSides1=1, EffectImplicitTargetA1=1, Category=BEAST_CAT, CategoryRecoveryTime=60000)
    BEAST_HIDDEN.append(cspell(SCX, 'appel', 12740, name, EffectMiscValue1=entry, DurationIndex=DUR[10000], EffectBasePoints1=0,
                               EffectDieSides1=1, EffectImplicitTargetA1=1, CastingTimeIndex=1))
S['tourelle'] = SC.single('tourelle', 'mec', 12740, 24, "Tourelle", "Pose une tourelle qui tire toutes les 0,5 s pendant 10 s.",
                          60000, 2000, 10, icon_sid=12749, EffectMiscValue1=C_TOUR, DurationIndex=DUR[10000], EffectBasePoints1=0,
                          EffectDieSides1=1, EffectImplicitTargetA1=1, Category=1271, CategoryRecoveryTime=0)
S['canon'] = SC.single('canon', 'mec', 12740, 32, "Canon à boulets",
                       "Pose un canon qui tire un boulet toutes les 2 s pendant 10 s ; chaque boulet laisse une brûlure cumulable 5 fois.",
                       30000, 2500, 12, icon_sid=4068, EffectMiscValue1=C_CANON, DurationIndex=DUR[10000], EffectBasePoints1=0,
                       EffectDieSides1=1, EffectImplicitTargetA1=1, Category=1272, CategoryRecoveryTime=0)
S['tirmeca'] = SC.ranked('tirmeca', 'mec', 2643, 48, 3, "Tir méca", 11, 20000, 2000, lambda L, k: (
    merge(RANGED, weapon(1, 60), {'EffectChainTarget1': 0},
          {'Effect2': 2, 'EffectBasePoints2': rv(80, L) - 1, 'EffectDieSides2': rv(100, L) - rv(80, L) + 1, 'EffectImplicitTargetA2': 6,
           'EffectBonusCoefficientFromAP2': 0.10, 'EffectChainTarget2': 0},
          {'Effect3': 42, 'EffectMiscValue3': C_ROBOT, 'EffectBasePoints3': 2, 'EffectDieSides3': 1, 'EffectImplicitTargetA3': 1,
           'EffectApplyAuraName3': 0}, {'DurationIndex': DUR[10000], 'School': 0}),
    "Inflige 60 %% des dégâts de l'arme plus %d à %d, et 3 robots de votre niveau surgissent pendant 10 s." % (rv(80, L), rv(100, L)), ''),
    icon_sid=12749)
S['recul'] = SC.single('recul', 'tir', 688, 6, "Recul", "Vous fait bondir de 15 mètres en arrière.", 3000, 0, 3, icon_sid=781,
                       **merge({'Effect1': 3, 'EffectImplicitTargetA1': 1}, none(2), none(3), {'DurationIndex': 0}))
S['triple'] = SC.single('triple', 'tir', 12042, 34, "Triple aspect",
                        "Pendant 15 s, cumule les effets des trois aspects : puissance d'attaque et dégâts physiques +10 %, armure +25 %.",
                        180000, 0, 8, icon_sid=20043, tooltip="Trois aspects actifs.",
                        **merge(auraf(1, 166, 0, 10), auraf(2, 79, 1, 10), auraf(3, 101, 1, 25), {'DurationIndex': DUR[15000]}))
S['appel'] = SC.single('appel', 'bes', 688, 50, "Appel animal",
                       "Invoque pendant 10 s toutes les bêtes que vous connaissez, à 50 % de leurs caractéristiques.", 300000, 0, 20,
                       icon_sid=883, **merge({'Effect1': 3, 'EffectImplicitTargetA1': 1}, none(2), none(3), {'DurationIndex': 0}))
S['ordre'] = SC.single('ordre', 'bes', 688, 58, "Ordre",
                       "Vos familiers et vos bêtes deviennent enragés pendant 20 s : taille, dégâts, hâte et puissance d'attaque +25 %.",
                       300000, 0, 10, icon_sid=19574, **merge({'Effect1': 3, 'EffectImplicitTargetA1': 1}, none(2), none(3), {'DurationIndex': 0}))
S['magique'] = SC.single('magique', 'tir', 12042, 60, "Balle magique",
                         "Pendant 10 s, chacun de vos tirs applique les effets des balles de feu, d'eau, de givre et de roche. Lancer une autre balle l'annule.",
                         600000, 0, 10, icon_sid=12042, tooltip="Balles combinées.",
                         **merge(auraf(1, 4, 0, 1), none(2), none(3), {'DurationIndex': DUR[10000]}))
GROUPS['balle'].append(S['magique'])
hs = {}
hs['enrage'] = cspell(SCX, 'ordre', 12042, "Ordre", DurationIndex=DUR[20000],
                      **merge(auraf(1, 61, 0, 25), auraf(2, 79, 127, 25), auraf(3, 138, 0, 25)))
hs['animal'] = cspell(SCX, 'animal_pet', 12042, "Aspect animal", DurationIndex=DUR[-1], SpellIconID=icon(13161),
                      **merge(auraf(1, 79, 127, 15), auraf(2, 101, 1, 25), none(3)))
hs['affaibli'] = cspell(SCX, 'appel', 12042, "Puissance réduite", DurationIndex=DUR[-1], **merge(auraf(1, 79, 127, -50), none(2), none(3)))
MODULE['sniper'] = dict(beasts=[S[k] for k, *_ in BEASTS], beast_hidden=BEAST_HIDDEN, hidden=hs,
                        bullets={'feu': S['feu'], 'eau': S['eau'], 'givre': S['givre'], 'roche': S['roche']})
# talents devenus actifs
S['elite'] = SC.single('elite', 'tir', 19434, 40, "Tir d'élite",
                       "Un tir dévastateur : 300 % des dégâts de l'arme et un saignement, puis Concentré : puissance d'attaque +20 % pendant 15 s.",
                       300000, 4000, 15, **merge(RANGED, weapon(1, 300), per(2, 80, aura=3), auraf(3, 166, 0, 20, target=1),
                                                 {'DurationIndex': DUR[15000], 'School': 0}))
S['mecafusil'] = SC.single('mecafusil', 'mec', 12042, 25, "Mécafusil",
                           "Pendant 15 s, votre vitesse de tir et vos dégâts physiques sont augmentés de 25 %.", 120000, 0, 8, icon_sid=12749,
                           tooltip="Tir accéléré.", **merge(auraf(1, 140, 0, 25), auraf(2, 79, 1, 25), none(3), {'DurationIndex': DUR[15000]}))
S['inventeur'] = SC.single('inventeur', 'mec', 12042, 40, "Inventeur",
                           "Pendant 20 s, vous devenez un robot : armure doublée, et 6 mini-robots combattent à vos côtés.", 480000, 0, 15,
                           icon_sid=12749, tooltip="Robot.",
                           **merge(auraf(1, 56, 6225, 1), auraf(2, 101, 1, 100),
                                   {'Effect3': 42, 'EffectMiscValue3': C_ROBOT, 'EffectBasePoints3': 5, 'EffectDieSides3': 1,
                                    'EffectImplicitTargetA3': 1, 'EffectApplyAuraName3': 0}, {'DurationIndex': DUR[20000]}))
NOTEACH.update([S['elite'], S['mecafusil'], S['inventeur']])

# ---------------------------------------------------------------- Métamorphe : totems, transformations, sorts gérés par le module
MCX = Ctx(MG, 63300, MC.skills, 7, META)
TOTEM_BASE_ENTRY = 990520
TOTEMS = {}
def totem(key, slot_effect, lv0, n, name, icon_sid, disp_src, passive_fn, desc_fn, mpct):
    ids = []
    for k, L in enumerate(rank_levels(lv0, n)):
        entry = TOTEM_BASE_ENTRY + len(TOTEMS)
        passive = passive_fn(L, entry)
        TOTEMS[entry] = (name, disp_src, passive)
        sid = MC.nid()
        sets = common(L, 1000, 0, mpct, icon_sid, base_cls=7)
        sets.update(NOFORM)
        sets.update({'Effect1': slot_effect, 'EffectMiscValue1': entry, 'EffectImplicitTargetA1': 41 + (slot_effect - 87),
                     'DurationIndex': DUR[60000], 'EffectBasePoints1': 0, 'EffectDieSides1': 1})
        ids.append(MG.add(sid, 8190, name, desc_fn(L), "Rang %d" % (k + 1), key=key, sets=sets))
        MC.sla.append((MC.skills['tot'], sid))
    MG.chain_ranks(ids)
    return ids

def t_feu(L, entry):
    d = cspell(MCX, 'totem_feu_dmg', 8187, "Totem de feu", School=2, EffectBasePoints1=rv(55, L) - 1,
               EffectDieSides1=rv(65, L) - rv(55, L) + 1, EffectRealPointsPerLevel1=0, EffectRadiusIndex1=RADIUS[10],
               EffectBonusCoefficient1=0.05)
    return cspell(MCX, 'totem_feu_p', 8188, "Totem de feu", EffectTriggerSpell1=d, EffectAmplitude1=3000, DurationIndex=DUR[-1])
def t_eau(L, entry):
    hh = cspell(MCX, 'totem_eau_soin', 5672 if 5672 in SPR else 774, "Totem d'eau", DurationIndex=DUR[5000],
                **merge({'Effect1': 10, 'EffectBasePoints1': rv(10, L) - 1, 'EffectDieSides1': 1, 'EffectImplicitTargetA1': 20,
                         'EffectRadiusIndex1': RADIUS[30], 'EffectApplyAuraName1': 0, 'EffectRealPointsPerLevel1': 0},
                        {'Effect2': 6, 'EffectApplyAuraName2': 8, 'EffectBasePoints2': max(1, rv(33, L) // 5) - 1, 'EffectDieSides2': 1,
                         'EffectImplicitTargetA2': 20, 'EffectRadiusIndex2': RADIUS[30], 'EffectAmplitude2': 1000,
                         'EffectRealPointsPerLevel2': 0}, none(3)))
    return cspell(MCX, 'totem_eau_p', 8188, "Totem d'eau", EffectTriggerSpell1=hh, EffectAmplitude1=3000, DurationIndex=DUR[-1])
def t_roche(L, entry):
    return cspell(MCX, 'totem_roche_p', 8076 if 8076 in SPR else 5677, "Totem de roche", DurationIndex=DUR[-1],
                  **merge({'Effect1': 35, 'EffectApplyAuraName1': 101, 'EffectMiscValue1': 1, 'EffectBasePoints1': 9, 'EffectDieSides1': 1,
                           'EffectImplicitTargetA1': 1, 'EffectRadiusIndex1': RADIUS[30]},
                          {'Effect2': 35, 'EffectApplyAuraName2': 118, 'EffectMiscValue2': 127, 'EffectBasePoints2': 24, 'EffectDieSides2': 1,
                           'EffectImplicitTargetA2': 1, 'EffectRadiusIndex2': RADIUS[30]},
                          {'Effect3': 35, 'EffectApplyAuraName3': 29, 'EffectMiscValue3': 0, 'EffectBasePoints3': rv(60, L) - 1,
                           'EffectDieSides3': 1, 'EffectImplicitTargetA3': 1, 'EffectRadiusIndex3': RADIUS[30]}))
def t_givre(L, entry):
    d = cspell(MCX, 'totem_givre_dmg', 8187, "Totem de givre", School=4, DurationIndex=DUR[5000], StackAmount=3,
               **merge({'EffectBasePoints1': rv(20, L) - 1, 'EffectDieSides1': rv(25, L) - rv(20, L) + 1, 'EffectRealPointsPerLevel1': 0,
                        'EffectRadiusIndex1': RADIUS[10]},
                       {'Effect2': 6, 'EffectApplyAuraName2': 3, 'EffectBasePoints2': max(1, rv(38, L) // 5) - 1, 'EffectDieSides2': 1,
                        'EffectImplicitTargetA2': 22, 'EffectImplicitTargetB2': 15, 'EffectRadiusIndex2': RADIUS[10], 'EffectAmplitude2': 1000},
                       {'Effect3': 6, 'EffectApplyAuraName3': 33, 'EffectBasePoints3': -11, 'EffectDieSides3': 1,
                        'EffectImplicitTargetA3': 22, 'EffectImplicitTargetB3': 15, 'EffectRadiusIndex3': RADIUS[10]}))
    return cspell(MCX, 'totem_givre_p', 8188, "Totem de givre", EffectTriggerSpell1=d, EffectAmplitude1=3000, DurationIndex=DUR[-1])

M['totem_feu'] = totem('totem_feu', 87, 10, 8, "Totem de feu", 1535, 5929, t_feu,
                       lambda L: "Pose un totem de feu pendant 1 min : toutes les 3 s, %d à %d points de dégâts de Feu aux ennemis à moins de 10 mètres." % (rv(55, L), rv(65, L)), 6)
M['totem_eau'] = totem('totem_eau', 89, 20, 6, "Totem d'eau", 5394, 3573, t_eau,
                       lambda L: "Pose un totem d'eau pendant 1 min : toutes les 3 s, rend %d points de vie aux membres du groupe et %d en 5 s." % (rv(10, L), max(1, rv(33, L) // 5) * 5), 6)
M['totem_roche'] = totem('totem_roche', 88, 40, 4, "Totem de roche", 8071, 5873, t_roche,
                         lambda L: "Pose un totem de roche pendant 1 min : armure +10 %%, soins reçus +25 %% et Force +%d pour le groupe." % rv(60, L), 6)
M['totem_givre'] = totem('totem_givre', 90, 50, 3, "Totem de givre", 8181, 5926, t_givre,
                         lambda L: "Pose un totem de givre pendant 1 min : toutes les 3 s, %d à %d points de dégâts de Givre, %d en 5 s (cumulable 3 fois) et ralentissement de 10 %%." % (rv(20, L), rv(25, L), max(1, rv(38, L) // 5) * 5), 6)
M['appel_tot'] = ms('appel_tot', 'tot', 688, 30, "Appel totémique", "Pose en une fois tous vos totems appris (feu, eau, roche, givre).",
                    1000, 0, 0, icon_sid=8190, **merge({'Effect1': 3, 'EffectImplicitTargetA1': 1}, none(2), none(3), {'DurationIndex': 0}))
M['renvoi_tot'] = ms('renvoi_tot', 'tot', 688, 30, "Renvoi totémique", "Retire vos totems et vous rend 75 % de leur coût en mana.",
                     1000, 0, 0, icon_sid=8071, **merge({'Effect1': 3, 'EffectImplicitTargetA1': 1}, none(2), none(3), {'DurationIndex': 0}))
M['centaure'] = ms('centaure', 'tot', 12042, 40, "Totem suprême",
                   "Vous prenez la forme d'un centaure pendant 20 s : soins +50 % et coût de vos sorts réduit de 50 %.", 600000, 0, 10,
                   icon_sid=16190, tooltip="Forme de centaure.",
                   **merge(auraf(1, 56, 2967, 1), auraf(2, 136, 127, 50), auraf(3, 108, 14, -50), {'DurationIndex': DUR[20000]}))
M['ours'] = ms('ours', 'dru', 12042, 40, "Monstre totémique",
               "Vous prenez la forme d'un ours du berceau pendant 20 s : puissance d'attaque et vitesse d'attaque +50 %.", 600000, 0, 10,
               icon_sid=9634, tooltip="Forme d'ours.",
               **merge(auraf(1, 56, 12678, 1), auraf(2, 166, 0, 50), auraf(3, 138, 0, 50), {'DurationIndex': DUR[20000]}))
M['golem'] = ms('golem', 'ang', 12042, 40, "Bouclier totémique",
                "Vous prenez la forme d'un golem pendant 20 s : dégâts subis -60 % et points de vie +50 %.", 600000, 0, 10,
                icon_sid=9800 if 9800 in SPR else 498, tooltip="Forme de golem.",
                **merge(auraf(1, 56, 4872, 1), auraf(2, 87, 127, -60), auraf(3, 133, 0, 50), {'DurationIndex': DUR[20000]}))
NOTEACH.update([M['centaure'], M['ours'], M['golem']])
hm = {}
hm['esprit'] = cspell(MCX, 'esprit', 12042, "Esprit guérisseur", DurationIndex=DUR[-1],
                      **merge(auraf(1, 108, 0, 150), auraf(2, 108, 11, -50), none(3)))
hm['force'] = cspell(MCX, 'force', 12042, "Force de l'esprit", DurationIndex=DUR[-1], **merge(auraf(1, 29, 0, 1), none(2), none(3)))
hm['jug_eau'] = cspell(MCX, 'jugement', 12042, "Jugement de l'eau", DurationIndex=DUR[15000], **merge(auraf(1, 137, 4, 25), none(2), none(3)))
hm['jug_feu'] = cspell(MCX, 'jugement', 585, "Jugement du renfort", School=1, **dmg(1, 150))
hm['jug_ang'] = cspell(MCX, 'jugement', 774, "Jugement du gardien", DurationIndex=DUR[5000], **merge(per(1, 30, aura=8, target=1), none(2), none(3)))
for _sp in MG.spells:
    if _sp['id'] == hm['force']:
        _sp['sets']['EffectRealPointsPerLevel1'] = 0
MODULE['meta'] = dict(hidden=hm, totems=['totem_feu', 'totem_eau', 'totem_roche', 'totem_givre'])

# ======================================================================== talents gérés par le module (sorts cachés et sorts actifs)
h['tombe'] = cspell(NC, 'k_tombe', 12042, "Étreinte de la tombe", DurationIndex=DUR[-1],
                    **merge(auraf(1, 137, 2, 1), auraf(2, 79, 1, 1), none(3)))
h['maitre'] = cspell(NC, 'k_maitre', 12042, "Maître nécromancien", DurationIndex=DUR[-1],
                     **merge(auraf(1, 79, 127, 1), auraf(2, 87, 127, -1), none(3)))
h['lien'] = cspell(NC, 'k_lien', 12042, "Lien des morts", DurationIndex=DUR[-1],
                   **merge(auraf(1, 81, 127, 20, target=21), none(2), none(3)))
h['crepuscule'] = cspell(NC, 'k_crep', 12042, "Crépuscule", DurationIndex=DUR[10000], ProcCharges=1,
                         **merge(auraf(1, 108, 10, -100), none(2), none(3)))
h['fleau'] = cspell(NC, 'k_fleau', 116, "Fléau rampant", DurationIndex=DUR[10000], **merge(auraf(1, 33, 0, -30, target=6), none(2)))
h['morsure'] = cspell(NC, 'k_morsure', 116, "Morsure du froid", DurationIndex=DUR[3000], **merge(auraf(1, 33, 0, -20, target=6), none(2)))
h['synergie'] = cspell(NC, 'k_syn', 12042, "Synergie givrée", DurationIndex=DUR[10000], ProcCharges=1,
                       **merge(auraf(1, 108, 0, 15), none(2), none(3)))
h['pyro'] = cspell(NC, 'k_pyro', 853, "Pyroclasme", DurationIndex=DUR[3000])
ISB = [cspell(NC, 'k_isb', 17800, "Vulnérabilité à l'ombre", EffectBasePoints1=4 * r - 1, EffectDieSides1=1, DurationIndex=DUR[12000])
       for r in range(1, 6)]
# Fléau double : copies des DoT (autre identifiant, donc cumulables avec l'original)
NDUP = Ctx(NG, 62430, NSKILL, 9, NECRO)
DUPS = {}
for k in ['mot', 'corruption', 'vol', 'malediction', 'peste', 'maudit']:
    DUPS[k] = []
    for sp in [x for x in NG.spells if x.get('key') == k and x['id'] not in TRIGGERED]:
        d = NG.add(NDUP.nid(), sp['base'], sp['name'], sp['desc'], sp['rank'], tooltip=sp['tooltip'], key=k, sets=dict(sp['sets']))
        TRIGGERED.add(d)
        DUPS[k].append(d)
N['reanimation'] = NCX.single('reanimation', 'inv', 12042, 20, "Réanimation rapide",
                              "Votre prochaine invocation dans les 15 s est instantanée.", 300000, 0, 5, icon_sid=688,
                              tooltip="Prochaine invocation instantanée.",
                              **merge(auraf(1, 108, 10, -100), none(2), none(3), {'ProcCharges': 1, 'DurationIndex': DUR[15000]}))
N['amplification'] = NCX.single('amplification', 'mal', 12042, 20, "Amplification",
                                "Votre prochaine DoT inflige 50 % de dégâts en plus.", 180000, 0, 5, icon_sid=18288,
                                tooltip="Prochaine DoT amplifiée.",
                                **merge(auraf(1, 108, 22, 50), none(2), none(3), {'ProcCharges': 1, 'DurationIndex': DUR[30000]}))
NOTEACH.update([N['reanimation'], N['amplification']])
AFFECT += [(h['crepuscule'], 0, NG.mask('trait')), (h['synergie'], 0, NG.mask('eclair')),
           (N['reanimation'], 0, NG.mask('invocation')),
           (N['amplification'], 0, NG.mask('mot') | NG.mask('corruption') | NG.mask('vol') | NG.mask('malediction') | NG.mask('peste') | NG.mask('maudit'))]

# Sniper : griffon, compagnons de meute, tir à bout portant, sorts cachés
C_GRIFFON, C_MEUTE = 990517, 990518
b['gr_aile'] = cspell(SCX, 'gr_aile', 11976, "Coup d'aile", DurationIndex=DUR[5000], **merge(weapon(1, 100), per(2, 20)))
b['gr_attraper'] = cspell(SCX, 'gr_attraper', 18265, "Attraper", DurationIndex=DUR[10000], School=0,
                          **merge(per(1, 30, aura=53), none(2), none(3)))
b['me_morsure'] = cspell(SCX, 'me_morsure', 11976, "Morsure", **merge(weapon(1, 100), none(2)))
creature(C_GRIFFON, "Griffon", 1149, 0.8, 1, 0.6, 0.7, 1.0, 1, [(b['gr_aile'], 1, 500, 1500), (b['gr_attraper'], 1, 1000, 10000)])
creature(C_MEUTE, "Compagnon de meute", 604, 0.9, 1, 0.3, 0.3, 1.0, 1, [(b['me_morsure'], 1, 1000, 3000)])
S['inv_griffon'] = SC.single('inv_griffon', 'bes', 12740, 40, "Griffon",
                             "Invoque un griffon de votre niveau pendant 10 s : Coup d'aile et Attraper, qui draine la vie de la cible. Recharge partagée de 60 s entre les bêtes.",
                             0, 0, 8, icon_sid=883, EffectMiscValue1=C_GRIFFON, DurationIndex=DUR[10000], EffectBasePoints1=0,
                             EffectDieSides1=1, EffectImplicitTargetA1=1, Category=BEAST_CAT, CategoryRecoveryTime=60000)
NOTEACH.add(S['inv_griffon'])
MODULE['sniper']['beasts'].append(S['inv_griffon'])
MODULE['sniper']['beast_hidden'].append(cspell(SCX, 'appel', 12740, "Griffon", EffectMiscValue1=C_GRIFFON, DurationIndex=DUR[10000],
                                               EffectBasePoints1=0, EffectDieSides1=1, EffectImplicitTargetA1=1, CastingTimeIndex=1))
S['contact'] = SC.single('contact', 'bes', 3044, 15, "Tir à bout portant",
                         "Un tir à bout portant, utilisable au corps à corps : 100 % des dégâts de l'arme.", 4000, 0, 5,
                         icon_sid=19503, **merge(weapon(1, 100), {'RangeIndex': RANGE[10], 'School': 0, 'EffectBonusCoefficientFromAP1': 0}))
NOTEACH.add(S['contact'])
hs['meute'] = cspell(SCX, 'meute', 12740, "Compagnon de meute", EffectMiscValue1=C_MEUTE, DurationIndex=DUR[-1], EffectBasePoints1=0,
                     EffectDieSides1=1, EffectImplicitTargetA1=1, CastingTimeIndex=1)
hs['solitaire'] = cspell(SCX, 'solitaire', 12042, "Tireur solitaire", DurationIndex=DUR[-1], **merge(auraf(1, 79, 1, 1), none(2), none(3)))
hs['piege'] = cspell(SCX, 'piege', 853, "Piégeage", DurationIndex=DUR[4000], **merge(auraf(1, 26, 0, 1, target=6)))
hs['robot'] = cspell(SCX, 'robot', 12042, "Robots améliorés", DurationIndex=DUR[-1], **merge(auraf(1, 133, 0, 1), auraf(2, 79, 127, 1), none(3)))
hs['blinde'] = cspell(SCX, 'blinde', 12042, "Familier blindé", DurationIndex=DUR[-1], **merge(auraf(1, 10, 127, 1), auraf(2, 101, 1, 1), none(3)))
hs['cri'] = cspell(SCX, 'cri_plus', 116, "Cri bestial amélioré", DurationIndex=DUR[6000], **merge(auraf(1, 101, 1, -3, target=6), none(2)))

# Métamorphe : Voie de la guérison, Fougue lunaire, Égide angélique, Guérison ancestrale
hm['voie'] = cspell(MCX, 'voie', 12042, "Voie de la guérison", DurationIndex=DUR[15000], StackAmount=3,
                    **merge(auraf(1, 4, 0, 1, target=21), none(2), none(3)))
hm['voie_soin'] = cspell(MCX, 'voie', 8936, "Voie de la guérison", **merge({'Effect1': 10, 'EffectBasePoints1': 0, 'EffectDieSides1': 1,
                                                                            'EffectImplicitTargetA1': 21, 'EffectRealPointsPerLevel1': 0,
                                                                            'EffectBonusCoefficient1': 0}, none(2), none(3)))
hm['lunaire'] = cspell(MCX, 'fougue', 12042, "Fougue lunaire", DurationIndex=DUR[10000], StackAmount=3,
                       **merge(auraf(1, 138, 0, 5), none(2), none(3)))
hm['massacre_g'] = cspell(MCX, 'massacre', 78, "Massacre", AttributesEx3=SPR[78][9] | 0x01000000,
                         **merge(weapon(1, 150), none(2), none(3)))
hm['massacre_b'] = cspell(MCX, 'massacre', 78, "Massacre", **merge(weapon(1, 150), none(2), none(3)))
hm['egide'] = cspell(MCX, 'egide', 11426, "Égide angélique", DurationIndex=DUR[10000],
                     **merge({'EffectBasePoints1': 0, 'EffectDieSides1': 1, 'EffectMiscValue1': 127, 'EffectRealPointsPerLevel1': 0,
                              'EffectBonusCoefficient1': 0}))
ANCESTRAL = [cspell(MCX, 'k_ancestral', 16177, "Guérison ancestrale", EffectBasePoints1=8 * r - 1, EffectDieSides1=1)
             for r in range(1, 4)]
TAL_PROC = []         # (sort de talent, famille, masque, procFlags, procEx)

# ======================================================================== talents (étape 6)

# sorts débloqués par talent
N['maudit'] = n_dot('maudit', 'mal', 172, 30, 1, "Maudit", 5, 500, 10000, 0.67, 10000, 14, icon_sid=603)
NOTEACH.update(N['maudit'])
N['explosion'] = n_direct('explosion', 'mag', 686, 40, 1, "Explosion d'énergie", 5, 750, 820, 1.14, 4000, 120000, 30,
                          icon_sid=25311, desc_extra=" Combine la puissance de Trait d'ombre, Éclair de givre et Boule de feu.")
NOTEACH.update(N['explosion'])
_heals = ['remous', 'recup', 'salve', 'pluie', 'belem', 'vague']
M['vague'] = ms('vague', 'tot', 8936, 35, "Vague salvatrice", "Rend instantanément 1200 points de vie à la cible.", 60000, 0, 15,
                icon_sid=25297, Effect2=0, EffectApplyAuraName2=0, EffectBasePoints1=1199, EffectDieSides1=1,
                EffectBonusCoefficient1=0.43, CastingTimeIndex=1)
M['rapidite'] = ms('rapidite', 'tot', 12042, 30, "Rapidité de la nature",
                   "Votre prochain soin avec un temps d'incantation est instantané.", 180000, 0, 0, icon_sid=17116,
                   tooltip="Prochain soin instantané.", EffectApplyAuraName1=108, EffectMiscValue1=10, EffectBasePoints1=-101,
                   EffectDieSides1=1, Effect2=0, EffectApplyAuraName2=0, Effect3=0, EffectApplyAuraName3=0, ProcCharges=1,
                   DurationIndex=DUR[-1])
M['brecup'] = ms('brecup', 'ang', 12042, 25, "Bouclier de récupération",
                 "Réduit les dégâts subis de 50 % pendant 5 s et vous rend 85 points de vie en 5 s.", 45000, 0, 5, icon_sid=498,
                 tooltip="Dégâts subis réduits de 50 %.",
                 EffectApplyAuraName1=87, EffectMiscValue1=127, EffectBasePoints1=-51, EffectDieSides1=1,
                 EffectApplyAuraName2=8, EffectBasePoints2=16, EffectDieSides2=1, EffectAmplitude2=1000, EffectMiscValue2=0,
                 Effect3=0, EffectApplyAuraName3=0, DurationIndex=DUR[5000], EffectBonusCoefficient2=0.066)
M['sanctuaire'] = ms('sanctuaire', 'ang', 20911, 30, "Aura du sanctuaire",
                     "Pendant 10 min, les dégâts subis par la cible à chaque coup sont réduits de 24.", 0, 0, 6, icon_sid=20911,
                     EffectBasePoints1=-25, EffectDieSides1=1, DurationIndex=DUR[600000])
NOTEACH.update([M['vague'], M['rapidite'], M['brecup'], M['sanctuaire']])
S['instinct_buff'] = SC.trig('instinct', 13165, "Instinct sauvage", "", tooltip="Vitesse de tir augmentée de 30 %.",
                             Effect1=6, EffectApplyAuraName1=140, EffectBasePoints1=29, EffectDieSides1=1, EffectImplicitTargetA1=1,
                             Effect2=0, EffectApplyAuraName2=0, Effect3=0, EffectApplyAuraName3=0, ProcFlags=0, ProcChance=101,
                             DurationIndex=DUR[12000], ManaCost=0, SpellLevel=10)

TALG = Gen(0, [])
TAL_ID = [63500]
TAL_AFFECT = []
TALENT_ROWS = []
TAB_ROWS = []
DUMMY_TALENTS = []                  # talents sans effet serveur pour l'instant (code à venir)
PASSIVE_BASE = 17810

def kmask(gen, keys):
    m = 0
    for k in keys:
        m |= k if isinstance(k, int) else gen.mask(k)     # entier = masque brut (sorts vanilla)
    return m

def talent_spell(gen, name, rk, nranks, effects, desc, icon_sid):
    sid = TAL_ID[0]; TAL_ID[0] += 1
    sets = {'SpellIconID': icon(icon_sid), 'DurationIndex': DUR[-1], 'SpellLevel': 10, 'BaseLevel': 10, 'ManaCost': 0,
            'RecoveryTime': 0, 'Category': 0, 'CategoryRecoveryTime': 0, 'ProcFlags': 0, 'ProcChance': 101}
    for i in range(3):
        sets.update({'Effect%d' % (i + 1): 0, 'EffectApplyAuraName%d' % (i + 1): 0, 'EffectMiscValue%d' % (i + 1): 0,
                     'EffectBasePoints%d' % (i + 1): 0, 'EffectDieSides%d' % (i + 1): 1, 'EffectImplicitTargetA%d' % (i + 1): 1,
                     'EffectTriggerSpell%d' % (i + 1): 0, 'EffectItemType%d' % (i + 1): 0})
    # les modificateurs de sorts ne s'appliquent qu'aux sorts de la même famille que le sort de talent
    sets['SpellFamilyName'] = gen.family
    sets['SpellFamilyFlags'] = 0
    for i, e in enumerate(effects):
        n = i + 1
        if e[0] == 'mod':          # ('mod', type, pct, keys, valeur)
            _, typ, pct, keys, v = e
            sets.update({'Effect%d' % n: 6, 'EffectApplyAuraName%d' % n: 108 if pct else 107, 'EffectMiscValue%d' % n: typ,
                         'EffectBasePoints%d' % n: int(v) - 1})
            TAL_AFFECT.append((sid, i, kmask(gen, keys)))
        elif e[0] == 'aura':       # ('aura', aura, misc, valeur)
            _, aura, misc, v = e
            sets.update({'Effect%d' % n: 6, 'EffectApplyAuraName%d' % n: aura, 'EffectMiscValue%d' % n: misc,
                         'EffectBasePoints%d' % n: int(v) - 1})
        elif e[0] == 'proc':       # ('proc', sort déclenché, chance, flags[, famille, masque, procEx])
            trig, chance, flags = e[1], e[2], e[3]
            sets.update({'Effect%d' % n: 6, 'EffectApplyAuraName%d' % n: 42, 'EffectTriggerSpell%d' % n: trig,
                         'ProcFlags': flags, 'ProcChance': chance})
            if len(e) > 4:
                TAL_PROC.append((sid, e[4], e[5], flags, e[6]))
        elif e[0] == 'dummy':
            sets.update({'Effect%d' % n: 6, 'EffectApplyAuraName%d' % n: 4})
        elif e[0] == 'learn':      # ('learn', sort appris avec le talent, retiré au reset)
            sets.update({'Effect%d' % n: 36, 'EffectTriggerSpell%d' % n: e[1], 'EffectImplicitTargetA%d' % n: 1})
    TALG.add(sid, PASSIVE_BASE, name, desc, "Rang %d" % (rk + 1) if nranks > 1 else "", family=False, sets=sets)
    return sid

def tree(gen, tab_id, tab_name, classmask, order, bg, icon_sid, talents):
    TAB_ROWS.append((tab_id, tab_name, icon(icon_sid), classmask, order, bg))
    col = {}
    tid_of = {}
    for t in talents:
        tier, name, ranks, ic, spec, desc = t[:6]
        prereq = t[6] if len(t) > 6 else None
        c = col.get(tier, 0); col[tier] = c + 1
        ids = []
        if spec[0] == 'vanilla':
            ids = list(spec[1])
        elif spec[0] == 'spell':
            ids = [spec[1]]
        else:
            for rk in range(ranks):
                effs = spec[1](rk + 1) if callable(spec[1]) else spec[1]
                if spec[0] == 'dummy':
                    effs = [('dummy',)]
                ids.append(talent_spell(gen, name, rk, ranks, effs, desc(rk + 1) if callable(desc) else desc, ic))
            if spec[0] == 'dummy':
                DUMMY_TALENTS.append((tab_name, name))
        talent_id = 3000 + len(TALENT_ROWS)
        tid_of[name] = (talent_id, ranks)
        pre = tid_of.get(prereq) if prereq else None
        row = [talent_id, tab_id, tier - 1, c] + (ids + [0] * 9)[:9] + [pre[0] if pre else 0, 0, 0, (pre[1] - 1) if pre else 0, 0, 0, 0, 0]
        TALENT_ROWS.append(row)

def P(v):                           # pourcentage par rang
    return lambda r: v * r
def mod(typ, pct, keys, per):
    return lambda r: [('mod', typ, pct, keys, per * r)]
def aura(a, misc, per):
    return lambda r: [('aura', a, misc, per * r)]
D = ('dummy', None)

N_SUMMONS = ['inv_squelette', 'inv_goule', 'inv_abo', 'inv_givre', 'inv_chien', 'inv_chevalier', 'inv_wyrm']
N_SHADOW = ['trait', 'tirombre', 'mot', 'corruption', 'vol', 'malediction', 'peste', 'maudit', 'mort', 'explosion']
N_DOTS = ['mot', 'corruption', 'vol', 'malediction', 'peste', 'maudit']
N_MAG = ['trait', 'eclair', 'boule', 'tirombre', 'javelot', 'meteorite', 'tempete', 'explosion']
CM_N, CM_S, CM_M = CBIT[NECRO], CBIT[SNIPER], CBIT[META]

tree(NG, 400, "Invocateur", CM_N, 0, "WarlockSummoning", 688, [
    (1, "Étreinte de la tombe", 5, 18698, D, lambda r: "Augmente l'Endurance de vos invocations de %d %% et leurs attaques de mêlée de %.1f %%." % (2 * r, 1.5 * r)),
    (1, "Squelettes aguerris", 3, 18694, ('fx', mod(0, True, ['k_sq'], 10)), lambda r: "Augmente les dégâts du Coup d'épée et du Saignement du squelette de %d %%." % (10 * r)),
    (1, "Rénovation améliorée", 2, 18692, ('fx', mod(22, True, ['renovation'], 10)), lambda r: "Augmente les soins de Rénovation de %d %%." % (10 * r)),
    (2, "Horde grandissante", 1, 18710, D, "Vous donne 1 point d'invocation supplémentaire."),
    (2, "Goule vorace", 3, 18705, ('fx', mod(0, True, ['k_goule'], 10)), lambda r: "Augmente les dégâts du Croc et les soins de la goule de %d %%." % (10 * r)),
    (2, "Chair putride", 5, 18731, D, lambda r: "Augmente l'Endurance de vos invocations de %d %%." % (3 * r)),
    (3, "Maîtrise de l'invocation", 1, 18708, D, "Vous permet de porter toutes les armes."),
    (3, "Abomination améliorée", 3, 18754, ('fx', mod(0, True, ['k_abo'], 10)), lambda r: "Augmente l'armure et les dégâts du Vomi de l'abomination de %d %%." % (10 * r)),
    (3, "Réanimation rapide", 1, 18708, ('spell', N['reanimation']), "Votre prochaine invocation dans les 15 s est instantanée. Recharge 5 min."),
    (4, "Armée des morts", 1, 18709, D, "Vous donne 1 point d'invocation supplémentaire.", "Horde grandissante"),
    (4, "Pouvoir impie", 5, 18769, ('fx', mod(0, True, ['k_sq', 'k_goule', 'k_abo', 'k_givre', 'k_chien', 'k_ck', 'k_wyrm'], 3)), lambda r: "Augmente les dégâts de vos invocations de %d %%." % (3 * r)),
    (4, "Maître invocateur", 2, 18709, ('fx', lambda r: [('mod', 10, False, ['invocation'], -2000 * r), ('mod', 14, True, ['invocation'], -20 * r)]),
     lambda r: "Réduit le temps d'invocation de vos invocations de %d s et leur coût de %d %%." % (2 * r, 20 * r)),
    (5, "Invocation : Chevalier de la mort", 1, 18788, ('spell', N['inv_chevalier']), "Débloque le Chevalier de la mort (2 points d'invocation).", "Pouvoir impie"),
    (5, "Chiens de la crypte", 3, 18769, ('fx', mod(1, False, ['k_chien'], 500)), lambda r: "Augmente l'étourdissement de la Charge de %.1f s et la réduction d'armure du Cri de %d %%." % (0.5 * r, 3 * r)),
    (5, "Givre éternel", 2, 116, ('fx', mod(0, True, ['k_givre'], 15)), lambda r: "Augmente le Bouclier du squelette de givre de %d %% des PV max et son Blizzard de %d %%." % (r, 15 * r)),
    (6, "Légion", 1, 18710, D, "Vous donne 1 point d'invocation supplémentaire.", "Armée des morts"),
    (6, "Maître nécromancien", 5, 23785, D, lambda r: "Chaque type d'invocation différent actif augmente vos dégâts et ceux de l'armée de %.1f %% et réduit les dégâts subis d'autant." % (0.3 * r)),
    (6, "Berserk amélioré", 2, 18788, ('fx', lambda r: [('mod', 1, False, ['berserk'], 2000 * r), ('mod', 1, False, ['annihilation'], 1500 * r)]),
     lambda r: "Augmente la durée de Berserk de %d s et celle d'Annihilation de %.1f s." % (2 * r, 1.5 * r)),
    (7, "Invocation : Wyrm de givre", 1, 116, ('spell', N['inv_wyrm']), "Débloque le Wyrm de givre (2 points d'invocation)."),
    (7, "Lien des morts", 1, 19028, D, "20 % des dégâts que vous subissez sont transférés à votre invocation principale."),
])
tree(NG, 401, "Malédiction", CM_N, 1, "WarlockCurses", 172, [
    (1, "Emprise", 5, 18174, ('fx', mod(16, False, N_SHADOW, 2)), lambda r: "Augmente de %d %% la chance de toucher de vos DoT et sorts d'Ombre." % (2 * r)),
    (1, "Corruption améliorée", 5, 17810, ('fx', mod(22, True, ['corruption'], 4)), lambda r: "Augmente les dégâts de Corruption de %d %%." % (4 * r)),
    (2, "Mot de l'ombre amélioré", 3, 589, ('fx', mod(22, True, ['mot'], 5)), lambda r: "Augmente les dégâts de Mot de l'ombre de %d %%." % (5 * r)),
    (2, "Vol de vie amélioré", 5, 18265, ('fx', mod(22, True, ['vol'], 2)), lambda r: "Augmente les dégâts de Vol de vie de %d %%." % (2 * r)),
    (2, "Récolte d'âme", 2, 18213, D, lambda r: "Tuer une cible affectée par une de vos DoT vous rend %d %% de votre mana maximum." % (5 * r)),
    (3, "Malédiction améliorée", 3, 980, ('fx', mod(22, True, ['malediction'], 5)), lambda r: "Augmente les dégâts de Malédiction de %d %%." % (5 * r)),
    (3, "Concentration funeste", 4, 18182, ('fx', mod(10, False, ['mort'], -500)), lambda r: "Réduit le temps d'incantation de Trait de la mort de %.1f s." % (0.5 * r)),
    (3, "Amplification", 1, 18288, ('spell', N['amplification']), "Votre prochaine DoT inflige 50 % de dégâts en plus. Recharge 3 min."),
    (4, "Portée sinistre", 1, 18218, ('fx', mod(5, True, N_DOTS, 10)), "Augmente la portée de vos DoT de 10 %."),
    (4, "Crépuscule", 4, 18094, D, lambda r: "Chaque tick de Corruption ou Mot de l'ombre a %d %% de chance de rendre instantané votre prochain Trait d'ombre." % (2 * r)),
    (4, "Peste améliorée", 2, 2944, ('fx', mod(22, True, ['peste'], 7)), lambda r: "Augmente les dégâts de Peste de %d %%." % (7 * r)),
    (5, "Maudit", 1, 603, ('spell', N['maudit'][0]), "Débloque le sort Maudit : 500 points de dégâts d'Ombre en 10 s, recharge 10 s."),
    (5, "Fléau rampant", 1, 18223, D, "Peste ralentit la cible de 30 %."),
    (5, "Contagion", 4, 18265, D, lambda r: "À la mort d'une cible, %d %% de chance que ses DoT se propagent à l'ennemi le plus proche." % (25 * r)),
    (6, "Maîtrise de l'ombre", 5, 18271, ('fx', aura(79, 32, 2)), lambda r: "Augmente vos dégâts d'Ombre de %d %%." % (2 * r)),
    (6, "Trait de la mort amélioré", 2, 18265, ('fx', mod(11, False, ['mort'], -10000)), lambda r: "Réduit la recharge de Trait de la mort de %d s." % (10 * r)),
    (7, "Fléau double", 1, 18220, D, "Les DoT posées par Trait de la mort se cumulent avec la DoT d'origine (2 par cible).", "Maîtrise de l'ombre"),
    (7, "Maléfice amélioré", 2, 18220, ('fx', mod(11, False, ['malefice'], -30000)), lambda r: "Réduit la recharge de Maléfice de %d s." % (30 * r)),
])
tree(NG, 402, "Magicien", CM_N, 2, "WarlockDestruction", 686, [
    (1, "Trait d'ombre amélioré", 5, 17793, ('fx', lambda r: [('proc', ISB[r - 1], 100, 0x10000, 5, NG.mask('trait') | NG.mask('tirombre'), 2)]), lambda r: "Un critique de Trait d'ombre ou Tir d'ombre augmente de %d %% les dégâts d'Ombre subis par la cible pour 4 sorts." % (4 * r)),
    (1, "Cataclysme", 5, 17778, ('fx', mod(14, True, N_MAG, -2)), lambda r: "Réduit le coût en mana de vos sorts Magicien de %d %%." % (2 * r)),
    (2, "Fléau", 5, 17788, ('fx', lambda r: [('mod', 10, False, ['trait', 'eclair', 'boule'], -100 * r), ('mod', 10, False, ['tirombre'], -200 * r)]),
     lambda r: "Réduit le temps d'incantation de Trait d'ombre, Éclair de givre et Boule de feu de %.1f s, et de Tir d'ombre de %.1f s." % (0.1 * r, 0.2 * r)),
    (2, "Morsure du froid", 5, 116, D, lambda r: "Augmente le ralentissement d'Éclair de givre de %d %%." % (4 * r)),
    (3, "Dévastation", 5, 18130, ('fx', mod(7, False, N_MAG, 1)), lambda r: "Augmente de %d %% la chance de coup critique de vos sorts Magicien." % r),
    (3, "Synergie givrée", 2, 116, D, lambda r: "Javelot de glace augmente de %d %% les dégâts de votre prochain Éclair de givre." % (15 * r)),
    (3, "Synergie gelée", 2, 8056, ('fx', lambda r: [('mod', 0, True, ['javelot'], 12.5 * r), ('mod', 0, True, ['eclair'], 5 * r)]),
     lambda r: "Augmente les dégâts de Javelot de glace de %d %% et d'Éclair de givre de %d %%." % (12.5 * r, 5 * r)),
    (4, "Intensité", 2, 18135, ('fx', mod(9, True, N_MAG, 35)), lambda r: "Réduit de %d %% le recul de vos sorts quand vous subissez des dégâts." % (35 * r)),
    (4, "Portée destructrice", 1, 17917, ('fx', mod(5, True, N_MAG, 10)), "Augmente la portée de vos sorts Magicien de 10 %."),
    (4, "Boule de feu améliorée", 5, 133, ('fx', mod(22, True, ['boule'], 10)), lambda r: "Augmente les dégâts sur la durée de Boule de feu de %d %%." % (10 * r)),
    (5, "Pyroclasme", 2, 18096, D, lambda r: "Météorite a %d %% de chance d'étourdir la cible pendant 3 s." % (13 * r)),
    (5, "Tir d'ombre amélioré", 3, 17877, ('fx', mod(11, False, ['tirombre'], -1000)), lambda r: "Réduit la recharge de Tir d'ombre de %d s." % r),
    (5, "Ruine", 1, 17959, ('fx', mod(15, True, N_MAG, 100)), "Les coups critiques de vos sorts Magicien infligent 200 % des dégâts au lieu de 150 %.", "Dévastation"),
    (6, "Tempête élémentaire", 5, 18459, ('fx', aura(79, 4 | 16 | 32, 2)), lambda r: "Augmente vos dégâts de Feu, de Givre et d'Ombre de %d %%." % (2 * r)),
    (7, "Explosion d'énergie", 1, 25311, ('spell', N['explosion'][0]), "Débloque Explosion d'énergie : Trait d'ombre, Éclair de givre et Boule de feu réunis à 80 %. Incantation 4 s, recharge 2 min."),
    (7, "Néant prolongé", 2, 12042, ('fx', mod(1, False, ['tempete'], 2500)), lambda r: "Augmente la durée de Tempête du néant de %.1f s." % (2.5 * r)),
])

S_SHOTS = ['arcanes', 'saignant', 'long', 'multiple', 'precision', 'bestial', 'explosif', 'dynamite', 'bombe', 'cri', 'marque']
S_SUMMONS = ['inv_sanglier', 'inv_tigre', 'inv_ours', 'inv_dino', 'inv_griffon']
tree(SG, 403, "Bestial", CM_S, 0, "HunterBeastMastery", 1515, [
    (1, "Endurance des bêtes", 5, 19583, ('vanilla', [19583, 19584, 19585, 19586, 19587]), ""),
    (1, "Instinct sauvage", 5, 19552, ('fx', lambda r: [('proc', S['instinct_buff'], r, PROC_RANGED)]),
     lambda r: "Vos tirs ont %d %% de chance d'augmenter votre vitesse de tir de 30 %% pendant 12 s." % r),
    (2, "Cuir épais", 3, 19609, ('vanilla', [19609, 19610, 19612]), ""),
    (2, "Meute", 1, 19621, D, "Vous donne un familier permanent supplémentaire, à 30 % des caractéristiques du familier principal."),
    (2, "Tir au contact", 1, 19503, ('spell', S['contact']), ""),
    (2, "Balle d'eau maîtrisée", 1, 10497, ('fx', mod(22, True, ['eau_dot'], 50)), "Balle d'eau a sa propre recharge de 15 s et sa DoT passe à 10 % de la PA."),
    (3, "Fureur déchaînée", 5, 19616, ('vanilla', [19616, 19617, 19618, 19619, 19620]), ""),
    (3, "Tir bestial amélioré", 2, 19574, ('fx', lambda r: [('mod', 11, False, ['bestial'], -1000 * r), ('mod', 0, True, ['bestial'], 14 * r)]),
     lambda r: "Tir bestial inflige %d %% de dégâts en plus et sa recharge est réduite de %d s." % (14 * r, r)),
    (3, "Cri bestial amélioré", 3, 1160, D, lambda r: "Augmente la réduction d'armure de Cri bestial de %d %%." % (3 * r)),
    (4, "Férocité", 5, 19598, ('vanilla', [19598, 19599, 19600, 19601, 19602]), ""),
    (4, "Instinct partagé", 3, 19621, ('fx', mod(1, False, S_SUMMONS, 2000)), lambda r: "Augmente la durée des bêtes invoquées de %d s." % (2 * r)),
    (5, "Lien animal", 2, 19578, ('vanilla', [19578, 20895]), ""),
    (5, "Intimidation", 1, 19577, ('spell', 19577), ""),
    (5, "Discipline bestiale", 2, 19590, ('fx', mod(11, False, S_SUMMONS, -5000)), lambda r: "Réduit la recharge des bêtes invoquées de %d s." % (5 * r)),
    (6, "Frénésie", 5, 19621, ('vanilla', [19621, 19622, 19623, 19624, 19625]), ""),
    (6, "Grande meute", 1, 19621, D, "Vous donne un deuxième familier permanent supplémentaire.", "Meute"),
    (6, "Combattant sauvage", 3, 19574, ('fx', aura(79, 1, 1)), lambda r: "Augmente vos dégâts physiques de %d %%." % r),
    (7, "Invocation : Griffon", 1, 19574, ('spell', S['inv_griffon']), "Débloque le Griffon."),
    (7, "Ordre amélioré", 2, 19574, ('fx', mod(11, False, ['ordre'], -60000)), lambda r: "Réduit la recharge d'Ordre de %d s." % (60 * r)),
])
tree(SG, 404, "Tireur d'élite", CM_S, 1, "HunterMarksmanship", 19434, [
    (1, "Efficacité", 5, 19416, ('fx', mod(14, True, S_SHOTS, -2)), lambda r: "Réduit le coût de vos tirs de %d %%." % (2 * r)),
    (1, "Marque améliorée", 5, 19421, ('fx', mod(8, True, ['marque'], 3)), lambda r: "Augmente le bonus de Marque de %d %%." % (3 * r)),
    (2, "Tirs létaux", 5, 19426, ('vanilla', [19426, 19427, 19429, 19430, 19431]), ""),
    (2, "Balle de feu maîtrisée", 1, 13795, ('fx', mod(22, True, ['feu_dot'], 50)), "Balle de feu a sa propre recharge de 20 s et sa DoT passe à 10 % de la PA."),
    (2, "Tir des arcanes amélioré", 2, 3044, ('fx', mod(11, False, ['arcanes'], -500)), lambda r: "Réduit la recharge de Tir des arcanes de %.1f s." % (0.5 * r)),
    (3, "Œil de faucon", 3, 19498, ('fx', mod(5, False, S_SHOTS, 4)), lambda r: "Augmente la portée de vos tirs de %d m." % (4 * r)),
    (3, "Tir saignant amélioré", 5, 1978, ('fx', mod(22, True, ['saignant'], 5)), lambda r: "Augmente les dégâts sur la durée de Tir saignant de %d %%." % (5 * r)),
    (4, "Tirs dévastateurs", 5, 19485, ('fx', mod(15, True, S_SHOTS, 3)), lambda r: "Augmente les dégâts critiques de vos tirs de %d %%." % (3 * r)),
    (4, "Tireur solitaire", 5, 19434, D, lambda r: "Sans familier permanent, les dégâts de vos tirs sont augmentés de %d %%." % (4 * r)),
    (5, "Visée parfaite", 1, 19434, ('fx', mod(10, True, ['precision'], -100)), "Tir de précision devient instantané."),
    (5, "Barrage", 3, 19461, ('fx', mod(0, True, ['multiple', 'explosif'], 5)), lambda r: "Augmente les dégâts de Tir multiple et Tir explosif de %d %%." % (5 * r)),
    (5, "Tir de dispersion", 1, 19503, ('spell', 19503), ""),
    (6, "Spécialisation armes à feu", 5, 19507, ('vanilla', [19507, 19508, 19509, 19510, 19511]), ""),
    (6, "Triple aspect amélioré", 2, 20043, ('fx', mod(11, False, ['triple'], -30000)), lambda r: "Réduit la recharge de Triple aspect de %d s." % (30 * r)),
    (7, "Tir d'élite", 1, 19434, ('spell', S['elite']), "Tir long, Tir de précision, Tir saignant et Tir des arcanes en un seul tir à 75 %, puis Concentré. Recharge 5 min."),
    (7, "Tir d'élite amélioré", 2, 19434, ('fx', mod(11, False, ['elite'], -30000)), lambda r: "Réduit la recharge de Tir d'élite de %d s." % (30 * r)),
])
tree(SG, 405, "Mécanisme", CM_S, 2, "HunterSurvival", 12749, [
    (1, "Pièges ingénieux", 3, 19239, ('fx', mod(1, False, ['glace'], 500)), lambda r: "Augmente la durée de Piège de glace de %.1f s." % (0.5 * r)),
    (1, "Mécanique de précision", 5, 12749, ('fx', mod(0, True, ['tourelle', 'canon', 'tirmeca'], 3)), lambda r: "Augmente les dégâts de vos invocations méca de %d %%." % (3 * r)),
    (2, "Piégeage", 5, 19184, D, lambda r: "Bombe méca et Dynamite ont %d %% de chance d'immobiliser les cibles pendant 4 s." % (5 * r)),
    (2, "Balle de givre maîtrisée", 1, 116, ('fx', mod(22, True, ['givre_dot'], 50)), "Balle de givre a sa propre recharge de 15 s et sa DoT passe à 10 % de la PA."),
    (2, "Survivant", 5, 19255, ('fx', aura(133, 0, 2)), lambda r: "Augmente vos points de vie maximum de %d %%." % (2 * r)),
    (3, "Mécanique avancée", 3, 12749, ('fx', mod(11, False, ['tourelle'], -10000)), lambda r: "Réduit la recharge de Tourelle de %d s." % (10 * r)),
    (3, "Dissuasion", 1, 19263, ('spell', 19263), ""),
    (3, "Canon renforcé", 3, 12749, ('fx', mod(0, True, ['canon'], 5)), lambda r: "Augmente les dégâts par tir du Canon à boulets de %d %%." % (5 * r)),
    (4, "Mécafusil", 1, 12749, ('spell', S['mecafusil']), "Arme et invocations méca : hâte et dégâts x1,25 pendant 15 s. Recharge 2 min."),
    (4, "Maîtrise des explosifs", 3, 4068, ('fx', mod(0, True, ['bombe', 'dynamite', 'tirmeca'], 5)), lambda r: "Augmente les dégâts de Bombe méca, Dynamite et Tir méca de %d %%." % (5 * r)),
    (4, "Pied sûr", 3, 19290, ('vanilla', [19290, 19294, 24283]), ""),
    (5, "Instinct de tueur", 3, 19370, ('vanilla', [19370, 19371, 19373]), ""),
    (5, "Robots améliorés", 3, 12749, D, lambda r: "Augmente les caractéristiques des robots de Tir méca de %d %%." % (5 * r)),
    (5, "Contre-attaque", 1, 19306, ('spell', 19306), ""),
    (6, "Réflexes éclair", 5, 19168, ('vanilla', [19168, 19180, 19181, 24296, 24297]), ""),
    (6, "Familier blindé", 3, 19609, D, lambda r: "Augmente la menace et l'armure de votre familier de %d %%." % (10 * r)),
    (7, "Inventeur", 1, 12749, ('spell', S['inventeur']), "Robot 20 s : armure x2, incantations -1 s, recharges -50 %, 6 mini-robots et une tourelle. Recharge 8 min."),
    (7, "Inventeur amélioré", 2, 12749, ('fx', mod(11, False, ['inventeur'], -90000)), lambda r: "Réduit la recharge d'Inventeur de %d s." % (90 * r)),
])

M_TOTEMS = ['totem_feu', 'totem_eau', 'totem_roche', 'totem_givre']
tree(MG, 283, "Totémique", CM_M, 0, "ShamanRestoration", 10497, [
    (1, "Esprit guérisseur", 1, 774, D, "Soins et absorptions x2,5 et recharges des soins -50 %, si ni Renforcement ni Armure massive n'est actif."),
    (1, "Salve améliorée", 5, 1064, ('fx', mod(10, False, ['salve'], -200)), lambda r: "Réduit le temps d'incantation de Salve de guérison de %.1f s." % (0.2 * r)),
    (1, "Concentration des marées", 5, 16179, ('fx', mod(14, True, _heals, -1)), lambda r: "Réduit le coût de vos soins de %d %%." % r),
    (2, "Guérison ancestrale", 3, 16176, ('fx', lambda r: [('proc', ANCESTRAL[r - 1], 100, 0x4000, 0, 0, 2)]), lambda r: "Après un soin critique, l'armure de la cible est augmentée de %d %% pendant 15 s." % (8 * r)),
    (2, "Focalisation totémique", 5, 16173, ('fx', mod(14, True, M_TOTEMS, -5)), lambda r: "Réduit le coût de vos totems de %d %%." % (5 * r)),
    (2, "Remous amélioré", 2, 774, ('fx', mod(22, True, ['remous'], 5)), lambda r: "Augmente les soins de Remous de %d %%." % (5 * r)),
    (3, "Focalisation des soins", 5, 16181, ('fx', mod(9, True, _heals, 14)), lambda r: "Réduit de %d %% le recul de vos soins quand vous subissez des dégâts." % (14 * r)),
    (3, "Maîtrise totémique", 2, 16189, ('fx', mod(6, True, ['totem_feu_dmg', 'totem_givre_dmg', 'totem_eau_soin'], 25)), lambda r: "Augmente le rayon de vos totems de %d %%." % (25 * r)),
    (3, "Grâce curative", 2, 29187, ('fx', mod(2, True, _heals, -7.5)), lambda r: "Réduit de %.1f %% la menace générée par vos soins." % (7.5 * r)),
    (4, "Totems restaurateurs", 5, 16187, ('fx', mod(0, True, ['totem_eau_soin'], 5)), lambda r: "Augmente les soins du Totem d'eau de %d %%." % (5 * r)),
    (4, "Maîtrise des marées", 5, 16194, ('fx', mod(7, False, _heals, 1)), lambda r: "Augmente de %d %% la chance de coup critique de vos soins." % r),
    (5, "Voie de la guérison", 3, 8936, D, lambda r: "Chaque Récupération augmente de %d %% les Récupérations suivantes sur la même cible." % (6 * r)),
    (5, "Rapidité de la nature", 1, 17116, ('spell', M['rapidite']), ""),
    (6, "Purification", 5, 16178, ('fx', mod(0, True, _heals, 2)), lambda r: "Augmente vos soins de %d %%." % (2 * r)),
    (6, "Vague salvatrice", 1, 25297, ('spell', M['vague']), ""),
    (7, "Totem suprême", 1, 16190, ('spell', M['centaure']), "Centaure 20 s : régénération de mana x1,5, coût des sorts -50 %, soins x1,5, hâte x1,5. Recharge 10 min.", "Purification"),
])
tree(MG, 281, "Druidique", CM_M, 1, "DruidFeralCombat", 5487, [
    (1, "Savoir ancestral", 5, 17485, ('fx', aura(132, 0, 1)), lambda r: "Augmente votre mana maximum de %d %%." % r),
    (1, "Guidance de l'esprit", 3, 16180, ('fx', aura(54, 0, 1)), lambda r: "Augmente votre chance de toucher de %d %%." % r),
    (2, "Frappes tonitruantes", 5, 16305, ('fx', aura(52, 0, 1)), lambda r: "Augmente votre chance de coup critique de %d %%." % r),
    (2, "Totems de guerre", 2, 8190, ('fx', mod(0, True, ['totem_feu_dmg', 'totem_givre_dmg'], 12.5)), lambda r: "Augmente les dégâts des totems de feu et de givre de %.1f %%." % (12.5 * r)),
    (2, "Fougue lunaire", 3, 8921, D, lambda r: "Augmente la hâte par cumul d'Éclair lunaire de %d %%." % r),
    (3, "Force de l'esprit", 3, 16294, D, lambda r: "Convertit %d %% de votre Intelligence en Force." % (33 * r if r < 3 else 100)),
    (3, "Totems renforçants", 2, 8075, ('fx', mod(8, True, ['totem_roche_p'], 15)), lambda r: "Augmente le bonus de Force du Totem de roche de %d %%." % (15 * r)),
    (3, "Spécialisation ambidextre", 5, 674, ('fx', aura(122, 0, 5)), lambda r: "Augmente les dégâts de votre main gauche de %d %%." % (5 * r)),
    (4, "Rafale", 5, 12319, ('vanilla', [12319, 12971, 12972, 12973, 12974]), ""),
    (4, "Robustesse", 5, 16252, ('fx', aura(142, 1, 2)), lambda r: "Augmente votre armure de %d %%." % (2 * r)),
    (5, "Massacre amélioré", 1, 12294, ('fx', mod(0, True, ['massacre'], 25)), "Massacre inflige 25 % de dégâts en plus."),
    (5, "Armes élémentaires", 4, 16266, ('fx', mod(0, True, ['colere', 'lunaire', 'stellaire'], 3)), lambda r: "Augmente les dégâts de Colère, Éclair lunaire et Feu stellaire de %d %%." % (3 * r)),
    (5, "Parade", 1, 3127, ('spell', 3127), ""),
    (6, "Maîtrise des armes", 5, 16538, ('fx', aura(79, 1, 1)), lambda r: "Augmente vos dégâts physiques de %d %%." % r),
    (7, "Monstre totémique", 1, 9634, ('spell', M['ours']), "Ours du berceau 20 s : PA, Agilité, Force et hâte x1,5, Massacre toutes les 4 s. Recharge 10 min.", "Massacre amélioré"),
    (7, "Enragé amélioré", 2, 12292, ('fx', mod(11, False, ['enrage'], -60000)), lambda r: "Réduit la recharge d'Enragé de %d s." % (60 * r)),
])
tree(MG, 282, "Angélique", CM_M, 2, "PaladinProtection", 25780, [
    (1, "Redoute", 5, 20127, ('vanilla', [20127, 20130, 20135, 20136, 20137]), ""),
    (1, "Précision", 3, 20189, ('fx', aura(54, 0, 1)), lambda r: "Augmente votre chance de toucher de %d %%." % r),
    (2, "Robustesse", 5, 16252, ('fx', aura(142, 1, 2)), lambda r: "Augmente votre armure de %d %%." % (2 * r)),
    (2, "Défense anticipée", 5, 16254, ('fx', aura(49, 0, 1)), lambda r: "Augmente votre chance d'esquive de %d %%." % r),
    (2, "Cri d'appel amélioré", 1, 1160, ('fx', mod(8, False, ['appel'], -5)), "Augmente de 5 % la baisse de puissance d'attaque de Cri d'appel."),
    (3, "Force de l'esprit", 3, 16294, D, lambda r: "Convertit %d %% de votre Intelligence en Force." % (33 * r if r < 3 else 100)),
    (3, "Armure céleste", 1, 750, ('spell', 750), "Vous permet de porter des armures en plaques."),
    (3, "Spécialisation bouclier", 3, 20148, ('fx', aura(150, 0, 10)), lambda r: "Augmente de %d %% le montant bloqué par votre bouclier." % (10 * r)),
    (3, "Coup de tonnerre amélioré", 2, 6343, ('fx', mod(11, False, ['ctonnerre'], -2500)), lambda r: "Réduit la recharge de Coup de tonnerre de %.1f s." % (2.5 * r)),
    (4, "Entrave améliorée", 2, 853, ('fx', mod(11, False, ['entrave'], -1000)), lambda r: "Réduit la recharge d'Entrave de %d s." % r),
    (4, "Bouclier de récupération", 1, 498, ('spell', M['brecup']), ""),
    (4, "Courroux protecteur amélioré", 3, 19746, ('fx', mod(11, False, ['courroux'], -20000)), lambda r: "Réduit la recharge de Courroux protecteur de %d s." % (20 * r)),
    (4, "Jugement du gardien", 2, 20271, D, lambda r: "Augmente le soin sur la durée de Jugement de %d %%." % (25 * r)),
    (5, "Aura du sanctuaire", 1, 20911, ('spell', M['sanctuaire']), ""),
    (5, "Riposte", 2, 20177, ('vanilla', [20177, 20179]), ""),
    (5, "Égide angélique", 3, 9800, D, lambda r: "Quand vos points de vie passent sous 35 %%, un bouclier absorbe %d %% de vos PV max. Une fois par minute." % [3, 6, 10][r - 1]),
    (6, "Spécialisation arme à une main", 5, 20196, ('vanilla', [20196, 20197, 20198, 20199, 20200]), ""),
    (6, "Sol consacré", 1, 20924, ('fx', lambda r: [('mod', 22, True, ['consecration'], 20), ('mod', 2, True, ['consecration'], 20)]), "Augmente les dégâts et la menace de Consécration de 20 %."),
    (7, "Bouclier totémique", 1, 9800, ('spell', M['golem']), "Golem 20 s : dégâts subis -60 %, vie x1,5, Agilité et Force x1,5. Recharge 10 min.", "Aura du sanctuaire"),
    (7, "Golem renforcé", 2, 9800, ('fx', mod(1, False, ['golem'], 2500)), lambda r: "Augmente la durée de Bouclier totémique de %.1f s." % (2.5 * r)),
])

AFFECT += [(hm['esprit'], 0, kmask(MG, _heals)), (hm['esprit'], 1, kmask(MG, _heals)),
           (M['centaure'], 2, kmask(MG, _heals + M_TOTEMS + ['terre', 'hfeu', 'tonnerre']))]

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
        if sp['id'] in skip or sp['id'] in TRIGGERED or sp['id'] in NOTEACH:
            continue
        lv = sp['sets'].get('SpellLevel', 1)
        tid = TEACH[0]; TEACH[0] += 1
        TG.add(tid, TEACH_BASE, sp['name'], sp['desc'], sp['rank'], family=False,
               sets={'EffectTriggerSpell1': sp['id'], 'SpellLevel': lv, 'BaseLevel': lv, 'MaxLevel': 0,
                     'SpellIconID': sp['sets'].get('SpellIconID', SPR[sp['base']][117])})
        TRAINER_SPELLS.setdefault(template, []).append((tid, max(10, 9 * lv * lv), lv))

START_SPELLS[NECRO] = [N['armure'], N['trait'][0]]
teach_all(NG, 900, set(START_SPELLS[NECRO]))

START_SPELLS[SNIPER] = [S['arcanes'][0]]
teach_all(SG, 901, set(START_SPELLS[SNIPER]))
VANILLA_FR = {1515: "Dompter une bête", 883: "Appel du familier", 2641: "Renvoyer le familier", 982: "Ressusciter le familier",
              6991: "Nourrir le familier", 5149: "Dressage des bêtes", 5384: "Feindre la mort"}
for vs, lv, tree_ in SNIPER_VANILLA:
    tid = TEACH[0]; TEACH[0] += 1
    TG.add(tid, TEACH_BASE, VANILLA_FR[vs], "", "", family=False,
           sets={'EffectTriggerSpell1': vs, 'SpellLevel': lv, 'BaseLevel': lv, 'MaxLevel': 0, 'SpellIconID': icon(vs)})
    TRAINER_SPELLS.setdefault(901, []).append((tid, max(10, 9 * lv * lv), lv))
    SC.sla.append((SC.skills[tree_], vs))

START_SPELLS[META] = [M['terre'][0], M['remous'][0]]
teach_all(MG, 902, set(START_SPELLS[META]))

# 4e spécialisation des classes vanilla (section 6 bis du doc)
exec(open(OUT + 'spe4.py', encoding='utf-8').read())

# Bombe collante (demandée par Alexis le 01/11) : sort de bas niveau utilisable au corps à corps (pas d'arme à distance).
# Défini après tous les autres sorts du Sniper pour ne pas décaler leurs numéros.
from spellgen import dbc_col as _dcb
S['collante'] = SC.ranked('collante', 'mec', 133, 1, 9, "Bombe collante", 3, 3000, 0, lambda L, k: (
    {'SpellIconID': 937, 'SpellVisual': SPR[4068][_dcb('SpellVisual')], 'School': 2, 'RangeIndex': RANGE[20],
     'Effect1': 2, 'EffectImplicitTargetA1': 6, 'EffectBasePoints1': rv(90, L) - 1, 'EffectDieSides1': rv(110, L) - rv(90, L) + 1,
     'EffectBonusCoefficient1': 0, 'EffectBonusCoefficientFromAP1': 0.05,
     'Effect2': 6, 'EffectApplyAuraName2': 3, 'EffectImplicitTargetA2': 6, 'EffectBasePoints2': max(1, rv(150, L) // 5) - 1,
     'EffectDieSides2': 1, 'EffectAmplitude2': 1000, 'DurationIndex': DUR[5000], 'EffectBonusCoefficient2': 0,
     'EffectBonusCoefficientFromAP2': 0.01, 'Effect3': 0, 'EffectApplyAuraName3': 0},
    "Lance une bombe qui colle à la cible : %d à %d points de dégâts de Feu, puis %d points de dégâts de Feu en 5 s. "
    "Utilisable au corps à corps." % (rv(90, L), rv(110, L), max(1, rv(150, L) // 5) * 5),
    "Brûle."))
START_SPELLS[SNIPER].append(S['collante'][0])
for _sid in S['collante']:
    _sp = [x for x in SG.spells if x['id'] == _sid][0]
    _lv = _sp['sets']['SpellLevel']
    _tid = TEACH[0]; TEACH[0] += 1
    TG.add(_tid, TEACH_BASE, _sp['name'], _sp['desc'], _sp['rank'], family=False,
           sets={'EffectTriggerSpell1': _sid, 'SpellLevel': _lv, 'BaseLevel': _lv, 'MaxLevel': 0, 'SpellIconID': 937})
    TRAINER_SPELLS.setdefault(901, []).append((_tid, max(10, 9 * _lv * _lv), _lv))

# (gabarit, entrée, nom, sous-titre, PNJ modèle, décalage, modèle 3D ou 0)
TRAINERS = [
    (900, 990170, "Mortis Valcendre", "Maître nécromancien", 459, 0, 10427),       # Comté du Nord
    (900, 990171, "Séraphine Noirsuaire", "Maître nécromancien", 461, 0, 10427),   # Hurlevent, l'Agneau égorgé
    (900, 990172, "Zul'gash", "Maître nécromancien", 3156, 0, 0),                    # Vallée des Épreuves
    (900, 990173, "Vol'kesh", "Maître nécromancien", 3324, 0, 0),                    # Orgrimmar, la Faille de l'ombre
    (900, 990190, "Morbius Fielgrise", "Maître nécromancien", 4563, 0, 0),         # Fossoyeuse, quartier des Magiciens
    (900, 990191, "Lucrèce Sombretombe", "Maître nécromancien", 2126, 0, 0),       # Clairière de Tirisfal (Deathknell)
    (900, 990193, "Edgar Ossevide", "Maître nécromancien", 2127, 0, 0),            # Brill, à côté de Rupert Boch
    (901, 990174, "Thordin Visée-Sûre", "Maître sniper", 1231, 0, 0),               # Kharanos
    (901, 990192, "Brokk Poudre-Fine", "Maître sniper", 895, 0, 0),                # Val d'Est-Gel, Anvilmar (camp de départ)
    (901, 990175, "Dagna Poudrenoire", "Maître sniper", 5117, 0, 0),                # Forgefer, salle des Armes
    (901, 990176, "Grok Œil-de-Fer", "Maître sniper", 3154, 0, 0),                  # Vallée des Épreuves
    (901, 990177, "Mazgar Longuevue", "Maître sniper", 3352, 0, 0),                 # Orgrimmar, vallée de l'Honneur
    (902, 990178, "Eldra Changeforme", "Maître métamorphe", 911, 0, 0),             # Comté du Nord
    (902, 990179, "Oswin Racinebrune", "Maître métamorphe", 928, 0, 0),             # Hurlevent, cathédrale
    (902, 990180, "Hilda Peaudours", "Maître métamorphe", 912, 0, 0),               # Val d'Est-Gel
    (902, 990181, "Torvin Gardepierre", "Maître métamorphe", 5113, 0, 0),           # Forgefer
    (902, 990182, "Ruzga Peau-de-Loup", "Maître métamorphe", 3153, 0, 0),           # Vallée des Épreuves
    (902, 990183, "Tok'jin", "Maître métamorphe", 3354, 0, 0),                      # Orgrimmar
    (902, 990184, "Mathias Voile-d'Os", "Maître métamorphe", 2119, 0, 0),           # Clairière de Tirisfal (Deathknell)
    (902, 990185, "Ysolde Murmure-des-Tombes", "Maître métamorphe", 4593, 0, 0),    # Fossoyeuse
]

def trainer_sql():
    L = ["-- Maîtres de classe des classes custom",
         "DELETE FROM npc_trainer_template WHERE entry BETWEEN 900 AND 909;",
         "DELETE FROM creature WHERE guid BETWEEN 9903000 AND 9903099;",
         "DELETE FROM creature_template WHERE Entry BETWEEN 990170 AND 990185 OR Entry BETWEEN 990190 AND 990199;"]
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

# ======================================================================== sorts de changement de spécialisation (module specs)
# appris au déblocage de la 2e spé chez le maître de classe ; 5 s d'incantation, hors combat
from spellgen import dbc_col as _dcs
dc_attr = _dcs('Attributes')
SPG = Gen(0, [])
SPEC_SPELLS = [65500, 65501, 65502]
for _i, (_sid, _icon) in enumerate(zip(SPEC_SPELLS, (776, 1553, 1575))):
    SPG.add(_sid, 8690, "Spécialisation %d" % (_i + 1),
            "Active votre %s spécialisation : talents et barres d'action. Hors combat uniquement." % ("1re", "2e", "3e")[_i],
            family=False, sets={'Effect1': 3, 'Effect2': 0, 'EffectImplicitTargetA1': 1, 'EffectBasePoints1': 0, 'EffectMiscValue1': 0,
                                'CastingTimeIndex': 6, 'Category': 0, 'RecoveryTime': 0, 'CategoryRecoveryTime': 0,
                                'Attributes': SPR[8690][dc_attr] | 0x10000000, 'SpellIconID': _icon, 'SpellLevel': 0, 'BaseLevel': 0})

# buff de prestige (module modes) : +30 % d'expérience et d'or, appliqué en permanence par le module aux personnages prestige
from spellgen import dbc_col as _dcp
PRESTIGE_SPELL = 65505
SPG.add(PRESTIGE_SPELL, 8690, "Prestige", "Expérience et or gagnés augmentés de 30 %.",
        tooltip="Expérience et or gagnés augmentés de 30 %.",
        family=False, sets={'Effect1': 6, 'EffectApplyAuraName1': 4, 'EffectImplicitTargetA1': 1, 'EffectBasePoints1': 29, 'EffectDieSides1': 1,
                            'EffectMiscValue1': 0, 'Effect2': 0, 'EffectApplyAuraName2': 0, 'Effect3': 0, 'EffectApplyAuraName3': 0,
                            'CastingTimeIndex': 1, 'DurationIndex': DUR[-1], 'Category': 0, 'RecoveryTime': 0, 'CategoryRecoveryTime': 0,
                            'Attributes': 0x80000000, 'SpellVisual': 0, 'SpellIconID': SPR[14752][_dcp('SpellIconID')], 'SpellLevel': 0, 'BaseLevel': 0})

# ======================================================================== icônes (demandées par Alexis le 01/11)
ICON_FIX = {N['inv_squelette']: 61, N['inv_goule']: 108, N['inv_abo']: 313, N['inv_givre']: 94, N['inv_chien']: 1614,
            N['inv_chevalier']: 1241, N['inv_wyrm']: 56,
            S['inv_sanglier']: 1578, S['inv_tigre']: 916, S['inv_ours']: 1559, S['inv_dino']: 1584, S['inv_griffon']: 1583}
for _sid in S['dynamite']:
    ICON_FIX[_sid] = 355
for _g in [NG, SG, MG, TG]:
    for _sp in _g.spells:
        _k = _sp['id'] if _g is not TG else _sp['sets'].get('EffectTriggerSpell1')
        if _k in ICON_FIX:
            _sp['sets']['SpellIconID'] = ICON_FIX[_k]

# Tir saignant et Tir bestial : modèle Morsure de serpent (le tir automatique continue), effets de Flèche de dispersion
_TIRS_SERPENT = set(S['saignant']) | set(S['bestial'])
for _sp in SG.spells:
    if _sp['id'] in _TIRS_SERPENT:
        _st = _sp['sets']
        _st.setdefault('Effect1', 31)
        _st.setdefault('EffectApplyAuraName1', 0)
        _st.setdefault('Effect2', 6)
        _st.setdefault('EffectImplicitTargetA2', 6)

# ======================================================================== corrections générales des sorts clonés
from spellgen import dbc_col as _dc
_ATTR, _ATTRX = _dc('Attributes'), _dc('AttributesEx')
for _g in [NG, SG, MG] + [g for g, a, b in V4_GENS]:
    for _sp in _g.spells:
        st = _sp['sets']
        base = SPR[_sp['base']]
        # bit « renvoie le familier » (sorts clonés depuis Invocation d'un diablotin) : seulement pour les vraies invocations de familier
        # « se brise aux dégâts » hérité du sort modèle (ex. Flèche de dispersion pour Tir saignant) : seulement pour l'invisibilité
        _aif = st.get('AuraInterruptFlags', base[_dc('AuraInterruptFlags')])
        _auras = [st.get('EffectApplyAuraName%d' % _e, base[_dc('EffectApplyAuraName%d' % _e)]) for _e in (1, 2, 3)]
        if _aif & 2 and not any(a in (16, 18) for a in _auras):
            st['AuraInterruptFlags'] = _aif & ~2
        # « arrête l'attaque automatique » hérité du modèle : seulement pour l'invisibilité
        _at = st.get('Attributes', base[_ATTR])
        if _at & 0x100000 and not any(a in (16, 18) for a in _auras):
            st['Attributes'] = _at & ~0x100000
        ax = st.get('AttributesEx', base[_ATTRX])
        if ax & 1 and st.get('Effect1', base[_dc('Effect1')]) != 56:
            st['AttributesEx'] = ax & ~1
        # tirs du Sniper avec incantation : sans l'attribut « emplacement à distance », le client affiche la barre d'incantation
        # (les dégâts restent ceux de l'arme à distance et les munitions sont consommées : classe de dégâts « distance »)
        if _g is SG and st.get('CastingTimeIndex', base[_dc('CastingTimeIndex')]) not in (0, 1):
            at = st.get('Attributes', base[_ATTR])
            if at & 2:
                st['Attributes'] = at & ~2

# pas d'objet totem exigé (sorts clonés depuis des totems de Chaman) ; buffs permanents : icône seulement, pas d'effet sur le personnage
import struct as _struct
_SVD = open('/home/claude/wow/classes/dbc/SpellVisual.dbc', 'rb').read()
_n, _f, _rs, _ss = _struct.unpack('<4I', _SVD[4:20])
_SV = {}
for _i in range(_n):
    _r = list(_struct.unpack('<%di' % _f, _SVD[20 + _i * _rs:20 + (_i + 1) * _rs]))
    _SV[_r[0]] = _r
SV_NEW, _SV_CLONE = [], {}
def visuel_sans_etat(v):
    r = _SV.get(v)
    if not r or (r[4] == 0 and r[5] == 0):
        return v
    if v not in _SV_CLONE:
        c = list(r)
        c[0] = 6000 + len(SV_NEW)
        c[4] = c[5] = 0
        SV_NEW.append(c)
        _SV_CLONE[v] = c[0]
    return _SV_CLONE[v]
_PERMA = {DUR[-1], DUR[300000], DUR[600000], DUR[1800000], DUR[3600000], DUR[7200000]}
for _g in [NG, SG, MG, TALG, T4G] + [g for g, a, b in V4_GENS]:
    for _sp in _g.spells:
        st = _sp['sets']
        base = SPR[_sp['base']]
        st['Totem1'] = 0
        st['Totem2'] = 0
        effs = [st.get('Effect%d' % n, base[_dc('Effect%d' % n)]) for n in (1, 2, 3)]
        if any(e in (6, 35) for e in effs) and 56 not in effs and st.get('DurationIndex', base[_dc('DurationIndex')]) in _PERMA:
            # buff permanent : animation d'incantation et d'impact gardées, effet continu sur le personnage retiré
            # (copie du visuel sans « StateKit » ; les passifs n'ont aucun visuel)
            _v = st.get('SpellVisual', base[_dc('SpellVisual')])
            _passif = st.get('Attributes', base[_ATTR]) & 0x40
            st['SpellVisual'] = 0 if _passif else visuel_sans_etat(_v)

exec(open('/home/claude/wow/classes/confort.py', encoding='utf-8').read())

# ======================================================================== sorties
def all_ids(d):
    out = []
    for v in d.values():
        out += v if isinstance(v, list) else [v]
    return out

L = ["-- Sorts des classes custom (généré par gen_sorts.py)", "SET NAMES utf8mb4;"]
L += NG.sql(62000, 62499)
L += TG.sql(64500, 65499)
L += TALG.sql(63500, 64499)
L += trainer_sql()
# sorts de départ du Nécromancien (remplacent Trait de l'ombre et Peau de démon)
L.append("DELETE FROM playercreateinfo_spell WHERE class=%d AND Spell IN (686, 687);" % NECRO)
for race in (1, 5, 8):
    for sp in START_SPELLS[NECRO]:
        L.append("INSERT IGNORE INTO playercreateinfo_spell (race, class, Spell, Note) VALUES (%d, %d, %d, 'Necromancien');" % (race, NECRO, sp))
L.append("UPDATE playercreateinfo_action SET action=%d WHERE class=%d AND type=0 AND action=686;" % (N['trait'][0], NECRO))
L.append("UPDATE playercreateinfo_action SET action=%d WHERE class=%d AND type=0 AND action=687;" % (N['armure'], NECRO))
L += SG.sql(62500, 62999)
L.append("DELETE FROM playercreateinfo_spell WHERE class=%d AND Spell IN (2973);" % SNIPER)
for race in (2, 3):
    for sp in START_SPELLS[SNIPER]:
        L.append("INSERT IGNORE INTO playercreateinfo_spell (race, class, Spell, Note) VALUES (%d, %d, %d, 'Sniper');" % (race, SNIPER, sp))
L.append("UPDATE playercreateinfo_action SET action=%d WHERE class=%d AND type=0 AND action=2973;" % (S['arcanes'][0], SNIPER))
L += MG.sql(63000, 63499)
# 4e spé des classes vanilla : sorts, talents, sorts vanilla modifiés, rangs vendus par les maîtres de classe
for _g, _a, _b in V4_GENS:
    L += _g.sql(_a, _b)
L += T4G.sql(56000, 56999)
L += SPG.sql(65500, 65509)
L += AG.sql(65600, 65699)
# Pierre de foyer sans temps de recharge (demande d'Alexis)
VPATCH.setdefault(8690, {})['CategoryRecoveryTime'] = 0
from spellgen import dbc_col as _dbc_col
SPELL_PATCH = {}
for _sid, _cols in sorted(VPATCH.items()):
    L.append("UPDATE spell_template SET %s WHERE Id=%d;" % (", ".join("%s=%d" % (k, v) for k, v in _cols.items()), _sid))
    _p = {}
    for k, v in _cols.items():
        if k == 'SpellFamilyFlags':
            _p[161] = v & 0xffffffff; _p[162] = (v >> 32) & 0xffffffff
        else:
            _p[_dbc_col(k)] = v & 0xffffffff
    SPELL_PATCH[str(_sid)] = {str(k): v for k, v in _p.items()}
L.append("DELETE FROM spell_group_spell WHERE SpellId BETWEEN 55000 AND 55999;")
for _gid, _sid in globals().get('V4_GROUP_ADD', []):
    L.append("INSERT INTO spell_group_spell (Id, SpellId) VALUES (%d, %d);" % (_gid, _sid))
L.append("DELETE FROM npc_trainer_template WHERE spell BETWEEN 64500 AND 65499 AND entry NOT BETWEEN 900 AND 909;")
L.append("DELETE FROM npc_trainer WHERE spell BETWEEN 64500 AND 65499;")
for _cls, _tid, _cost, _lv in V4_TRAIN:
    L.append("INSERT IGNORE INTO npc_trainer_template (entry, spell, spellcost, reqskill, reqskillvalue, reqlevel) SELECT DISTINCT TrainerTemplateId, "
             "%d, %d, 0, 0, %d FROM creature_template WHERE TrainerType=0 AND TrainerClass=%d AND TrainerTemplateId>0;" % (_tid, _cost, _lv, _cls))
    L.append("INSERT IGNORE INTO npc_trainer (entry, spell, spellcost, reqskill, reqskillvalue, reqlevel) SELECT Entry, %d, %d, 0, 0, %d "
             "FROM creature_template WHERE TrainerType=0 AND TrainerClass=%d AND TrainerTemplateId=0;" % (_tid, _cost, _lv, _cls))
# Métamorphe : les sorts du druide disparaissent de la création ; les maîtres druides deviennent maîtres métamorphes
L.append("DELETE FROM playercreateinfo_spell WHERE class=%d AND Spell IN (5176, 5185);" % META)
for race in (4, 6, 7, 8):                  # races du Métamorphe
    for sp in START_SPELLS[META]:
        L.append("INSERT IGNORE INTO playercreateinfo_spell (race, class, Spell, Note) VALUES (%d, %d, %d, 'Metamorphe');" % (race, META, sp))
L.append("UPDATE playercreateinfo_action SET action=%d WHERE class=%d AND type=0 AND action=5176;" % (M['terre'][0], META))
L.append("UPDATE playercreateinfo_action SET action=%d WHERE class=%d AND type=0 AND action=5185;" % (M['remous'][0], META))
L.append("CREATE TABLE IF NOT EXISTS custom_backup_npc_trainer_druide SELECT * FROM npc_trainer WHERE entry IN "
         "(SELECT Entry FROM creature_template WHERE TrainerType=0 AND TrainerClass=11);")
L.append("DELETE FROM npc_trainer WHERE entry IN (SELECT Entry FROM creature_template WHERE TrainerType=0 AND TrainerClass=11);")
L.append("UPDATE creature_template SET TrainerTemplateId=902, SubName='Maître métamorphe' WHERE TrainerType=0 AND TrainerClass=11 AND Entry < 990000;")
# créatures : invocations, bêtes, tourelles, robots, totems
L.append("DELETE FROM creature_spell_list_entry WHERE Id BETWEEN 990500 AND 990599;")
L.append("DELETE FROM creature_spell_list WHERE Id BETWEEN 990500 AND 990599;")
L.append("DELETE FROM creature_template_spells WHERE entry BETWEEN 990500 AND 990599;")
L.append("DELETE FROM creature_template WHERE Entry BETWEEN 990500 AND 990599;")
L.append("DROP TEMPORARY TABLE IF EXISTS tmp_ct;")
L.append("CREATE TEMPORARY TABLE tmp_ct LIKE creature_template;")
for entry, name, disp, scale, ucls, hp, dm, arm, ctype, spells_, ranged in CREATURES:
    L.append("INSERT INTO tmp_ct SELECT * FROM creature_template WHERE Entry=1860;")
    L.append("UPDATE tmp_ct SET Entry=%d, Name='%s', SubName='', MinLevel=1, MaxLevel=60, DisplayId1=%d, DisplayId2=0, DisplayId3=0, "
             "DisplayId4=0, DisplayIdProbability1=100, DisplayIdProbability2=0, DisplayIdProbability3=0, DisplayIdProbability4=0, "
             "Scale=%s, UnitClass=%d, HealthMultiplier=%s, DamageMultiplier=%s, ArmorMultiplier=%s, CreatureType=%d, SpellList=%d, "
             "PetSpellDataId=0, ExperienceMultiplier=0, LootId=0, MinLootGold=0, MaxLootGold=0, AIName='', ScriptName='', Family=0 WHERE Entry=1860;"
             % (entry, esc(name), disp, scale, ucls, hp, dm, arm, ctype, entry))
    L.append("INSERT INTO creature_spell_list_entry (Id, Name, ChanceSupportAction, ChanceRangedAttack) VALUES (%d, '%s', 0, %d);" % (entry, esc(name), 100 if ranged else 0))
    for pos, (sp, tgt, ini, rep) in enumerate(spells_):
        L.append("INSERT INTO creature_spell_list (Id, Position, SpellId, Flags, CombatCondition, TargetId, ScriptId, Availability, "
                 "Probability, InitialMin, InitialMax, RepeatMin, RepeatMax, Comments) VALUES (%d, %d, %d, 0, -1, %d, 0, 100, 1, %d, %d, %d, %d, '%s');"
                 % (entry, pos, sp, tgt, ini, ini + 500, rep, rep + 500, esc(name)))
for entry, (name, src, passive) in sorted(TOTEMS.items()):
    L.append("INSERT INTO tmp_ct SELECT * FROM creature_template WHERE Entry=%d;" % src)
    L.append("UPDATE tmp_ct SET Entry=%d, Name='%s', MinLevel=1, MaxLevel=60, ScriptName='', AIName='' WHERE Entry=%d;" % (entry, esc(name), src))
    L.append("INSERT INTO creature_template_spells (entry, setId, spell1) VALUES (%d, 0, %d);" % (entry, passive))
L.append("INSERT INTO creature_template SELECT * FROM tmp_ct;")
L.append("DROP TEMPORARY TABLE tmp_ct;")
# groupes exclusifs : balles, aspects
L.append("DELETE FROM spell_group_spell WHERE Id IN (900, 901, 902);")
L.append("DELETE FROM spell_group WHERE Id IN (900, 901, 902);")
for gid, (gname, ids) in zip((900, 901, 902), [('Sniper balles', GROUPS.get('balle', [])), ('Sniper aspects', GROUPS.get('aspect', [])),
                                                ('Metamorphe buffs', GROUPS.get('meta', []))]):
    if not ids:
        continue
    L.append("INSERT INTO spell_group (Id, Rule, Name) VALUES (%d, 2, '%s');" % (gid, gname))
    for sid in ids:
        L.append("INSERT INTO spell_group_spell (Id, SpellId) VALUES (%d, %d);" % (gid, sid))
L.append("DELETE FROM spell_affect WHERE entry BETWEEN 62000 AND 64499 OR entry BETWEEN 55000 AND 56999;")
L.append("DELETE FROM spell_proc_event WHERE entry BETWEEN 62000 AND 64499 OR entry BETWEEN 55000 AND 56999;")
for sid, fam, m, flags, pex in TAL_PROC:
    L.append("INSERT INTO spell_proc_event (entry, SchoolMask, SpellFamilyName, SpellFamilyMask0, SpellFamilyMask1, SpellFamilyMask2, procFlags, procEx, ppmRate, CustomChance, Cooldown) "
             "VALUES (%d, 0, %d, %d, %d, %d, %d, %d, 0, 0, 0);" % (sid, fam, m, m, m, flags, pex))
for sid, e, m in AFFECT_N + AFFECT + TAL_AFFECT:
    L.append("INSERT INTO spell_affect (entry, effectId, SpellFamilyMask) VALUES (%d, %d, %d);" % (sid, e, m))

# lignes de compétence (onglets du grimoire)
SKILLLINES = [(900, "Invocateur", 354), (901, "Malédiction", 355), (902, "Magicien", 593),
              (903, "Tireur d'élite", 163), (904, "Bestial", 50), (905, "Mécanisme", 51)]
RENAME_SKILL = {573: "Totémique", 134: "Druidique", 574: "Angélique"}
SLA_ROWS = []
sla_id = 21000
for cls, lst in ((NECRO, NSLA), (NECRO, NCX.sla), (SNIPER, SC.sla), (META, MC.sla)):
    for skill, sid in lst:
        SLA_ROWS.append([sla_id, skill, sid, 0, CBIT[cls], 0, 0, 1, 0, 0, 0, 0, 0, 0, 0])
        sla_id += 1
for cls, skill, sid in V4_SLA:
    SLA_ROWS.append([sla_id, skill, sid, 0, CBIT[cls], 0, 0, 1, 0, 0, 0, 0, 0, 0, 0])
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

def layout_tab(rows):
    byid = {r[0]: r for r in rows}
    for _pass in range(12):
        changed = False
        grid = {(r[2], r[3]): r for r in rows}
        reserved = set()
        for r in sorted([r for r in rows if r[13]], key=lambda r: r[2]):
            p = byid.get(r[13])
            if not p or p[2] == r[2]:
                continue
            col = p[3]
            for t in range(p[2] + 1, r[2]):
                reserved.add((t, col))
        for r in sorted([r for r in rows if r[13]], key=lambda r: r[2]):
            p = byid.get(r[13])
            if not p or p[2] == r[2]:
                continue
            col = p[3]
            if r[3] != col:
                other = grid.get((r[2], col))
                old_c = r[3]
                r[3] = col
                if other is not None:
                    other[3] = old_c
                    grid[(r[2], old_c)] = other
                else:
                    grid.pop((r[2], old_c), None)
                grid[(r[2], col)] = r
                changed = True
            for t in range(p[2] + 1, r[2]):
                x = grid.get((t, col))
                if x is None:
                    continue
                free = [c for c in range(4) if (t, c) not in grid and (t, c) not in reserved]
                if not free:
                    free = [c for c in range(4) if c != col and grid.get((t, c)) is not None and (t, c) not in reserved]
                if not free:
                    print('ATTENTION mise en page bloquée', x[0])
                    continue
                c = free[0]
                y = grid.get((t, c))
                x[3], grid[(t, c)] = c, x
                if y is not None:
                    y[3], grid[(t, col)] = col, y
                else:
                    grid.pop((t, col), None)
                changed = True
        if not changed:
            break
    # vérification
    grid = {(r[2], r[3]): r for r in rows}
    for r in rows:
        p = byid.get(r[13]) if r[13] else None
        if p and p[2] != r[2]:
            bad = p[3] != r[3] or any((t, r[3]) in grid for t in range(p[2] + 1, r[2]))
            if bad:
                print('ATTENTION prérequis mal placé', r[0], p[0])
from collections import defaultdict as _dd
_tabs = _dd(list)
for _r in TALENT_ROWS:
    _tabs[_r[1]].append(_r)
for _t, _rows in _tabs.items():
    layout_tab(_rows)

# talents : Talent.dbc (sans les talents du druide) et TalentTab.dbc (serveur), lignes pour le client
tt = DBC(OUT + 'srv/TalentTab.dbc')
TT = {r[0]: r for r in tt.rows}
META_TABS = {}
tab_new = []
for tab_id, nom, ic, cmask, order, bg in TAB_ROWS:
    if tab_id in TT:
        META_TABS[tab_id] = (nom, ic, bg)
        continue
    r = list(TT[302]); r[0] = tab_id; r[1] = nom
    for c in range(2, 9): r[c] = 0
    r[10] = ic; r[11] = 511; r[12] = cmask; r[13] = order; r[14] = bg
    tab_new.append(r)
rows2 = [list(r) for r in tt.rows]
rs2 = {}
for i, r in enumerate(rows2):
    if r[0] in META_TABS:
        nom, ic, bg = META_TABS[r[0]]
        rs2[(i, 1)] = nom; rs2[(i, 14)] = bg; r[10] = ic
tt.rows = rows2
data, _ = rebuild(tt, {}, rs2)
open(OUT + 'out/TalentTab.dbc', 'wb').write(append_rows(data, tab_new))
tl = DBC(OUT + 'srv/Talent.dbc')
keep = [r for r in tl.rows if r[1] not in (283, 281, 282)]
data = b'WDBC' + struct.pack('<4I', len(keep) + len(TALENT_ROWS), tl.nf, tl.rs, len(tl.sb)) + \
       b''.join(struct.pack('<%dI' % tl.nf, *[v & 0xffffffff for v in r]) for r in keep + TALENT_ROWS) + tl.sb
open(OUT + 'out/Talent.dbc', 'wb').write(data)
print('talents', len(TALENT_ROWS), 'sorts de talent', len(TALG.spells), 'sans effet serveur', len(DUMMY_TALENTS))
json.dump(DUMMY_TALENTS, open(OUT + 'talents_a_coder.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)

json.dump({'talenttab_new': tab_new, 'talenttab_meta': {str(k): v for k, v in META_TABS.items()},
           'spell': NG.dbc_rows() + SG.dbc_rows() + MG.dbc_rows() + TG.dbc_rows() + TALG.dbc_rows() + sum((_g.dbc_rows() for _g, _a, _b in V4_GENS), []) + T4G.dbc_rows() + SPG.dbc_rows() + AG.dbc_rows(),
           'spell_patch': SPELL_PATCH, 'spell_text': SPELL_TEXT, 'spellvisual_new': SV_NEW, 'form_patch': {str(k): v for k, v in globals().get('FORM_PATCH', {}).items()}, 'sla': SLA_ROWS, 'skilllines': sk_new, 'rename_skill': RENAME_SKILL,
           'masks': {'necro': NG.masks, 'sniper': SG.masks, 'meta': MG.masks}, 'ids': {'necro': N, 'sniper': S, 'meta': M}},
          open(OUT + 'sorts_rows.json', 'w', encoding='utf-8'), ensure_ascii=False)
open(OUT + 'sorts.sql', 'w', encoding='utf-8').write("\n".join(L) + "\n")
print('necro', len(NG.spells), 'sniper', len(SG.spells), 'meta', len(MG.spells), 'apprentissage', len(TG.spells), 'sla', len(SLA_ROWS))

# ======================================================================== constantes pour le module C++
def talent_ids(name):
    for r in TALENT_ROWS:
        pass
    return []
TNAMES = {}
for t in TALG.spells:
    TNAMES.setdefault(t['name'], []).append(t['id'])
def ranks(key, gen):
    return [sp['id'] for sp in gen.spells if sp.get('key') == key and sp['id'] not in TRIGGERED]
H = ["// Généré par gen_sorts.py : identifiants des sorts et créatures des classes custom", "#pragma once", "#include <cstdint>", "",
     "namespace classes_data", "{"]
def arr(name, vals):
    H.append("    static const uint32_t %s[] = { %s };" % (name, ", ".join(str(v) for v in vals) if vals else "0"))
    H.append("    static const uint32_t %s_N = %d;" % (name, len(vals)))
def one(name, v):
    H.append("    static const uint32_t %s = %d;" % (name, v))
nd = MODULE['necro']
H.append("    // Nécromancien : invocations (sort visible, sort caché, Annihilation, créature, coût)")
H.append("    struct Invocation { uint32_t front, hidden, anni, entry, cost; };")
H.append("    static const Invocation INVOCATIONS[] = { %s };" % ", ".join("{%d, %d, %d, %d, %d}" % t for t in nd['summons']))
H.append("    static const uint32_t INVOCATIONS_N = %d;" % len(nd['summons']))
for k, v in nd['hidden'].items():
    one("N_H_" + k.upper(), v)
one("N_GH_RENOV", a['gh_renov'])        # Rénovation de la goule (lancée sur le joueur par le module : l'IA des créatures ne voit pas les joueurs)
for k in ['peste_explo', 'berserk', 'mortexplo', 'renovation', 'sang', 'chevalier_renf', 'annihilation', 'mort', 'malefice', 'camouflage']:
    arr("N_" + k.upper(), ranks(k, NG))
for k in nd['dots']:
    arr("N_DOT_" + k.upper(), ranks(k, NG))
for tname, cname in [("Horde grandissante", "T_HORDE"), ("Armée des morts", "T_ARMEE"), ("Légion", "T_LEGION"),
                     ("Maîtrise de l'invocation", "T_MAITRISE_INV"), ("Récolte d'âme", "T_RECOLTE"), ("Fléau rampant", "T_FLEAU"),
                     ("Esprit guérisseur", "T_ESPRIT"), ("Force de l'esprit", "T_FORCE"), ("Tir au contact", "T_CONTACT")]:
    arr(cname, TNAMES.get(tname, []))
sd = MODULE['sniper']
arr("S_BEASTS", sd['beasts']); arr("S_BEAST_HIDDEN", sd['beast_hidden'])
for k, v in sd['hidden'].items():
    one("S_H_" + k.upper(), v)
for k in ['recul', 'appel', 'ordre', 'magique', 'animal']:
    arr("S_" + k.upper(), ranks(k, SG))
for k, ids in sd['bullets'].items():
    arr("S_BALLE_" + k.upper(), ids)
md = MODULE['meta']
for k, v in md['hidden'].items():
    one("M_H_" + k.upper(), v)
for k in ['appel_tot', 'renvoi_tot', 'jugement', 'renfo', 'massive', 'beau'] + md['totems']:
    arr("M_" + k.upper(), ranks(k, MG))
H.append("    // talents gérés par le module")
for tname, cname in [("Étreinte de la tombe", "T_ETREINTE"), ("Chair putride", "T_CHAIR"), ("Maître nécromancien", "T_MAITRE"),
                     ("Lien des morts", "T_LIEN"), ("Crépuscule", "T_CREPUSCULE"), ("Contagion", "T_CONTAGION"),
                     ("Fléau double", "T_DOUBLE"), ("Morsure du froid", "T_MORSURE"), ("Synergie givrée", "T_SYNERGIE"),
                     ("Pyroclasme", "T_PYRO"), ("Meute", "T_MEUTE"), ("Grande meute", "T_GRANDE_MEUTE"),
                     ("Cri bestial amélioré", "T_CRI"), ("Balle d'eau maîtrisée", "T_B_EAU"), ("Balle de feu maîtrisée", "T_B_FEU"),
                     ("Balle de givre maîtrisée", "T_B_GIVRE"), ("Tireur solitaire", "T_SOLITAIRE"), ("Piégeage", "T_PIEGE"),
                     ("Robots améliorés", "T_ROBOTS"), ("Familier blindé", "T_BLINDE"), ("Voie de la guérison", "T_VOIE"),
                     ("Fougue lunaire", "T_FOUGUE"), ("Jugement du gardien", "T_JUG_GARDIEN"), ("Égide angélique", "T_EGIDE")]:
    arr(cname, TNAMES.get(tname, []))
for k in ['meute', 'solitaire', 'piege', 'robot', 'blinde', 'cri']:
    one("S_H2_" + k.upper(), hs[k])
for k in ['voie', 'voie_soin', 'lunaire', 'egide', 'massacre_g', 'massacre_b']:
    one("M_H2_" + k.upper(), hm[k])
for k, ids in DUPS.items():
    arr("N_DUP_" + k.upper(), ids)
for k in ['meteorite', 'javelot', 'eclair']:
    arr("N_" + k.upper(), ranks(k, NG))
for k in ['cri', 'bombe', 'dynamite']:
    arr("S_" + k.upper(), ranks(k, SG))
for k in ['feu', 'eau', 'givre']:
    arr("S_BALLE2_" + k.upper(), ranks(k, SG))
for k in ['recup', 'lunaire', 'massacre']:
    arr("M_" + k.upper(), ranks(k, MG))
one("C_ROBOT", C_ROBOT); one("C_MEUTE", C_MEUTE); one("BULLET_CAT", BULLET_CAT)
H.append("    // listes pour l'IA des bots")
for k in ['armure', 'trait', 'eclair', 'boule', 'tirombre', 'javelot', 'mot', 'corruption', 'vol', 'malediction', 'peste', 'maudit']:
    arr("BN_" + k.upper(), ranks(k, NG))
for k in ['fauve', 'arcanes', 'saignant', 'marque', 'long', 'multiple', 'precision', 'bestial', 'explosif']:
    arr("BS_" + k.upper(), ranks(k, SG))
for k in ['terre', 'hfeu', 'tonnerre', 'colere', 'lunaire', 'stellaire', 'massacre', 'remous', 'recup', 'salve', 'lien']:
    arr("BM_" + k.upper(), ranks(k, MG))
H.append("    // 4e spé des classes vanilla")
for _n, _v in V4H:
    arr(_n, _v)
# arbres de la 4e spé pour les bots : talents dans l'ordre des paliers (id du talent, nombre de rangs)
B4_CLASS, B4_START, B4_COUNT, B4_TID, B4_RANKS = [], [], [], [], []
for _cls, _tab in V4_TABS:
    _rows = sorted([r for r in TALENT_ROWS if r[1] == _tab], key=lambda r: (r[2], r[3]))
    B4_CLASS.append(_cls); B4_START.append(len(B4_TID)); B4_COUNT.append(len(_rows))
    for r in _rows:
        B4_TID.append(r[0]); B4_RANKS.append(sum(1 for v in r[4:13] if v))
for _n, _v in [('B4_CLASS', B4_CLASS), ('B4_START', B4_START), ('B4_COUNT', B4_COUNT), ('B4_TID', B4_TID), ('B4_RANKS', B4_RANKS)]:
    arr(_n, _v)
T4NAMES = {}
for t in T4G.spells:
    T4NAMES.setdefault(t['name'], []).append(t['id'])
for _n, _t in V4T:
    arr(_n, T4NAMES.get(_t, []))
arr("BIEN_NOURRI", BIEN_NOURRI)
one("ROUTE_SPELL", ROUTE_SPELL)
H.append("}")
open(OUT + 'ClassesData.h', 'w', encoding='utf-8').write("\n".join(H) + "\n")
print('en-tête module : ClassesData.h')
