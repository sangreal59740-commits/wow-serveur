# 4e spécialisation des classes vanilla (doc section 6 bis), exécuté dans gen_sorts.py (mêmes globales).
# Chaque classe : un Gen dans la famille de sorts de la classe (bits libres >= 34), un arbre de talents (onglet 4),
# des sorts appris par talent, des modifications de sorts vanilla (VPATCH, serveur + client).

from spellgen import dbc_col
V4_GENS = []            # (gen, premier id, dernier id)
V4_SLA = []             # (classe, ligne de compétence, sort)
V4_TRAIN = []           # (classe, sort d'apprentissage, coût, niveau)
V4H = []                # constantes pour le module : (nom, [valeurs])
V4T = []                # talents lus par le module : (nom C++, nom du talent)
VPATCH = {}             # sort vanilla -> {colonne SQL: valeur}

def vflags(sid):
    return SPR[sid][161] | (SPR[sid][162] << 32)

def vmask(*ids):
    m = 0
    for i in ids:
        m |= vflags(i)
    return m

def vtag(gen, key, ids):
    """donne un bit de famille à des sorts vanilla qui n'en ont pas, pour les viser avec des talents"""
    bit = gen.mask(key)
    for i in ids:
        VPATCH.setdefault(i, {})['SpellFamilyFlags'] = vflags(i) | bit
    return bit

def vset(ids, **cols):
    for i in ids:
        VPATCH.setdefault(i, {}).update(cols)

def sc(v60, L0):
    """valeur d'un sort à rang unique appris au niveau L0 : (points de base, points par niveau jusqu'au niveau 60)"""
    v0 = rank_value(v60, L0)
    return int(round(v0)) - 1, (v60 - v0) / float(60 - L0)

def teach_v4(cls, gen, ids):
    for sid in ids[1:]:
        sp = next(s for s in gen.spells if s['id'] == sid)
        lv = sp['sets'].get('SpellLevel', 1)
        tid = TEACH[0]; TEACH[0] += 1
        TG.add(tid, TEACH_BASE, sp['name'], sp['desc'], sp['rank'], family=False,
               sets={'EffectTriggerSpell1': sid, 'SpellLevel': lv, 'BaseLevel': lv, 'MaxLevel': 0,
                     'SpellIconID': sp['sets'].get('SpellIconID', SPR[sp['base']][117])})
        V4_TRAIN.append((cls, tid, max(10, 9 * lv * lv), lv))

def none3(*ns):
    out = {}
    for n in ns:
        out.update({'Effect%d' % n: 0, 'EffectApplyAuraName%d' % n: 0, 'EffectBasePoints%d' % n: 0, 'EffectMiscValue%d' % n: 0,
                    'EffectRealPointsPerLevel%d' % n: 0, 'EffectTriggerSpell%d' % n: 0})
    return out

def aur(n, aura, misc, val, target=1):
    d = auraf(n, aura, misc, val, target)
    d.update({'EffectRealPointsPerLevel%d' % n: 0, 'EffectTriggerSpell%d' % n: 0, 'EffectAmplitude%d' % n: 0,
              'EffectImplicitTargetB%d' % n: 0, 'EffectRadiusIndex%d' % n: 0})
    return d

# talents de la 4e spé : sorts passifs dans leur propre plage (les ID de sorts du joueur doivent rester < 65536 : paquets 1.12 en uint16)
TALG_MAIN, TAL_ID_MAIN = TALG, TAL_ID
T4G = Gen(0, [])
TALG, TAL_ID = T4G, [56000]

# ======================================================================== Paladin : Soleil
PALADIN = 2
PG = Gen(10, range(34, 64))
V4_GENS.append((PG, 55000, 55124))
PC = Ctx(PG, 55000, {'sacre': 594}, PALADIN, PALADIN)
P = {}

HL, FOL, HSHOCK, CONS, JUDG, HOJ = 0x80000000, 0x40000000, 0x200000, 0x20, 0x800000, 0x800
EXO = [879, 5614, 5615, 10312, 10313, 10314]
HWRATH = [2812, 10318]
HAMMER = [24275, 24274, 24239]
vtag(PG, 'v_exo', EXO)
vtag(PG, 'v_hw', HWRATH + HAMMER)
# Exorcisme et Colère divine : toutes les espèces
vset(EXO + HWRATH, TargetCreatureType=0)
# Bénédictions de puissance, de sagesse et des rois (et versions supérieures) : 60 min
vset([19740, 19834, 19835, 19836, 19837, 19838, 25291, 19742, 19850, 19852, 19853, 19854, 25290, 20217,
      25782, 25916, 25894, 25918, 25898], DurationIndex=DUR[3600000])

def _trait(L, k):
    mn, mx, t = round(rank_value(716, L)), round(rank_value(890, L)), round(rank_value(67, L))
    extra = {'School': 1, 'SpellVisual': visual(25912), 'RangeIndex': RANGE[30], 'CastingTimeIndex': 171,
             'EffectBasePoints1': mn - 1, 'EffectDieSides1': mx - mn + 1, 'EffectRealPointsPerLevel1': 0,
             'EffectBasePoints2': t - 1, 'EffectDieSides2': 1, 'EffectRealPointsPerLevel2': 0,
             'EffectBonusCoefficient1': 1.0, 'EffectBonusCoefficient2': 0.05}
    return (extra, "Lance un trait de lumière qui inflige %d à %d points de dégâts du Sacré, puis %d points de dégâts du Sacré "
            "en 12 s." % (mn, mx, 4 * t), "%d points de dégâts du Sacré toutes les 3 s." % t)
P['trait'] = PC.ranked('trait', 'sacre', 18809, 20, 6, "Trait de lumière", 26, 0, 0, _trait, icon_sid=585)
teach_v4(PALADIN, PG, P['trait'])

# Jugement du soleil (déclenché par le Jugement) puis Sceau du soleil
P['jug'] = cspell(PC, 'jug_soleil', 20286, "Jugement du soleil", SpellFamilyFlags=0x400, EffectBonusCoefficient1=0.65,
                  **merge(dmg(1, 211, 22), none3(2, 3)))
P['sceau'] = PC.single('sceau', 'sacre', 20293, 10, "Sceau du soleil",
                       "Remplit le Paladin de la puissance du soleil pendant 30 s. Le Jugement inflige les dégâts du Jugement "
                       "d'Autorité +30 % et ne consomme pas le sceau. Tant qu'il est actif, l'incantation de Trait de lumière "
                       "est réduite de 0,5 s et la recharge d'Exorcisme de 5 s. Un seul sceau peut être actif à la fois.",
                       0, 0, 8, icon_sid=21082, tooltip="Jugement renforcé, non consommé.",
                       SpellFamilyFlags=0x8000000, ProcFlags=0, ProcChance=0,
                       **merge(aur(1, 107, 11, -5000), aur(2, 107, 10, -500), {'EffectBasePoints3': P['jug'] - 1}))
AFFECT.append((P['sceau'], 0, PG.mask('v_exo')))
AFFECT.append((P['sceau'], 1, PG.mask('trait')))
NOTEACH.add(P['sceau'])

_b, _pl = sc(58, 30)
P['feu'] = PC.single('feu_sacre', 'sacre', 20924, 30, "Feu sacré",
                     "Embrase la zone ciblée de feu sacré : %d points de dégâts du Sacré en 8 s aux ennemis dans un rayon de "
                     "8 mètres." % (58 * 8), 8000, 0, 30, icon_sid=20924,
                     EffectImplicitTargetA1=28, EffectImplicitTargetB1=0, Targets=64, RangeIndex=RANGE[30], MaxLevel=60,
                     EffectBasePoints1=_b, EffectRealPointsPerLevel1=_pl, EffectBonusCoefficient1=0.05)
NOTEACH.add(P['feu'])

_b, _pl = sc(142, 30)
P['juger'] = PC.single('juger', 'sacre', 10894, 30, "Juger par la lumière",
                       "La lumière juge la cible : %d points de dégâts du Sacré en 18 s, son armure est réduite de 10 %% et toutes "
                       "ses résistances magiques de 20 %%." % (142 * 6), 0, 0, 18, icon_sid=20271,
                       tooltip="Armure -10 %, résistances -20 %, dégâts du Sacré toutes les 3 s.",
                       School=1, SpellVisual=visual(15261), MaxLevel=60, EffectBasePoints1=_b, EffectRealPointsPerLevel1=_pl,
                       EffectBonusCoefficient1=0.167, **merge(aur(2, 101, 1, -10, target=6), aur(3, 101, 126, -20, target=6)))
NOTEACH.add(P['juger'])

P['appel'] = PC.single('appel_soleil', 'sacre', 12042, 40, "Appel du Soleil",
                       "Appelle la puissance du soleil pendant 20 s : dégâts du Sacré +150 %, vitesse d'incantation +25 % et "
                       "puissance des sorts +25 %.", 180000, 0, 0, icon_sid=10318,
                       tooltip="Dégâts du Sacré +150 %, hâte et puissance des sorts +25 %.", School=1, DurationIndex=DUR[20000],
                       **merge(aur(1, 79, 2, 150), aur(2, 65, 0, 25), aur(3, 4, 0, 1)))
