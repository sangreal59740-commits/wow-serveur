# Nouvelles classes du 23/11/2026 (doc « Nouvelles classes et soutiens ») : Tisserand de vie (12), Fossoyeur (13), Martyr (14).
# Exécuté dans gen_sorts.py (mêmes globales), après spe4.py et la définition des maîtres de classe.
# Sorts à rang unique qui grandissent avec le niveau (points par niveau jusqu'au niveau 60), coût en % du mana de base.
# Les mécaniques que les données ne décrivent pas (Fils, sauts, fantômes, pactes...) sont gérées par le module classes (NouvellesCast).

TISS, FOSS, MART = 12, 13, 14
for _c in (TISS, FOSS, MART):
    CBIT[_c] = 1 << (_c - 1)
NV_GENS = []             # (gen, premier id, dernier id)
NV_SQL = []              # lignes SQL ajoutées à sorts.sql
NVH = []                 # constantes pour le module : (nom, [valeurs])
NV_SKILLLINES = [(906, "Trame", 56), (907, "Lien", 613), (908, "Fil tranchant", 78), (909, "Moire", 253),
                 (910, "Profanateur", 38), (911, "Requiem", 593), (912, "Charnier", 354), (913, "Passeur", 355),
                 (914, "Bastion", 257), (915, "Saignée", 26), (916, "Offrande", 56), (917, "Hémophage", 355)]
NV_TPL = {906: TISS, 907: FOSS, 908: MART}     # gabarit de maître -> classe
NV_TABS = []

TWG = Gen(14, range(0, 64)); NV_GENS.append((TWG, 40000, 40499))
FSG = Gen(15, range(0, 64)); NV_GENS.append((FSG, 41000, 41499))
TWC = Ctx(TWG, 40000, {'trame': 906, 'lien': 907, 'fil': 908, 'moire': 909}, 5, TISS)
FSC = Ctx(FSG, 41000, {'prof': 910, 'req': 911, 'char': 912, 'pass': 913}, 3, FOSS)
TWH = Ctx(TWG, 40300, {}, 5, TISS)            # sorts cachés (déclenchés par le module)
FSH = Ctx(FSG, 41300, {}, 3, FOSS)

CAST2 = dict(CAST); CAST2.update({6000: 171, 500: 3, 750: 110, 10000: 7})
DUR.update({9000: 105, 18000: 85, 25000: 63, 7000: 165, 40000: 64, 90000: 23, 180000: 25})
PROC_MELEE = 0x4 | 0x10              # coup en mêlée (blanc ou technique)

BASE = {'Stances': 0, 'StancesNot': 0, 'Category': 0, 'CategoryRecoveryTime': 0, 'Reagent1': 0, 'ReagentCount1': 0,
        'Totem1': 0, 'RequiresSpellFocus': 0, 'CasterAuraState': 0, 'TargetAuraState': 0, 'ManaCostPerlevel': 0,
        'ManaPerSecond': 0, 'ManaPerSecondPerLevel': 0, 'ModalNextSpell': 0, 'TargetCreatureType': 0, 'StackAmount': 0,
        'ProcFlags': 0, 'ProcChance': 101, 'ProcCharges': 0}

def nS(ctx, key, tree, base, lv, name, desc, cd=0, cast=0, mpct=0, energy=0, icon_sid=None, tooltip='', dur=None, rng=None,
      school=None, **sets):
    s = dict(BASE)
    s.update({'SpellLevel': lv, 'BaseLevel': lv, 'MaxLevel': 60, 'CastingTimeIndex': CAST2[cast], 'RecoveryTime': cd,
              'PowerType': 3 if energy else 0, 'ManaCost': energy, 'ManaCostPercentage': 0 if energy else mpct})
    if dur is not None:
        s['DurationIndex'] = DUR[dur]
    if rng is not None:
        s['RangeIndex'] = RANGE[rng]
    if school is not None:
        s['School'] = school
    if icon_sid:
        s['SpellIconID'] = icon(icon_sid)
    s.update(sets)
    sid = ctx.g.add(ctx.nid(), base, name, desc, "", tooltip=tooltip, key=key, sets=s)
    ctx.sla.append((ctx.skills[tree], sid))
    return sid

def nH(ctx, key, base, name, tooltip='', dur=None, school=None, **sets):
    s = dict(BASE)
    s.update({'SpellLevel': 0, 'BaseLevel': 0, 'MaxLevel': 60, 'ManaCost': 0, 'ManaCostPercentage': 0, 'PowerType': 0,
              'RecoveryTime': 0, 'CastingTimeIndex': 1, 'EquippedItemClass': -1, 'EquippedItemSubClassMask': 0,
              'StartRecoveryTime': 0, 'StartRecoveryCategory': 0})
    if dur is not None:
        s['DurationIndex'] = DUR[dur]
    if school is not None:
        s['School'] = school
    s.update(sets)
    return ctx.trig(key, base, name, "", tooltip=tooltip, **s)

def nV(n, v60, lv, sides=1):
    """valeur d'effet qui grandit avec le niveau : v60 au niveau 60 (bas de la fourchette), sides = écart"""
    b, pl = sc(v60, lv)
    return {'EffectBasePoints%d' % n: b, 'EffectDieSides%d' % n: max(1, int(sides)), 'EffectRealPointsPerLevel%d' % n: pl}

def FIX(n, v):
    return {'EffectBasePoints%d' % n: int(v) - 1, 'EffectDieSides%d' % n: 1, 'EffectRealPointsPerLevel%d' % n: 0}

def nE(n, effect, target=6, aura=0, misc=0, b=0, radius=None, amp=0, trig=0, chain=0, coef=0.0, tb=0):
    d = {'Effect%d' % n: effect, 'EffectImplicitTargetA%d' % n: target, 'EffectImplicitTargetB%d' % n: tb,
         'EffectApplyAuraName%d' % n: aura, 'EffectMiscValue%d' % n: misc, 'EffectAmplitude%d' % n: amp,
         'EffectTriggerSpell%d' % n: trig, 'EffectChainTarget%d' % n: chain, 'EffectBonusCoefficient%d' % n: coef,
         'EffectRadiusIndex%d' % n: RADIUS[radius] if radius else 0, 'EffectPointsPerComboPoint%d' % n: 0.0}
    return d

def OFF(*ns):
    out = {}
    for n in ns:
        out.update(nE(n, 0, target=0))
        out.update({'EffectBasePoints%d' % n: 0, 'EffectDieSides%d' % n: 0, 'EffectRealPointsPerLevel%d' % n: 0})
    return out

def DMG(n, lo, hi, lv, coef, target=6, radius=None, tb=0, chain=0):
    return merge(nE(n, 2, target, radius=radius, tb=tb, chain=chain, coef=coef), nV(n, lo, lv, hi - lo + 1))

def HEAL(n, lo, hi, lv, coef, target=21, chain=0):
    return merge(nE(n, 10, target, chain=chain, coef=coef), nV(n, lo, lv, hi - lo + 1))

def PER(n, aura, total, dur, amp, lv, coef_total, target=6, radius=None, tb=0, effect=6):
    ticks = dur // amp
    return merge(nE(n, effect, target, aura=aura, amp=amp, radius=radius, tb=tb, coef=round(coef_total / ticks, 4)),
                 nV(n, max(1, round(total / ticks)), lv))

def AUR(n, aura, misc, val, target=1, radius=None, tb=0, effect=6, amp=0, lv=None, trig=0):
    d = nE(n, effect, target, aura=aura, misc=misc, radius=radius, tb=tb, amp=amp, trig=trig)
    d.update(FIX(n, val) if lv is None else nV(n, val, lv))
    return d

def WEAP(n, flat, lv, target=6, radius=None, tb=0):
    """dégâts de l'arme (normalisés) + bonus fixe qui grandit avec le niveau"""
    return merge(nE(n, 121, target, radius=radius, tb=tb), nV(n, flat, lv))

def WPCT(n, pct, target=6):
    return merge(nE(n, 31, target), FIX(n, pct))

def CP(n, k):
    return merge(nE(n, 80, 6), FIX(n, k))

def DUMMY(n, target=6, radius=None, tb=0):
    return merge(nE(n, 3, target, radius=radius, tb=tb), FIX(n, 1))

def coefc(cast_ms):
    return round(max(1500, cast_ms) / 3500.0, 3)

MELEE = {'DmgClass': 2, 'PreventionType': 2, 'RangeIndex': RANGE[5], 'EquippedItemClass': 2, 'EquippedItemSubClassMask': 173555,
         'InterruptFlags': 0}

TW = {}     # Tisserand
FS = {}     # Fossoyeur

# ======================================================================== Tisserand de vie : sorts cachés
TW['fils'] = nH(TWH, 'h_fils', 139, "Fils", tooltip="Soins reçus augmentés de 2 % par Fil.", dur=30000, StackAmount=5,
              Attributes=0x10000, **merge(AUR(1, 118, 0, 2, target=25), OFF(2, 3)))          # allié : soins reçus +2 % par Fil
TW['fils_e'] = nH(TWH, 'h_fils_e', 589, "Fils", tooltip="Fils noués : Trancher les fils les consomme.", dur=30000, StackAmount=5,
                School=3, **merge(AUR(1, 4, 0, 1, target=6), OFF(2, 3)))                      # ennemi : marqueur pour Trancher
TW['trancher_d'] = nH(TWH, 'h_trancher', 5176, "Trancher les fils", School=3, **merge(DMG(1, 1, 1, 0, 0.43), OFF(2, 3)))
TW['toile_hot'] = nH(TWH, 'h_toile_hot', 139, "Toile protectrice", tooltip="Récupère des points de vie.", dur=10000, School=3,
                   **merge(PER(1, 8, 400, 10000, 2000, 8, 0.2, target=21), OFF(2, 3)))
TW['don_e'] = nH(TWH, 'h_don', 1243, "Don de trame", tooltip="Récupère du mana.", dur=5000,
               **merge(AUR(1, 21, 0, 3, target=21, amp=1000), OFF(2, 3)))                     # 3 % du mana max par seconde
TW['bonus_soin'] = nH(TWH, 'h_bonus_soin', 2061, "Grande trame", School=3, **merge(HEAL(1, 1, 1, 0, 0), OFF(2, 3)))
TW['mortel'] = nH(TWH, 'h_mortel', 589, "Fil mortel", tooltip="Dégâts d'Ombre toutes les 3 s.", dur=15000, StackAmount=5, School=5,
                **merge(PER(1, 3, 150, 15000, 3000, 1, 0.25), OFF(2, 3)))
TW['mortel_x'] = nH(TWH, 'h_mortel_x', 589, "Fil mortel", School=5, **merge(DMG(1, 1, 1, 0, 0), OFF(2, 3)))
TW['noeud_m'] = nH(TWH, 'h_noeud', 1243, "Nœud serré", tooltip="Les Fils mortels frappent deux fois plus vite.", dur=6000,
                 **merge(AUR(1, 4, 0, 1, target=6), OFF(2, 3)))
TW['atropos_m'] = nH(TWH, 'h_atropos', 1243, "Fil d'Atropos", tooltip="Les Fils mortels infligent 100 % de dégâts en plus.", dur=8000,
                   **merge(AUR(1, 4, 0, 1, target=6), OFF(2, 3)))
TW['destin_r'] = nH(TWH, 'h_destin', 2061, "Fil du destin", School=1, **merge(HEAL(1, 1, 1, 0, 0, target=1), OFF(2, 3)))
TW['trepas'] = nH(TWH, 'h_trepas', 1243, "Refus du trépas", tooltip="Dégâts subis réduits de 80 %.", dur=3000,
                **merge(AUR(1, 87, 127, -80), OFF(2, 3)))
TW['ariane_v'] = nH(TWH, 'h_ariane', 1243, "Fil d'Ariane", dur=1000, **merge(AUR(1, 4, 0, 1), OFF(2, 3)))

# ======================================================================== Tisserand de vie : sorts (valeurs au niveau 60)
TW['toucher'] = nS(TWC, 'toucher', 'trame', 2050, 1, "Toucher vital",
                 "Tisse un fil de vie dans la cible : rend 750 à 850 points de vie (au niveau 60) et pose 1 Fil.",
                 cast=2000, mpct=10, icon_sid=774, school=3, **merge(HEAL(1, 750, 850, 1, 0.57), OFF(2, 3)))
TW['trait'] = nS(TWC, 'trait', 'fil', 5176, 1, "Trait de fil",
               "Lance un fil acéré : 300 à 340 points de dégâts de Nature (au niveau 60) et pose 1 Fil sur la cible.",
               cast=2000, mpct=8, icon_sid=5176, school=3, **merge(DMG(1, 300, 340, 1, 0.57), OFF(2, 3)))
TW['vie'] = nS(TWC, 'vie', 'trame', 139, 2, "Fil de vie",
             "Rend 900 points de vie en 15 s (au niveau 60). Si la cible n'a plus de blessure, le fil saute sur l'allié le plus blessé "
             "(3 sauts au maximum).", mpct=9, icon_sid=139, school=3, tooltip="Récupère des points de vie.", dur=15000,
             **merge(PER(1, 8, 900, 15000, 3000, 2, 1.0, target=21), OFF(2, 3)))
TW['trancher'] = nS(TWC, 'trancher', 'fil', 5176, 2, "Trancher les fils",
                  "Tranche les Fils noués sur la cible : 400 points de dégâts de Nature, plus 150 par Fil consommé (au niveau 60). "
                  "Dégâts doublés si la cible a moins de 25 % de sa vie.", cd=8000, mpct=6, icon_sid=8921, school=3,
                  **merge(DUMMY(1), OFF(2, 3)))
TW['vigueur'] = nS(TWC, 'vigueur', 'lien', 1243, 4, "Fil de vigueur",
                 "Noue un fil de vigueur sur la cible : chances de coup critique des attaques et des sorts augmentées de 1 % "
                 "(niveau 4) à 6 % (niveau 60) pendant 60 min.", mpct=6, icon_sid=1126, dur=3600000,
                 tooltip="Chances de coup critique augmentées.",
                 **merge(AUR(1, 52, 0, 1, target=21), {'EffectRealPointsPerLevel1': 5.0 / 56},
                         AUR(2, 71, 127, 1, target=21), {'EffectRealPointsPerLevel2': 5.0 / 56}, OFF(3)))
TW['entrave'] = nS(TWC, 'entrave', 'fil', 339, 4, "Entrave de fils", "Ligote la cible dans des fils : immobilisée pendant 4 s.",
                 cd=20000, mpct=5, icon_sid=339, dur=4000, **merge(AUR(1, 26, 0, 0, target=6), OFF(2, 3)), CastingTimeIndex=1)
TW['epines'] = nS(TWC, 'epines', 'fil', 589, 6, "Fil d'épines", "Enroule un fil d'épines : 500 points de dégâts de Nature en 10 s (au niveau 60).",
                mpct=7, icon_sid=467, school=3, dur=10000, tooltip="Dégâts de Nature toutes les 2 s.",
                **merge(PER(1, 3, 500, 10000, 2000, 6, 0.8), OFF(2, 3)))
TW['toile_p'] = nS(TWC, 'toile_p', 'lien', 17, 8, "Toile protectrice",
                 "Tisse une toile autour de la cible : absorbe 650 points de dégâts (au niveau 60) pendant 30 s. À la fin de la toile, "
                 "la cible récupère 400 points de vie en 10 s.", cd=6000, mpct=10, icon_sid=17, dur=30000, school=3,
                 tooltip="Absorbe des dégâts.", **merge(AUR(1, 69, 127, 650, target=21, lv=8), {'EffectBonusCoefficient1': 0.1}, OFF(2, 3)))
TW['lien_f'] = nS(TWC, 'lien_f', 'lien', 1243, 10, "Lien de force",
                "Lie un allié au Tisserand pendant 30 min : dégâts et hâte augmentés de 5 %. Un seul allié lié à la fois.",
                mpct=5, icon_sid=6346, dur=1800000, tooltip="Dégâts et hâte augmentés de 5 %.",
                **merge(AUR(1, 79, 127, 5, target=21), AUR(2, 138, 0, 5, target=21), AUR(3, 65, 0, 5, target=21)))
TW['raccom'] = nS(TWC, 'raccom', 'trame', 2061, 12, "Raccommodage", "Recoud les plaies : rend instantanément 400 à 450 points de vie (au niveau 60).",
                cd=6000, mpct=8, icon_sid=2061, school=3, **merge(HEAL(1, 400, 450, 12, 0.43), OFF(2, 3)))
TW['laceration'] = nS(TWC, 'laceration', 'fil', 8921, 14, "Lacération",
                    "Lacère la cible : 220 à 250 points de dégâts de Nature, puis 150 points de dégâts en 5 s (au niveau 60).",
                    cd=6000, mpct=7, icon_sid=8921, school=3, dur=5000, tooltip="Saigne.",
                    **merge(PER(1, 3, 150, 5000, 1000, 14, 0.1), DMG(2, 220, 250, 14, 0.43), OFF(3)))
TW['resu'] = nS(TWC, 'resu', 'trame', 20770, 16, "Résurrection", "Renoue le fil de vie d'un allié mort. Hors combat.",
              cast=4000, mpct=25, icon_sid=2006)
TW['tissage'] = nS(TWC, 'tissage', 'lien', 1243, 18, "Tissage rapide", "Accélère la cible : hâte augmentée de 20 % pendant 15 s.",
                 cd=60000, mpct=6, icon_sid=12042, dur=15000, tooltip="Hâte augmentée de 20 %.",
                 **merge(AUR(1, 138, 0, 20, target=21), AUR(2, 65, 0, 20, target=21), AUR(3, 140, 0, 20, target=21)))
TW['navette'] = nS(TWC, 'navette', 'trame', 1064, 20, "Navette",
                 "Envoie une navette de soin qui rebondit sur 3 alliés : 600, puis 450, puis 300 points de vie (au niveau 60).",
                 cast=2500, mpct=14, icon_sid=1064, school=3, **merge(HEAL(1, 600, 640, 20, 0.71, target=45, chain=3), OFF(2, 3)),
                 DmgMultiplier1=0.75)
TW['fils_t'] = nS(TWC, 'fils_t', 'fil', 15407, 22, "Fils tranchants", "Canalisé : 4 coups de 160 points de dégâts de Nature en 3 s (au niveau 60).",
                cd=10000, mpct=9, icon_sid=15407, school=3, dur=3000, tooltip="Dégâts de Nature.",
                **merge(PER(1, 3, 640, 3000, 750, 22, 0.86), OFF(2, 3)))
TW['cocon'] = nS(TWC, 'cocon', 'lien', 1243, 24, "Cocon", "Enveloppe la cible d'un cocon : dégâts subis réduits de 40 % pendant 6 s.",
               cd=60000, mpct=6, icon_sid=1022, dur=6000, tooltip="Dégâts subis réduits de 40 %.",
               **merge(AUR(1, 87, 127, -40, target=21), OFF(2, 3)))
