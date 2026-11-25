# Nécromancien, 4e spé « Nécropole » (tank par les invocations), validée le 25/11/2026 (doc « Nouvelles classes et soutiens »).
# Exécuté dans gen_sorts.py (mêmes globales), après les arbres des autres classes : les identifiants déjà attribués ne bougent pas.
# Le Nécromancien reste derrière en tissu : le géant mort-vivant (appris par le 1er talent) et l'abomination tankent.
# Les sorts à effet factice (Lien d'os, Ordre, Cri de la tombe, Aspect, Mur, Sacrifice) sont gérés par le module classes.

NSKILL['nec'] = 918
NEC_SKILLLINES = [(918, "Nécropole", 354)]
C_GEANT = 990545
NPC = Ctx(NG, 62459, NSKILL, 9, NECRO)      # sorts visibles de la Nécropole (62459-62499)
NEC = {}
NEC_H = {}

def _threat(n, v60, target=6, b=None):
    tb, pl = lin(v60)
    d = {'Effect%d' % n: 63, 'EffectBasePoints%d' % n: tb, 'EffectDieSides%d' % n: 1, 'EffectRealPointsPerLevel%d' % n: pl,
         'EffectImplicitTargetA%d' % n: target, 'EffectApplyAuraName%d' % n: 0}
    if b:
        d['EffectImplicitTargetB%d' % n] = b
    return d

# ---------------------------------------------------------------- géant mort-vivant
a['ge_poing'] = cspell(NC, 'k_geant', 11976, "Poing écrasant", **merge(weapon(1, 120), _threat(2, 150), none(3)))
a['ge_pietine'] = cspell(NC, 'k_geant', 1680, "Piétinement", School=0,
                         **merge(dmg(1, 220, 40, target=22), {'EffectImplicitTargetB1': 15, 'EffectRadiusIndex1': RADIUS[8]},
                                 _threat(2, 200, target=22, b=15), {'EffectRadiusIndex2': RADIUS[8]}, none(3)))
a['ge_rugit'] = cspell(NC, 'k_geant', 355, "Rugissement", DurationIndex=DUR[3000], RecoveryTime=0)
creature(C_GEANT, "Géant mort-vivant", 9760, 0.9, 1, 1.6, 0.8, 2.5, 6,
         [(a['ge_poing'], 1, 1000, 2000), (a['ge_pietine'], 1, 2000, 6000), (a['ge_rugit'], 1, 0, 8000)])

# sort d'invocation (appris par le talent Pacte des colosses), même mécanique que les autres invocations
_front = NPC.single('invocation', 'nec', 688, 10, "Invocation : Géant mort-vivant",
                    "Invoque un géant mort-vivant qui tanke pour vous. Coûte 2 points d'invocation.", 0, 3000, 20, icon_sid=712,
                    Effect1=3, EffectImplicitTargetA1=1, EffectMiscValue1=C_GEANT, DurationIndex=0, Category=0)
_hidden = cspell(NC, 'invocation', 12740, "Invocation : Géant mort-vivant", EffectMiscValue1=C_GEANT, DurationIndex=DUR[-1],
                 EffectBasePoints1=0, EffectDieSides1=1, EffectImplicitTargetA1=1, CastingTimeIndex=1)
_anni = cspell(NC, 'annihilation', 12740, "Annihilation", EffectMiscValue1=C_GEANT, DurationIndex=DUR[5000],
               EffectBasePoints1=0, EffectDieSides1=1, EffectImplicitTargetA1=1, EffectRadiusIndex1=RADIUS[5])
N['inv_geant'] = _front
SUMMON_TABLE.append((_front, _hidden, _anni, C_GEANT, 2))
NOTEACH.add(_front)

# ---------------------------------------------------------------- sorts de la spé
def _dummy(target=1):
    return {'Effect1': 3, 'EffectImplicitTargetA1': target, 'EffectBasePoints1': 0, 'EffectDieSides1': 1, 'EffectApplyAuraName1': 0,
            'Effect2': 0, 'EffectApplyAuraName2': 0, 'Effect3': 0, 'EffectApplyAuraName3': 0, 'DurationIndex': 0}

NEC['lien'] = NPC.single('nec_lien', 'nec', 12042, 12, "Lien d'os",
                         "30 % des dégâts que vous subissez sont transférés à votre invocation principale. Dure jusqu'à annulation.",
                         0, 0, 3, icon_sid=19028, tooltip="Dégâts partagés avec l'invocation principale.",
                         **merge(auraf(1, 4, 0, 1), none(2), none(3), {'DurationIndex': DUR[-1]}))
NEC['ordre'] = NPC.single('nec_ordre', 'nec', 688, 14, "Ordre : provocation",
                          "Votre invocation principale provoque votre cible et l'oblige à l'attaquer pendant 3 s.", 8000, 0, 3,
                          icon_sid=355, **merge(_dummy(6), {'RangeIndex': RANGE[40]}))