NOTEACH.add(P['appel'])
P['appel_sp'] = cspell(PC, 'appel_sp', 12042, "Appel du Soleil", DurationIndex=DUR[-1],
                       **merge(aur(1, 13, 2, 1), none3(2, 3)))

HOLY = [HL | FOL | HSHOCK | CONS, 'v_exo', 'v_hw', 'trait', 'feu_sacre', 'juger']
tree(PG, 406, "Soleil", CBIT[PALADIN], 3, "PaladinHoly", 10318, [
    (1, "Lumière lointaine", 1, 20271, ('fx', lambda r: [('mod', 5, False, [JUDG | HOJ], 20), ('mod', 5, False, [HSHOCK], 10),
                                                           ('learn', P['sceau'])]),
     "Jugement, Marteau de la justice et Horion sacré portent à 30 m. Vous apprenez le Sceau du soleil."),
    (1, "Aube intérieure", 5, 20257, ('fx', lambda r: [('aura', 79, 2, 2 * r), ('aura', 136, 0, 2 * r)]),
     lambda r: "Augmente vos dégâts et vos soins du Sacré de %d %%." % (2 * r)),
    (2, "Résolution", 5, 20254, ('fx', mod(9, True, HOLY, 14)),
     lambda r: "Réduit de %d %% le recul de vos sorts du Sacré quand vous subissez des dégâts." % (14 * r)),
    (2, "Ferveur", 5, 20210, ('fx', aura(71, 2, 1)), lambda r: "Augmente de %d %% la chance de coup critique de vos sorts du Sacré." % r),
    (3, "Trait de lumière", 1, 585, ('spell', P['trait'][0]),
     "Lance un trait de lumière : dégâts du Sacré puis dégâts du Sacré sur la durée. Incantation 6 s. Rangs suivants chez le maître Paladin."),
    (3, "Clarté", 5, 20224, ('fx', mod(14, True, HOLY, -2)), lambda r: "Réduit le coût en mana de vos sorts du Sacré de %d %%." % (2 * r)),
    (4, "Trait ardent", 2, 585, ('fx', lambda r: [('mod', 0, True, ['trait'], 10 * r), ('mod', 22, True, ['trait'], 10 * r)]),
     lambda r: "Augmente les dégâts de Trait de lumière de %d %%." % (10 * r)),
    (4, "Brûlure persistante", 2, 15261, ('fx', lambda r: [('mod', 1, False, ['trait'], 3000 * r), ('mod', 22, True, ['trait'], 15 * r)]),
     lambda r: "Augmente la durée des dégâts sur la durée de Trait de lumière de %d s et leurs dégâts de %d %%." % (3 * r, 15 * r)),
    (4, "Trait rapide", 3, 20216, ('fx', mod(10, False, ['trait'], -500)),
     lambda r: "Réduit le temps d'incantation de Trait de lumière de %.1f s." % (0.5 * r), "Trait de lumière"),
    (5, "Feu sacré", 1, 20924, ('spell', P['feu']), "Pose une Consécration au sol à 30 m : dégâts du Sacré aux ennemis dans un rayon de 8 m. Recharge 8 s."),
    (5, "Juger par la lumière", 1, 20271, ('spell', P['juger']),
     "Dégâts du Sacré sur la durée ; l'armure de la cible est réduite de 10 % et ses résistances magiques de 20 %."),
    (6, "Lumière brûlante", 5, 20335, ('fx', aura(79, 2, 2)), lambda r: "Augmente vos dégâts du Sacré de %d %%." % (2 * r)),
    (6, "Zénith", 3, 20924, ('fx', lambda r: [('mod', 0, True, ['feu_sacre', 'juger'], 10 * r), ('mod', 22, True, ['feu_sacre', 'juger'], 10 * r)]),
     lambda r: "Augmente les dégâts de Feu sacré et de Juger par la lumière de %d %%." % (10 * r)),
    (7, "Appel du Soleil", 1, 10318, ('spell', P['appel']),
     "Pendant 20 s : dégâts du Sacré +150 %, vitesse d'incantation et puissance des sorts +25 %. Recharge 3 min."),
    (7, "Soleil prolongé", 2, 10318, ('fx', mod(1, False, ['appel_soleil'], 2500)),
     lambda r: "Augmente la durée d'Appel du Soleil de %.1f s." % (2.5 * r)),
])
for _sid in PC.sla:
    V4_SLA.append((PALADIN,) + _sid)
V4H += [('P4_JUG_SOLEIL', [P['jug']]), ('P4_SCEAU', [P['sceau']]), ('P4_APPEL', [P['appel']]), ('P4_APPEL_SP', [P['appel_sp']])]

# ======================================================================== Guerrier : Berserker
WARRIOR = 1
WG = Gen(4, range(34, 64))
V4_GENS.append((WG, 55125, 55249))
WC = Ctx(WG, 55125, {'fureur': 256}, WARRIOR, WARRIOR)
W = {}
WHIRLWIND = vflags(1680)

W['crit'] = cspell(WC, 'w_crit', 12042, "Instinct du berserker", DurationIndex=DUR[-1], **merge(aur(1, 52, 0, 1), none3(2, 3)))
W['endurci'] = cspell(WC, 'w_endurci', 12042, "Endurci", DurationIndex=DUR[-1], **merge(aur(1, 87, 127, -1), none3(2, 3)))
W['soif'] = cspell(WC, 'w_soif', 12042, "Soif de carnage", DurationIndex=0,
                   **merge({'Effect1': 3, 'EffectImplicitTargetA1': 1, 'EffectApplyAuraName1': 0, 'EffectBasePoints1': 0}, none3(2, 3)))

W['fou'] = WC.single('fou', 'fureur', 12042, 30, "Fou de rage",
                     "Vous entrez dans une rage folle jusqu'à annulation : rage générée par vos attaques +10 %, chance de coup "
                     "critique +2 % et dégâts des coups critiques +20 %.", 1000, 0, 0, icon_sid=18499,
                     tooltip="Rage +10 %, critique +2 %, dégâts critiques +20 %.", DurationIndex=DUR[-1], School=0,
                     **merge(aur(1, 52, 0, 2), aur(2, 163, 127, 20), aur(3, 4, 0, 1)))
NOTEACH.add(W['fou'])

_b, _pl = sc(150, 35)
W['crachat'] = WC.single('crachat', 'fureur', 10161, 35, "Crachat de rage",
                         "Crache votre rage en cône devant vous : 120 %% des dégâts de l'arme et %d points de dégâts de Feu aux "
                         "ennemis à moins de 10 mètres, ralentis de 30 %% pendant 8 s." % 150, 10000, 0, 0, icon_sid=16396,
                         tooltip="Ralenti de 30 %.", PowerType=1, ManaCost=250, School=2, DmgClass=2, MaxLevel=60,
                         SpellVisual=visual(16396), DurationIndex=DUR[8000], EquippedItemClass=-1,
                         **merge(weapon(1, 120, target=24), {'EffectRadiusIndex1': RADIUS[10], 'EffectRealPointsPerLevel1': 0},
                                 {'Effect2': 2, 'EffectApplyAuraName2': 0, 'EffectBasePoints2': _b, 'EffectDieSides2': 1,
                                  'EffectRealPointsPerLevel2': _pl, 'EffectImplicitTargetA2': 24, 'EffectRadiusIndex2': RADIUS[10],
                                  'EffectBonusCoefficient2': 0, 'EffectMiscValue2': 0},
                                 aur(3, 33, 0, -30, target=24), {'EffectRadiusIndex3': RADIUS[10]}))
NOTEACH.add(W['crachat'])

_b, _pl = sc(236, 40)
_b2, _pl2 = sc(30, 40)
W['frappe'] = WC.single('frappe_folle', 'fureur', 11585, 40, "Frappe folle",
                        "Une frappe démente : dégâts de l'arme + 236, et un saignement de 300 points de dégâts en 20 s. "
                        "Le saignement se cumule 2 fois.", 6000, 0, 0, icon_sid=25286,
                        tooltip="Saigne : dégâts physiques toutes les 2 s.", PowerType=1, ManaCost=100, School=0, DmgClass=2,
                        Stances=0, StancesNot=0, CasterAuraState=0, TargetAuraState=0, Category=0, StackAmount=2, MaxLevel=60,
                        DurationIndex=DUR[20000],
                        **merge({'Effect1': 17, 'EffectBasePoints1': _b, 'EffectDieSides1': 1, 'EffectRealPointsPerLevel1': _pl,
                                 'EffectImplicitTargetA1': 6, 'EffectApplyAuraName1': 0},
                                {'Effect2': 6, 'EffectApplyAuraName2': 3, 'EffectBasePoints2': _b2, 'EffectDieSides2': 1,
                                 'EffectRealPointsPerLevel2': _pl2, 'EffectImplicitTargetA2': 6, 'EffectAmplitude2': 2000,
                                 'EffectMechanic2': 15, 'EffectMiscValue2': 0}, none3(3)))
NOTEACH.add(W['frappe'])

