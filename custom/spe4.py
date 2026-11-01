# 4e spécialisation des classes vanilla (doc section 6 bis), exécuté dans gen_sorts.py (mêmes globales).
# Chaque classe : un Gen dans la famille de sorts de la classe (bits libres >= 34), un arbre de talents (onglet 4),
# des sorts appris par talent, des modifications de sorts vanilla (VPATCH, serveur + client).

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

# ======================================================================== fin : on rend la main au générateur principal
TALG, TAL_ID = TALG_MAIN, TAL_ID_MAIN
