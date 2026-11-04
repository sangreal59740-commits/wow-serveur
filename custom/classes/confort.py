# Confort de jeu (demandes d'Alexis du 04/11) : exécuté par gen_sorts.py avant l'écriture des sorties
#   potions et élixirs : durée doublée
#   nourriture : buffs « bien nourri » +50 %, 30 min, +5 % d'expérience (module classes)
#   buffs de classe hors combat (5 à 30 min) : 60 min ; poisons et armes du chaman : 60 min
#   sort 65506 « Sur la route » : +20 % de vitesse à pied et en monture (module routes)
import re as _re
from dbc import DBC
from spellgen import dbc_col as _dcc

def _v(sid, col):
    return SPR[sid][_dcc(col)]

_DURMS = {r[0]: r[1] for r in DBC('/home/claude/wow/classes/dbc/SpellDuration.dbc').rows}
_MSIDX = {}
for _k, _ms in sorted(_DURMS.items()):
    _MSIDX.setdefault(_ms, _k)
SPELL_TEXT = {}             # sort -> {colonne Spell.dbc: [(motif, remplacement)] ou ('+', texte ajouté)}

def _texte(sid, col, *ops):
    SPELL_TEXT.setdefault(str(sid), {}).setdefault(str(col), []).extend(ops)

# ---------------------------------------------------------------- potions et élixirs : durée x2
_pot = q("SELECT DISTINCT spellid_1 FROM item_template WHERE class=0 AND spelltrigger_1=0 AND spellid_1>0 AND "
         "(subclass IN (2, 3) OR name LIKE '%Elixir%' OR name LIKE '%Potion%' OR name LIKE '%Flask%' OR name LIKE '%Draught%')")
POTIONS_X2, POTIONS_SANS = [], []
_EXCLU = _re.compile(r"^(Food|Drink|Dreamless Sleep|Greater Dreamless Sleep|Cowardly Flight|Rumsey Rum.*|Trogg Ale|zzOLD.*)$")
_NOMS = {int(i): n for i, n in q("SELECT Id, SpellName FROM spell_template WHERE Id IN (%s)" % ",".join(r[0] for r in _pot))}
for (_s,) in _pot:
    _s = int(_s)
    if _s not in SPR or _EXCLU.match(_NOMS.get(_s, '').strip()):
        continue
    if not any(_v(_s, 'Effect%d' % n) in (6, 35) for n in (1, 2, 3)):
        continue
    _ms = _DURMS.get(_v(_s, 'DurationIndex'), 0)
    if _ms < 10000 or _ms > 7200000:
        continue
    _idx = _MSIDX.get(_ms * 2)
    if _idx is None:
        POTIONS_SANS.append(_s)
        continue
    VPATCH.setdefault(_s, {})['DurationIndex'] = _idx
    POTIONS_X2.append(_s)
print('potions et élixirs x2 :', len(POTIONS_X2), 'sans durée double disponible :', POTIONS_SANS)

# ---------------------------------------------------------------- nourriture
BIEN_NOURRI = [int(r[0]) for r in q("SELECT Id FROM spell_template WHERE SpellName='Well Fed' AND Id<30000")]
BIEN_NOURRI += [18191, 18192, 18193, 18194, 18222, 22730, 25661, 18125, 18141, 23697]
BIEN_NOURRI = sorted(set(s for s in BIEN_NOURRI if s in SPR))
for _s in BIEN_NOURRI:
    _p = VPATCH.setdefault(_s, {})
    _p['DurationIndex'] = DUR[1800000]
    for n in (1, 2, 3):
        if _v(_s, 'Effect%d' % n) == 6:
            _val = _v(_s, 'EffectBasePoints%d' % n) + _v(_s, 'EffectDieSides%d' % n)
            _p['EffectBasePoints%d' % n] = max(int(round(_val * 1.5)) - _v(_s, 'EffectDieSides%d' % n), 0)
    _texte(_s, 147, ('+', " Expérience gagnée augmentée de 5 %."))