tree(WG, 407, "Berserker", CBIT[WARRIOR], 3, "WarriorFury", 2458, [
    (1, "Instinct du berserker", 1, 2458, D,
     "Vous apprenez la Posture berserker. En Posture berserker, votre chance de coup critique est augmentée de 3 % supplémentaires (6 % au total)."),
    (1, "Sang chaud", 5, 12880, ('fx', aura(79, 1, 1)), lambda r: "Augmente vos dégâts physiques de %d %%." % r),
    (2, "Peau épaisse", 5, 12295, ('fx', aura(101, 1, 2)), lambda r: "Augmente votre armure de %d %%." % (2 * r)),
    (2, "Hargne", 3, 12317, ('fx', aura(138, 0, 1)), lambda r: "Augmente votre vitesse d'attaque de %d %%." % r),
    (3, "Fureur aveugle", 5, 12320, D, lambda r: "Sous 50 %% de vie, votre chance de coup critique est augmentée de %d %%." % (2 * r)),
    (3, "Carnage", 3, 12290, D, lambda r: "Vos coups vous rendent %d %% des dégâts infligés sous forme de points de vie." % r),
    (4, "Endurci", 3, 12298, D, lambda r: "Sous 50 %% de vie, les dégâts que vous subissez sont réduits de %d %%." % (2 * r)),
    (4, "Tourbillon amélioré", 3, 1680, ('fx', mod(0, True, [WHIRLWIND], 10)), lambda r: "Augmente les dégâts de Tourbillon de %d %%." % (10 * r)),
    (5, "Fou de rage", 1, 18499, ('spell', W['fou']),
     "Buff permanent : rage générée par vos attaques +10 %, coups critiques +2 %, dégâts des coups critiques +20 %."),
    (5, "Soif de carnage", 3, 12292, ('fx', lambda r: [('proc', W['soif'], 100, 0x4 | 0x10, 0, 0, 2)]),
     lambda r: "Chacun de vos coups critiques vous rend %d %% de vos points de vie maximum." % r),
    (6, "Crachat de rage", 1, 16396, ('spell', W['crachat']),
     "Cône de rage devant vous : 120 % des dégâts de l'arme et des dégâts de Feu, cibles ralenties de 30 %. Recharge 10 s."),
    (6, "Crachat de rage amélioré", 3, 16396, ('fx', mod(0, True, ['crachat'], 5)), lambda r: "Augmente les dégâts de Crachat de rage de %d %%." % (5 * r),
     "Crachat de rage"),
    (7, "Frappe folle", 1, 25286, ('spell', W['frappe']),
     "Frappe héroïque x1,5 instantanée et saignement de 300 points de dégâts en 20 s, cumulable 2 fois. Recharge 6 s."),
    (7, "Folie sanglante", 2, 12867, ('fx', mod(22, True, ['frappe_folle'], 15)),
     lambda r: "Augmente les dégâts du saignement de Frappe folle de %d %%." % (15 * r)),
])
for _sid in WC.sla:
    V4_SLA.append((WARRIOR,) + _sid)
V4H += [('W4_CRIT', [W['crit']]), ('W4_ENDURCI', [W['endurci']]), ('W4_SOIF', [W['soif']]), ('W4_FOU', [W['fou']])]
V4T += [('T4_INSTINCT', "Instinct du berserker"), ('T4_FUREUR_AV', "Fureur aveugle"), ('T4_CARNAGE', "Carnage"),
        ('T4_ENDURCI', "Endurci"), ('T4_SOIF', "Soif de carnage")]

# ======================================================================== Démoniste : Transfuge
WARLOCK = 8
KG = Gen(5, [34, 35, 36, 37] + list(range(40, 64)))
V4_GENS.append((KG, 55250, 55374))
KC = Ctx(KG, 55250, {'demono': 354}, WARLOCK, WARLOCK)
K = {}
DA = [706, 1086, 11733, 11734, 11735]
SB, CORR, IMMO, SF = vflags(686), vflags(172), vflags(348), vflags(6353)
DAM = vtag(KG, 'v_da', DA)
# Double armure : une 2e couche d'Armure démoniaque par rang (hors du groupe des armures, donc cumulable)
K['da2'] = []
for _i, _sid in enumerate(DA):
    K['da2'].append(cspell(KC, 'da2', _sid, "Armure démoniaque", SpellLevel=SPR[_sid][dbc_col('SpellLevel')], MaxLevel=0,
                           DurationIndex=SPR[_sid][dbc_col('DurationIndex')], SpellIconID=icon(_sid)))
DAM |= KG.mask('da2')
K['menace'] = cspell(KC, 'k_menace', 12042, "Armure démoniaque renforcée", DurationIndex=DUR[-1], **merge(aur(1, 10, 127, 1), none3(2, 3)))
K['incant'] = cspell(KC, 'k_incant', 12042, "Incantation démoniaque", DurationIndex=DUR[-1],
                     **merge(aur(1, 108, 0, -25), aur(2, 108, 22, -25), none3(3)))
AFFECT.append((K['incant'], 0, IMMO))
AFFECT.append((K['incant'], 1, IMMO | CORR))
K['absorb2'] = cspell(KC, 'absorption', 12042, "Absorption démoniaque", DurationIndex=DUR[20000], SpellIconID=icon(18788),
                      **merge(aur(1, 79, 127, 25), aur(2, 87, 127, -10), none3(3)))

K['cri'] = KC.single('cri', 'demono', 355, 10, "Cri démoniaque",
                     "Un cri démoniaque force la cible à vous attaquer pendant 3 s.", 10000, 0, 5, icon_sid=1161,
                     tooltip="Provoqué.", PowerType=0, Stances=0, StancesNot=0, RangeIndex=RANGE[20], School=5)
NOTEACH.add(K['cri'])
_b, _pl = sc(48, 35)
K['sol'] = KC.single('sol', 'demono', 20924, 35, "Sol éradiqué",
                     "Éradique le sol autour de vous : 384 points de dégâts d'Ombre en 8 s aux ennemis à moins de 8 mètres.",
                     8000, 0, 30, icon_sid=11433, School=5, SpellVisual=visual(11433), MaxLevel=60,
                     EffectBasePoints1=_b, EffectRealPointsPerLevel1=_pl, EffectBonusCoefficient1=0.042)
NOTEACH.add(K['sol'])
K['absorb'] = KC.single('absorption', 'demono', 18788, 40, "Absorption démoniaque",
                        "Vous absorbez votre démon. Pendant 20 s : points de vie maximum, armure, résistances et dégâts +25 %, "
                        "dégâts subis -10 %.", 180000, 0, 0, icon_sid=18788,
                        tooltip="PV, armure, résistances et dégâts +25 %, dégâts subis -10 %.", DurationIndex=DUR[20000],
                        **merge(aur(2, 133, 0, 25), aur(3, 101, 127, 25)))
NOTEACH.add(K['absorb'])

tree(KG, 408, "Transfuge", CBIT[WARLOCK], 3, "WarlockSummoning", 18788, [
    (1, "Armure démoniaque renforcée", 5, 706, ('fx', mod(8, True, [DAM], 2)),
     lambda r: "Augmente les effets d'Armure démoniaque de %d %% ; tant qu'elle est active, votre menace est augmentée de %d %%. "
               "Vous pouvez porter la maille et le bouclier." % (2 * r, 5 * r)),
    (1, "Pacte gangrené", 5, 18692, ('fx', aura(137, 2, 4)), lambda r: "Augmente votre Endurance de %d %%." % (4 * r)),
    (2, "Cri démoniaque", 1, 1161, ('spell', K['cri']), "Force la cible à vous attaquer pendant 3 s. Recharge 10 s."),
    (2, "Malveillance", 5, 18174, ('fx', aura(10, 127, 10)), lambda r: "Augmente la menace que vous générez de %d %%." % (10 * r)),
    (3, "Lien gangrené", 1, 19028, D, "10 % des dégâts infligés par votre démon vous soignent."),
    (3, "Tolérance gangrenée", 5, 18731, ('fx', aura(49, 0, 1)), lambda r: "Augmente votre chance d'esquiver de %d %%." % r),
    (4, "Lien gangrené amélioré", 2, 19028, D, lambda r: "Les soins de Lien gangrené passent à %d %% des dégâts du démon." % (10 + 5 * r),
     "Lien gangrené"),
    (4, "Résistance démoniaque", 3, 18769, ('fx', aura(22, 126, 10)), lambda r: "Augmente toutes vos résistances de %d." % (10 * r)),
    (5, "Incantation démoniaque", 1, 18288, ('fx', lambda r: [('mod', 10, True, [SB | IMMO | SF | CORR], -100), ('mod', 0, True, [SB], -50),
                                                             ('mod', 0, True, [SF], -75)]),
     "Trait de l'ombre, Immolation, Corruption et Feu de l'âme deviennent instantanés. En échange, dégâts de Trait de l'ombre -50 %, "
     "d'Immolation et de Corruption -25 %, de Feu de l'âme -75 %."),
    (5, "Double armure", 1, 706, D, "Armure démoniaque se cumule 2 fois.", "Armure démoniaque renforcée"),
    (6, "Sol éradiqué", 1, 11433, ('spell', K['sol']), "Dégâts d'Ombre autour de vous pendant 8 s. Recharge 8 s."),
    (6, "Sol profané", 3, 11433, ('fx', mod(22, True, ['sol'], 10)), lambda r: "Augmente les dégâts de Sol éradiqué de %d %%." % (10 * r), "Sol éradiqué"),
    (7, "Absorption démoniaque", 1, 18788, ('spell', K['absorb']),
     "Absorbe votre démon : 20 s de PV, armure, résistances et dégâts +25 %, dégâts subis -10 %. Recharge 3 min."),
    (7, "Absorption prolongée", 2, 18788, ('fx', mod(1, False, ['absorption'], 2500)),
     lambda r: "Augmente la durée d'Absorption démoniaque de %.1f s." % (2.5 * r)),
])
for _sid in KC.sla:
    V4_SLA.append((WARLOCK,) + _sid)