TW['demeler'] = nS(TWC, 'demeler', 'trame', 4987, 26, "Démêler", "Démêle les fils néfastes : retire 1 effet magique, 1 poison et 1 maladie.",
                 mpct=6, icon_sid=4987, **merge(merge(nE(1, 38, 21, misc=1), FIX(1, 1)), merge(nE(2, 38, 21, misc=4), FIX(2, 1)),
                                                 merge(nE(3, 38, 21, misc=3), FIX(3, 1))))
TW['toile'] = nS(TWC, 'toile', 'fil', 26573, 28, "Toile",
               "Tisse une toile au sol à 30 m : 100 points de dégâts de Nature par seconde pendant 6 s aux ennemis à 8 m (au niveau 60), "
               "ralentis de 30 %.", cd=10000, mpct=10, icon_sid=8921, school=3, dur=6000, rng=30, Targets=64,
               **merge(PER(1, 3, 600, 6000, 1000, 28, 0.6, target=28, radius=8, effect=27),
                       AUR(2, 33, 0, -30, target=28, radius=8, effect=27), OFF(3)))
TW['metier'] = nS(TWC, 'metier', 'trame', 139, 30, "Métier à tisser",
                "Installe un métier à tisser : les membres du groupe à 20 m récupèrent 60 points de vie par seconde pendant 10 s (au niveau 60).",
                cd=30000, mpct=14, icon_sid=740, school=3, dur=10000, tooltip="Récupère des points de vie.",
                **merge(PER(1, 8, 600, 10000, 1000, 30, 0.8, target=20, radius=20), OFF(2, 3)))
TW['ariane'] = nS(TWC, 'ariane', 'lien', 1243, 32, "Fil d'Ariane", "Se tire le long d'un fil jusqu'à un allié à 30 m.",
                cd=30000, mpct=4, icon_sid=1953, rng=30, **merge(DUMMY(1, target=21), OFF(2, 3)))
TW['don'] = nS(TWC, 'don', 'lien', 1243, 34, "Don de trame", "Rend 15 % de son mana au Tisserand et à un allié en 5 s.",
             cd=300000, icon_sid=29166, **merge(DUMMY(1, target=21), OFF(2, 3)))
TW['pelote'] = nS(TWC, 'pelote', 'fil', 5176, 36, "Pelote",
                "Projette une pelote de fils : 620 à 700 points de dégâts de Nature (au niveau 60) et pose 1 Fil sur la cible.",
                cast=3000, mpct=12, icon_sid=2912, school=3, **merge(DMG(1, 620, 700, 36, 0.86), OFF(2, 3)))
TW['grande'] = nS(TWC, 'grande', 'trame', 2060, 40, "Grande trame",
                "Grand tissage de vie : rend 1 800 à 2 000 points de vie (au niveau 60), 10 % de plus par Fil sur la cible.",
                cast=3000, mpct=20, icon_sid=2060, school=3, **merge(HEAL(1, 1800, 2000, 40, 0.86), OFF(2, 3)))
TW['partages'] = nS(TWC, 'partages', 'lien', 1243, 44, "Liens partagés",
                  "Relie le groupe pendant 10 s : les dégâts subis par un membre sont répartis entre tous les membres à 30 m.",
                  cd=120000, mpct=12, icon_sid=19752, dur=10000, tooltip="Dégâts subis répartis dans le groupe.",
                  **merge(AUR(1, 4, 0, 1, target=20, radius=30), OFF(2, 3)))
TW['ressoudure'] = nS(TWC, 'ressoudure', 'trame', 139, 46, "Ressoudure",
                    "Ressoude tout le groupe : 500 points de vie en 10 s aux membres à 30 m (au niveau 60).",
                    cast=2000, cd=20000, mpct=18, icon_sid=596, school=3, dur=10000, tooltip="Récupère des points de vie.",
                    **merge(PER(1, 8, 500, 10000, 2000, 46, 0.5, target=20, radius=30), OFF(2, 3)))
TW['destin'] = nS(TWC, 'destin', 'lien', 1243, 48, "Fil du destin",
                "Protège la cible pendant 1 min : le prochain coup mortel la laisse à 1 point de vie et la soigne de 20 % de sa vie.",
                cd=600000, mpct=8, icon_sid=20711, dur=60000, tooltip="Le prochain coup mortel est évité.",
                **merge(AUR(1, 4, 0, 1, target=21), OFF(2, 3)))
TW['tempete'] = nS(TWC, 'tempete', 'fil', 5176, 50, "Tempête de fils",
                 "Déchaîne une tempête de fils : 500 à 560 points de dégâts de Nature à la cible et jusqu'à 4 ennemis proches (au niveau 60).",
                 cast=2000, cd=15000, mpct=14, icon_sid=16914, school=3,
                 **merge(DMG(1, 500, 560, 50, 0.43, chain=5), OFF(2, 3)), DmgMultiplier1=1.0)
TW['rapiecage'] = nS(TWC, 'rapiecage', 'trame', 12051, 52, "Rapiéçage", "Canalisé : rend 32 % du mana en 8 s.",
                   cd=180000, icon_sid=12051, dur=8000, tooltip="Récupère du mana.",
                   **merge(AUR(1, 21, 0, 4, target=1, amp=1000), OFF(2, 3)))
# Moire (DPS au corps à corps, mana)
TW['fuseau'] = nS(TWC, 'fuseau', 'moire', 1752, 1, "Coup de fuseau", "Frappe avec l'arme : dégâts de l'arme +40 (au niveau 60) et pose 1 Fil mortel.",
                mpct=5, icon_sid=8820, **merge(WEAP(1, 40, 1), OFF(2, 3)), **MELEE)
TW['noeud'] = nS(TWC, 'noeud', 'moire', 1243, 2, "Serrer le nœud",
               "Pendant 6 s, les Fils mortels de la cible infligent leurs dégâts deux fois plus vite.", cd=12000, mpct=4, icon_sid=11426,
               rng=30, **merge(DUMMY(1), OFF(2, 3)))
TW['linceul'] = nS(TWC, 'linceul', 'moire', 17, 6, "Linceul", "S'enveloppe d'un linceul : absorbe 500 points de dégâts (au niveau 60) pendant 15 s.",
                 cd=30000, mpct=8, icon_sid=17, dur=15000, tooltip="Absorbe des dégâts.",
                 **merge(AUR(1, 69, 127, 500, target=1, lv=6), {'EffectBonusCoefficient1': 0.1}, OFF(2, 3)))
TW['fil_noir'] = nS(TWC, 'fil_noir', 'moire', 1752, 12, "Fil noir", "Frappe avec l'arme : dégâts de l'arme +80 (au niveau 60) et pose 2 Fils mortels.",
                  cd=6000, mpct=7, icon_sid=5374, **merge(WEAP(1, 80, 12), OFF(2, 3)), **MELEE)
TW['fil_tendu'] = nS(TWC, 'fil_tendu', 'moire', 20252, 14, "Fil tendu", "Se tire le long d'un fil jusqu'à un ennemi situé entre 8 et 25 m.",
                   cd=20000, mpct=4, icon_sid=100, **merge(nE(1, 96, 6), FIX(1, 0), OFF(2, 3)), RangeIndex=95)
TW['noeud_c'] = nS(TWC, 'noeud_c', 'moire', 853, 20, "Nœud coulant", "Étrangle la cible : étourdie pendant 3 s si elle porte au moins 3 Fils mortels.",
                 cd=30000, mpct=5, icon_sid=853, dur=3000, rng=5, **merge(AUR(1, 12, 0, 0, target=6), OFF(2, 3)))
TW['funebre'] = nS(TWC, 'funebre', 'moire', 1449, 28, "Toile funèbre", "Pose 1 Fil mortel à tous les ennemis à moins de 8 m.",
                 cd=10000, mpct=9, icon_sid=13018, school=5, **merge(DUMMY(1, target=22, radius=8, tb=15), OFF(2, 3)))
TW['recolte'] = nS(TWC, 'recolte', 'moire', 1243, 36, "Récolte",
                 "Récolte la vie qui s'échappe : rend 5 % de vos points de vie par Fil mortel sur la cible, sans retirer les Fils.",
                 cd=30000, mpct=4, icon_sid=18265, rng=30, **merge(DUMMY(1), OFF(2, 3)))
TW['atropos'] = nS(TWC, 'atropos', 'moire', 1243, 42, "Fil d'Atropos",
                 "Sur une cible à moins de 25 % de sa vie : ses Fils mortels infligent 100 % de dégâts en plus pendant 8 s.",
                 cd=20000, mpct=5, icon_sid=17877, rng=30, **merge(DUMMY(1), OFF(2, 3)))
TW['contagion'] = nS(TWC, 'contagion', 'moire', 1243, 50, "Contagion", "Copie les Fils mortels de la cible sur 2 ennemis proches.",
                   cd=15000, mpct=8, icon_sid=18266, rng=30, **merge(DUMMY(1), OFF(2, 3)))

# sorts appris par talent (Trame, Lien, Fil tranchant, Moire)
TW['conducteur'] = nS(TWC, 'conducteur', 'trame', 1243, 20, "Fil conducteur",
                    "Pendant 20 s, la cible reçoit 20 % de tous les soins faits sur les autres membres du groupe.", cd=120000, mpct=6,
                    icon_sid=6077, dur=20000, tooltip="Reçoit une part des soins du groupe.", **merge(AUR(1, 4, 0, 1, target=21), OFF(2, 3)))
TW['recousu'] = nS(TWC, 'recousu', 'trame', 2061, 30, "Recousu",
                 "Consomme le Fil de vie de la cible et la soigne aussitôt de 12 s de ce soin.", cd=15000, mpct=6, icon_sid=8936,
                 **merge(DUMMY(1, target=21), OFF(2, 3)))
TW['tapisserie'] = nS(TWC, 'tapisserie', 'trame', 1243, 50, "Tapisserie de vie",
                    "Pendant 20 s : chaque soin pose 1 Fil, soins augmentés de 30 % et coût réduit de 50 %.", cd=300000, icon_sid=724,
                    dur=20000, tooltip="Soins +30 %, coût -50 %.",
                    **merge(AUR(1, 136, 127, 30), AUR(2, 72, 127, -50), OFF(3)))
TW['infusion'] = nS(TWC, 'infusion', 'lien', 1243, 20, "Infusion de trame",
                  "Pendant 15 s, la cible inflige 20 % de dégâts et de soins en plus, et ses sorts coûtent 20 % de moins.", cd=180000, mpct=6,
                  icon_sid=10060, dur=15000, tooltip="Dégâts et soins +20 %, coût -20 %.",
                  **merge(AUR(1, 79, 127, 20, target=21), AUR(2, 136, 127, 20, target=21), AUR(3, 72, 127, -20, target=21)))
TW['aura'] = nS(TWC, 'aura', 'lien', 19746, 40, "Aura de trame", "Aura : les membres du groupe à 30 m infligent 3 % de dégâts en plus et en subissent 3 % de moins.",
              icon_sid=19746, dur=-1, tooltip="Dégâts +3 %, dégâts subis -3 %.",
              **merge(AUR(1, 79, 127, 3, target=1, radius=30, effect=35), AUR(2, 87, 127, -3, target=1, radius=30, effect=35), OFF(3)))
TW['grand_t'] = nS(TWC, 'grand_t', 'lien', 1243, 50, "Grand tissage",
                 "Pendant 15 s, le groupe à 30 m inflige 15 % de dégâts en plus, gagne 15 % de hâte et subit 15 % de dégâts en moins.",
                 cd=300000, icon_sid=19752, dur=15000, tooltip="Dégâts et hâte +15 %, dégâts subis -15 %.",
                 **merge(AUR(1, 79, 127, 15, target=20, radius=30), AUR(2, 138, 0, 15, target=20, radius=30),
                         AUR(3, 87, 127, -15, target=20, radius=30)))
TW['baillon'] = nS(TWC, 'baillon', 'fil', 15487, 20, "Bâillon de fil", "Bâillonne la cible : interrompt son sort et la réduit au silence pendant 3 s.",
                 cd=45000, mpct=4, icon_sid=15487, dur=3000, rng=30, **merge(nE(1, 68, 6), FIX(1, 0), AUR(2, 27, 0, 0, target=6), OFF(3)))
TW['garrot'] = nS(TWC, 'garrot', 'fil', 589, 30, "Garrot", "Serre un garrot de fils : 900 points de dégâts de Nature en 12 s (au niveau 60), et pose 1 Fil toutes les 4 s.",
                mpct=9, icon_sid=6789, school=3, dur=12000, tooltip="Dégâts de Nature toutes les 4 s.",
                **merge(PER(1, 3, 900, 12000, 4000, 30, 1.0), OFF(2, 3)))
TW['lame'] = nS(TWC, 'lame', 'fil', 1243, 50, "Lame de trame",
              "Pendant 20 s : chaque sort pose 2 Fils, Trancher les fils n'a plus de recharge et vos dégâts augmentent de 15 %.",
              cd=300000, icon_sid=16914, dur=20000, tooltip="Dégâts +15 %.", **merge(AUR(1, 79, 127, 15), OFF(2, 3)))
TW['bouche'] = nS(TWC, 'bouche', 'moire', 1766, 20, "Bouche cousue", "Coud la bouche de la cible : interrompt son sort et la réduit au silence pendant 2 s.",
                cd=20000, mpct=3, icon_sid=1766, dur=2000, **merge(nE(1, 68, 6), FIX(1, 0), AUR(2, 27, 0, 0, target=6), OFF(3)), **MELEE)
TW['derniere'] = nS(TWC, 'derniere', 'moire', 1243, 50, "Dernière maille",
                  "Pendant 20 s : chaque coup pose 2 Fils mortels, les Fils se cumulent jusqu'à 10 et infligent 20 % de dégâts en plus.",
                  cd=300000, icon_sid=8820, dur=20000, tooltip="Fils mortels renforcés.", **merge(AUR(1, 4, 0, 1), OFF(2, 3)))
T_TALENT_SPELLS = ['conducteur', 'recousu', 'tapisserie', 'infusion', 'aura', 'grand_t', 'baillon', 'garrot', 'lame', 'bouche', 'derniere']
NOTEACH.update(TW[k] for k in T_TALENT_SPELLS)

# ======================================================================== Fossoyeur : sorts cachés
FS['pourriture'] = nH(FSH, 'h_pourriture', 589, "Pourriture", tooltip="Dégâts d'Ombre toutes les 3 s.", dur=12000, StackAmount=5, School=5,
                    **merge(PER(1, 3, 300, 12000, 3000, 1, 0.0), OFF(2, 3)))
FS['entrave_d'] = nH(FSH, 'h_entrave', 1715, "Malédiction d'entrave", tooltip="Vitesse de déplacement réduite de 50 %.", dur=10000,
                   School=5, Mechanic=11, **merge(AUR(1, 33, 0, -50, target=6), OFF(2, 3)))
FS['epuise_d'] = nH(FSH, 'h_epuise', 1715, "Malédiction d'épuisement", tooltip="Vitesse d'attaque et d'incantation réduites de 20 %.",
                  dur=10000, School=5, **merge(AUR(1, 138, 0, -20, target=6), AUR(2, 65, 0, -20, target=6), OFF(3)))
FS['curee_d'] = nH(FSH, 'h_curee', 16827, "Curée", School=0, **merge(DMG(1, 300, 340, 6, 0.0), OFF(2, 3)), DmgClass=2)
FS['drain_pet'] = nH(FSH, 'h_drain_pet', 2061, "Drain de chair", School=5, **merge(HEAL(1, 1, 1, 0, 0, target=21), OFF(2, 3)))
FS['force_pet'] = nH(FSH, 'h_force_pet', 1243, "Force volée", tooltip="Dégâts augmentés de 20 %.", dur=20000,
                   **merge(AUR(1, 79, 127, 20, target=21), OFF(2, 3)))
FS['celerite_pet'] = nH(FSH, 'h_celerite_pet', 1243, "Célérité volée", tooltip="Vitesse d'attaque augmentée de 20 %.", dur=20000,
                      **merge(AUR(1, 138, 0, 20, target=21), OFF(2, 3)))
FS['moelle_pet'] = nH(FSH, 'h_moelle_pet', 1243, "Moelle volée", tooltip="Armure augmentée de 30 %.", dur=20000,
                    **merge(AUR(1, 101, 1, 30, target=21), OFF(2, 3)))
FS['festin_pet'] = nH(FSH, 'h_festin_pet', 1243, "Festin", tooltip="Vitesse d'attaque augmentée de 20 %.", dur=15000,
                    **merge(AUR(1, 138, 0, 20, target=21), AUR(2, 20, 0, 10, target=21, amp=1000), OFF(3)))
FS['pacte_pet'] = nH(FSH, 'h_pacte_pet', 1243, "Pacte du charnier", tooltip="Dégâts, points de vie et armure augmentés.", dur=-1,
                   **merge(AUR(1, 79, 127, 4), AUR(2, 133, 0, 4), AUR(3, 101, 1, 1)))
FS['vengeresse_d'] = nH(FSH, 'h_vengeresse', 5176, "Âme vengeresse", School=5, **merge(DMG(1, 80, 80, 1, 0.1), OFF(2, 3)))
FS['liberation_h'] = nH(FSH, 'h_liberation', 2061, "Libération", School=5, **merge(HEAL(1, 1, 1, 0, 0), OFF(2, 3)))
FS['partage_m'] = nH(FSH, 'h_partage', 1243, "Partage des chairs", dur=10000, **merge(AUR(1, 4, 0, 1), OFF(2, 3)))

# ======================================================================== Fossoyeur : sorts communs
FS['voile'] = nS(FSC, 'voile', 'prof', 1784, 4, "Voile de tombe", "Se cache sous un voile de terre : camouflé, vitesse réduite de 30 %.",
               cd=10000, icon_sid=1784, **merge(AUR(3, 33, 0, -30)))
FS['bouclier'] = nS(FSC, 'bouclier', 'pass', 17, 8, "Bouclier d'âme", "Entoure la cible d'un bouclier d'âme : absorbe 700 points de dégâts (au niveau 60) pendant 30 s.",
                  cd=30000, mpct=10, icon_sid=17, dur=30000, school=5, tooltip="Absorbe des dégâts.",
                  **merge(AUR(1, 69, 127, 700, target=21, lv=8), {'EffectBonusCoefficient1': 0.1}, OFF(2, 3)))
FS['exhum'] = nS(FSC, 'exhum', 'pass', 20770, 16, "Exhumation", "Exhume un allié mort et le ramène à la vie. Hors combat.",
               cast=4000, mpct=25, icon_sid=20770)
FS['poussiere'] = nS(FSC, 'poussiere', 'prof', 2094, 20, "Poussière de tombe", "Jette de la terre aux yeux de la cible : désorientée pendant 4 s.",
                   cd=30000, mpct=4, icon_sid=2094, dur=4000, **merge(AUR(1, 7, 0, 0, target=6), OFF(2, 3)), PowerType=0, ManaCost=0)