# textes figés dans les descriptions de la nourriture (« 25 points d'Endurance », « 15 min »)
for (_f, _b) in q("SELECT f.Id, b.Id FROM spell_template f JOIN spell_template b ON b.Id IN (f.EffectTriggerSpell1, f.EffectTriggerSpell2, f.EffectTriggerSpell3) "
                  "WHERE b.Id IN (%s) AND f.Id<>b.Id" % ",".join(map(str, BIEN_NOURRI))):
    _f, _b = int(_f), int(_b)
    if _f not in SPR:
        continue
    _ops = [(r'15 min', '30 min')]
    for n in (1, 2):
        if _v(_b, 'Effect%d' % n) == 6:
            _old = _v(_b, 'EffectBasePoints%d' % n) + _v(_b, 'EffectDieSides%d' % n)
            _new = VPATCH[_b]['EffectBasePoints%d' % n] + _v(_b, 'EffectDieSides%d' % n)
            _ops.append((r'(?<![\d$])%d (points)' % _old, r'%d \1' % _new))
    _ops.append(('+', " Bien nourri : +5 % d'expérience."))
    _texte(_f, 138, *_ops)
print('bien nourri :', len(BIEN_NOURRI))

# ---------------------------------------------------------------- buffs de classe : 60 min
_BUFFS = ['Arcane Intellect', 'Amplify Magic', 'Dampen Magic', 'Frost Armor', 'Ice Armor', 'Mage Armor', 'Demon Skin', 'Demon Armor',
          'Unending Breath', 'Detect Invisibility', 'Detect Lesser Invisibility', 'Detect Greater Invisibility', 'Power Word: Fortitude',
          'Divine Spirit', 'Shadow Protection', 'Prayer of Shadow Protection', 'Inner Fire', 'Fear Ward', 'Shadowguard', 'Touch of Weakness',
          'Mark of the Wild', 'Thorns', 'Omen of Clarity', 'Blessing of Light', 'Blessing of Salvation', 'Blessing of Sanctuary',
          'Greater Blessing of Light', 'Greater Blessing of Salvation', 'Greater Blessing of Sanctuary', 'Righteous Fury',
          'Water Walking', 'Water Breathing', 'Lightning Shield']
_COURT = {_MSIDX[ms] for ms in (300000, 600000, 900000, 1200000, 1800000) if ms in _MSIDX}
BUFFS_60 = []
for (_s,) in q("SELECT Id FROM spell_template WHERE SpellName IN (%s) AND Id<30000" % ",".join("'%s'" % esc(n) for n in _BUFFS)):
    _s = int(_s)
    if _s not in SPR or _v(_s, 'DurationIndex') not in _COURT:
        continue
    if not any(_v(_s, 'Effect%d' % n) in (6, 35) for n in (1, 2, 3)):
        continue
    VPATCH.setdefault(_s, {})['DurationIndex'] = DUR[3600000]
    BUFFS_60.append(_s)
print('buffs de classe à 60 min :', len(BUFFS_60))
# poisons et armes du chaman (enchantement temporaire : la durée est la valeur de l'effet, en secondes)
_ARMES = ['Crippling Poison', 'Deadly Poison', 'Deadly Poison II', 'Deadly Poison III', 'Deadly Poison IV', 'Deadly Poison V',
          'Instant Poison', 'Instant Poison II', 'Instant Poison III', 'Instant Poison IV', 'Instant Poison V', 'Instant Poison VI',
          'Mind-numbing Poison', 'Mind-numbing Poison II', 'Mind-numbing Poison III', 'Wound Poison',
          'Rockbiter Weapon', 'Flametongue Weapon', 'Frostbrand Weapon', 'Windfury Weapon']
ARMES_60 = []
for (_s,) in q("SELECT Id FROM spell_template WHERE Effect1=54 AND SpellName IN (%s)" % ",".join("'%s'" % esc(n) for n in _ARMES)):
    _s = int(_s)
    if _s in SPR:
        VPATCH.setdefault(_s, {})['EffectBasePoints1'] = 3599
        ARMES_60.append(_s)
# textes « 30 minutes » / « 5 min » des poisons et des armes (sorts qui les appliquent et objets)
for (_s,) in q("SELECT Id FROM spell_template WHERE SpellName IN (%s)" % ",".join("'%s'" % esc(n) for n in _ARMES)):
    _s = int(_s)
    if _s in SPR:
        _texte(_s, 138, (r'30 minutes', '60 minutes'), (r'30 min\b', '60 min'), (r'5 minutes', '60 minutes'), (r'(?<!\d)5 min\b', '60 min'))
print('poisons et armes à 60 min :', len(ARMES_60))

# buffs des classes custom
_CUSTOM60 = {'Armure démoniaque', 'Armure de nature', 'Lames spectrales', 'Bouclier de terre', 'Aura du sanctuaire', 'Lien de vie'}
_n60 = 0
for _g in [NG, SG, MG, TALG, T4G] + [g for g, a, b in V4_GENS]:
    for _sp in _g.spells:
        if _sp['name'] in _CUSTOM60:
            _d = _sp['sets'].get('DurationIndex', SPR[_sp['base']][_dcc('DurationIndex')])
            if _d in _COURT:
                _sp['sets']['DurationIndex'] = DUR[3600000]
                _n60 += 1