V4H += [('K4_DA', DA), ('K4_DA2', K['da2']), ('K4_MENACE', [K['menace']]), ('K4_INCANT', [K['incant']]),
        ('K4_ABSORB', [K['absorb']]), ('K4_ABSORB2', [K['absorb2']])]
V4T += [('T4_ARMURE', "Armure démoniaque renforcée"), ('T4_LIEN', "Lien gangrené"), ('T4_LIEN_AM', "Lien gangrené amélioré"),
        ('T4_INCANT', "Incantation démoniaque"), ('T4_DOUBLE', "Double armure")]

# ======================================================================== Chaman : Ruines
SHAMAN = 7
HG = Gen(11, [36, 37, 38, 39, 40, 41] + list(range(43, 64)))
V4_GENS.append((HG, 55375, 55499))
HC = Ctx(HG, 55375, {'amelio': 373}, SHAMAN, SHAMAN)
Hh = {}
LSHIELD = [324, 325, 905, 945, 8134, 10431, 10432]
CHAIN = vflags(421)
STONESKIN, TOTEMS_M = 0x8000, 537395200

Hh['terre'] = HC.single('bouclier_terre', 'amelio', 10432, 10, "Bouclier de terre",
                        "Entoure le Chaman d'un bouclier de terre pendant 10 min. Chaque coup reçu absorbe 10 % de ses dégâts et "
                        "consomme une charge. 5 charges. Un seul bouclier élémentaire à la fois.", 0, 0, 8, icon_sid=10432,
                        tooltip="Absorbe 10 % de chaque coup reçu.", School=3, ProcCharges=5, ProcFlags=0, ProcChance=0,
                        DurationIndex=DUR[600000], **merge(aur(1, 4, 0, 10), none3(2, 3)))
NOTEACH.add(Hh['terre'])
Hh['defi'] = HC.single('defi', 'amelio', 355, 10, "Défi tellurique", "La terre force la cible à vous attaquer pendant 3 s.",
                       10000, 0, 5, icon_sid=5730, tooltip="Provoqué.", PowerType=0, Stances=0, StancesNot=0, RangeIndex=RANGE[20], School=3)
NOTEACH.add(Hh['defi'])
Hh['fracas'] = HC.single('fracas', 'amelio', 20549, 25, "Fracas de pierre",
                         "Frappe le sol et étourdit pendant 3 s les ennemis à moins de 8 mètres.", 30000, 0, 10, icon_sid=8056,
                         tooltip="Étourdi.", DurationIndex=DUR[3000], School=3, EffectRadiusIndex1=RADIUS[8], Attributes=SPR[20549][dbc_col('Attributes')] & ~0x10)
NOTEACH.add(Hh['fracas'])
_b, _pl = sc(80, 40)
Hh['hot'] = cspell(HC, 'runique_hot', 774, "Appel runique", SpellLevel=40, BaseLevel=40, MaxLevel=60, DurationIndex=DUR[10000], School=3,
                   **merge({'Effect1': 6, 'EffectApplyAuraName1': 8, 'EffectBasePoints1': _b, 'EffectDieSides1': 1,
                            'EffectRealPointsPerLevel1': _pl, 'EffectImplicitTargetA1': 1, 'EffectAmplitude1': 1000,
                            'EffectBonusCoefficient1': 0.05}, none3(2, 3)))
Hh['runique'] = HC.single('runique', 'amelio', 12042, 40, "Appel runique",
                          "Des runes de pierre absorbent 30 % des dégâts que vous subissez pendant 15 s. À la fin, elles vous rendent "
                          "800 points de vie en 10 s.", 180000, 0, 0, icon_sid=20594, tooltip="Dégâts subis -30 %.",
                          DurationIndex=DUR[15000], School=3, **merge(aur(1, 87, 127, -30), none3(2, 3)))
NOTEACH.add(Hh['runique'])

tree(HG, 409, "Ruines", CBIT[SHAMAN], 3, "ShamanEnhancement", 8071, [
    (1, "Bouclier de terre", 1, 10432, ('spell', Hh['terre']),
     "Bouclier de 5 charges : chaque coup reçu absorbe 10 % de ses dégâts. Remplace Bouclier de foudre."),
    (1, "Armure de pierre", 5, 16258, ('fx', aura(101, 1, 5)), lambda r: "Augmente votre armure de %d %%." % (5 * r)),
    (2, "Défi tellurique", 1, 5730, ('spell', Hh['defi']), "Force la cible à vous attaquer pendant 3 s. Recharge 10 s."),
    (2, "Rancune de la terre", 5, 16176, ('fx', aura(10, 127, 5)), lambda r: "Augmente la menace que vous générez de %d %%." % (5 * r)),
    (3, "Peau de pierre améliorée", 3, 8071, ('fx', mod(8, True, [STONESKIN], 20)),
     lambda r: "Augmente la réduction de dégâts du Totem de peau de pierre de %d %%." % (20 * r)),
    (3, "Économie totémique", 5, 16173, ('fx', mod(14, True, [TOTEMS_M], -10)), lambda r: "Réduit le coût en mana de vos totems de %d %%." % (10 * r)),
    (4, "Fracas de pierre", 1, 8056, ('spell', Hh['fracas']), "Étourdit 3 s les ennemis à moins de 8 mètres. Recharge 30 s."),
    (4, "Charges terrestres", 3, 10432, ('fx', mod(4, False, ['bouclier_terre'], 1)),
     lambda r: "Bouclier de terre a %d charge(s) de plus." % r, "Bouclier de terre"),
    (5, "Chaîne tellurique", 1, 421, ('fx', lambda r: [('mod', 10, True, [CHAIN], -100), ('mod', 0, True, [CHAIN], -40)]),
     "Chaîne d'éclairs devient instantanée ; ses dégâts sont réduits de 40 %."),
    (5, "Bouclier double", 1, 324, D, "Bouclier de terre et Bouclier de foudre peuvent être actifs en même temps.", "Charges terrestres"),
    (6, "Granit", 5, 16258, ('fx', aura(87, 127, -1)), lambda r: "Réduit les dégâts que vous subissez de %d %%." % r),
    (7, "Appel runique", 1, 20594, ('spell', Hh['runique']),
     "Absorbe 30 % des dégâts subis pendant 15 s, puis rend 800 PV en 10 s. Recharge 3 min."),
    (7, "Runes durables", 2, 20594, ('fx', mod(1, False, ['runique'], 2500)), lambda r: "Augmente la durée d'Appel runique de %.1f s." % (2.5 * r)),
])
for _sid in HC.sla:
    V4_SLA.append((SHAMAN,) + _sid)
V4H += [('H4_TERRE', [Hh['terre']]), ('H4_FOUDRE', LSHIELD), ('H4_RUNIQUE', [Hh['runique']]), ('H4_HOT', [Hh['hot']])]
V4T += [('T4_DOUBLE_B', "Bouclier double")]

# ======================================================================== Mage : Nature
MAGE = 3
AG = Gen(3, [32, 33, 34, 35, 36, 37] + list(range(39, 64)))
V4_GENS.append((AG, 55500, 55699))
AC = Ctx(AG, 55500, {'arcanes': 237}, MAGE, MAGE)
A = {}
A_FIRE, A_HEAL, A_KEEP = [], [], [11366, 11113]       # sort de Feu -> soin ; rangs 1 appris par talent (gardés)
AHEALS = []
NATVIS = visual(25297)