FS['enterre'] = nS(FSC, 'enterre', 'pass', 642, 40, "Enterré vivant",
                 "S'enterre pendant 6 s : insensible à tout, rend 20 % des points de vie, aucune action possible.", cd=300000, icon_sid=642,
                 dur=6000, tooltip="Enterré.", **merge(AUR(1, 39, 127, 0), AUR(2, 20, 0, 3, amp=1000), AUR(3, 12, 0, 0)))
# Profanateur (énergie, points de combo, arme à deux mains)
FS['posture'] = nS(FSC, 'posture', 'prof', 1243, 1, "Posture du profanateur",
                 "Passe à l'énergie et aux points de combo : puissance d'attaque augmentée de 10 %. Annulez l'effet pour revenir au mana.",
                 cd=1000, icon_sid=1787, dur=-1, tooltip="Énergie, puissance d'attaque +10 %.", **merge(AUR(1, 166, 0, 10), OFF(2, 3)))
FS['pelle'] = nS(FSC, 'pelle', 'prof', 1752, 1, "Coup de pelle", "Frappe à la pelle : dégâts de l'arme +60 (au niveau 60). Rapporte 1 point de combo.",
               energy=40, icon_sid=1752, **merge(WEAP(1, 60, 1), CP(2, 1), OFF(3)), **MELEE)
FS['m_pourriture'] = nS(FSC, 'm_pourriture', 'prof', 20375, 2, "Malédiction de pourriture",
                      "Maudit votre arme pendant 30 min : 30 % de chances par coup de poser une pourriture (300 points de dégâts d'Ombre en 12 s, "
                      "au niveau 60, cumulable 5 fois). Une seule malédiction d'arme à la fois.", icon_sid=172, dur=1800000,
                      tooltip="Vos coups peuvent maudire la cible.", ProcFlags=PROC_MELEE, ProcChance=30,
                      **merge(AUR(1, 42, 0, 0, trig=FS['pourriture']), OFF(2, 3)))
FS['m_entrave'] = nS(FSC, 'm_entrave', 'prof', 20375, 10, "Malédiction d'entrave",
                   "Maudit votre arme pendant 30 min : 20 % de chances par coup de ralentir la cible de 50 % pendant 10 s.", icon_sid=1715,
                   dur=1800000, tooltip="Vos coups peuvent ralentir la cible.", ProcFlags=PROC_MELEE, ProcChance=20,
                   **merge(AUR(1, 42, 0, 0, trig=FS['entrave_d']), OFF(2, 3)))
FS['m_epuise'] = nS(FSC, 'm_epuise', 'prof', 20375, 22, "Malédiction d'épuisement",
                  "Maudit votre arme pendant 30 min : 20 % de chances par coup de réduire de 20 % la vitesse d'attaque et d'incantation "
                  "de la cible pendant 10 s.", icon_sid=702, dur=1800000, tooltip="Vos coups peuvent épuiser la cible.",
                  ProcFlags=PROC_MELEE, ProcChance=20, **merge(AUR(1, 42, 0, 0, trig=FS['epuise_d']), OFF(2, 3)))
FS['biere'] = []
for _k, _L in enumerate(rank_levels(6)):
    _b, _cp = rv(200, _L), rv(220, _L)
    _sid = FSC.g.add(FSC.nid(), 2098, "Mise en bière",
                     "Coup de grâce : %d points de dégâts, plus %d par point de combo." % (_b, _cp), "Rang %d" % (_k + 1), key='biere',
                     sets=merge(BASE, {'SpellLevel': _L, 'BaseLevel': _L, 'MaxLevel': 0, 'CastingTimeIndex': 1, 'RecoveryTime': 0,
                                       'PowerType': 3, 'ManaCost': 35, 'ManaCostPercentage': 0, 'SpellIconID': icon(2098)},
                                nE(1, 2, 6), FIX(1, _b), {'EffectPointsPerComboPoint1': float(_cp)}, MELEE))
    FSC.sla.append((910, _sid))
    FS['biere'].append(_sid)
FSC.g.chain_ranks(FS['biere'])
FS['manche'] = nS(FSC, 'manche', 'prof', 1766, 14, "Coup de manche", "Coup de manche de pelle : interrompt le sort et réduit au silence pendant 2 s.",
                cd=10000, energy=25, icon_sid=1766, dur=2000,
                **merge(nE(1, 68, 6), FIX(1, 0), AUR(2, 27, 0, 0, target=6), OFF(3)), **MELEE)
FS['sortie'] = nS(FSC, 'sortie', 'prof', 1833, 18, "Sortie de terre",
                "Surgit de terre (camouflé) : dégâts de l'arme +250 %, étourdit 2 s, 2 points de combo.", energy=60, icon_sid=1833, dur=2000,
                **merge(AUR(1, 12, 0, 0, target=6), CP(2, 2), WPCT(3, 250)), Stances=0x20000000, **MELEE)
FS['sortie_st'] = FS['sortie']
FS['tourbillon'] = nS(FSC, 'tourbillon', 'prof', 1680, 28, "Tourbillon de pelle", "Frappe tous les ennemis à 8 m : dégâts de l'arme +40 (au niveau 60).",
                    cd=10000, energy=50, icon_sid=1680, **merge(WEAP(1, 40, 28, target=22, radius=8, tb=15), OFF(2, 3)),
                    **merge(MELEE, {'RangeIndex': RANGE[0]}))
FS['profanation'] = nS(FSC, 'profanation', 'prof', 1752, 36, "Profanation",
                     "Profane la cible : dégâts de l'arme +100 (au niveau 60), 30 % de plus par malédiction sur la cible.",
                     cd=10000, energy=40, icon_sid=8678, **merge(WEAP(1, 100, 36), DUMMY(2), OFF(3)), **MELEE)
# Requiem (mana, 70 % de puissance de base, 100 % avec Voix du requiem au rang 5)
FS['pierre'] = nS(FSC, 'pierre', 'req', 5176, 1, "Pierre tombale", "Fait tomber une pierre tombale : 490 à 560 points de dégâts de Nature (au niveau 60).",
                cast=3500, mpct=11, icon_sid=5487, school=3, **merge(DMG(1, 490, 560, 1, 1.0), OFF(2, 3)))
FS['eclat'] = nS(FSC, 'eclat', 'req', 116, 2, "Éclat d'os",
               "Projette un éclat d'os : 175 à 203 points de dégâts de Nature (au niveau 60), et hébète la cible (vitesse -50 %) pendant 6 s.",
               cd=8000, mpct=6, icon_sid=6343, school=3, dur=6000, Mechanic=27, CastingTimeIndex=1,
               **merge(AUR(1, 33, 0, -50, target=6), DMG(2, 175, 203, 2, 0.43), OFF(3)))
FS['glas'] = nS(FSC, 'glas', 'req', 8921, 6, "Glas",
              "Sonne le glas : 210 à 238 points de dégâts d'Ombre, puis 280 points de dégâts d'Ombre en 12 s (au niveau 60).",
              cast=2000, mpct=8, icon_sid=589, school=5, dur=12000, tooltip="Dégâts d'Ombre toutes les 3 s.",
              **merge(PER(1, 3, 280, 12000, 3000, 6, 0.4), DMG(2, 210, 238, 6, 0.43), OFF(3)))
FS['stele'] = nS(FSC, 'stele', 'req', 853, 12, "Chute de stèle",
               "Fait tomber une stèle : 140 à 161 points de dégâts de Nature (au niveau 60), et étourdit la cible pendant 3 s.",
               cd=30000, mpct=6, icon_sid=853, school=3, dur=3000, rng=30,
               **merge(AUR(1, 12, 0, 0, target=6), DMG(2, 140, 161, 12, 0.21), OFF(3)))
FS['eboulement'] = nS(FSC, 'eboulement', 'req', 26573, 20, "Éboulement",
                    "Provoque un éboulement à 30 m : 336 à 378 points de dégâts de Nature (au niveau 60) aux ennemis à 8 m, hébétés pendant 6 s.",
                    cast=3000, mpct=14, icon_sid=8056, school=3, dur=6000, rng=30, Targets=64,
                    **merge(DMG(1, 336, 378, 20, 0.29, target=28, radius=8), AUR(2, 33, 0, -50, target=28, radius=8), OFF(3)))
FS['onde'] = nS(FSC, 'onde', 'req', 120, 28, "Onde de terre",
              "Fait onduler le sol devant vous : 210 à 238 points de dégâts de Nature (au niveau 60) aux ennemis à 10 m, étourdis pendant 2 s.",
              cd=30000, mpct=10, icon_sid=8046, school=3, dur=2000,
              **merge(DMG(1, 210, 238, 28, 0.19, target=24, radius=10), AUR(2, 12, 0, 0, target=24, radius=10), OFF(3)))
FS['pluie'] = nS(FSC, 'pluie', 'req', 10, 36, "Pluie de pierres",
               "Canalisé : une pluie de pierres frappe la zone ciblée pendant 8 s : 8 fois 126 points de dégâts de Nature (au niveau 60) "
               "aux ennemis à 8 m, hébétés.", mpct=18, icon_sid=8056, school=3, dur=8000, rng=30, Targets=64,
               **merge(PER(1, 3, 1008, 8000, 1000, 36, 0.8, target=28, radius=8, effect=27),
                       AUR(2, 33, 0, -50, target=28, radius=8, effect=27), OFF(3)))
FS['chant'] = nS(FSC, 'chant', 'req', 5176, 44, "Chant du requiem",
               "Entonne le requiem : 1 050 à 1 190 points de dégâts de Nature (au niveau 60), et étourdit la cible pendant 2 s.",
               cast=6000, cd=30000, mpct=20, icon_sid=8105, school=3, dur=2000,
               **merge(DMG(1, 1050, 1190, 44, 1.2), AUR(2, 12, 0, 0, target=6), OFF(3)))
# Charnier (mana, sombredogue)
C_SOMBREDOGUE, C_CHAROGNARD = 990720, 990721
FS['invoc'] = nS(FSC, 'invoc', 'char', 697, 10, "Invocation du sombredogue", "Invoque votre sombredogue acolyte, qui combat à vos côtés.",
               cast=10000, mpct=30, icon_sid=691,
               **merge(nE(1, 56, 32, misc=C_SOMBREDOGUE), FIX(1, 0), OFF(2, 3)))
FS['drain'] = nS(FSC, 'drain', 'char', 15407, 12, "Drain de chair",
               "Canalisé : draine 400 points de vie à la cible en 5 s (au niveau 60). Votre sombredogue est soigné du double.",
               mpct=8, icon_sid=689, school=5, dur=5000, tooltip="Perd des points de vie.",
               **merge(PER(1, 3, 400, 5000, 1000, 12, 0.5), OFF(2, 3)))
FS['curee'] = nS(FSC, 'curee', 'char', 1243, 14, "Curée", "Votre sombredogue mord sa cible : 300 à 340 points de dégâts (au niveau 60).",
               cd=6000, mpct=4, icon_sid=16827, **merge(DUMMY(1, target=1), OFF(2, 3)))
FS['relever'] = nS(FSC, 'relever', 'char', 697, 16, "Relever l'acolyte", "Relève votre sombredogue tombé au combat.",
                 cast=6000, mpct=20, icon_sid=982, **merge(nE(1, 56, 32, misc=C_SOMBREDOGUE), FIX(1, 0), OFF(2, 3)))
FS['festin'] = nS(FSC, 'festin', 'char', 1243, 20, "Festin de cadavre",
                "Votre sombredogue dévore un cadavre à 10 m : il récupère 30 % de ses points de vie et sa vitesse d'attaque augmente de 20 % "
                "pendant 15 s.", cd=30000, mpct=4, icon_sid=20577, **merge(DUMMY(1, target=1), OFF(2, 3)))
FS['d_force'] = nS(FSC, 'd_force', 'char', 1243, 22, "Drain de force",
                 "Vole la force de la cible pendant 20 s : force et agilité réduites de 10 %, dégâts de votre sombredogue augmentés de 20 %.",
                 cast=3000, cd=20000, mpct=7, icon_sid=702, dur=20000, rng=30, tooltip="Force et agilité réduites de 10 %.",
                 **merge(AUR(1, 137, 0, -10, target=6), AUR(2, 137, 1, -10, target=6), OFF(3)))
FS['d_celerite'] = nS(FSC, 'd_celerite', 'char', 1243, 24, "Drain de célérité",
                    "Vole la célérité de la cible pendant 20 s : ralentie de 30 %, vitesse d'attaque de votre sombredogue augmentée de 20 %.",
                    cast=3000, cd=20000, mpct=7, icon_sid=1715, dur=20000, rng=30, tooltip="Vitesse de déplacement réduite de 30 %.",
                    **merge(AUR(1, 33, 0, -30, target=6), OFF(2, 3)))
FS['meute'] = nS(FSC, 'meute', 'char', 12740, 30, "Nuée de rats zombies",
               "Appelle 6 rats zombies qui combattent pendant 15 s. Leurs morsures ralentissent la cible de 10 %, cumulable.",
               cd=180000, mpct=12, icon_sid=5487, dur=15000, CastingTimeIndex=1, EffectMiscValue1=990721, EffectBasePoints1=5,
               EffectDieSides1=1, EffectRealPointsPerLevel1=0, EffectImplicitTargetA1=1, EffectRadiusIndex1=RADIUS[5])
FS['d_moelle'] = nS(FSC, 'd_moelle', 'char', 1243, 34, "Drain de moelle",
                  "Vole la moelle de la cible pendant 20 s : armure réduite de 15 %, armure de votre sombredogue augmentée de 30 %.",
                  cast=3000, cd=20000, mpct=7, icon_sid=8647, dur=20000, rng=30, tooltip="Armure réduite de 15 %.",
                  **merge(AUR(1, 101, 1, -15, target=6), OFF(2, 3)))
FS['partage'] = nS(FSC, 'partage', 'char', 1243, 40, "Partage des chairs",
                 "Pendant 10 s, 30 % des dégâts que vous subissez sont transférés à votre sombredogue.", cd=60000, mpct=5, icon_sid=19028,
                 dur=10000, tooltip="30 % des dégâts subis vont au sombredogue.", **merge(AUR(1, 4, 0, 1), OFF(2, 3)))
# Passeur (fantômes liés à un allié pendant 1 min)
def ame(key, lv, name, desc, tip, effects, icon_sid):
    return nS(FSC, key, 'pass', 1243, lv, name, desc + " Un seul fantôme par allié, 3 fantômes au maximum.", mpct=6, icon_sid=icon_sid,
             dur=60000, tooltip=tip, **effects)
FS['a_ardente'] = ame('a_ardente', 10, "Âme ardente", "Lie un fantôme ardent à un allié pendant 1 min : hâte augmentée de 10 %.",
                     "Hâte augmentée de 10 %.", merge(AUR(1, 138, 0, 10, target=21), AUR(2, 65, 0, 10, target=21), AUR(3, 140, 0, 10, target=21)), 18266)
FS['a_feroce'] = ame('a_feroce', 10, "Âme féroce", "Lie un fantôme féroce à un allié pendant 1 min : chances de coup critique augmentées de 5 %.",
                    "Coup critique +5 %.", merge(AUR(1, 52, 0, 5, target=21), AUR(2, 71, 127, 5, target=21), OFF(3)), 17877)
FS['a_bienv'] = ame('a_bienv', 12, "Âme bienveillante",
                   "Lie un fantôme bienveillant à un allié pendant 1 min : points de vie maximum augmentés de 10 %, et 1 % de sa vie rendu toutes les 2 s.",
                   "Vie augmentée, récupère des points de vie.", merge(AUR(1, 133, 0, 10, target=21), AUR(2, 20, 0, 1, target=21, amp=2000), OFF(3)), 20711)
FS['a_sereine'] = ame('a_sereine', 18, "Âme sereine", "Lie un fantôme serein à un allié pendant 1 min : 2 % de son mana rendu toutes les 5 s.",
                     "Récupère du mana.", merge(AUR(1, 21, 0, 2, target=21, amp=5000), OFF(2, 3)), 6346)
FS['a_gardienne'] = ame('a_gardienne', 26, "Âme gardienne", "Lie un fantôme gardien à un allié pendant 1 min : dégâts subis réduits de 10 %.",
                       "Dégâts subis réduits de 10 %.", merge(AUR(1, 87, 127, -10, target=21), OFF(2, 3)), 19752)
FS['a_vengeresse'] = ame('a_vengeresse', 32, "Âme vengeresse",
                        "Lie un fantôme vengeur à un allié pendant 1 min : il frappe la cible de l'allié pour 80 points de dégâts d'Ombre toutes les 2 s.",
                        "Un fantôme frappe vos ennemis.", merge(AUR(1, 23, 0, 0, target=21, amp=2000, trig=FS['vengeresse_d']), OFF(2, 3)), 18265)
FS['cortege'] = nS(FSC, 'cortege', 'pass', 1243, 38, "Cortège", "Pendant 15 s, vos fantômes actifs profitent à tout le groupe.",
                 cd=180000, mpct=10, icon_sid=19746, **merge(DUMMY(1, target=1), OFF(2, 3)))
FS['passage'] = nS(FSC, 'passage', 'pass', 1243, 44, "Passage", "L'allié devient intangible pendant 3 s : insensible aux dégâts physiques.",
                 cd=120000, mpct=6, icon_sid=1020, dur=3000, tooltip="Insensible aux dégâts physiques.", **merge(AUR(1, 39, 1, 0, target=21), OFF(2, 3)))
FS['liberation'] = nS(FSC, 'liberation', 'pass', 1243, 50, "Libération",
                    "Vos fantômes explosent : chacun soigne son allié de 15 % de ses points de vie, puis disparaît.",
                    cd=30000, mpct=8, icon_sid=18265, **merge(DUMMY(1, target=1), OFF(2, 3)))
F_AMES = ['a_ardente', 'a_feroce', 'a_bienv', 'a_sereine', 'a_gardienne', 'a_vengeresse']
NOTEACH.update([FS['invoc'], FS['a_ardente'], FS['a_feroce']])
# malédictions d'arme : une seule à la fois (deux avec Malédictions jumelles), gérées par le module

# ======================================================================== Fossoyeur : sorts des arbres (validés le 24/11)
REQ_KEYS = ['pierre', 'eclat', 'glas', 'stele', 'eboulement', 'onde', 'pluie', 'chant']
def PERX(n, aura, amp, target=6):
    """effet périodique dont la valeur par tick est donnée par le module (CastCustomSpell)"""
    return merge(nE(n, 6, target, aura=aura, amp=amp), FIX(n, 1))
FS['h_daze4'] = nH(FSH, 'h_daze4', 1715, "Poids de la terre", tooltip="Hébété : vitesse réduite de 50 %.", dur=4000, School=3, Mechanic=27,
                 **merge(AUR(1, 33, 0, -50, target=6), OFF(2, 3)))