print('buffs custom à 60 min :', _n60)

# ---------------------------------------------------------------- vitesse sur les routes
ROUTE_SPELL = 65506
SPG.add(ROUTE_SPELL, 8690, "Sur la route", "Vitesse de déplacement augmentée de 20 % sur les routes et les chemins.",
        tooltip="Vitesse de déplacement augmentée de 20 %.",
        family=False, sets={'Effect1': 6, 'EffectApplyAuraName1': 129, 'EffectImplicitTargetA1': 1, 'EffectBasePoints1': 19, 'EffectDieSides1': 1,
                            'EffectMiscValue1': 0, 'Effect2': 6, 'EffectApplyAuraName2': 130, 'EffectImplicitTargetA2': 1,
                            'EffectBasePoints2': 19, 'EffectDieSides2': 1, 'EffectMiscValue2': 0, 'Effect3': 0, 'EffectApplyAuraName3': 0,
                            'CastingTimeIndex': 1, 'DurationIndex': DUR[-1], 'Category': 0, 'RecoveryTime': 0, 'CategoryRecoveryTime': 0,
                            'AuraInterruptFlags': 0, 'InterruptFlags': 0,
                            'Attributes': 0x80000000, 'SpellVisual': 0, 'SpellIconID': SPR[2379][_dcc('SpellIconID')],
                            'SpellLevel': 0, 'BaseLevel': 0})

# ---------------------------------------------------------------- reliques : effets « Équipé » des artefacts (65600-65699)
# niveaux 10 à 60 ; une stat au budget d'un casque bleu du niveau (budget = niveau) : 14 points = 1 % de critique,
# 10 points = 1 % de toucher, 1,5 point = 1 défense, 1 point = 1,16 puissance des sorts, 1 point = 2 PA
from spellgen import Gen
AG = Gen(0, [])
RELIQUES_NIVEAUX = [10, 20, 30, 40, 50, 60]
RELIQUES_VAL = {
    'cc': lambda L: max(1, int(round(L / 14.0))), 'tm': lambda L: max(1, int(round(L / 10.0))),
    'def': lambda L: int(round(L / 1.5)), 'ps': lambda L: int(round(L * 1.16)), 'pa': lambda L: 2 * L}
_RB = {'cc': 7597, 'tm': 15464, 'def': 13384, 'ps': 9343, 'pa': 9142}
_RN = {'cc': ("Critique", "Augmente de $s1 % vos chances d'infliger un coup critique.", "Chances de coup critique augmentées de $s1 %."),
       'tm': ("Toucher", "Améliore de $s1 % vos chances de toucher.", "Chances de toucher augmentées de $s1 %."),
       'def': ("Défense", "Défense augmentée de $s1.", "Défense augmentée de $s1."),
       'ps': ("Puissance des sorts", "Augmente les dégâts et les soins produits par les sorts et effets magiques de $s1 au maximum.",
              "Dégâts et soins des sorts augmentés de $s1 au maximum."),
       'pa': ("Puissance d'attaque", "+$s1 à la puissance d'attaque.", "Puissance d'attaque augmentée de $s1.")}
RELIQUES_SORTS = {}
_rid = 65600
for _k in ('cc', 'tm', 'def', 'ps', 'pa'):
    for _val in sorted(set(RELIQUES_VAL[_k](L) for L in RELIQUES_NIVEAUX)):
        _st = {'EffectBasePoints1': _val - 1, 'EffectDieSides1': 1, 'EffectBaseDice1': 1, 'DurationIndex': DUR[-1]}
        if _v(_RB[_k], 'Effect2') == 6:
            _st.update({'EffectBasePoints2': _val - 1, 'EffectDieSides2': 1, 'EffectBaseDice2': 1})
        AG.add(_rid, _RB[_k], _RN[_k][0] + " %d" % _val, _RN[_k][1], tooltip=_RN[_k][2], family=False, sets=_st)
        RELIQUES_SORTS['%s%d' % (_k, _val)] = _rid
        _rid += 1
json.dump({'niveaux': RELIQUES_NIVEAUX, 'sorts': RELIQUES_SORTS,
           'valeurs': {k: {str(L): f(L) for L in RELIQUES_NIVEAUX} for k, f in RELIQUES_VAL.items()}},
          open('/home/claude/wow/classes/reliques_sorts.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('reliques : sorts', len(RELIQUES_SORTS))