def _heal_family(key, fire_ids, base, name, cast, cd, mpct, mn60, mx60, coef, desc_fn, hot=None, target=21, extra=None, icon_sid=25297):
    ids = []
    for k, fid in enumerate(fire_ids):
        L = SPR[fid][dbc_col('SpellLevel')]
        f = 0.93 if (k + 1 < len(fire_ids) and SPR[fire_ids[k + 1]][dbc_col('SpellLevel')] == L) else 1.0
        mn, mx = round(rank_value(mn60, L) * f), round(rank_value(mx60, L) * f)
        sets = common(L, cd, 0, mpct, icon_sid, base_cls=MAGE)
        sets.update({'CastingTimeIndex': cast, 'School': 3, 'SpellVisual': NATVIS, 'RangeIndex': RANGE[40], 'DmgClass': 1,
                     'Effect1': 10, 'EffectApplyAuraName1': 0, 'EffectBasePoints1': mn - 1, 'EffectDieSides1': mx - mn + 1,
                     'EffectRealPointsPerLevel1': 0, 'EffectImplicitTargetA1': target, 'EffectImplicitTargetB1': 0,
                     'EffectBonusCoefficient1': coef, 'EffectMiscValue1': 0, 'EffectTriggerSpell1': 0, 'EffectChainTarget1': 0,
                     'Effect2': 0, 'EffectApplyAuraName2': 0, 'Effect3': 0, 'EffectApplyAuraName3': 0, 'Mechanic': 0,
                     'TargetCreatureType': 0, 'AttributesEx3': 0})
        t = 0
        if hot:
            tick60, amp, dur = hot
            t = round(rank_value(tick60, L) * f)
            sets.update({'Effect2': 6, 'EffectApplyAuraName2': 8, 'EffectBasePoints2': t - 1, 'EffectDieSides2': 1,
                         'EffectRealPointsPerLevel2': 0, 'EffectImplicitTargetA2': target, 'EffectImplicitTargetB2': 0,
                         'EffectAmplitude2': amp, 'EffectBonusCoefficient2': coef / 10.0, 'DurationIndex': DUR[dur],
                         'EffectRadiusIndex2': sets.get('EffectRadiusIndex1', 0)})
        if extra:
            sets.update(extra)
            if hot and 'EffectRadiusIndex1' in extra:
                sets['EffectRadiusIndex2'] = extra['EffectRadiusIndex1']
            if hot and 'EffectImplicitTargetB1' in extra:
                sets['EffectImplicitTargetB2'] = extra['EffectImplicitTargetB1']
        hid = AG.add(AC.nid(), base, name, desc_fn(mn, mx, t), "Rang %d" % (k + 1), key=key, sets=sets)
        AC.sla.append((237, hid))
        ids.append(hid)
        A_FIRE.append(fid); A_HEAL.append(hid)
    AG.chain_ranks(ids)
    teach_v4(MAGE, AG, ids)
    AHEALS.append(key)
    return ids

A['boule'] = _heal_family('boule_vie', [133, 143, 145, 3140, 8400, 8401, 8402, 10148, 10149, 10150, 10151, 25306], 10965,
                          "Boule de vie", CAST[3000], 0, 40, 1966, 2194, 0.857,
                          lambda a, b, t: "Une boule de vie soigne l'allié ciblé de %d à %d points de vie." % (a, b))
A['vif'] = _heal_family('vif', [2948, 8444, 8445, 8446, 10205, 10206, 10207], 10917, "Vif-éclat", CAST[1500], 0, 25, 812, 959, 0.429,
                        lambda a, b, t: "Un éclat de vie rapide soigne l'allié ciblé de %d à %d points de vie." % (a, b), icon_sid=9858)
A['trait'] = _heal_family('trait_vie', [2136, 2137, 2138, 8412, 8413, 10197, 10199], 10917, "Trait de vie", CAST[0], 8000, 15, 446, 524, 0.429,
                          lambda a, b, t: "Soigne instantanément l'allié ciblé de %d à %d points de vie." % (a, b), icon_sid=8936)
A['flor'] = _heal_family('floraison', [2120, 2121, 8422, 8423, 10215, 10216], 10216, "Floraison", CAST[3000], 0, 55, 1041, 1099, 0.286,
                         lambda a, b, t: "Fait fleurir la zone ciblée : soigne les alliés dans un rayon de 8 mètres de %d à %d points de vie, "
                                         "puis de %d points de vie en 8 s." % (a, b, 4 * t),
                         hot=(50, 2000, 8000), target=31,
                         extra={'Targets': 64, 'RangeIndex': RANGE[30], 'EffectRadiusIndex1': RADIUS[8], 'EffectImplicitTargetB1': 0},
                         icon_sid=740)
A['explo'] = _heal_family('explo_vie', [11366, 12505, 12522, 12523, 12524, 12525, 12526, 18809], 10965, "Explosion vitale", 171, 0, 50,
                          2560, 2850, 1.0, lambda a, b, t: "Une explosion de vie soigne l'allié ciblé de %d à %d points de vie, puis de %d "
                                                           "points de vie en 12 s." % (a, b, 4 * t), hot=(100, 3000, 12000), icon_sid=25297)
A['vague'] = _heal_family('vague_vie', [11113, 13018, 13019, 13020, 13021], 10965, "Vague de vie", CAST[0], 45000, 35, 400, 460, 0.193,
                          lambda a, b, t: "Une vague de vie soigne les alliés à moins de 10 mètres de %d à %d points de vie." % (a, b),
                          target=30, extra={'EffectRadiusIndex1': RADIUS[10], 'RangeIndex': RANGE[0]}, icon_sid=740)

# Biome : soin sur la durée (comme Rénovation), rangs chez le maître Mage
def _biome(L, k):
    t = round(rank_value(194, L))
    return ({'School': 3, 'SpellVisual': visual(774), 'RangeIndex': RANGE[40], 'EffectBasePoints1': t - 1, 'EffectDieSides1': 1,
             'EffectRealPointsPerLevel1': 0, 'EffectBonusCoefficient1': 0.2, 'TargetCreatureType': 0},
            "Soigne l'allié ciblé de %d points de vie en 15 s." % (5 * t), "%d points de vie toutes les 3 s." % t)
A['biome'] = AC.ranked('biome', 'arcanes', 25315, 20, 6, "Biome", 18, 0, 0, _biome, icon_sid=774)
teach_v4(MAGE, AG, A['biome'])
AHEALS.append('biome')

A['armure'] = AC.single('armure_nat', 'arcanes', 7302, 15, "Armure de nature",
                        "Une armure d'écorce vous entoure pendant 30 min : armure +20 % et puissance des soins +20 %. "
                        "Une seule armure de mage à la fois.", 0, 0, 12, icon_sid=8936,
                        tooltip="Armure +20 %, puissance des soins +20 %.", School=3, DurationIndex=DUR[1800000],
                        **merge(aur(1, 101, 1, 20), aur(2, 4, 0, 1), none3(3)))
NOTEACH.add(A['armure'])
A['armure_sp'] = cspell(AC, 'armure_sp', 12042, "Armure de nature", DurationIndex=DUR[-1], **merge(aur(1, 135, 127, 1), none3(2, 3)))

_b, _pl = sc(942, 30)
A['bouclier'] = AC.single('bouclier_nat', 'arcanes', 10901, 30, "Bouclier de nature",
                          "Entoure l'allié ciblé d'un bouclier de nature qui absorbe 942 points de dégâts pendant 30 s. "
                          "La cible ne peut pas recevoir d'autre bouclier pendant 15 s.", 4000, 0, 30, icon_sid=8936,
                          tooltip="Absorbe des dégâts.", School=3, SpellVisual=visual(7302), MaxLevel=60, EffectBasePoints1=_b,
                          EffectRealPointsPerLevel1=_pl, EffectBonusCoefficient1=0.1)
NOTEACH.add(A['bouclier'])
A['ecorce'] = cspell(AC, 'ecorce', 12042, "Écorce protectrice", DurationIndex=DUR[5000], SpellIconID=icon(8936),
                     **merge(aur(1, 101, 1, 10), none3(2, 3)))
A['ai'] = cspell(AC, 'ai_bonus', 12042, "Intelligence sylvestre", DurationIndex=DUR[-1],
                 **merge(aur(1, 29, 3, 1), aur(2, 29, 4, 1), none3(3)))
A['lien'] = AC.single('lien_vie', 'arcanes', 1243, 40, "Lien de vie",
                      "Lie la vie de l'allié ciblé à la vôtre pendant 5 min : chacun de vos soins sur un autre allié le soigne aussi "
                      "de 10 % du montant. Un seul Lien de vie à la fois.", 0, 0, 10, icon_sid=19236,
                      tooltip="Reçoit 10 % des soins du Mage.", School=3, DurationIndex=DUR[300000], RangeIndex=RANGE[40],
                      **merge(aur(1, 4, 0, 1, target=21), none3(2, 3)))
NOTEACH.add(A['lien'])
A['lien_soin'] = cspell(AC, 'lien_soin', 10917, "Lien de vie", School=3, SpellVisual=visual(774),
                        **merge({'Effect1': 10, 'EffectBasePoints1': 0, 'EffectDieSides1': 1, 'EffectImplicitTargetA1': 21,
                                 'EffectBonusCoefficient1': 0, 'EffectRealPointsPerLevel1': 0}, none3(2, 3)))