FS['h_daze_f'] = nH(FSH, 'h_daze_f', 1715, "Faille", tooltip="Hébété : vitesse réduite de 50 %.", dur=2000, School=3, Mechanic=27,
                  **merge(AUR(1, 33, 0, -50, target=6), OFF(2, 3)))
FS['h_gravats'] = nH(FSH, 'h_gravats', 5176, "Gravats", tooltip="Dégâts de Nature toutes les 2 s.", dur=4000, School=3,
                   **merge(PERX(1, 3, 2000), OFF(2, 3)))
FS['h_terre'] = nH(FSH, 'h_terre', 5176, "Requiem", School=3, **merge(DMG(1, 1, 1, 0, 0.0), OFF(2, 3)))
FS['h_faille'] = nH(FSH, 'h_faille', 2120, "Faille", tooltip="Dégâts de Nature chaque seconde.", dur=8000, School=3, Targets=64, RangeIndex=RANGE[30],
                  **merge(PER(1, 3, 1120, 8000, 1000, 50, 0.4, target=28, radius=10, effect=27), OFF(2, 3)))
FS['h_energie'] = [nH(FSH, 'h_energie', 13750, "Énergie macabre", **merge(nE(1, 30, 1, misc=3), FIX(1, _r), OFF(2, 3))) for _r in (1, 2, 3)]
FS['h_hurlement'] = nH(FSH, 'h_hurlement', 5484, "Hurlement", tooltip="En fuite.", dur=3000, School=5, Mechanic=5,
                     **merge(AUR(1, 7, 0, 0, target=6), OFF(2, 3)))
FS['h_alpha_d'] = nH(FSH, 'h_alpha_d', 16827, "Molosse d'os", School=0, DmgClass=2, **merge(DMG(1, 1, 1, 0, 0.0), OFF(2, 3)))
FS['h_rat'] = nH(FSH, 'h_rat', 1715, "Morsure de rat zombie", tooltip="Vitesse de déplacement réduite de 10 % par morsure.", dur=6000,
               StackAmount=5, School=5, **merge(AUR(1, 33, 0, -10, target=6), OFF(2, 3)))
FS['pacte_pet2'] = nH(FSH, 'h_pacte_pet2', 1243, "Dressage du charnier", tooltip="Vitesse d'attaque et critique augmentés.", dur=-1,
                    **merge(AUR(1, 138, 0, 1), AUR(2, 52, 0, 1), OFF(3)))
FS['h_maitrise'] = nH(FSH, 'h_maitrise', 1243, "Maîtrise de la pelle", dur=-1, **merge(AUR(1, 52, 0, 1), OFF(2, 3)))
FS['h_bouclier_p'] = nH(FSH, 'h_bouclier_p', 17, "Bouclier partagé", tooltip="Absorbe des dégâts.", dur=30000, School=5,
                      **merge(AUR(1, 69, 127, 1), OFF(2, 3)))
FS['h_legion_d'] = nH(FSH, 'h_legion_d', 5176, "Légion des trépassés", School=5, **merge(DMG(1, 150, 150, 50, 0.1), OFF(2, 3)))
FS['h_legion_x'] = nH(FSH, 'h_legion_x', 5176, "Explosion du trépassé", School=5, **merge(DMG(1, 500, 500, 50, 0.2), OFF(2, 3)))
FS['h_ame_maudite'] = nH(FSH, 'h_ame_maudite', 589, "Âme maudite", tooltip="Dégâts d'Ombre toutes les 3 s.", dur=18000, School=5, StackAmount=10,
                       **merge(PER(1, 3, 852, 18000, 3000, 50, 1.0), OFF(2, 3)))
FS['h_passage'] = nH(FSH, 'h_passage', 2061, "Passage", School=5, **merge(HEAL(1, 1, 1, 0, 0), OFF(2, 3)))
# Profanateur
FS['fosse'] = nS(FSC, 'fosse', 'prof', 1714, 20, "Fosse commune",
                 "Pendant 15 s, chaque malédiction posée par votre arme se propage à un autre ennemi à 8 m.", cd=120000, icon_sid=603,
                 dur=15000, tooltip="Les malédictions se propagent.", PowerType=3, ManaCost=0, **merge(AUR(1, 4, 0, 1), OFF(2, 3)))
FS['danse'] = nS(FSC, 'danse', 'prof', 13750, 50, "Danse macabre",
                 "Pendant 20 s : énergie régénérée 50 % plus vite, dégâts augmentés de 20 %.", cd=300000, icon_sid=13750, dur=20000,
                 tooltip="Énergie +50 %, dégâts +20 %.", PowerType=3, ManaCost=0, **merge(AUR(1, 110, 3, 50), AUR(2, 79, 127, 20), OFF(3)))
# Requiem (70 % de base comme les autres sorts du Requiem)
FS['fissure'] = nS(FSC, 'fissure', 'req', 8042, 30, "Fissure",
                   "Ouvre une fissure devant vous sur 20 m : 280 à 315 points de dégâts de Nature (au niveau 60) et hébète les ennemis pendant 6 s.",
                   cd=15000, mpct=8, icon_sid=8046, school=3, dur=6000, Mechanic=27,
                   **merge(DMG(1, 280, 315, 30, 0.3, target=24, radius=20), AUR(2, 33, 0, -50, target=24, radius=20), OFF(3)))
FS['tombeau'] = nS(FSC, 'tombeau', 'req', 2120, 50, "Tombeau ouvert",
                   "Ouvre un tombeau à 30 m : 1 400 à 1 610 points de dégâts de Nature (au niveau 60) aux ennemis à 10 m, étourdis pendant 3 s. "
                   "Une faille reste ouverte 8 s : 140 points de dégâts de Nature par seconde, ennemis hébétés.",
                   cd=180000, mpct=16, icon_sid=8056, school=3, dur=3000, rng=30, Targets=64,
                   **merge(DMG(1, 1400, 1610, 50, 0.8, target=28, radius=10), AUR(2, 12, 0, 0, target=28, radius=10), OFF(3)))
REQ_KEYS += ['fissure', 'tombeau', 'h_faille']
# Charnier
FS['frenesie'] = nS(FSC, 'frenesie', 'char', 19574, 30, "Frénésie du dogue",
                    "Votre sombredogue entre en frénésie pendant 15 s : dégâts augmentés de 30 %, vitesse d'attaque augmentée de 20 %.",
                    cd=120000, mpct=5, icon_sid=19574, dur=15000, tooltip="Dégâts +30 %, vitesse d'attaque +20 %.", RangeIndex=RANGE[100],
                    **merge(AUR(1, 79, 127, 30, target=5), AUR(2, 138, 0, 20, target=5), OFF(3)))
FS['hurlement'] = nS(FSC, 'hurlement', 'char', 5484, 40, "Hurlement", "Votre sombredogue hurle : les ennemis à 10 m de lui fuient pendant 3 s.",
                     cd=60000, mpct=6, icon_sid=5484, **merge(DUMMY(1, target=1), OFF(2, 3)))
FS['alpha'] = nS(FSC, 'alpha', 'char', 19574, 50, "Alpha des morts",
                 "Pendant 20 s, votre sombredogue devient un Molosse d'os : dégâts augmentés de 50 %, chacun de ses coups touche tous les ennemis à 8 m.",
                 cd=300000, mpct=10, icon_sid=19574, dur=20000, tooltip="Molosse d'os : dégâts +50 %, coups de zone.", RangeIndex=RANGE[100],
                 **merge(AUR(1, 79, 127, 50, target=5), AUR(2, 61, 0, 30, target=5), OFF(3)))
# Passeur
FS['garde'] = nS(FSC, 'garde', 'pass', 6940, 30, "Garde du passeur", "Pendant 8 s, l'allié subit 30 % de dégâts en moins.",
                 cd=60000, mpct=5, icon_sid=6940, dur=8000, tooltip="Dégâts subis réduits de 30 %.", **merge(AUR(1, 87, 127, -30, target=21), OFF(2, 3)))
FS['legion'] = nS(FSC, 'legion', 'pass', 1243, 50, "Légion des trépassés",
                  "Pendant 20 s, vos fantômes gardent leur effet et frappent la cible de leur allié : 150 points de dégâts d'Ombre par seconde "
                  "(au niveau 60), chaque coup vous rend 1 % de mana. À la fin, chaque fantôme explose sur sa cible : 500 points de dégâts d'Ombre "
                  "aux ennemis à 8 m, et pose Âme maudite (850 points de dégâts d'Ombre en 18 s, cumulable).",
                  cd=300000, mpct=10, icon_sid=18540, dur=20000, tooltip="Les fantômes attaquent.", **merge(AUR(1, 4, 0, 1), OFF(2, 3)))
F_TALENT_SPELLS = ['fosse', 'danse', 'fissure', 'tombeau', 'frenesie', 'hurlement', 'alpha', 'garde', 'legion']
NOTEACH.update(FS[k] for k in F_TALENT_SPELLS)

# ======================================================================== Martyr (validé le 24/11) : énergie, sorts de sang (énergie + % des PV), Ferveur
# Coûts en PV, Ferveur (+20 % par charge consommée), effets qui grandissent avec les PV max : module (NouvellesClasses.cpp).
MAG = Gen(16, range(0, 64)); NV_GENS.append((MAG, 42000, 42499))
MAC = Ctx(MAG, 42000, {'bast': 914, 'saig': 915, 'offr': 916, 'hemo': 917}, 1, MART)
MAH = Ctx(MAG, 42300, {}, 1, MART)
MA = {}
MA_SANG = []             # (clé, % des PV, consomme la Ferveur)
def LEECH(n, v60, lv, coef, target=6, radius=None, tb=0):
    return merge(nE(n, 9, target, radius=radius, tb=tb, coef=coef), nV(n, v60, lv), {'EffectMultipleValue%d' % n: 1.0})
def sang(key, pct, conso=True):
    MA_SANG.append((key, pct, conso))
PASSIF = {'Attributes': 0x40 | 0x10000, 'DurationIndex': DUR[-1]}
# sorts cachés
MA['ferveur'] = nH(MAH, 'h_ferveur', 12292, "Ferveur", tooltip="Prochain sort de sang : +20 % d'effet par charge.", dur=30000, StackAmount=5,
                  **merge(AUR(1, 4, 0, 1), OFF(2, 3)))
MA['bonus_d'] = nH(MAH, 'h_bonus_d', 23881, "Ferveur", School=0, **merge(DMG(1, 1, 1, 0, 0.0), OFF(2, 3)))
MA['bonus_s'] = nH(MAH, 'h_bonus_s', 2061, "Sang", School=0, **merge(HEAL(1, 1, 1, 0, 0), OFF(2, 3)))
MA['leech_x'] = nH(MAH, 'h_leech_x', 6789, "Sang", School=5, **merge(nE(1, 9, 6), FIX(1, 1), {'EffectMultipleValue1': 1.0}, OFF(2, 3)))
MA['caillot_h'] = nH(MAH, 'h_caillot', 17, "Caillot", tooltip="Absorbe des dégâts.", dur=15000, **merge(AUR(1, 69, 127, 1), OFF(2, 3)))
MA['plaie_d'] = nH(MAH, 'h_plaie', 772, "Plaie sanglante", tooltip="Saigne.", dur=6000, School=0, Mechanic=15, **merge(PERX(1, 3, 2000), OFF(2, 3)))
MA['lames_d'] = nH(MAH, 'h_lames', 772, "Lames ébréchées", tooltip="Saigne.", dur=10000, School=0, Mechanic=15, StackAmount=5,
                  **merge(PER(1, 3, 40, 10000, 2000, 1, 0.0), OFF(2, 3)))
MA['riposte'] = [nH(MAH, 'h_riposte', 23922, "Riposte sanglante", tooltip="Prochain Coup de bouclier sanglant renforcé.", dur=10000, ProcCharges=1,
                    **merge(nE(1, 6, 1, aura=108, misc=0), FIX(1, 10 * _r), OFF(2, 3))) for _r in (1, 2, 3)]
MA['communion_d'] = nH(MAH, 'h_communion', 6789, "Communion", School=5, **merge(DMG(1, 150, 150, 20, 0.1), OFF(2, 3)))
MA['seigneur_st'] = nH(MAH, 'h_seigneur_st', 1784, "Seigneur du sang", tooltip="Camouflé.", dur=30000, Attributes=0, AttributesEx=0,
                      AuraInterruptFlags=0, **merge(AUR(1, 16, 0, 5), OFF(2, 3)))
MA['seigneur_a'] = nH(MAH, 'h_seigneur_a', 13218, "Sang vicié", tooltip="Soins reçus réduits de 25 %.", dur=10000, School=5,
                     **merge(AUR(1, 118, 0, -25, target=6), OFF(2, 3)))
MA['h_crit'] = nH(MAH, 'h_crit', 1243, "Seigneur du sang", dur=-1, **merge(AUR(1, 52, 0, 1), OFF(2, 3)))
MA['h_soif'] = nH(MAH, 'h_soif', 12292, "Soif de sang", tooltip="Dégâts augmentés.", dur=-1, **merge(AUR(1, 79, 127, 1), OFF(2, 3)))
MA['h_instinct'] = nH(MAH, 'h_instinct', 12975, "Instinct de survie", tooltip="Dégâts subis réduits.", dur=-1, **merge(AUR(1, 87, 127, -1), OFF(2, 3)))
MA['h_predateur'] = nH(MAH, 'h_predateur', 1243, "Prédateur", dur=-1, **merge(AUR(1, 79, 127, 1), OFF(2, 3)))
for _sid in MA['riposte']:
    TAL_AFFECT.append((_sid, 0, MAG.mask('bouclier_s')))
# commun
MA['frappe'] = nS(MAC, 'frappe', 'bast', 78, 1, "Frappe de sang", "Frappe avec l'arme : dégâts de l'arme +50 (au niveau 60).",
                  energy=40, icon_sid=12294, **merge(WEAP(1, 50, 1), OFF(2, 3)), **MELEE)
MA['serment'] = nS(MAC, 'serment', 'bast', 6673, 4, "Serment de sang", "Le groupe prête serment pendant 5 min : endurance augmentée de 5 %.",
                   energy=20, icon_sid=6673, dur=300000, tooltip="Endurance augmentée de 5 %.",
                   **merge(AUR(1, 137, 2, 5, target=20, radius=30), OFF(2, 3)))
MA['transfusion'] = nS(MAC, 'transfusion', 'hemo', 6789, 10, "Transfusion", "Draine 300 points de vie à la cible (au niveau 60).",
                       cd=12000, energy=30, icon_sid=7651, rng=30, school=5, **merge(LEECH(1, 300, 10, 0.3), OFF(2, 3)))
MA['charge'] = nS(MAC, 'charge', 'bast', 100, 20, "Charge sanglante", "Charge un ennemi entre 8 et 25 m et l'étourdit pendant 1 s.",
                  cd=15000, energy=15, icon_sid=100, **OFF(2))
MA['pacte'] = nS(MAC, 'pacte', 'saig', 12292, 30, "Pacte de sang", "Sort de sang (5 % de vos PV) : pendant 15 s, votre énergie se régénère 50 % plus vite.",
                 cd=180000, icon_sid=12292, dur=15000, tooltip="Énergie régénérée 50 % plus vite.", **merge(AUR(1, 110, 3, 50), OFF(2, 3)))
sang('pacte', 5)
MA['dernier'] = nS(MAC, 'dernier', 'offr', 12975, 40, "Dernier sacrifice",
                   "Passif : un coup qui devrait vous tuer vous laisse à 1 point de vie et soigne votre groupe de 15 % de ses points de vie. "
                   "Une fois toutes les 10 min.", icon_sid=20608, **merge(AUR(1, 4, 0, 1), OFF(2, 3), PASSIF))
# Bastion (tank)
MA['bouclier_s'] = nS(MAC, 'bouclier_s', 'bast', 23922, 1, "Coup de bouclier sanglant",
                      "Frappe avec l'arme : dégâts de l'arme +40 (au niveau 60), menace élevée.", energy=35, icon_sid=23922,
                      **merge(WEAP(1, 40, 1), merge(nE(2, 63, 6), nV(2, 150, 1)), OFF(3)), **MELEE)
MA['defi'] = nS(MAC, 'defi', 'bast', 355, 2, "Défi du sang", "Provoque la cible : elle vous attaque pendant 3 s.", cd=10000, energy=10, icon_sid=355)
MA['peau'] = nS(MAC, 'peau', 'bast', 71, 8, "Peau de sang", "Durcit votre sang pendant 30 min : armure augmentée de 15 %.", icon_sid=71,
                dur=1800000, tooltip="Armure augmentée.", **merge(AUR(1, 101, 1, 15), OFF(2, 3)))
MA['plaie'] = nS(MAC, 'plaie', 'bast', 6343, 12, "Plaie partagée",
                 "Ouvre vos plaies : 150 points de dégâts (au niveau 60) aux ennemis à 8 m, menace élevée. +20 % par charge de Ferveur, sans la consommer.",
                 cd=6000, energy=40, icon_sid=6343, school=0, DmgClass=1,
                 **merge(DMG(1, 150, 165, 12, 0.1, target=22, radius=8, tb=15), merge(nE(2, 63, 22, radius=8, tb=15), nV(2, 150, 12)), OFF(3)))
MA['caillot'] = nS(MAC, 'caillot', 'bast', 17, 18, "Caillot",
                   "Sort de sang (3 % de vos PV) : un caillot absorbe 10 % de vos points de vie maximum en dégâts pendant 15 s.",
                   cd=20000, energy=20, icon_sid=2565, dur=15000, tooltip="Absorbe des dégâts.", **merge(AUR(1, 69, 127, 1), OFF(2, 3)))
sang('caillot', 3)
MA['parade'] = nS(MAC, 'parade', 'bast', 20230, 26, "Parade sanglante", "Vos chances de parer augmentent de 30 % pendant 8 s.",
                  cd=30000, energy=25, icon_sid=20230, dur=8000, tooltip="Parade augmentée de 30 %.", **merge(AUR(1, 47, 0, 30), OFF(2, 3)))
MA['coagulation'] = nS(MAC, 'coagulation', 'bast', 871, 34, "Coagulation", "Sort de sang (5 % de vos PV) : dégâts subis réduits de 30 % pendant 10 s.",
                       cd=120000, energy=20, icon_sid=871, dur=10000, tooltip="Dégâts subis réduits.", **merge(AUR(1, 87, 127, -30), OFF(2, 3)))
sang('coagulation', 5)
MA['cri'] = nS(MAC, 'cri', 'bast', 1161, 42, "Cri du martyr", "Sort de sang (3 % de vos PV) : les ennemis à 10 m vous attaquent pendant 6 s.",
               cd=180000, energy=30, icon_sid=1161)
