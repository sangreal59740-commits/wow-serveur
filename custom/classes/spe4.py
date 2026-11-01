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

# ======================================================================== fin : on rend la main au générateur principal
TALG, TAL_ID = TALG_MAIN, TAL_ID_MAIN