HEALK = AHEALS + ['bouclier_nat', 'lien_soin']
tree(AG, 410, "Nature", CBIT[MAGE], 3, "MageArcane", 25297, [
    (1, "Cœur de la nature", 1, 25297, D,
     "Vos sorts de Feu deviennent des soins de Nature (Boule de feu, Brûlure, Trait de feu, Choc de flammes, Explosion pyrotechnique, "
     "Vague explosive). Un reset de talents vous rend vos sorts de Feu."),
    (1, "Sève", 5, 774, ('fx', aura(136, 0, 2)), lambda r: "Augmente vos soins de %d %%." % (2 * r)),
    (2, "Armure de nature", 1, 8936, ('spell', A['armure']), "Armure +20 % et puissance des soins +20 % pendant 30 min."),
    (2, "Pollen", 5, 9858, ('fx', mod(7, False, HEALK, 1)), lambda r: "Augmente de %d %% la chance de coup critique de vos soins." % r),
    (3, "Biome", 1, 774, ('spell', A['biome'][0]), "Soin sur la durée de 15 s. Rangs suivants chez le maître Mage."),
    (3, "Biome luxuriant", 5, 774, ('fx', lambda r: [('mod', 0, True, ['biome'], 5 * r), ('mod', 22, True, ['biome'], 5 * r)]),
     lambda r: "Augmente les soins de Biome de %d %%." % (5 * r), "Biome"),
    (4, "Écorce protectrice", 1, 8936, D, "Vos soins augmentent l'armure de la cible de 10 % pendant 5 s."),
    (4, "Intelligence sylvestre", 1, 1459, D,
     "Sur vous, Intelligence des arcanes et Illumination des arcanes donnent 20 % d'Intelligence en plus, et autant d'Esprit."),
    (4, "Concentration naturelle", 3, 17116, ('fx', mod(14, True, HEALK, -2)), lambda r: "Réduit le coût de vos soins de %d %%." % (2 * r)),
    (5, "Bouclier de nature", 1, 8936, ('spell', A['bouclier']), "Absorbe des dégâts pendant 30 s, comme Mot de pouvoir : Bouclier."),
    (5, "Bouclier renforcé", 3, 8936, ('fx', mod(8, True, ['bouclier_nat'], 10)),
     lambda r: "Augmente l'absorption de Bouclier de nature de %d %%." % (10 * r), "Bouclier de nature"),
    (6, "Harmonie", 5, 17116, ('fx', aura(136, 0, 2)), lambda r: "Augmente vos soins de %d %%." % (2 * r)),
    (7, "Lien de vie", 1, 19236, ('spell', A['lien']),
     "Un allié reçoit 10 % de chacun de vos soins sur les autres, pendant 5 min."),
    (7, "Lien de vie amélioré", 2, 19236, D, lambda r: "Lien de vie transmet %d %% de vos soins." % (10 + 5 * r), "Lien de vie"),
])
for _sid in AC.sla:
    V4_SLA.append((MAGE,) + _sid)
V4_GROUP_ADD = [(13, A['armure'])]
V4H += [('A4_FIRE', A_FIRE), ('A4_HEAL', A_HEAL), ('A4_KEEP', A_KEEP), ('A4_ARMURE', [A['armure']]), ('A4_ARMURE_SP', [A['armure_sp']]),
        ('A4_BOUCLIER', [A['bouclier']]), ('A4_ECORCE', [A['ecorce']]), ('A4_AI', [A['ai']]),
        ('A4_INT', [1459, 1460, 1461, 10156, 10157, 23028]), ('A4_LIEN', [A['lien']]), ('A4_LIEN_SOIN', [A['lien_soin']])]
V4T += [('T4_COEUR', "Cœur de la nature"), ('T4_ECORCE', "Écorce protectrice"), ('T4_SYLV', "Intelligence sylvestre"),
        ('T4_LIEN_V', "Lien de vie"), ('T4_LIEN_VAM', "Lien de vie amélioré")]

# ======================================================================== Voleur : Fantôme
ROGUE = 4
RG = Gen(8, range(36, 64))
V4_GENS.append((RG, 55700, 55824))
RC = Ctx(RG, 55700, {'finesse': 39}, ROGUE, ROGUE)
R = {}
C_FANTOME = 990590

_b, _pl = sc(35, 10)
R['lames_dmg'] = cspell(RC, 'lames_dmg', 11976, "Lames spectrales", School=5, SpellLevel=10, BaseLevel=10, DmgClass=1, SpellVisual=visual(686),
                        **merge({'Effect1': 2, 'EffectBasePoints1': _b, 'EffectDieSides1': 1, 'EffectRealPointsPerLevel1': _pl,
                                 'EffectImplicitTargetA1': 6, 'EffectApplyAuraName1': 0, 'EffectBonusCoefficient1': 0}, none3(2, 3)))
R['lames'] = RC.single('lames', 'finesse', 12042, 10, "Lames spectrales",
                       "Imprègne vos armes d'ombre pendant 30 min : chacun de vos coups inflige 35 points de dégâts d'Ombre "
                       "supplémentaires.", 0, 0, 0, icon_sid=18174, tooltip="Coups +35 dégâts d'Ombre.", School=5, PowerType=3,
                       ManaCost=0, DurationIndex=DUR[1800000], ProcFlags=0x4 | 0x10, ProcChance=100,
                       **merge({'Effect1': 6, 'EffectApplyAuraName1': 42, 'EffectTriggerSpell1': R['lames_dmg'], 'EffectImplicitTargetA1': 1,
                                'EffectBasePoints1': 0, 'EffectMiscValue1': 0}, none3(2, 3)))
NOTEACH.add(R['lames'])

_b, _pl = sc(90, 15)
R['entaille'] = RC.single('entaille', 'finesse', 11294, 15, "Entaille d'ombre",
                          "Une entaille chargée d'ombre : 60 % des dégâts de l'arme, puis 360 points de dégâts d'Ombre en 12 s. "
                          "Ajoute 1 point de combo.", 0, 0, 0, icon_sid=1752, tooltip="Dégâts d'Ombre toutes les 3 s.",
                          PowerType=3, ManaCost=45, School=5, MaxLevel=60, DurationIndex=DUR[12000],
                          **merge(weapon(1, 60), {'EffectRealPointsPerLevel1': 0},
                                  {'Effect3': 6, 'EffectApplyAuraName3': 3, 'EffectBasePoints3': _b, 'EffectDieSides3': 1,
                                   'EffectRealPointsPerLevel3': _pl, 'EffectImplicitTargetA3': 6, 'EffectAmplitude3': 3000,
                                   'EffectMiscValue3': 0, 'EffectTriggerSpell3': 0}))
NOTEACH.add(R['entaille'])
_b, _pl = sc(142, 20)
R['murmure'] = RC.single('murmure', 'finesse', 10894, 20, "Murmure d'ombre",
                         "Murmure une malédiction d'ombre : 852 points de dégâts d'Ombre en 18 s.", 0, 0, 0, icon_sid=589,
                         tooltip="Dégâts d'Ombre toutes les 3 s.", PowerType=3, ManaCost=30, School=5, MaxLevel=60, RangeIndex=RANGE[20],
                         EffectBasePoints1=_b, EffectRealPointsPerLevel1=_pl, EffectBonusCoefficient1=0)
NOTEACH.add(R['murmure'])
_b, _pl = sc(60, 25)
R['supplice'] = RC.single('supplice', 'finesse', 11275, 25, "Supplice",
                          "Coup de grâce qui inflige des dégâts d'Ombre en 15 s, selon les points de combo : 1 point : 400, "
                          "2 points : 500, 3 points : 600, 4 points : 700, 5 points : 800.", 0, 0, 0, icon_sid=1943,
                          tooltip="Dégâts d'Ombre toutes les 3 s.", PowerType=3, ManaCost=25, School=5, MaxLevel=60,
                          DurationIndex=DUR[15000], EffectBasePoints1=_b, EffectRealPointsPerLevel1=_pl, EffectPointsPerComboPoint1=20.0,
                          EffectAmplitude1=3000, EffectMechanic1=0, Mechanic=0, **none3(2, 3))
NOTEACH.add(R['supplice'])

a['fant_frappe'] = cspell(RC, 'k_fantome', 11976, "Frappe d'ombre", School=5, **merge(weapon(1, 100), dmg(2, 40)))
creature(C_FANTOME, "Fantôme", 10935, 1.0, 1, 0.3, 0.4, 0.8, 6, [(a['fant_frappe'], 1, 1000, 3000)])
R['spectre'] = RC.single('spectre', 'finesse', 12740, 20, "Spectre",
                         "Invoque un fantôme qui combat à vos côtés pendant 15 s.", 120000, 0, 0, icon_sid=19028,
                         PowerType=3, ManaCost=25, School=5, DurationIndex=DUR[15000], CastingTimeIndex=1,
                         EffectMiscValue1=C_FANTOME, EffectBasePoints1=0, EffectDieSides1=1, EffectImplicitTargetA1=1, EffectRadiusIndex1=RADIUS[3])
NOTEACH.add(R['spectre'])
R['horde'] = RC.single('horde', 'finesse', 12740, 30, "Horde spectrale",
                       "Invoque 3 fantômes qui combattent à vos côtés pendant 12 s.", 120000, 0, 0, icon_sid=19028,
                       PowerType=3, ManaCost=40, School=5, DurationIndex=DUR[12000], CastingTimeIndex=1,
                       EffectMiscValue1=C_FANTOME, EffectBasePoints1=2, EffectDieSides1=1, EffectImplicitTargetA1=1, EffectRadiusIndex1=RADIUS[3])