NEC['drain'] = NPC.single('nec_drain', 'nec', 689, 18, "Drain nécrotique",
                          "Canalisé : inflige 400 points de dégâts d'Ombre en 5 s ; votre invocation principale est soignée d'autant.",
                          10000, 0, 8, icon_sid=689, tooltip="Perd des points de vie au profit de l'invocation du Nécromancien.",
                          School=5, DurationIndex=DUR[5000], MaxLevel=60,
                          **merge(per(1, 80), {'EffectBonusCoefficient1': 0.1}, none(2), none(3)))
NEC['carapace'] = NPC.single('nec_carapace', 'nec', 11426, 24, "Carapace d'os",
                             "Entoure une de vos invocations d'os : absorbe 1 500 points de dégâts. Dure 30 s.", 20000, 0, 10,
                             icon_sid=6229, tooltip="Absorbe des dégâts.", School=5, MaxLevel=60, DurationIndex=DUR[30000],
                             **merge(per(1, 1500, aura=69, target=21, amp=0), {'EffectMiscValue1': 127, 'EffectBonusCoefficient1': 0.1},
                                     none(2), none(3), {'RangeIndex': RANGE[40]}))
NEC['cri'] = NPC.single('nec_cri', 'nec', 688, 30, "Cri de la tombe",
                        "Toutes vos invocations provoquent les ennemis à moins de 10 mètres pendant 6 s.", 120000, 0, 8,
                        icon_sid=1161, **_dummy())
NEC['aspect'] = NPC.single('nec_aspect', 'nec', 13165, 36, "Aspect du gardien",
                           "Toute la menace que vous générez passe sur votre invocation principale. Dure jusqu'à annulation.",
                           1000, 0, 2, icon_sid=19028, tooltip="La menace du Nécromancien passe sur son invocation principale.",
                           **merge(auraf(1, 10, 127, -100), none(2), none(3), {'DurationIndex': DUR[-1]}))
NEC['mur'] = NPC.single('nec_mur', 'nec', 688, 44, "Mur de cadavres",
                        "Les dégâts subis par toutes vos invocations sont réduits de 40 % pendant 10 s.", 180000, 0, 6,
                        icon_sid=871, **_dummy())
NEC['sacrifice'] = NPC.single('nec_sacrifice', 'nec', 688, 50, "Sacrifice d'os",
                              "Détruit une invocation mineure (squelette, goule, chien, squelette de givre) : votre invocation principale est soignée de 15 % de ses points de vie.",
                              60000, 0, 5, icon_sid=18540, **_dummy())
NEC['rugissement'] = NPC.single('nec_rugissement', 'nec', 688, 25, "Rugissement des tombes",
                                "Votre géant provoque les ennemis à moins de 15 mètres et sa menace est triplée pendant 10 s.", 60000, 0, 6,
                                icon_sid=5209, **_dummy())
NEC['titan'] = NPC.single('nec_titan', 'nec', 688, 40, "Titan de la Nécropole",
                          "Pendant 20 s, votre géant devient un titan : points de vie +50 %, dégâts subis -30 %, menace triplée, chaque coup provoque sa cible.",
                          300000, 0, 10, icon_sid=12975, **_dummy())
NOTEACH.update([NEC['rugissement'], NEC['titan']])

# sorts cachés lancés par le module
NEC_H['cri'] = cspell(NC, 'nec_cri', 1161, "Cri de la tombe", EffectRadiusIndex1=RADIUS[10], DurationIndex=DUR[6000])
NEC_H['cri15'] = cspell(NC, 'nec_rugissement', 1161, "Rugissement des tombes", EffectRadiusIndex1=RADIUS[13], DurationIndex=DUR[6000])
NEC_H['mur'] = cspell(NC, 'nec_mur', 12042, "Mur de cadavres", DurationIndex=DUR[10000],
                      **merge(auraf(1, 87, 127, -40, target=1), none(2), none(3)))
NEC_H['menace3'] = cspell(NC, 'nec_rugissement', 12042, "Menace triplée", DurationIndex=DUR[10000],
                          **merge(auraf(1, 10, 127, 200, target=1), none(2), none(3)))
NEC_H['titan'] = cspell(NC, 'nec_titan', 12042, "Titan de la Nécropole", DurationIndex=DUR[20000],
                        **merge(auraf(1, 133, 0, 50, target=1), auraf(2, 87, 127, -30, target=1), auraf(3, 10, 127, 200, target=1),
                                {'EffectApplyAuraName3': 10}))
NEC_H['titan_taille'] = cspell(NC, 'nec_titan', 12042, "Titan", DurationIndex=DUR[20000],
                               **merge(auraf(1, 61, 0, 40, target=1), none(2), none(3)))
NEC_H['pacte'] = cspell(NC, 'nec_pacte', 12042, "Pacte des colosses", DurationIndex=DUR[-1],
                        **merge(auraf(1, 79, 127, -40, target=1), none(2), none(3)))
# auras d'entretien posées sur les invocations (valeurs fixées par le module selon les talents)
NEC_H['os'] = cspell(NC, 'nec_os', 12042, "Os épais", DurationIndex=DUR[-1],
                     **merge(auraf(1, 101, 1, 1), auraf(2, 10, 127, 1), auraf(3, 133, 0, 1)))