sang('cri', 3, False)
MA['mur'] = nS(MAC, 'mur', 'bast', 12975, 50, "Mur de chair",
               "Sort de sang (5 % de vos PV) : points de vie maximum augmentés de 30 % pendant 20 s, et vous récupérez 30 % de vos points de vie.",
               cd=300000, icon_sid=12975, dur=20000, tooltip="Points de vie maximum augmentés de 30 %.", **merge(AUR(1, 133, 0, 30), OFF(2, 3)))
sang('mur', 5)
# Saignée (DPS cac)
MA['entaille'] = nS(MAC, 'entaille', 'saig', 772, 1, "Entaille",
                    "Frappe avec l'arme : dégâts de l'arme +60, puis la cible saigne : 200 points de dégâts en 10 s (au niveau 60).",
                    energy=40, icon_sid=772, dur=10000, school=0, tooltip="Saigne.", Mechanic=15,
                    **merge(WEAP(1, 60, 1), PER(2, 3, 200, 10000, 2000, 1, 0.0), OFF(3)), **MELEE)
MA['soif'] = nS(MAC, 'soif', 'saig', 12292, 2, "Soif de sang",
                "Passif : vos dégâts augmentent de 1 % par tranche de 2 % de points de vie qui vous manquent (25 % au maximum).",
                icon_sid=12292, **merge(AUR(1, 4, 0, 1), OFF(2, 3), PASSIF))
MA['hachoir'] = nS(MAC, 'hachoir', 'saig', 12294, 6, "Hachoir",
                   "Sort de sang (2 % de vos PV) : dégâts de l'arme +80 (au niveau 60), +20 % par charge de Ferveur.",
                   cd=6000, energy=20, icon_sid=7384, **merge(WEAP(1, 80, 6), OFF(2, 3)), **MELEE)
sang('hachoir', 2)
MA['tourbillon_s'] = nS(MAC, 'tourbillon_s', 'saig', 1680, 12, "Tourbillon de sang", "Frappe les ennemis à 8 m : dégâts de l'arme +30 (au niveau 60).",
                        cd=10000, energy=50, icon_sid=1680, **merge(WEAP(1, 30, 12, target=22, radius=8, tb=15), OFF(2, 3)),
                        **merge(MELEE, {'RangeIndex': RANGE[0]}))
MA['frenesie_s'] = nS(MAC, 'frenesie_s', 'saig', 1719, 18, "Frénésie écarlate", "Sort de sang (5 % de vos PV) : hâte augmentée de 20 % pendant 15 s.",
                      cd=120000, icon_sid=1719, dur=15000, tooltip="Hâte augmentée de 20 %.", **merge(AUR(1, 138, 0, 20), OFF(2, 3)))
sang('frenesie_s', 5)
MA['execution'] = nS(MAC, 'execution', 'saig', 5308, 24, "Exécution", "Achève une cible à moins de 20 % de vie : 300 % des dégâts de l'arme.",
                     cd=6000, energy=30, icon_sid=5308, TargetAuraState=2, **merge(WPCT(1, 300), OFF(2, 3)), **MELEE)
MA['desespoir'] = nS(MAC, 'desespoir', 'saig', 1464, 30, "Coup du désespoir",
                     "Dégâts de l'arme +100 (au niveau 60), doublés si vous avez moins de 35 % de vos points de vie.",
                     cd=10000, energy=35, icon_sid=1464, **merge(WEAP(1, 100, 30), OFF(2, 3)), **MELEE)
MA['hemorragie'] = nS(MAC, 'hemorragie', 'saig', 772, 38, "Hémorragie",
                      "Sort de sang (3 % de vos PV) : la cible saigne, 900 points de dégâts en 15 s (au niveau 60), +20 % par charge de Ferveur.",
                      cd=10000, energy=20, icon_sid=16511, dur=15000, school=0, tooltip="Saigne.", Mechanic=15,
                      **merge(PER(1, 3, 900, 15000, 3000, 38, 0.0), OFF(2, 3)), **MELEE)
sang('hemorragie', 3)
MA['festin_l'] = nS(MAC, 'festin_l', 'saig', 23881, 46, "Festin de lames", "Vos 3 prochains coups vous rendent 30 % de leurs dégâts en points de vie.",
                    cd=30000, energy=25, icon_sid=23881, dur=20000, tooltip="Vos coups vous soignent.", **merge(AUR(1, 4, 0, 1), OFF(2, 3)))
# Offrande (soin)
MA['don_s'] = nS(MAC, 'don_s', 'offr', 2050, 1, "Don de sang", "Rend 600 à 700 points de vie (au niveau 60).", cast=1500, energy=40,
                 icon_sid=2050, rng=40, **merge(HEAL(1, 600, 700, 1, 0.43), OFF(2, 3)))
MA['transfu_v'] = nS(MAC, 'transfu_v', 'offr', 139, 2, "Transfusion de vie", "Rend 900 points de vie en 12 s (au niveau 60).", energy=30,
                     icon_sid=139, dur=12000, rng=40, tooltip="Récupère des points de vie.", **merge(PER(1, 8, 900, 12000, 3000, 2, 0.5, target=21), OFF(2, 3)))
MA['partage_s'] = nS(MAC, 'partage_s', 'offr', 1064, 8, "Sang partagé", "Soin qui rebondit sur 3 alliés : 500, 375 puis 280 points de vie (au niveau 60).",
                     cast=2000, energy=50, icon_sid=1064, rng=40, DmgMultiplier1=0.75, **merge(HEAL(1, 500, 550, 8, 0.4, chain=3), OFF(2, 3)))
MA['sacrifice'] = nS(MAC, 'sacrifice', 'offr', 6940, 14, "Sacrifice", "Pendant 10 s, 50 % des dégâts subis par l'allié sont transférés sur vous.",
                     cd=60000, energy=20, icon_sid=6940, dur=10000, rng=40, tooltip="50 % des dégâts subis vont au Martyr.",
                     **merge(AUR(1, 4, 0, 1, target=21), OFF(2, 3)))
MA['souffle'] = nS(MAC, 'souffle', 'offr', 20770, 16, "Dernier souffle", "Ramène un allié mort à la vie. Hors combat.", cast=4000, icon_sid=2006)
MA['communion'] = nS(MAC, 'communion', 'offr', 15237, 20, "Communion",
                     "Draine 150 points de vie (au niveau 60) à chaque ennemi à 10 m et répartit le total entre les membres de votre groupe.",
                     cd=15000, energy=40, icon_sid=15237, **merge(DUMMY(1, target=1), OFF(2, 3)))
MA['fontaine'] = nS(MAC, 'fontaine', 'offr', 724, 28, "Fontaine de sang",
                    "Sort de sang (4 % de vos PV) : une fontaine jaillit à vos pieds pendant 10 s et rend 60 points de vie (au niveau 60) "
                    "par seconde aux alliés à 20 m, +20 % par charge de Ferveur.", cd=30000, energy=30, icon_sid=724, **merge(DUMMY(1, target=1), OFF(2, 3)))
sang('fontaine', 4)
MA['grand_s'] = nS(MAC, 'grand_s', 'offr', 2060, 36, "Grand sacrifice",
                   "Sort de sang (6 % de vos PV) : rend 2 000 à 2 300 points de vie (au niveau 60), +20 % par charge de Ferveur.",
                   cd=10000, cast=2500, energy=30, icon_sid=2060, rng=40, **merge(HEAL(1, 2000, 2300, 36, 0.86), OFF(2, 3)))
sang('grand_s', 6)
MA['beni'] = nS(MAC, 'beni', 'offr', 20217, 44, "Sang béni", "Bénit un allié pendant 5 min : chaque soin qu'il reçoit vous soigne de 20 % de sa valeur.",
                energy=20, icon_sid=20217, dur=300000, rng=40, tooltip="Les soins reçus soignent aussi le Martyr.",
                **merge(AUR(1, 4, 0, 1, target=21), OFF(2, 3)))
# Hémophage (DPS PvP, drain de vie)
MA['morsure'] = nS(MAC, 'morsure', 'hemo', 6789, 1, "Morsure", "Draine 200 points de vie à la cible (au niveau 60).", energy=40, icon_sid=17877,
                   rng=20, school=5, **merge(LEECH(1, 200, 1, 0.43), OFF(2, 3)))
MA['sangsue'] = nS(MAC, 'sangsue', 'hemo', 172, 2, "Sangsue", "Draine 600 points de vie en 15 s (au niveau 60).", energy=30, icon_sid=18265,
                   dur=15000, rng=30, school=5, tooltip="Perd des points de vie.",
                   **merge(PER(1, 53, 600, 15000, 3000, 2, 0.8), {'EffectMultipleValue1': 1.0}, OFF(2, 3)))
MA['siphon'] = nS(MAC, 'siphon', 'hemo', 689, 8, "Siphon", "Canalisé : draine 120 points de vie (au niveau 60) chaque seconde pendant 5 s.",
                  energy=50, icon_sid=689, dur=5000, rng=20, school=5, tooltip="Perd des points de vie.",
                  **merge(PER(1, 53, 600, 5000, 1000, 8, 0.6), {'EffectMultipleValue1': 1.0}, OFF(2, 3)))
MA['horreur'] = nS(MAC, 'horreur', 'hemo', 6789, 12, "Horreur sanglante", "La cible est horrifiée pendant 3 s.", cd=45000, energy=25,
                   icon_sid=6789, dur=3000, rng=20, school=5, Mechanic=24, tooltip="Horrifié.", **merge(AUR(1, 7, 0, 0, target=6), OFF(2, 3)))
MA['marque'] = nS(MAC, 'marque', 'hemo', 1130, 18, "Marque du sang",
                  "Sort de sang (3 % de vos PV) : pendant 15 s, 20 % des dégâts subis par la cible vous soignent, +20 % par charge de Ferveur.",
                  cd=30000, energy=20, icon_sid=1130, dur=15000, rng=30, tooltip="Marquée par le sang.", **merge(AUR(1, 4, 0, 1, target=6), OFF(2, 3)))
sang('marque', 3)
MA['fige'] = nS(MAC, 'fige', 'hemo', 12323, 24, "Sang figé", "Fige le sang de la cible : vitesse réduite de 50 % pendant 8 s.", energy=20,
                icon_sid=12323, dur=8000, rng=20, school=5, Mechanic=11, tooltip="Vitesse réduite.", **merge(AUR(1, 33, 0, -50, target=6), OFF(2, 3)))
MA['purge'] = nS(MAC, 'purge', 'hemo', 370, 30, "Purge de sang", "Retire 2 effets magiques de la cible.", cd=10000, energy=30, icon_sid=370, rng=30,
                 **merge(merge(nE(1, 38, 6, misc=1), FIX(1, 2)), OFF(2, 3)))
MA['anemie'] = nS(MAC, 'anemie', 'hemo', 172, 38, "Anémie", "Sort de sang (3 % de vos PV) : soins reçus par la cible réduits de 50 % pendant 10 s.",
                  cd=15000, energy=20, icon_sid=13218, dur=10000, rng=30, school=5, tooltip="Soins reçus réduits.",
                  **merge(AUR(1, 118, 0, -50, target=6), OFF(2, 3)))
sang('anemie', 3)
MA['festin_s'] = nS(MAC, 'festin_s', 'hemo', 8122, 46, "Festin sanglant",
                    "Sort de sang (5 % de vos PV) : draine 300 points de vie (au niveau 60) à chaque ennemi à 10 m, +20 % par charge de Ferveur.",
                    cd=30000, energy=30, icon_sid=7651, school=5, **merge(LEECH(1, 300, 46, 0.2, target=22, radius=10, tb=15), OFF(2, 3)))
sang('festin_s', 5)
# sorts de talent
MA['rempart'] = nS(MAC, 'rempart', 'bast', 2687, 30, "Rempart vivant", "Pendant 15 s, chaque coup reçu vous rend 5 points d'énergie.",
                   cd=60000, icon_sid=2687, dur=15000, tooltip="Les coups reçus rendent de l'énergie.", **merge(AUR(1, 4, 0, 1), OFF(2, 3)))
MA['forteresse'] = nS(MAC, 'forteresse', 'bast', 642, 50, "Forteresse de sang",
                      "Pendant 20 s : points de vie maximum +20 %, dégâts subis -20 %, soins reçus +20 %, chaque coup reçu donne 1 Ferveur, "
                      "et vos sorts de sang ne coûtent pas de points de vie.", cd=300000, icon_sid=642, dur=20000, tooltip="Forteresse de sang.",
                      **merge(AUR(1, 133, 0, 20), AUR(2, 87, 127, -20), AUR(3, 118, 0, 20)))
MA['fureur'] = nS(MAC, 'fureur', 'saig', 18499, 30, "Fureur du sang", "Sort de sang (3 % de vos PV) : vos 3 prochains coups sont critiques.",
                  cd=60000, icon_sid=18499, dur=20000, tooltip="Prochains coups critiques.", StackAmount=3, **merge(AUR(1, 4, 0, 1), OFF(2, 3)))
sang('fureur', 3, False)
MA['caille'] = nS(MAC, 'caille', 'saig', 772, 50, "Sang caillé",
                  "Sort de sang (4 % de vos PV) : 1 700 points de dégâts en 20 s (au niveau 60), +20 % par charge de Ferveur, et armure de la cible "
                  "réduite de 10 %.", cd=60000, energy=30, icon_sid=13218, dur=20000, school=0, Mechanic=15, tooltip="Saigne, armure réduite.",
                  **merge(PER(1, 3, 1700, 20000, 2000, 50, 0.0), AUR(2, 101, 1, -10, target=6), OFF(3)), **MELEE)
sang('caille', 4)
MA['don_u'] = nS(MAC, 'don_u', 'offr', 633, 30, "Don ultime", "Sort de sang (8 % de vos PV) : rend aussitôt 30 % de ses points de vie maximum à l'allié.",
                 cd=120000, icon_sid=633, rng=40, **merge(DUMMY(1, target=21), OFF(2, 3)))
sang('don_u', 8)
MA['saint'] = nS(MAC, 'saint', 'offr', 20711, 50, "Saint martyr",
                 "Pendant 20 s, chacun de vos soins soigne aussi tout le groupe de 20 % de sa valeur, et vos sorts de sang ne coûtent pas de points de vie.",
                 cd=300000, icon_sid=20711, dur=20000, tooltip="Saint martyr.", **merge(AUR(1, 4, 0, 1), OFF(2, 3)))
MA['etreinte'] = nS(MAC, 'etreinte', 'hemo', 339, 30, "Étreinte du sang",
                    "Immobilise la cible pendant 3 s et lui draine 400 points de vie (au niveau 60).", cd=30000, energy=20, icon_sid=339, dur=3000,
                    rng=20, school=5, Mechanic=7, tooltip="Immobilisé.", **merge(LEECH(1, 400, 30, 0.43), AUR(2, 26, 0, 0, target=6), OFF(3)))
MA['seigneur'] = nS(MAC, 'seigneur', 'hemo', 1856, 50, "Seigneur du sang",
                    "Pendant 30 s : camouflé sans interruption, vitesse 130 %, critique +10 %, drains +50 %, et vos drains réduisent de 25 % "
                    "les soins reçus par la cible.", cd=300000, icon_sid=1856, dur=30000, tooltip="Seigneur du sang.",
                    **merge(AUR(1, 129, 0, 30), AUR(2, 52, 0, 10), OFF(3)))
M_TALENT_SPELLS = ['rempart', 'forteresse', 'fureur', 'caille', 'don_u', 'saint', 'etreinte', 'seigneur']
NOTEACH.update(MA[k] for k in M_TALENT_SPELLS)
DRAINS_M = ['transfusion', 'morsure', 'sangsue', 'siphon', 'festin_s', 'etreinte']
HEALS_M = ['don_s', 'transfu_v', 'partage_s', 'grand_s']

# ======================================================================== talents
T5G = Gen(0, [])
TALG_PREV, TAL_ID_PREV = TALG, TAL_ID
TALG, TAL_ID = T5G, [44000]
ALL_HEAL = ['toucher', 'vie', 'raccom', 'navette', 'metier', 'grande', 'ressoudure', 'toile_p']
FIL_SPELLS = ['trait', 'trancher', 'epines', 'laceration', 'fils_t', 'toile', 'pelote', 'tempete', 'garrot']
MOIRE = ['fuseau', 'fil_noir', 'funebre', 'contagion']
def m2(typ, keys, per):
    return lambda r: [('mod', typ, True, keys, per * r)]
def flat(typ, keys, per):
    return lambda r: [('mod', typ, False, keys, per * r)]