NOTEACH.add(R['horde'])
R['crit'] = cspell(RC, 'r_crit', 12042, "Pénombre", DurationIndex=DUR[-1], **merge(aur(1, 52, 0, 1), none3(2, 3)))
R['forme'] = RC.single('forme', 'finesse', 12042, 40, "Forme spectrale",
                       "Vous devenez à demi spectral pendant 20 s : dégâts +30 %, Lames spectrales infligent le double de dégâts et "
                       "la recharge de Spectre est remise à zéro.", 180000, 0, 0, icon_sid=19028,
                       tooltip="Dégâts +30 %, Lames spectrales x2.", PowerType=3, ManaCost=0, School=5, DurationIndex=DUR[20000],
                       **merge(aur(1, 79, 127, 30), aur(2, 108, 0, 100), aur(3, 4, 0, 1)))
AFFECT.append((R['forme'], 1, RG.mask('lames_dmg')))
NOTEACH.add(R['forme'])

tree(RG, 411, "Fantôme", CBIT[ROGUE], 3, "RogueSubtlety", 19028, [
    (1, "Lames spectrales", 1, 18174, ('spell', R['lames']), "Vos coups infligent 35 points de dégâts d'Ombre supplémentaires pendant 30 min."),
    (1, "Froid du néant", 5, 18271, ('fx', aura(79, 32, 2)), lambda r: "Augmente vos dégâts d'Ombre de %d %%." % (2 * r)),
    (2, "Entaille d'ombre", 1, 1752, ('spell', R['entaille']), "60 % des dégâts de l'arme et 360 points de dégâts d'Ombre en 12 s. 1 point de combo."),
    (2, "Lames affûtées", 5, 18174, ('fx', mod(0, True, ['lames_dmg'], 5)), lambda r: "Augmente les dégâts de Lames spectrales de %d %%." % (5 * r)),
    (3, "Spectre", 1, 19028, ('spell', R['spectre']), "Invoque un fantôme pendant 15 s. Recharge 2 min."),
    (3, "Murmure d'ombre", 1, 589, ('spell', R['murmure']), "852 points de dégâts d'Ombre en 18 s, à 20 m."),
    (3, "Pas de l'ombre", 3, 13750, ('fx', aura(49, 0, 1)), lambda r: "Augmente votre chance d'esquiver de %d %%." % r),
    (4, "Supplice", 1, 1943, ('spell', R['supplice']), "Coup de grâce : dégâts d'Ombre sur 15 s selon les points de combo."),
    (4, "Hantise", 3, 589, ('fx', lambda r: [('mod', 22, True, ['entaille', 'supplice', 'murmure'], 10 * r)]),
     lambda r: "Augmente les dégâts sur la durée d'Entaille d'ombre, de Murmure d'ombre et de Supplice de %d %%." % (10 * r)),
    (5, "Horde spectrale", 1, 19028, ('spell', R['horde']), "Invoque 3 fantômes pendant 12 s. Recharge 2 min."),
    (5, "Pénombre", 3, 14278, D, lambda r: "Augmente de %d %% vos chances de coup critique contre les cibles qui ne vous attaquent pas." % r),
    (6, "Lien spectral", 2, 19028, ('fx', mod(1, False, ['spectre', 'horde'], 3000)), lambda r: "Vos fantômes restent %d s de plus." % (3 * r)),
    (6, "Âme errante", 5, 14278, ('fx', aura(87, 127, -1)), lambda r: "Réduit les dégâts que vous subissez de %d %%." % r),
    (7, "Forme spectrale", 1, 19028, ('spell', R['forme']), "20 s : dégâts +30 %, Lames spectrales x2, recharge de Spectre remise à zéro. Recharge 3 min."),
    (7, "Spectre durable", 2, 19028, ('fx', mod(1, False, ['forme'], 2500)), lambda r: "Augmente la durée de Forme spectrale de %.1f s." % (2.5 * r)),
])
for _sid in RC.sla:
    V4_SLA.append((ROGUE,) + _sid)
V4H += [('R4_CRIT', [R['crit']]), ('R4_FORME', [R['forme']]), ('R4_SPECTRE', [R['spectre']])]
V4T += [('T4_PENOMBRE', "Pénombre")]

# ======================================================================== Chasseur : Infirmier
HUNTER = 3
IG = Gen(9, range(32, 64))
V4_GENS.append((IG, 55825, 55949))
IC = Ctx(IG, 55825, {'precision': 163}, HUNTER, HUNTER)
I = {}
FORM_FURTIF, FORM_INFIRMIER = 20, 21
ST_INF = 1 << (FORM_INFIRMIER - 1)
FORM_PATCH = {FORM_FURTIF: ("Posture furtive", 0), FORM_INFIRMIER: ("Posture infirmier", 1)}
HSHOTS_V = {'auto': [75], 'arcane': [3044, 14281, 14282, 14283, 14284, 14285, 14286, 14287],
            'serpent': [1978, 13549, 13550, 13551, 13552, 13553, 13554, 13555, 25295],
            'multi': [2643, 14288, 14289, 14290, 25294], 'volley': [1510, 14294, 14295],
            'aimed': [19434, 20900, 20901, 20902, 20903, 20904]}
# en Posture infirmier, les tirs de dégâts sont remplacés par les tirs de soin
vset(sum(HSHOTS_V.values(), []), StancesNot=ST_INF)

I['furtif'] = IC.single('posture', 'precision', 2457, 10, "Posture furtive", "Posture du chasseur : vos tirs infligent des dégâts.",
                        1000, 0, 0, icon_sid=5384, School=0, PowerType=0, EffectMiscValue1=FORM_FURTIF, EffectApplyAuraName1=36)
I['infirmier'] = IC.single('posture', 'precision', 2457, 10, "Posture infirmier",
                           "Posture du soigneur : vos tirs de distance soignent vos alliés au lieu de blesser vos ennemis.",
                           1000, 0, 0, icon_sid=1515 if False else 3662, School=0, PowerType=0, EffectMiscValue1=FORM_INFIRMIER,
                           EffectApplyAuraName1=36)
NOTEACH.update([I['furtif'], I['infirmier']])

# soins cachés : direct et sur la durée (montant calculé par le module)
I['soin'] = cspell(IC, 'i_soin', 10917, "Soin de campagne", School=3, Stances=0, StancesNot=0, SpellVisual=visual(25297),
                   **merge({'Effect1': 10, 'EffectBasePoints1': 0, 'EffectDieSides1': 1, 'EffectImplicitTargetA1': 21,
                            'EffectBonusCoefficient1': 0, 'EffectRealPointsPerLevel1': 0}, none3(2, 3)))
I['hot'] = cspell(IC, 'i_hot', 10929, "Morsure apaisante", School=3, Stances=0, StancesNot=0, DurationIndex=DUR[15000], SpellIconID=icon(1978),
                  **merge({'Effect1': 6, 'EffectApplyAuraName1': 8, 'EffectBasePoints1': 0, 'EffectDieSides1': 1,
                           'EffectImplicitTargetA1': 21, 'EffectAmplitude1': 3000, 'EffectBonusCoefficient1': 0,
                           'EffectRealPointsPerLevel1': 0}, none3(2, 3)))
I['degats'] = cspell(IC, 'i_degats', 3044, "Rafale", School=0, DmgClass=3,
                     **merge({'Effect1': 2, 'EffectBasePoints1': 0, 'EffectDieSides1': 1, 'EffectImplicitTargetA1': 6,
                              'EffectBonusCoefficient1': 0, 'EffectRealPointsPerLevel1': 0}, none3(2, 3)))

# tirs de soin : effet factice, le module calcule le soin (arme x mult + base + PA distance x apc)
I4_SHOT, I4_SRC, I4_W, I4_MULT, I4_APC, I4_KIND = [], [], [], [], [], []
def _hshots(key, src_ids, name, base60, w, mult, apc, kind, desc_fn, extra=None, icon_sid=None):
    ids = []
    for k, sid in enumerate(src_ids):
        L = SPR[sid][dbc_col('SpellLevel')]
        b = round(rank_value(base60, L)) if base60 else 0
        sets = {'Stances': ST_INF, 'StancesNot': 0, 'School': 3, 'SpellVisual': NATVIS, 'TargetCreatureType': 0,
                'Effect1': 3, 'EffectApplyAuraName1': 0, 'EffectBasePoints1': max(0, b - 1), 'EffectDieSides1': 1,
                'EffectImplicitTargetA1': 21, 'EffectImplicitTargetB1': 0, 'EffectRealPointsPerLevel1': 0, 'EffectChainTarget1': 0,
                'EffectTriggerSpell1': 0, 'EffectRadiusIndex1': 0, 'Mechanic': 0}
        sets.update(none3(2, 3))
        if extra:
            sets.update(extra)
        if icon_sid:
            sets['SpellIconID'] = icon(icon_sid)
        hid = IG.add(IC.nid(), sid, name, desc_fn(b), "Rang %d" % (k + 1) if len(src_ids) > 1 else "", key=key, sets=sets)
        IC.sla.append((163, hid))
        ids.append(hid)
        I4_SHOT.append(hid); I4_SRC.append(sid); I4_W.append(w); I4_MULT.append(mult); I4_APC.append(apc); I4_KIND.append(kind)
    IG.chain_ranks(ids) if len(ids) > 1 else None
    return ids