NEC_H['ancrage'] = cspell(NC, 'nec_ancrage', 12042, "Ancrage", DurationIndex=DUR[-1],
                          **merge(auraf(1, 49, 0, 1), auraf(2, 47, 0, 1), auraf(3, 79, 127, 1)))
NEC_H['colosse'] = cspell(NC, 'nec_colosse', 12042, "Colosse d'os", DurationIndex=DUR[-1],
                          **merge(auraf(1, 77, 12, 1), auraf(2, 77, 5, 1), auraf(3, 61, 0, 20)))
NEC_H['taunt'] = cspell(NC, 'nec_titan', 355, "Provocation", DurationIndex=DUR[3000], RecoveryTime=0)

# ---------------------------------------------------------------- arbre Nécropole (tank), 51 points
_NEC_SUMMONS = ['k_geant', 'k_abo']
tree(NG, 426, "Nécropole", CM_N, 3, "WarlockSummoning", 712, [
    (1, "Pacte des colosses", 5, 712, D,
     lambda r: "Verrou de la spé. Vous apprend Invocation : Géant mort-vivant et vous donne 1 point d'invocation, mais vos sorts infligent 40 %% de dégâts en moins. Augmente les points de vie et les dégâts du géant et de l'abomination de %d %%." % (4 * r)),
    (1, "Os épais", 5, 18731, D, lambda r: "Augmente l'armure de vos invocations de %d %%." % (6 * r)),
    (2, "Fureur du colosse", 5, 1161, D, lambda r: "Augmente la menace générée par le géant et l'abomination de %d %%." % (20 * r)),
    (2, "Carapace améliorée", 3, 6229, D, lambda r: "Augmente l'absorption de Carapace d'os de %d %%." % (10 * r)),
    (2, "Ordre rapide", 2, 355, D, lambda r: "Réduit la recharge d'Ordre : provocation de %d s." % (2 * r)),
    (3, "Haine viscérale", 3, 5209, D, lambda r: "Vomi et Crochet de l'abomination, Piétinement et Poing écrasant du géant génèrent %d %% de menace en plus." % (30 * r)),
    (3, "Chair cousue", 5, 18731, D, lambda r: "Augmente les points de vie de vos invocations de %d %%." % (4 * r)),
    (3, "Drain amélioré", 2, 689, D, lambda r: "Augmente les dégâts et les soins de Drain nécrotique de %d %%." % (10 * r)),
    (4, "Rugissement des tombes", 1, 5209, ('spell', NEC['rugissement']), "Votre géant provoque les ennemis à moins de 15 mètres et sa menace est triplée pendant 10 s. Recharge 1 min."),
    (4, "Lien d'os amélioré", 2, 19028, D, lambda r: "Lien d'os transfère %d %% des dégâts au lieu de 30 %%." % (30 + 10 * r)),
    (4, "Ancrage", 3, 2565, D, lambda r: "Augmente les chances d'esquive et de parade de vos invocations de %d %%." % (2 * r)),
    (5, "Colosse d'os", 1, 12975, D, "Votre géant gagne 20 % de points de vie, grandit et devient insensible aux étourdissements et à la peur."),
    (5, "Horde des tombes", 1, 18710, D, "Vous donne 1 point d'invocation supplémentaire."),
    (5, "Mur amélioré", 2, 871, D, lambda r: "Réduit la recharge de Mur de cadavres de %d s." % (30 * r)),
    (6, "Aimant à haine", 3, 1161, D, lambda r: "Contre un ennemi qui attaque le Nécromancien ou un soigneur, la menace de vos invocations augmente de %d %%." % (50 * r)),
    (6, "Moelle vivace", 2, 774, D, lambda r: "Vos invocations récupèrent %d %% de leurs points de vie toutes les 5 s." % r),
    (7, "Titan de la Nécropole", 1, 12975, ('spell', NEC['titan']), "Ultime : pendant 20 s, votre géant devient un titan : points de vie +50 %, dégâts subis -30 %, menace triplée, chaque coup provoque sa cible. Recharge 5 min."),
    (7, "Titan prolongé", 2, 12975, D, lambda r: "Augmente la durée de Titan de la Nécropole de %.1f s." % (2.5 * r)),
])

# maître de classe : les sorts de la Nécropole (hors talents) s'ajoutent à la liste du Nécromancien
for _sp in NG.spells:
    if _sp['id'] in NEC.values() and _sp['id'] not in NOTEACH:
        _lv = _sp['sets'].get('SpellLevel', 1)
        _tid = TEACH[0]; TEACH[0] += 1
        TG.add(_tid, TEACH_BASE, _sp['name'], _sp['desc'], _sp['rank'], family=False,
               sets={'EffectTriggerSpell1': _sp['id'], 'SpellLevel': _lv, 'BaseLevel': _lv, 'MaxLevel': 0,
                     'SpellIconID': _sp['sets'].get('SpellIconID', SPR[_sp['base']][117])})
        TRAINER_SPELLS.setdefault(900, []).append((_tid, max(10, 9 * _lv * _lv), _lv))