tree(TWG, 414, "Trame", CBIT[TISS], 0, "PriestHoly", 2050, [
    (1, "Doigts agiles", 5, 2050, ('fx', flat(10, ['toucher'], -100)), lambda r: "Réduit le temps d'incantation de Toucher vital de %.1f s." % (0.1 * r)),
    (1, "Fil subtil", 5, 6346, ('fx', m2(2, ALL_HEAL, -4)), lambda r: "Réduit de %d %% la menace générée par vos soins." % (4 * r)),
    (2, "Fil de vie amélioré", 3, 139, ('fx', lambda r: [('mod', 22, True, ['vie'], 5 * r), ('mod', 0, True, ['vie'], 5 * r)]),
     lambda r: "Augmente les soins de Fil de vie de %d %%." % (5 * r)),
    (2, "Concentration", 5, 14751, ('fx', m2(9, ALL_HEAL, 14)), lambda r: "Réduit de %d %% le recul de vos soins quand vous subissez des dégâts." % (14 * r)),
    (2, "Trame serrée", 2, 7843, D, lambda r: "Chaque Fil sur un allié augmente ses soins reçus de %d %% de plus." % r),
    (3, "Reflet", 3, 14751, ('fx', aura(134, 0, 5)), lambda r: "%d %% de votre régénération de mana continue pendant les incantations." % (5 * r)),
    (3, "Navette améliorée", 3, 1064, ('fx', m2(0, ['navette'], 5)), lambda r: "Augmente les soins de Navette de %d %%." % (5 * r)),
    (3, "Raccommodage rapide", 2, 2061, ('fx', flat(11, ['raccom'], -1500)), lambda r: "Réduit la recharge de Raccommodage de %.1f s." % (1.5 * r)),
    (4, "Fil conducteur", 1, 6077, ('spell', TW['conducteur']),
     "Pendant 20 s, la cible reçoit 20 % de tous les soins faits sur les autres membres du groupe. Recharge 2 min."),
    (4, "Maîtrise des fils", 5, 15359, ('fx', flat(7, ALL_HEAL, 1)), lambda r: "Augmente de %d %% les chances de coup critique de vos soins." % r),
    (4, "Métier renforcé", 1, 740, ('fx', lambda r: [('mod', 22, True, ['metier'], 20), ('mod', 1, False, ['metier'], 4000)]),
     "Augmente les soins de Métier à tisser de 20 % et sa durée de 4 s."),
    (5, "Recousu", 1, 8936, ('spell', TW['recousu']), "Consomme le Fil de vie de la cible et la soigne aussitôt de 12 s de ce soin. Recharge 15 s.", "Fil de vie amélioré"),
    (5, "Fil d'urgence", 3, 2050, ('fx', flat(7, ['toucher'], 10)), lambda r: "Augmente de %d %% les chances de coup critique de Toucher vital." % (10 * r)),
    (5, "Trame de groupe", 2, 596, ('fx', m2(22, ['ressoudure'], 15)), lambda r: "Augmente les soins de Ressoudure de %d %%." % (15 * r)),
    (6, "Don de la trame", 5, 20711, ('fx', aura(136, 127, 2)), lambda r: "Augmente vos soins de %d %%." % (2 * r)),
    (6, "Grande trame rapide", 2, 2060, ('fx', flat(10, ['grande'], -250)), lambda r: "Réduit le temps d'incantation de Grande trame de %.2f s." % (0.25 * r)),
    (7, "Tapisserie de vie", 1, 724, ('spell', TW['tapisserie']), "Pendant 20 s : chaque soin pose 1 Fil, soins +30 %, coût -50 %. Recharge 5 min."),
    (7, "Tapisserie prolongée", 2, 724, ('fx', flat(1, ['tapisserie'], 2500)), lambda r: "Augmente la durée de Tapisserie de vie de %.1f s." % (2.5 * r), "Tapisserie de vie"),
])
tree(TWG, 415, "Lien", CBIT[TISS], 1, "PriestDiscipline", 17, [
    (1, "Toile renforcée", 5, 17, ('fx', m2(8, ['toile_p'], 5)), lambda r: "Augmente l'absorption de Toile protectrice de %d %%." % (5 * r)),
    (1, "Esprit lucide", 5, 14751, ('fx', aura(132, 0, 2)), lambda r: "Augmente votre mana maximum de %d %%." % (2 * r)),
    (2, "Lien de force amélioré", 3, 6346, ('fx', lambda r: [('mod', 8, False, ['lien_f'], r)]),
     lambda r: "Lien de force augmente les dégâts et la hâte de %d %% de plus." % r),
    (2, "Tissage rapide amélioré", 2, 12042, ('fx', flat(11, ['tissage'], -15000)), lambda r: "Réduit la recharge de Tissage rapide de %d s." % (15 * r)),
    (2, "Inébranlable", 5, 14751, ('fx', lambda r: [('aura', 117, 12, 3 * r), ('aura', 117, 5, 3 * r)]),
     lambda r: "Augmente de %d %% vos chances de résister aux étourdissements et à la peur." % (3 * r)),
    (3, "Cocon amélioré", 2, 1022, ('fx', flat(8, ['cocon'], -5)), lambda r: "Cocon réduit les dégâts de %d %% de plus." % (5 * r)),
    (3, "Don renforcé", 3, 29166, D, lambda r: "Don de trame rend %d %% de mana en plus." % (3 * r)),
    (3, "Infusion de trame", 1, 10060, ('spell', TW['infusion']), "Pendant 15 s, la cible inflige 20 % de dégâts et de soins en plus et ses sorts coûtent 20 % de moins. Recharge 3 min."),
    (4, "Liens partagés améliorés", 2, 19752, ('fx', flat(1, ['partages'], 2500)), lambda r: "Augmente la durée de Liens partagés de %.1f s." % (2.5 * r)),
    (4, "Méditation", 3, 14751, ('fx', aura(134, 0, 5)), lambda r: "%d %% de votre régénération de mana continue pendant les incantations." % (5 * r)),
    (4, "Vigilance", 5, 17, D, lambda r: "Les alliés sous Toile protectrice subissent %d %% de dégâts en moins." % r),
    (5, "Double lien", 1, 6346, D, "Lien de force peut lier 2 alliés en même temps."),
    (5, "Fil réparateur", 3, 139, D, lambda r: "Augmente de %d %% le soin de fin de Toile protectrice." % (10 * r)),
    (5, "Destin tissé", 2, 20711, ('fx', flat(11, ['destin'], -120000)), lambda r: "Réduit la recharge de Fil du destin de %d min." % (2 * r)),
    (6, "Aura de trame", 1, 19746, ('spell', TW['aura']), "Aura : les membres du groupe à 30 m infligent 3 % de dégâts en plus et en subissent 3 % de moins."),
    (6, "Fil d'acier", 5, 1022, D, lambda r: "Toile protectrice et Cocon augmentent l'armure de la cible de %d %%." % (4 * r)),
    (7, "Grand tissage", 1, 19752, ('spell', TW['grand_t']), "Pendant 15 s, le groupe inflige 15 % de dégâts en plus, gagne 15 % de hâte et subit 15 % de dégâts en moins. Recharge 5 min."),
    (7, "Grand tissage prolongé", 2, 19752, ('fx', flat(1, ['grand_t'], 2500)), lambda r: "Augmente la durée de Grand tissage de %.1f s." % (2.5 * r), "Grand tissage"),
])
tree(TWG, 416, "Fil tranchant", CBIT[TISS], 2, "PriestShadow", 5176, [
    (1, "Doigts vifs", 5, 5176, ('fx', flat(10, ['trait'], -100)), lambda r: "Réduit le temps d'incantation de Trait de fil de %.1f s." % (0.1 * r)),
    (1, "Fil acéré", 5, 8921, ('fx', flat(7, FIL_SPELLS, 1)), lambda r: "Augmente de %d %% les chances de coup critique de vos sorts de Fil tranchant." % r),
    (2, "Fil d'épines amélioré", 3, 467, ('fx', m2(22, ['epines'], 5)), lambda r: "Augmente les dégâts de Fil d'épines de %d %%." % (5 * r)),
    (2, "Bobine", 5, 2912, D, lambda r: "Trait de fil et Pelote ont %d %% de chances de poser 2 Fils." % (4 * r)),
    (2, "Trancher amélioré", 2, 8921, ('fx', flat(11, ['trancher'], -1000)), lambda r: "Réduit la recharge de Trancher les fils de %d s." % r),
    (3, "Lacération profonde", 3, 8921, ('fx', m2(22, ['laceration'], 15)), lambda r: "Augmente les dégâts du saignement de Lacération de %d %%." % (15 * r)),
    (3, "Toile collante", 2, 8921, ('fx', flat(12, ['toile'], -10)), lambda r: "Toile ralentit de %d %% de plus." % (10 * r)),
    (3, "Bâillon de fil", 1, 15487, ('spell', TW['baillon']), "Interrompt le sort de la cible et la réduit au silence pendant 3 s. Recharge 45 s."),
    (4, "Tension", 5, 16914, D, lambda r: "Augmente de %d %% vos dégâts contre une cible portant au moins 3 Fils." % (2 * r)),
    (4, "Mana filé", 3, 14751, D, lambda r: "Vos sorts critiques vous rendent %d %% de leur coût en mana." % (10 * r)),
    (4, "Fils tranchants améliorés", 2, 15407, ('fx', lambda r: [('mod', 22, True, ['fils_t'], 25 * r)]),
     lambda r: "Augmente les dégâts de Fils tranchants de %d %% (un coup de plus par rang)." % (25 * r)),
    (5, "Garrot", 1, 6789, ('spell', TW['garrot']), "900 points de dégâts de Nature en 12 s (au niveau 60), et pose 1 Fil toutes les 4 s."),
    (5, "Pelote rapide", 2, 2912, ('fx', flat(10, ['pelote'], -250)), lambda r: "Réduit le temps d'incantation de Pelote de %.2f s." % (0.25 * r)),
    (5, "Coupe nette", 2, 8921, ('fx', flat(7, ['trancher'], 15)), lambda r: "Augmente de %d %% les chances de coup critique de Trancher les fils." % (15 * r)),
    (6, "Fil d'argent", 5, 16914, ('fx', aura(79, 127, 2)), lambda r: "Augmente vos dégâts de %d %%." % (2 * r)),
    (6, "Tempête améliorée", 2, 16914, ('fx', flat(11, ['tempete'], -2500)), lambda r: "Réduit la recharge de Tempête de fils de %.1f s." % (2.5 * r)),
    (7, "Lame de trame", 1, 16914, ('spell', TW['lame']), "Pendant 20 s : chaque sort pose 2 Fils, Trancher les fils sans recharge, dégâts +15 %. Recharge 5 min."),
    (7, "Lame de trame prolongée", 2, 16914, ('fx', flat(1, ['lame'], 2500)), lambda r: "Augmente la durée de Lame de trame de %.1f s." % (2.5 * r), "Lame de trame"),
])
tree(TWG, 417, "Moire", CBIT[TISS], 3, "RogueAssassination", 8820, [
    (1, "Fuseau affûté", 5, 8820, ('fx', aura(52, 0, 1)), lambda r: "Augmente de %d %% vos chances de coup critique au corps à corps." % r),
    (1, "Fil empoisonné", 5, 5374, D, lambda r: "Augmente de %d %% les dégâts des Fils mortels." % (3 * r)),
    (2, "Linceul épais", 3, 17, ('fx', m2(8, ['linceul'], 10)), lambda r: "Augmente l'absorption de Linceul de %d %%." % (10 * r)),
    (2, "Double maille", 5, 8820, D, lambda r: "Coup de fuseau a %d %% de chances de poser 2 Fils mortels." % (4 * r)),
    (2, "Nœud rapide", 2, 11426, ('fx', flat(11, ['noeud'], -2000)), lambda r: "Réduit la recharge de Serrer le nœud de %d s." % (2 * r)),
    (3, "Pas spectral", 2, 1784, ('fx', aura(49, 0, 2)), lambda r: "Augmente vos chances d'esquiver de %d %%." % (2 * r)),
    (3, "Fil tendu amélioré", 2, 100, ('fx', flat(11, ['fil_tendu'], -5000)), lambda r: "Réduit la recharge de Fil tendu de %d s." % (5 * r)),
    (3, "Bouche cousue", 1, 1766, ('spell', TW['bouche']), "Interrompt le sort de la cible et la réduit au silence pendant 2 s. Recharge 20 s."),
    (4, "Agonie", 5, 18265, D, lambda r: "Augmente de %d %% les dégâts de vos coups contre une cible portant au moins 3 Fils mortels." % (2 * r)),
    (4, "Toile funèbre rapide", 3, 13018, ('fx', flat(11, ['funebre'], -2000)), lambda r: "Réduit la recharge de Toile funèbre de %d s." % (2 * r)),
    (4, "Fil vampirique", 2, 18265, D, lambda r: "Les Fils mortels vous soignent de %d %% de leurs dégâts." % (10 * r)),
    (5, "Refus du trépas", 1, 20711, D, "Un coup qui devrait vous tuer vous laisse à 1 point de vie, puis vos dégâts subis sont réduits de 80 % pendant 3 s. Une fois toutes les 5 min."),
    (5, "Nœud coulant amélioré", 2, 853, ('fx', flat(1, ['noeud_c'], 500)), lambda r: "Augmente la durée de Nœud coulant de %.1f s." % (0.5 * r)),
    (5, "Récolte abondante", 3, 18265, D, lambda r: "Récolte rend %d %% de vie de plus par Fil mortel." % r),
    (6, "Ombre de la Moire", 5, 18266, ('fx', aura(79, 32, 2)), lambda r: "Augmente vos dégâts d'Ombre de %d %%." % (2 * r)),
    (6, "Atropos implacable", 2, 17877, D, lambda r: "Fil d'Atropos fonctionne sur une cible à moins de %d %% de sa vie." % (25 + 5 * r)),
    (7, "Dernière maille", 1, 8820, ('spell', TW['derniere']), "Pendant 20 s : chaque coup pose 2 Fils mortels, cumulables jusqu'à 10, et 20 % plus puissants. Recharge 5 min."),
    (7, "Dernière maille prolongée", 2, 8820, ('fx', flat(1, ['derniere'], 2500)), lambda r: "Augmente la durée de Dernière maille de %.1f s." % (2.5 * r), "Dernière maille"),
])
# Fossoyeur : arbres validés le 24/11 (le premier talent de Requiem, Charnier et Passeur est le pacte qui verrouille la spé)
TID = {}                 # (onglet, talent) -> sorts des rangs, pour le module
def tree5(gen, tab_id, name, classmask, order, bg, icon_sid, talents):
    n0 = len(TALENT_ROWS)
    tree(gen, tab_id, name, classmask, order, bg, icon_sid, talents)
    for t, row in zip(talents, TALENT_ROWS[n0:]):
        TID[(tab_id, t[1])] = [v for v in row[4:13] if v]