I['tir'] = _hshots('tir_soin', [75], "Tir de soin", 0, 1, 120, 0, 0,
                   lambda b: "Tir automatique de soin : soigne l'allié ciblé de 120 % des dégâts de votre arme à distance.")
I['revig'] = _hshots('revigorant', HSHOTS_V['arcane'], "Tir revigorant", 220, 0, 100, 20, 0,
                     lambda b: "Soigne instantanément l'allié ciblé de %d points de vie, plus 20 %% de votre puissance d'attaque à distance." % b)
I['apaise'] = _hshots('apaisante', HSHOTS_V['serpent'], "Morsure apaisante", 670, 0, 100, 10, 1,
                      lambda b: "Soigne l'allié ciblé de %d points de vie en 15 s, plus 10 %% de votre puissance d'attaque à distance." % b)
I['multi'] = _hshots('multi_soin', HSHOTS_V['multi'], "Tir de soin multiple", 150, 1, 120, 0, 2,
                     lambda b: "Soigne l'allié ciblé et 2 alliés proches de 120 %% des dégâts de votre arme + %d." % round(b * 1.2))
I['vise'] = _hshots('visee', HSHOTS_V['aimed'], "Visée salvatrice", 600, 1, 120, 0, 0,
                    lambda b: "Un tir précis qui soigne l'allié ciblé de 120 %% des dégâts de votre arme + %d." % round(b * 1.2))
# Salve de soins : zone au sol, soin sur la durée
I['salve'] = []
for _k, _sid in enumerate(HSHOTS_V['volley']):
    _L = SPR[_sid][dbc_col('SpellLevel')]
    _t = round(rank_value(100, _L))
    _s = common(_L, 60000, 0, 25, 1510, base_cls=HUNTER)
    _s.update({'Stances': ST_INF, 'School': 3, 'SpellVisual': visual(740), 'CastingTimeIndex': 1, 'Targets': 64, 'RangeIndex': RANGE[35],
               'AttributesEx': 0, 'DurationIndex': DUR[6000], 'Effect1': 27, 'EffectApplyAuraName1': 8, 'EffectBasePoints1': _t - 1,
               'EffectDieSides1': 1, 'EffectImplicitTargetA1': 31, 'EffectImplicitTargetB1': 0, 'EffectAmplitude1': 1000,
               'EffectRadiusIndex1': RADIUS[8], 'EffectRealPointsPerLevel1': 0, 'EffectTriggerSpell1': 0, 'EffectBonusCoefficient1': 0})
    _s.update(none3(2, 3))
    _h = IG.add(IC.nid(), 10216, "Salve de soins", "Une salve de flèches de soin : %d points de vie par seconde pendant 6 s aux alliés "
                "dans un rayon de 8 mètres." % _t, "Rang %d" % (_k + 1), key='salve', sets=_s)
    IC.sla.append((163, _h)); I['salve'].append(_h)
    I4_SHOT.append(_h); I4_SRC.append(_sid); I4_W.append(0); I4_MULT.append(0); I4_APC.append(0); I4_KIND.append(9)
IG.chain_ranks(I['salve'])

I['fusee'] = IC.single('fusee', 'precision', 3044, 30, "Fusée de soin",
                       "Tire une fusée de soin : l'allié ciblé et les alliés à moins de 8 mètres sont soignés de 320 points de vie, "
                       "plus 10 % de votre puissance d'attaque à distance.", 8000, 0, 12, icon_sid=1543,
                       **merge({'Stances': ST_INF, 'School': 3, 'SpellVisual': NATVIS, 'Effect1': 3, 'EffectApplyAuraName1': 0,
                                'EffectBasePoints1': 319, 'EffectDieSides1': 1, 'EffectImplicitTargetA1': 21, 'EffectRealPointsPerLevel1': 0,
                                'TargetCreatureType': 0}, none3(2, 3)))
I4_SHOT.append(I['fusee']); I4_SRC.append(0); I4_W.append(0); I4_MULT.append(100); I4_APC.append(10); I4_KIND.append(3)
NOTEACH.add(I['fusee'])
_b, _pl = sc(150, 25)
I['bandage'] = IC.single('bandage', 'precision', 10929, 25, "Bandage de combat",
                         "Pose un bandage de combat sur un allié à 20 mètres : 450 points de vie en 9 s.", 10000, 0, 10, icon_sid=10840,
                         tooltip="Récupère des points de vie toutes les 3 s.", School=3, Stances=0, StancesNot=0, RangeIndex=RANGE[20], DurationIndex=DUR[10000],
                         MaxLevel=60, EffectBasePoints1=_b, EffectRealPointsPerLevel1=_pl, EffectAmplitude1=3000, EffectBonusCoefficient1=0)
NOTEACH.add(I['bandage'])
I['rafale'] = IC.single('rafale', 'precision', 12042, 40, "Rafale",
                        "Tire 3 Tirs multiples d'un coup sur tout le monde à moins de 20 mètres : en Posture infirmier, soigne vos "
                        "alliés ; en Posture furtive, blesse vos ennemis.", 180000, 0, 20, icon_sid=25294, School=0,
                        **merge(aur(1, 4, 0, 1), none3(2, 3)), DurationIndex=DUR[1000])
NOTEACH.add(I['rafale'])

ISHOTK = ['tir_soin', 'revigorant', 'apaisante', 'multi_soin', 'visee', 'salve', 'fusee']
VSHOTM = vmask(*sum(HSHOTS_V.values(), []))
tree(IG, 412, "Infirmier", CBIT[HUNTER], 3, "HunterMarksmanship", 3662, [
    (1, "Postures de campagne", 1, 3662, ('fx', lambda r: [('learn', I['furtif']), ('learn', I['infirmier'])]),
     "Vous apprenez la Posture furtive (vos tirs blessent) et la Posture infirmier (vos tirs soignent vos alliés)."),
    (1, "Puissance de campagne", 5, 19431, ('fx', aura(167, 0, 2)), lambda r: "Augmente votre puissance d'attaque à distance de %d %%." % (2 * r)),
    (2, "Trousse de campagne", 5, 10840, ('fx', aura(136, 0, 2)), lambda r: "Augmente vos soins de %d %%." % (2 * r)),
    (2, "Main sûre", 3, 19426, ('fx', mod(7, False, ['i_soin', 'i_hot'], 2)), lambda r: "Augmente de %d %% la chance de coup critique de vos soins." % (2 * r)),
    (3, "Munitions bénies", 5, 19416, ('fx', mod(14, True, [VSHOTM] + ISHOTK, -2)), lambda r: "Réduit le coût en mana de vos tirs de %d %%." % (2 * r)),
    (3, "Familier infirmier", 1, 1515, D, "Votre familier soigne l'allié le plus blessé toutes les 6 s."),
    (4, "Bandage de combat", 1, 10840, ('spell', I['bandage']), "450 points de vie en 9 s sur un allié à 20 m. Recharge 10 s."),
    (4, "Triage", 3, 10840, D, lambda r: "Vos tirs de soin soignent %d %% de plus les cibles sous 50 %% de vie." % (5 * r)),
    (5, "Fusée de soin", 1, 1543, ('spell', I['fusee']), "Soigne l'allié ciblé et les alliés à 8 mètres. Recharge 8 s."),
    (5, "Cadence de campagne", 3, 19461, ('fx', aura(140, 0, 4)), lambda r: "Augmente votre vitesse de tir de %d %%." % (4 * r)),
    (6, "Vocation", 5, 19498, ('fx', aura(137, 3, 3)), lambda r: "Augmente votre Intelligence de %d %%." % (3 * r)),
    (7, "Rafale", 1, 25294, ('spell', I['rafale']), "3 Tirs multiples d'un coup sur tout le monde à 20 m : soins ou dégâts selon la posture. Recharge 3 min."),
    (7, "Rafale améliorée", 2, 25294, ('fx', mod(11, False, ['rafale'], -30000)), lambda r: "Réduit la recharge de Rafale de %d s." % (30 * r)),
])
for _sid in IC.sla:
    V4_SLA.append((HUNTER,) + _sid)
V4H += [('I4_SHOT', I4_SHOT), ('I4_SRC', I4_SRC), ('I4_W', I4_W), ('I4_MULT', I4_MULT), ('I4_APC', I4_APC), ('I4_KIND', I4_KIND),
        ('I4_SOIN', [I['soin']]), ('I4_HOT', [I['hot']]), ('I4_DEGATS', [I['degats']]), ('I4_RAFALE', [I['rafale']]),
        ('I4_POSTURES', [I['furtif'], I['infirmier']]), ('I4_FORM', [FORM_INFIRMIER])]
V4T += [('T4_POSTURES', "Postures de campagne"), ('T4_FAMILIER', "Familier infirmier"), ('T4_TRIAGE', "Triage")]

# ======================================================================== fin : on rend la main au générateur principal
TALG, TAL_ID = TALG_MAIN, TAL_ID_MAIN