POLE = 1 << 6                                                    # arme d'hast
DEUXM = (1 << 1) | (1 << 5) | (1 << 6) | (1 << 8) | (1 << 10)    # haches, masses, armes d'hast, épées 2M, bâtons
MALS = ['m_pourriture', 'm_entrave', 'm_epuise']
tree5(FSG, 418, "Profanateur", CBIT[FOSS], 0, "RogueCombat", 1752, [
    (1, "Maîtrise de la pelle", 5, 12700, ('fx', lambda r: [('aura', 52, 0, r), ('sets', {'EquippedItemClass': 2, 'EquippedItemSubClassMask': POLE})]),
     lambda r: "Augmente de %d %% vos chances de coup critique avec une arme d'hast, et de %d %% avec une autre arme à deux mains." % (r, r // 2)),
    (1, "Pelleteur", 5, 13712, ('fx', aura(49, 0, 1)), lambda r: "Augmente vos chances d'esquiver de %d %%." % r),
    (2, "Coup de pelle amélioré", 3, 1752, ('fx', flat(14, ['pelle'], -3)), lambda r: "Réduit le coût en énergie de Coup de pelle de %d." % (3 * r)),
    (2, "Pourriture tenace", 3, 172, ('fx', flat(18, MALS, 3)), lambda r: "Augmente de %d %% les chances de vos malédictions d'arme." % (3 * r)),
    (2, "Poigne du fossoyeur", 2, 1766, ('fx', flat(1, ['manche'], 500)), lambda r: "Augmente la durée du silence de Coup de manche de %.1f s." % (0.5 * r)),
    (3, "Mise en bière améliorée", 3, 2098, ('fx', m2(0, ['biere'], 5)), lambda r: "Augmente les dégâts de Mise en bière de %d %%." % (5 * r)),
    (3, "Terre ancienne", 5, 12163, ('fx', lambda r: [('aura', 79, 1, r), ('sets', {'EquippedItemClass': 2, 'EquippedItemSubClassMask': DEUXM})]),
     lambda r: "Augmente de %d %% les dégâts infligés avec une arme à deux mains." % r),
    (3, "Remblai", 2, 1784, ('fx', m2(12, ['voile'], -50)), lambda r: "Réduit de %d %% le ralentissement de Voile de tombe." % (15 * r)),
    (4, "Fosse commune", 1, 603, ('spell', FS['fosse']), "Pendant 15 s, chaque malédiction posée par votre arme se propage à un autre ennemi à 8 m. Recharge 2 min."),
    (4, "Pelletée funèbre", 5, 1752, D, lambda r: "Vos coups qui rapportent des points de combo ont %d %% de chances d'en rapporter un de plus." % (4 * r)),
    (4, "Sortie de terre améliorée", 2, 1833, ('fx', flat(1, ['sortie'], 500)), lambda r: "Augmente l'étourdissement de Sortie de terre de %.1f s." % (0.5 * r)),
    (5, "Profanation améliorée", 3, 8678, D, lambda r: "Profanation inflige %d %% de dégâts en plus par malédiction (au lieu de 30 %%)." % (30 + 5 * r)),
    (5, "Tourbillon amélioré", 2, 1680, ('fx', flat(11, ['tourbillon'], -2000)), lambda r: "Réduit la recharge de Tourbillon de pelle de %d s." % (2 * r)),
    (5, "Fièvre des tombes", 3, 13750, ('fx', aura(138, 0, 2)), lambda r: "Augmente votre vitesse d'attaque de %d %%." % (2 * r)),
    (6, "Énergie macabre", 3, 13750, ('fx', lambda r: [('proc', FS['h_energie'][r - 1], 100, PROC_MELEE, 0, 0, 2)]),
     lambda r: "Chacun de vos coups critiques vous rend %d point%s d'énergie." % (r, 's' if r > 1 else '')),
    (6, "Malédictions jumelles", 1, 1714, D, "Deux malédictions d'arme peuvent être actives en même temps."),
    (7, "Danse macabre", 1, 13750, ('spell', FS['danse']), "Pendant 20 s : énergie régénérée 50 % plus vite, dégâts augmentés de 20 %. Recharge 5 min."),
    (7, "Danse prolongée", 2, 13750, ('fx', flat(1, ['danse'], 2500)), lambda r: "Augmente la durée de Danse macabre de %.1f s." % (2.5 * r), "Danse macabre"),
])
tree5(FSG, 419, "Requiem", CBIT[FOSS], 1, "WarlockDestruction", 5487, [
    (1, "Voix du requiem", 5, 8105, ('fx', lambda r: [('mod', 0, True, REQ_KEYS, round(8.6 * r)), ('mod', 22, True, REQ_KEYS, round(8.6 * r))]),
     lambda r: "Augmente de %d %% les dégâts des sorts du Requiem (70 %% -> 100 %% au rang 5). Le sombredogue et les fantômes vous sont interdits." % round(8.6 * r)),
    (1, "Pierre polie", 5, 5487, ('fx', flat(10, ['pierre'], -100)), lambda r: "Réduit le temps d'incantation de Pierre tombale de %.1f s." % (0.1 * r)),
    (2, "Éclat d'os amélioré", 3, 6343, ('fx', flat(1, ['eclat'], 1000)), lambda r: "Augmente l'hébétement d'Éclat d'os de %d s." % r),
    (2, "Poids de la terre", 2, 8056, ('fx', lambda r: [('proc', FS['h_daze4'], 50 * r, 0x10000, 15, FSG.mask('pierre') | FSG.mask('eclat') | FSG.mask('glas') | FSG.mask('stele') | FSG.mask('eboulement') | FSG.mask('onde') | FSG.mask('chant') | FSG.mask('fissure') | FSG.mask('tombeau'), 2)]),
     lambda r: "Vos sorts critiques du Requiem ont %d %% de chances d'hébéter la cible pendant 4 s." % (50 * r)),
    (2, "Concentration funèbre", 3, 14751, ('fx', m2(9, REQ_KEYS, 23)), lambda r: "Réduit de %d %% le recul de vos sorts quand vous subissez des dégâts." % (23 * r)),
    (3, "Glas amélioré", 3, 589, ('fx', m2(22, ['glas'], 10)), lambda r: "Augmente de %d %% les dégâts d'Ombre de Glas." % (10 * r)),
    (3, "Écho du glas", 2, 8921, ('fx', flat(10, ['glas'], -250)), lambda r: "Réduit le temps d'incantation de Glas de %.2f s." % (0.25 * r)),
    (3, "Terre fertile", 5, 8105, ('fx', flat(7, REQ_KEYS, 1)), lambda r: "Augmente de %d %% les chances de coup critique de vos sorts du Requiem." % r),
    (4, "Fissure", 1, 8046, ('spell', FS['fissure']), "Fissure devant vous sur 20 m : 400 points de dégâts de Nature et hébètement. Recharge 15 s."),
    (4, "Gravats", 5, 8056, D, lambda r: "Vos sorts critiques du Requiem infligent encore %d %% de leurs dégâts en 4 s." % (8 * r)),
    (4, "Onde de terre améliorée", 2, 8046, ('fx', flat(6, ['onde'], 2)), lambda r: "Augmente la portée d'Onde de terre de %d m." % (2 * r)),
    (5, "Pluie de pierres améliorée", 2, 8056, ('fx', lambda r: [('mod', 0, True, ['pluie'], 10 * r), ('mod', 22, True, ['pluie'], 10 * r)]),
     lambda r: "Augmente les dégâts de Pluie de pierres de %d %%." % (10 * r)),
    (5, "Acharnement", 3, 12292, D, lambda r: "Augmente de %d %% les dégâts de vos sorts du Requiem contre les cibles étourdies ou hébétées." % (4 * r)),
    (5, "Économie des tombes", 3, 14751, ('fx', m2(14, REQ_KEYS, -3)), lambda r: "Réduit de %d %% le coût en mana de vos sorts du Requiem." % (3 * r)),
    (6, "Requiem éternel", 3, 8105, ('fx', flat(10, ['chant'], -1000)), lambda r: "Réduit le temps d'incantation de Chant du requiem de %d s." % r),
    (6, "Écrasement", 1, 5487, D, "Pierre tombale a 15 % de chances de plus d'être critique contre une cible étourdie ou hébétée."),
    (7, "Tombeau ouvert", 1, 8056, ('spell', FS['tombeau']), "Zone de 10 m : 2 000 à 2 300 points de dégâts de Nature, étourdit 3 s ; une faille reste 8 s (200 par seconde, hébète). Recharge 3 min."),
    (7, "Faille profonde", 2, 8056, ('fx', lambda r: [('mod', 1, False, ['h_faille'], 2000 * r), ('mod', 22, True, ['h_faille'], 15 * r), ('mod', 11, False, ['tombeau'], -30000 * r)]),
     lambda r: "La faille de Tombeau ouvert dure %d s de plus et inflige %d %% de dégâts en plus ; recharge réduite de %d s." % (2 * r, 15 * r, 30 * r), "Tombeau ouvert"),
])
DRAINS_F = ['d_force', 'd_celerite', 'd_moelle']
tree5(FSG, 420, "Charnier", CBIT[FOSS], 2, "WarlockSummoning", 691, [
    (1, "Pacte du charnier", 5, 691, ('fx', lambda r: [('learn', FS['invoc'])]),
     lambda r: "Vous permet d'invoquer votre sombredogue ; ses dégâts et ses points de vie augmentent de %d %%. Les fantômes vous sont interdits." % (4 * r)),
    (1, "Peau de goule", 5, 20594, D, lambda r: "Augmente l'armure de votre sombredogue de %d %%." % (10 * r)),
    (2, "Curée améliorée", 3, 16827, D, lambda r: "Augmente les dégâts de Curée de %d %%." % (10 * r)),
    (2, "Drains rapides", 2, 702, ('fx', flat(10, DRAINS_F, -500)), lambda r: "Réduit de %.1f s l'incantation des drains de force, de célérité et de moelle." % (0.5 * r)),
    (2, "Faim insatiable", 3, 689, ('fx', m2(22, ['drain'], 5)), lambda r: "Augmente de %d %% les dégâts de Drain de chair." % (5 * r)),
    (3, "Lien de la meute", 5, 19574, D, lambda r: "Augmente la vitesse d'attaque de votre sombredogue de %d %%." % (3 * r)),
    (3, "Résurrection rapide", 2, 982, ('fx', flat(10, ['relever'], -2000)), lambda r: "Réduit l'incantation de Relever l'acolyte de %d s." % (2 * r)),
    (3, "Festin prolongé", 3, 20577, D, lambda r: "Festin de cadavre dure %d s de plus." % (5 * r)),
    (4, "Frénésie du dogue", 1, 19574, ('spell', FS['frenesie']), "Pendant 15 s, votre sombredogue inflige 30 % de dégâts en plus et attaque 20 % plus vite. Recharge 2 min."),
    (4, "Crocs d'os", 5, 16827, D, lambda r: "Augmente de %d %% les chances de coup critique de votre sombredogue." % (2 * r)),
    (4, "Rapport de force", 2, 702, D, lambda r: "Drain de force augmente les dégâts de votre sombredogue de %d %% (au lieu de 20 %%)." % (20 + 5 * r)),
    (5, "Meute nombreuse", 2, 5487, ('fx', flat(8, ['meute'], 2)), lambda r: "Nuée de rats zombies appelle %d rats de plus." % (2 * r)),
    (5, "Os renforcés", 3, 20594, D, lambda r: "Augmente les points de vie de votre sombredogue de %d %% et ses chances de coup critique de %d %%." % (5 * r, r)),
    (5, "Charogne", 3, 20577, D, lambda r: "Quand votre sombredogue tue un ennemi, vous regagnez %d %% de votre mana." % (2 * r)),
    (6, "Dressage macabre", 3, 691, D, lambda r: "Augmente les dégâts de votre sombredogue de %d %%." % (5 * r)),
    (6, "Hurlement", 1, 5484, ('spell', FS['hurlement']), "Les ennemis à 10 m de votre sombredogue fuient pendant 3 s. Recharge 1 min."),
    (7, "Alpha des morts", 1, 19574, ('spell', FS['alpha']), "Pendant 20 s, votre sombredogue inflige 50 % de dégâts en plus et chacun de ses coups touche tous les ennemis à 8 m. Recharge 5 min."),
    (7, "Alpha prolongé", 2, 19574, ('fx', flat(1, ['alpha'], 2500)), lambda r: "Augmente la durée d'Alpha des morts de %.1f s." % (2.5 * r), "Alpha des morts"),
])
tree5(FSG, 421, "Passeur", CBIT[FOSS], 3, "WarlockCurses", 18266, [
    (1, "Pacte du passeur", 5, 18266, ('fx', lambda r: [('learn', FS['a_ardente']), ('learn', FS['a_feroce']), ('mod', 8, True, F_AMES, 5 * r)]),
     lambda r: "Vous permet de lier des fantômes à vos alliés ; leurs effets augmentent de %d %%. Le sombredogue vous est interdit." % (5 * r)),
    (1, "Veille funèbre", 5, 6346, ('fx', aura(10, 127, -4)), lambda r: "Réduit de %d %% la menace que vous générez." % (4 * r)),
    (2, "Bouclier d'âme amélioré", 3, 17, ('fx', m2(8, ['bouclier'], 10)), lambda r: "Augmente l'absorption de Bouclier d'âme de %d %%." % (10 * r)),
    (2, "Liens durables", 2, 18266, ('fx', flat(1, F_AMES, 30000)), lambda r: "Vos fantômes restent liés %d s de plus." % (30 * r)),
    (2, "Voix douce", 3, 6346, ('fx', m2(14, F_AMES, -10)), lambda r: "Réduit de %d %% le coût en mana de vos âmes." % (10 * r)),
    (3, "Âme bienveillante améliorée", 3, 20711, ('fx', m2(8, ['a_bienv'], 10)), lambda r: "Augmente de %d %% les effets d'Âme bienveillante." % (10 * r)),
    (3, "Âme sereine améliorée", 2, 6346, ('fx', m2(8, ['a_sereine'], 25)), lambda r: "Augmente de %d %% les effets d'Âme sereine." % (25 * r)),
    (3, "Passeur aguerri", 5, 14751, ('fx', aura(137, 3, 2)), lambda r: "Augmente votre intelligence de %d %%." % (2 * r)),
    (4, "Garde du passeur", 1, 6940, ('spell', FS['garde']), "Pendant 8 s, l'allié subit 30 % de dégâts en moins. Recharge 1 min."),
    (4, "Âmes rapides", 2, 18266, ('fx', flat(21, F_AMES, -750)), lambda r: "Réduit de %.2f s le temps de recharge global de vos âmes." % (0.75 * r)),
    (4, "Âme gardienne améliorée", 5, 19752, ('fx', flat(8, ['a_gardienne'], -1)), lambda r: "Âme gardienne réduit les dégâts subis de %d %% de plus." % r),
    (5, "Cortège prolongé", 2, 19746, D, lambda r: "Augmente la durée de Cortège de %d s." % (5 * r)),
    (5, "Âme vengeresse améliorée", 3, 18265, D, lambda r: "Augmente de %d %% les dégâts d'Âme vengeresse." % (15 * r)),
    (5, "Procession", 1, 19746, D, "Vous pouvez avoir 4 fantômes actifs au lieu de 3."),
    (5, "Bouclier partagé", 2, 17, D, lambda r: "Quand vous protégez un allié de Bouclier d'âme, vous recevez un bouclier de %d %% de son absorption." % (20 * r)),
    (6, "Libération améliorée", 3, 18265, D, lambda r: "Augmente de %d %% les soins de Libération." % (5 * r)),
    (6, "Passage amélioré", 1, 1020, ('fx', lambda r: [('mod', 1, False, ['passage'], 2000)]), "Passage dure 2 s de plus et rend 10 % de ses points de vie à l'allié."),
    (7, "Légion des trépassés", 1, 18540, ('spell', FS['legion']), "Pendant 20 s, vos fantômes frappent la cible de leur allié, puis explosent et posent Âme maudite. Recharge 5 min."),
    (7, "Légion prolongée", 2, 18540, ('fx', lambda r: [('mod', 1, False, ['legion'], 2500 * r), ('mod', 11, False, ['legion'], -30000 * r)]),
     lambda r: "Augmente la durée de Légion des trépassés de %.1f s et réduit sa recharge de %d s." % (2.5 * r, 30 * r), "Légion des trépassés"),
])
# Martyr : arbres validés le 24/11
tree5(MAG, 422, "Bastion", CBIT[MART], 0, "WarriorProtection", 71, [
    (1, "Peau épaisse", 5, 12297, ('fx', aura(101, 1, 2)), lambda r: "Augmente votre armure de %d %%." % (2 * r)),
    (1, "Sang tenace", 5, 12975, ('fx', aura(133, 0, 2)), lambda r: "Augmente vos points de vie maximum de %d %%." % (2 * r)),
    (2, "Caillot amélioré", 3, 2565, D, lambda r: "Augmente l'absorption de Caillot de %d %%." % (10 * r)),
    (2, "Défi assuré", 2, 355, ('fx', flat(11, ['defi'], -2000)), lambda r: "Réduit la recharge de Défi du sang de %d s." % (2 * r)),
    (2, "Plaie amplifiée", 3, 6343, ('fx', m2(2, ['plaie'], 10)), lambda r: "Augmente de %d %% la menace de Plaie partagée." % (10 * r)),
    (3, "Sang provocant", 5, 355, ('fx', aura(10, 127, 3)), lambda r: "Augmente de %d %% la menace de toutes vos attaques." % (3 * r)),
    (3, "Sang bouillonnant", 3, 23922, ('fx', flat(14, ['bouclier_s'], -3)), lambda r: "Réduit le coût de Coup de bouclier sanglant de %d points d'énergie." % (3 * r)),
    (3, "Ferveur du gardien", 2, 12292, D, lambda r: "Chaque coup reçu a %d %% de chances de vous donner 1 Ferveur." % (10 * r)),
    (4, "Rempart vivant", 1, 2687, ('spell', MA['rempart']), "Pendant 15 s, chaque coup reçu vous rend 5 points d'énergie. Recharge 1 min."),
    (4, "Coagulation améliorée", 2, 871, ('fx', flat(11, ['coagulation'], -30000)), lambda r: "Réduit la recharge de Coagulation de %d s." % (30 * r)),
    (4, "Endurance du martyr", 5, 12976, ('fx', aura(137, 2, 1)), lambda r: "Augmente votre endurance de %d %%." % r),
    (5, "Riposte sanglante", 3, 23922, ('fx', lambda r: [('proc', MA['riposte'][r - 1], 100, 0x8 | 0x20, 0, 0, 0x10 | 0x20 | 0x40)]),
     lambda r: "Après une esquive, une parade ou un blocage, votre prochain Coup de bouclier sanglant inflige %d %% de dégâts en plus." % (10 * r)),
    (5, "Cri amélioré", 2, 1161, ('fx', flat(11, ['cri'], -30000)), lambda r: "Réduit la recharge de Cri du martyr de %d s." % (30 * r)),
    (5, "Plaie sanglante", 3, 772, D, lambda r: "Plaie partagée fait saigner les ennemis : %d points de dégâts en 6 s." % (50 * r)),
    (6, "Chair indestructible", 3, 12975, ('fx', aura(87, 127, -1)), lambda r: "Réduit les dégâts subis de %d %%." % r),
    (6, "Caillot réflexe", 1, 2565, D, "Sous 25 % de vos points de vie, un Caillot gratuit se forme. Une fois par minute."),
    (7, "Forteresse de sang", 1, 642, ('spell', MA['forteresse']), "Pendant 20 s : PV max +20 %, dégâts subis -20 %, soins reçus +20 %, chaque coup reçu donne 1 Ferveur, sorts de sang sans coût en PV. Recharge 5 min."),
    (7, "Sang riche", 2, 71, ('fx', lambda r: [('aura', 22, 126, 25 * r), ('mod', 8, False, ['peau'], 2 * r)]),
     lambda r: "Augmente de %d vos résistances à toutes les magies, et Peau de sang augmente l'armure de %d %% de plus." % (25 * r, 2 * r), "Forteresse de sang"),
])
tree5(MAG, 423, "Saignée", CBIT[MART], 1, "WarriorArms", 772, [
    (1, "Lame affûtée", 5, 12700, ('fx', aura(52, 0, 1)), lambda r: "Augmente vos chances de coup critique de %d %%." % r),
    (1, "Soif accrue", 5, 12292, D, lambda r: "Le bonus maximum de Soif de sang passe à %d %%." % (25 + 2 * r)),
    (2, "Entaille profonde", 3, 772, ('fx', m2(22, ['entaille'], 15)), lambda r: "Augmente de %d %% les dégâts du saignement d'Entaille." % (15 * r)),
    (2, "Hachoir amélioré", 2, 7384, ('fx', flat(11, ['hachoir'], -1000)), lambda r: "Réduit la recharge de Hachoir de %d s." % r),
    (2, "Cœur battant", 3, 13750, ('fx', aura(110, 3, 5)), lambda r: "Augmente votre régénération d'énergie de %d %%." % (5 * r)),
    (3, "Maîtrise des armes à deux mains", 5, 12163, ('fx', lambda r: [('aura', 79, 1, r), ('sets', {'EquippedItemClass': 2, 'EquippedItemSubClassMask': DEUXM})]),
     lambda r: "Augmente de %d %% les dégâts infligés avec une arme à deux mains." % r),
    (3, "Tourbillon de sang amélioré", 2, 1680, ('fx', flat(11, ['tourbillon_s'], -2000)), lambda r: "Réduit la recharge de Tourbillon de sang de %d s." % (2 * r)),
    (3, "Exécution améliorée", 3, 5308, ('fx', flat(14, ['execution'], -5)), lambda r: "Réduit le coût d'Exécution de %d points d'énergie." % (5 * r)),
    (4, "Fureur du sang", 1, 18499, ('spell', MA['fureur']), "Vos 3 prochains coups sont critiques. Coûte 3 % de vos points de vie. Recharge 1 min."),
    (4, "Hémorragie améliorée", 2, 16511, ('fx', m2(22, ['hemorragie'], 10)), lambda r: "Augmente les dégâts d'Hémorragie de %d %%." % (10 * r)),
    (4, "Instinct de survie", 5, 12975, D, lambda r: "Sous 35 %% de vos points de vie, les dégâts subis sont réduits de %d %%." % (2 * r)),
    (5, "Frénésie prolongée", 2, 1719, ('fx', flat(1, ['frenesie_s'], 5000)), lambda r: "Augmente la durée de Frénésie écarlate de %d s." % (5 * r)),
    (5, "Désespoir", 3, 1464, D, lambda r: "Coup du désespoir est doublé sous %d %% de vos points de vie." % (35 + 5 * r)),
    (5, "Ferveur sanglante", 3, 12292, D, lambda r: "Vos coups critiques ont %d %% de chances de donner 1 Ferveur de plus." % (15 * r)),
    (6, "Lames ébréchées", 3, 772, ('fx', lambda r: [('proc', MA['lames_d'], 10 * r, 0x4)]),
     lambda r: "Vos attaques automatiques ont %d %% de chances de faire saigner la cible : 40 points de dégâts en 10 s, cumulable 5 fois." % (10 * r)),
    (6, "Festin prolongé", 1, 23881, D, "Festin de lames dure 5 coups au lieu de 3."),
    (7, "Sang caillé", 1, 13218, ('spell', MA['caille']), "1 700 points de dégâts en 20 s, +20 % par Ferveur, armure de la cible -10 %. 30 énergie et 4 % des PV, recharge 1 min."),
    (7, "Sang critique", 2, 12700, ('fx', lambda r: [('aura', 54, 0, 2 * r), ('aura', 52, 0, 2 * r)]),
     lambda r: "Augmente vos chances de toucher et de coup critique de %d %%." % (2 * r), "Sang caillé"),
])
tree5(MAG, 424, "Offrande", CBIT[MART], 2, "PriestHoly", 2050, [
    (1, "Mains vives", 5, 2050, ('fx', flat(10, ['don_s'], -100)), lambda r: "Réduit le temps d'incantation de Don de sang de %.1f s." % (0.1 * r)),
    (1, "Sang calme", 5, 6346, ('fx', m2(2, HEALS_M, -4)), lambda r: "Réduit de %d %% la menace générée par vos soins." % (4 * r)),
    (2, "Transfusion améliorée", 3, 139, ('fx', lambda r: [('mod', 0, True, ['transfu_v'], 5 * r), ('mod', 22, True, ['transfu_v'], 5 * r)]),
     lambda r: "Augmente les soins de Transfusion de vie de %d %%." % (5 * r)),
    (2, "Sang pur", 2, 13750, ('fx', aura(35, 3, 10)), lambda r: "Augmente votre énergie maximum de %d." % (10 * r)),
    (2, "Sacrifice renforcé", 3, 6940, D, lambda r: "Réduit de %d %% les dégâts que Sacrifice vous transfère." % (10 * r)),
    (3, "Vigueur du martyr", 5, 12976, ('fx', aura(137, 2, 2)), lambda r: "Augmente votre endurance de %d %%." % (2 * r)),
    (3, "Sang partagé amélioré", 3, 1064, ('fx', m2(0, ['partage_s'], 5)), lambda r: "Augmente les soins de Sang partagé de %d %%." % (5 * r)),
    (3, "Communion élargie", 2, 15237, D, lambda r: "Augmente le rayon de Communion de %d m." % (5 * r)),
    (4, "Don ultime", 1, 633, ('spell', MA['don_u']), "Rend aussitôt 30 % de ses points de vie maximum à l'allié. Coûte 8 % de vos points de vie. Recharge 2 min."),
    (4, "Fontaine améliorée", 2, 724, D, lambda r: "Fontaine de sang dure %d s de plus." % (2 * r)),
    (4, "Grâce sanglante", 5, 15359, ('fx', flat(7, HEALS_M, 1)), lambda r: "Augmente de %d %% les chances de coup critique de vos soins." % r),
    (5, "Grand sacrifice rapide", 2, 2060, ('fx', flat(10, ['grand_s'], -250)), lambda r: "Réduit le temps d'incantation de Grand sacrifice de %.2f s." % (0.25 * r)),
    (5, "Sang béni amélioré", 3, 20217, D, lambda r: "Sang béni vous soigne de %d %% des soins reçus par l'allié." % (20 + 5 * r)),
    (5, "Cœur généreux", 3, 20711, ('fx', aura(136, 127, 2)), lambda r: "Augmente vos soins de %d %%." % (2 * r)),
    (6, "Ferveur bienveillante", 3, 12292, D, lambda r: "Vos soins critiques ont %d %% de chances de donner 1 Ferveur de plus." % (33 * r)),
    (6, "Vie offerte", 1, 20608, D, "Dernier sacrifice : recharge de 5 min au lieu de 10, soin de 25 % au lieu de 15 %."),
    (7, "Saint martyr", 1, 20711, ('spell', MA['saint']), "Pendant 20 s, chacun de vos soins soigne aussi tout le groupe de 20 % de sa valeur ; sorts de sang sans coût en PV. Recharge 5 min."),
    (7, "Saint martyr prolongé", 2, 20711, ('fx', flat(1, ['saint'], 2500)), lambda r: "Saint martyr dure %.1f s de plus et le soin partagé passe à %d %%." % (2.5 * r, 20 + 5 * r), "Saint martyr"),
])
tree5(MAG, 425, "Hémophage", CBIT[MART], 3, "WarlockCurses", 689, [
    (1, "Crocs aiguisés", 5, 17877, ('fx', lambda r: [('mod', 0, True, DRAINS_M, 2 * r), ('mod', 22, True, DRAINS_M, 2 * r)]),
     lambda r: "Augmente de %d %% les dégâts de vos drains." % (2 * r)),
    (1, "Sang froid", 5, 12976, ('fx', aura(117, 12, 2)), lambda r: "Augmente de %d %% vos chances de résister aux étourdissements." % (2 * r)),
    (2, "Morsure profonde", 3, 17877, ('fx', m2(0, ['morsure'], 5)), lambda r: "Augmente les dégâts de Morsure de %d %%." % (5 * r)),
    (2, "Sangsue tenace", 2, 18265, ('fx', flat(28, ['sangsue'], 50)), lambda r: "Sangsue a %d %% de chances de résister à la dissipation." % (50 * r)),
    (2, "Siphon stable", 3, 689, ('fx', m2(9, ['siphon'], 23)), lambda r: "Réduit de %d %% le recul de Siphon quand vous subissez des dégâts." % (23 * r)),
    (3, "Horreur prolongée", 2, 6789, ('fx', flat(1, ['horreur'], 500)), lambda r: "Augmente la durée d'Horreur sanglante de %.1f s." % (0.5 * r)),
    (3, "Sang figé amélioré", 3, 12323, ('fx', flat(12, ['fige'], -5)), lambda r: "Sang figé ralentit de %d %% de plus." % (5 * r)),
    (3, "Soif inextinguible", 5, 7651, ('fx', m2(27, DRAINS_M, 3)), lambda r: "Vos drains vous soignent de %d %% de plus." % (3 * r)),
    (4, "Étreinte du sang", 1, 339, ('spell', MA['etreinte']), "Immobilise la cible 3 s et lui draine 400 points de vie. 20 énergie, recharge 30 s."),
    (4, "Purge améliorée", 2, 370, ('fx', flat(11, ['purge'], -3000)), lambda r: "Réduit la recharge de Purge de sang de %d s." % (3 * r)),
    (4, "Prédateur", 5, 1130, D, lambda r: "Augmente de %d %% vos dégâts contre les cibles à moins de 50 %% de leur vie." % (2 * r)),
    (5, "Marque profonde", 3, 1130, D, lambda r: "Marque du sang vous soigne de %d %% des dégâts subis par la cible." % (20 + 5 * r)),
    (5, "Anémie prolongée", 2, 13218, ('fx', flat(1, ['anemie'], 2000)), lambda r: "Augmente la durée d'Anémie de %d s." % (2 * r)),
    (5, "Veines ouvertes", 3, 7651, ('fx', flat(7, DRAINS_M, 2)), lambda r: "Augmente de %d %% les chances de coup critique de vos drains." % (2 * r)),
    (6, "Résilience du sang", 3, 12976, ('fx', lambda r: [('aura', 117, 12, 5 * r), ('aura', 117, 5, 5 * r), ('aura', 117, 7, 5 * r)]),
     lambda r: "Augmente de %d %% vos chances de résister aux étourdissements, à la peur et aux immobilisations." % (5 * r)),
    (6, "Festin étendu", 1, 7651, ('fx', lambda r: [('mod', 6, False, ['festin_s'], 5)]), "Le rayon de Festin sanglant passe de 10 à 15 m."),
    (7, "Seigneur du sang", 1, 1856, ('spell', MA['seigneur']), "30 s : camouflé sans interruption, vitesse 130 %, drains +50 %, soins reçus par la cible -25 %, critique +10 %. Recharge 5 min."),
    (7, "Seigneur prolongé", 2, 1856, D, lambda r: "Seigneur du sang augmente vos chances de coup critique de %d %% de plus." % (10 * r), "Seigneur du sang"),
])
NV_TABS = [(TISS, 414), (TISS, 415), (TISS, 416), (TISS, 417), (FOSS, 418), (FOSS, 419), (FOSS, 420), (FOSS, 421),
           (MART, 422), (MART, 423), (MART, 424), (MART, 425)]
TALG, TAL_ID = TALG_PREV, TAL_ID_PREV

# ======================================================================== créatures : sombredogue et charognards
NV_SQL.append("DELETE FROM creature_template WHERE Entry BETWEEN 990720 AND 990729;")
NV_SQL.append("DELETE FROM pet_levelstats WHERE creature_entry BETWEEN 990720 AND 990729;")
NV_SQL.append("DROP TEMPORARY TABLE IF EXISTS tmp_ct_nv;")
NV_SQL.append("CREATE TEMPORARY TABLE tmp_ct_nv LIKE creature_template;")
for _e, _src, _name, _disp in ((C_SOMBREDOGUE, 417, "Sombredogue", 11421), (C_CHAROGNARD, 417, "Rat zombie", 1141)):
    NV_SQL.append("INSERT INTO tmp_ct_nv SELECT * FROM creature_template WHERE Entry=%d;" % _src)
    NV_SQL.append("UPDATE tmp_ct_nv SET Entry=%d, Name='%s', SubName='', DisplayId1=%d, DisplayId2=0, DisplayId3=0, DisplayId4=0, "
                  "DisplayIdProbability1=100, DisplayIdProbability2=0, DisplayIdProbability3=0, DisplayIdProbability4=0, CreatureType=1, "
                  "Family=1, PetSpellDataId=0, ScriptName='', AIName='' WHERE Entry=%d;" % (_e, _name, _disp, _src))
    NV_SQL.append("INSERT INTO pet_levelstats (creature_entry, level, hp, mana, armor, str, agi, sta, inte, spi) "
                  "SELECT %d, level, hp, mana, armor, str, agi, sta, inte, spi FROM pet_levelstats WHERE creature_entry=%d;" % (_e, _src))
NV_SQL.append("INSERT INTO creature_template SELECT * FROM tmp_ct_nv;")
NV_SQL.append("DROP TEMPORARY TABLE tmp_ct_nv;")

# ======================================================================== maîtres de classe, sorts de départ
START_SPELLS[TISS] = [TW['toucher'], TW['trait'], TW['fuseau']]
START_SPELLS[FOSS] = [FS['pierre'], FS['posture'], FS['pelle']]
START_SPELLS[MART] = [MA['frappe'], MA['bouclier_s'], MA['don_s']]
teach_all(TWG, 906, set(START_SPELLS[TISS]))
teach_all(FSG, 907, set(START_SPELLS[FOSS]))
teach_all(MAG, 908, set(START_SPELLS[MART]))
_tid = TEACH[0]; TEACH[0] += 1
TG.add(_tid, TEACH_BASE, "Armure en plaques", "Permet de porter les armures en plaques.", "", family=False,
       sets={'EffectTriggerSpell1': 750, 'SpellLevel': 40, 'BaseLevel': 40, 'MaxLevel': 0, 'SpellIconID': icon(750)})
TRAINER_SPELLS.setdefault(908, []).append((_tid, 2000, 40))
TRAINERS += [
    (906, 990700, "Elyndra Fil-d'Argent", "Maître tisserand", 3595, 0, 0),     # Sombrevallon (Teldrassil)
    (906, 990701, "Zan'jira", "Maître tisserand", 3707, 0, 0),                  # Vallée des Épreuves
    (906, 990702, "Hanu Tisse-Vent", "Maître tisserand", 3062, 0, 0),           # Camp Narache (Mulgore)
    (906, 990703, "Lyrisse Navette-d'Or", "Maître tisserand", 4090, 0, 0),      # Darnassus
    (906, 990704, "Vol'zira", "Maître tisserand", 6014, 0, 0),                  # Orgrimmar
    (906, 990705, "Ahanu Longue-Trame", "Maître tisserand", 3044, 0, 0),        # Pitons-du-Tonnerre
    (907, 990706, "Gaspard Pelleterre", "Maître fossoyeur", 915, 0, 0),         # Comté du Nord
    (907, 990707, "Fizzle Creusecombe", "Maître fossoyeur", 916, 0, 0),         # Frigolande (Val d'Est-Gel)
    (907, 990708, "Mortimer Glas", "Maître fossoyeur", 2122, 0, 0),             # Clairière de Tirisfal
    (907, 990709, "Ambroise Fosse-Noire", "Maître fossoyeur", 918, 0, 0),       # Hurlevent
    (907, 990710, "Ophélia Terre-Grise", "Maître fossoyeur", 4582, 0, 0),       # Fossoyeuse
    (908, 990711, "Frère Aldric", "Maître martyr", 911, 1, 0),                  # Comté du Nord
    (908, 990712, "Bruni Cœur-Brisé", "Maître martyr", 912, 2, 0),              # Frigolande
    (908, 990713, "Gor'mash Saigne-Cœur", "Maître martyr", 3153, 1, 0),         # Vallée des Épreuves
    (908, 990714, "Hilde Sang-Fidèle", "Maître martyr", 1229, 0, 0),            # Forgefer
]
for _cls, _races, _start in ((TISS, (4, 6, 8), START_SPELLS[TISS]), (FOSS, (1, 5, 7), START_SPELLS[FOSS]), (MART, (1, 2, 3, 8), START_SPELLS[MART])):
    for _race in _races:
        for _btn, _sp in enumerate(_start):
            NV_SQL.append("INSERT IGNORE INTO playercreateinfo_spell (race, class, Spell, Note) VALUES (%d, %d, %d, 'Nouvelle classe');" % (_race, _cls, _sp))
            NV_SQL.append("INSERT IGNORE INTO playercreateinfo_action (race, class, button, action, type) VALUES (%d, %d, %d, %d, 0);" % (_race, _cls, _btn + 1, _sp))

# ======================================================================== constantes pour le module
for _k in ('fils', 'fils_e', 'trancher_d', 'toile_hot', 'don_e', 'bonus_soin', 'mortel', 'mortel_x', 'noeud_m', 'atropos_m', 'destin_r',
           'trepas', 'epines', 'laceration', 'toucher', 'trait', 'vie', 'trancher', 'toile_p', 'lien_f', 'ariane', 'don', 'pelote', 'grande', 'partages', 'destin',
           'fuseau', 'noeud', 'fil_noir', 'fil_tendu', 'noeud_c', 'funebre', 'recolte', 'atropos', 'contagion', 'conducteur', 'recousu',
           'tapisserie', 'garrot', 'lame', 'derniere', 'navette', 'raccom', 'metier', 'ressoudure', 'tempete'):
    NVH.append(('TW_' + _k.upper(), [TW[_k]]))
for _k in ('pourriture', 'curee_d', 'drain_pet', 'force_pet', 'celerite_pet', 'moelle_pet', 'festin_pet', 'pacte_pet', 'vengeresse_d',
           'liberation_h', 'posture', 'profanation', 'invoc', 'relever', 'drain', 'curee', 'festin', 'd_force', 'd_celerite', 'meute',
           'd_moelle', 'partage', 'cortege', 'liberation', 'm_pourriture', 'm_entrave', 'm_epuise') + tuple(F_AMES):
    NVH.append(('F_' + _k.upper(), [FS[_k]]))
NVH.append(('F_AMES', [FS[k] for k in F_AMES]))
for _k in ('fosse', 'danse', 'fissure', 'tombeau', 'frenesie', 'hurlement', 'alpha', 'garde', 'legion', 'h_daze4', 'h_daze_f', 'h_gravats',
           'h_terre', 'h_faille', 'h_hurlement', 'h_alpha_d', 'h_rat', 'pacte_pet2', 'h_maitrise', 'h_bouclier_p', 'h_legion_d', 'h_legion_x',
           'h_ame_maudite', 'h_passage', 'bouclier', 'passage', 'sortie', 'tourbillon', 'pelle', 'pierre', 'eclat', 'glas', 'stele',
           'eboulement', 'onde', 'chant'):
    NVH.append(('F_' + _k.upper(), [FS[_k]]))
NVH.append(('F_BIERE', FS['biere']))
NVH.append(('F_REQ', [FS[k] for k in ('pierre', 'eclat', 'glas', 'stele', 'eboulement', 'onde', 'chant', 'fissure', 'tombeau')]))
NVH.append(('F_MALS', [FS['pourriture'], FS['entrave_d'], FS['epuise_d']]))
for (_tab, _tname), _cname in [((418, "Maîtrise de la pelle"), "TF_MAITRISE"), ((418, "Pelletée funèbre"), "TF_PELLETEE"),
                               ((418, "Profanation améliorée"), "TF_PROFANATION"), ((418, "Malédictions jumelles"), "TF_JUMELLES"),
                               ((419, "Gravats"), "TF_GRAVATS"), ((419, "Acharnement"), "TF_ACHARNEMENT"), ((419, "Écrasement"), "TF_ECRASEMENT"),
                               ((420, "Peau de goule"), "TF_PEAU"), ((420, "Curée améliorée"), "TF_CUREE"), ((420, "Lien de la meute"), "TF_LIEN"),
                               ((420, "Festin prolongé"), "TF_FESTIN"), ((420, "Crocs d'os"), "TF_CROCS"), ((420, "Rapport de force"), "TF_RAPPORT"),
                               ((420, "Os renforcés"), "TF_OS"), ((420, "Charogne"), "TF_CHAROGNE"), ((420, "Dressage macabre"), "TF_DRESSAGE"),
                               ((421, "Cortège prolongé"), "TF_CORTEGE"), ((421, "Âme vengeresse améliorée"), "TF_VENGERESSE"),
                               ((421, "Procession"), "TF_PROCESSION"), ((421, "Bouclier partagé"), "TF_BOUCLIER"),
                               ((421, "Libération améliorée"), "TF_LIBERATION"), ((421, "Passage amélioré"), "TF_PASSAGE"),
                               ((422, "Caillot amélioré"), "TM_CAILLOT_A"), ((422, "Ferveur du gardien"), "TM_GARDIEN"),
                               ((422, "Plaie sanglante"), "TM_PLAIE_S"), ((422, "Caillot réflexe"), "TM_REFLEXE"),
                               ((423, "Soif accrue"), "TM_SOIF_A"), ((423, "Instinct de survie"), "TM_INSTINCT"), ((423, "Désespoir"), "TM_DESESPOIR"),
                               ((423, "Ferveur sanglante"), "TM_FERVEUR_S"), ((423, "Festin prolongé"), "TM_FESTIN_P"),
                               ((424, "Sacrifice renforcé"), "TM_SACRIFICE_R"), ((424, "Communion élargie"), "TM_COMMUNION_E"),
                               ((424, "Fontaine améliorée"), "TM_FONTAINE_A"), ((424, "Sang béni amélioré"), "TM_BENI_A"),
                               ((424, "Ferveur bienveillante"), "TM_FERVEUR_B"), ((424, "Vie offerte"), "TM_VIE_OFFERTE"),
                               ((424, "Saint martyr prolongé"), "TM_SAINT_P"), ((425, "Prédateur"), "TM_PREDATEUR"),
                               ((425, "Marque profonde"), "TM_MARQUE_P"), ((425, "Seigneur prolongé"), "TM_SEIGNEUR_P")]:
    NVH.append((_cname, TID[(_tab, _tname)]))
# Martyr
for _k, _v in MA.items():
    NVH.append(('MA_' + _k.upper(), _v if isinstance(_v, list) else [_v]))
NVH.append(('MA_SANG', [MA[k] for k, _p, _c in MA_SANG]))
NVH.append(('MA_SANG_PCT', [_p for k, _p, _c in MA_SANG]))
NVH.append(('MA_SANG_CONSO', [1 if _c else 0 for k, _p, _c in MA_SANG]))
NVH.append(('MA_DRAINS', [MA[k] for k in DRAINS_M]))
NVH.append(('MA_SOINS', [MA[k] for k in HEALS_M]))
NVH.append(('C_SOMBREDOGUE', [C_SOMBREDOGUE]))
NVH.append(('C_CHAROGNARD', [C_CHAROGNARD]))
for _tname, _cname in [("Trame serrée", "TT_SERREE"), ("Vigilance", "TT_VIGILANCE"), ("Double lien", "TT_DOUBLE"),
                       ("Fil réparateur", "TT_REPARATEUR"), ("Fil d'acier", "TT_ACIER"), ("Don renforcé", "TT_DON"), ("Bobine", "TT_BOBINE"),
                       ("Tension", "TT_TENSION"), ("Mana filé", "TT_MANA"), ("Fil empoisonné", "TT_EMPOISONNE"), ("Double maille", "TT_MAILLE"),
                       ("Agonie", "TT_AGONIE"), ("Fil vampirique", "TT_VAMPIRIQUE"), ("Refus du trépas", "TT_TREPAS"),
                       ("Récolte abondante", "TT_RECOLTE"), ("Atropos implacable", "TT_ATROPOS"), ("Voix du requiem", "TF_REQUIEM"),
                       ("Pacte du charnier", "TF_CHARNIER"), ("Pacte du passeur", "TF_PASSEUR")]:
    NVH.append((_cname, [t['id'] for t in T5G.spells if t['name'] == _tname]))
