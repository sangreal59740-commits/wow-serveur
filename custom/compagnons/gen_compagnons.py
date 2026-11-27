# Génère tout ce qu'il faut aux compagnons (doc « Nouvelles classes et soutiens », 25/11) :
#  - SQL monde (compagnons.sql) : sorts des talents, des ultimes et des canaux de statistiques, pierres, armes, tenues, orbes, butin
#  - lignes Spell.dbc pour le client (compagnons_rows.json, ajoutées au patch par fr/build.py)
#  - données C++ du module (CompagnonsData.h) et données Lua de l'addon (Donnees.lua)
import json, re, sys, struct, subprocess, unicodedata
sys.path.insert(0, '/home/claude/wow/classes')
sys.path.insert(0, '/home/claude/wow/fr')
sys.path.insert(0, '/home/claude/wow/compagnons/gen')
from spellgen import Gen, q, esc, icon, visual, DUR, CAST, RADIUS, RANGE, SPR, dbc_col
from defs import DEFS, TENUES, ULT, RACE

OUT = '/home/claude/wow/compagnons/gen/'
SRV = '/home/claude/wow-serveur/modules/compagnons/src/'
ADDON = '/home/claude/wow/addons/Compagnons/'
DOC = json.load(open(OUT + 'doc2.json', encoding='utf-8'))
DOCN = {c['nom']: c for c in DOC}
IDX = json.load(open(OUT + 'index.json', encoding='utf-8'))
SRT = json.load(open('/home/claude/wow/classes/sorts_rows.json', encoding='utf-8'))
ROWS = {r[0]: r for r in SRT['spell']}           # sorts custom (lignes DBC)
for k, r in SPR.items():
    ROWS.setdefault(k, r)

RARETES = ['gris', 'vert', 'bleu', 'epique', 'legendaire']
PUISSANCE = [80, 90, 100, 110, 130]                # % des sorts par rapport à la classe
STUFF = [60, 80, 100, 120, 140]                    # % du stuff bleu
PRIX = [500, 1000, 2000, 4000, 6000]
DEUX_MAINS = {'m2', 'e2', 'h2', 'bat', 'hast'}

# ======================================================================== rangs des sorts (chaînes)
NEXT = {}
for sid, prev, first, rk in [tuple(int(x) for x in r) for r in q("SELECT spell_id, prev_spell, first_spell, `rank` FROM spell_chain")]:
    if prev:
        NEXT[prev] = sid
for m in re.finditer(r"INSERT INTO spell_chain \(spell_id, prev_spell, first_spell, `rank`, req_spell\) VALUES \((\d+), (\d+), (\d+), (\d+), 0\);",
                     open('/home/claude/wow/classes/sorts.sql', encoding='utf-8').read()):
    sid, prev = int(m.group(1)), int(m.group(2))
    if prev:
        NEXT[prev] = sid
from dbc import DBC as _DBC
for _r in _DBC('/home/claude/wow/classes/out/SkillLineAbility.dbc').rows:
    if _r[8] and _r[2] not in NEXT and IDX['names'].get(str(_r[2]), [''])[0] == IDX['names'].get(str(_r[8]), ['?'])[0]:
        NEXT[_r[2]] = _r[8]
PREV = {v: k for k, v in NEXT.items()}

def level_of(sid):
    r = ROWS.get(sid)
    return r[dbc_col('SpellLevel')] if r else 0

def chain(first):
    while first in PREV:
        first = PREV[first]
    out, s = [], first
    while s:
        out.append((s, max(1, level_of(s))))
        s = NEXT.get(s)
    return out

def fr_name(sid):
    return IDX['names'].get(str(sid), ['?'])[0]

def resolve(cls, name):
    ids = IDX['byclass'].get(str(cls), {}).get(name.lower())
    if not ids:
        # sort appris par talent : rang 1 du talent de ce nom
        global TALDBC
        if TALDBC is None:
            TALDBC = _DBC('/home/claude/wow/classes/out/Talent.dbc').rows
        for t in TALDBC:
            if t[4] and fr_name(t[4]).lower() == name.lower():
                ids = [t[4]]
                break
    if not ids:
        raise SystemExit('sort introuvable : %s (classe %d)' % (name, cls))
    return chain(min(ids, key=lambda i: (level_of(i), i)))[0][0]

TALDBC = None
# échanges de sorts de la spé Corrompu (le module classes remplace les soins par leur version corrompue)
CD = open('/home/claude/wow-serveur/modules/classes/src/ClassesData.h', encoding='utf-8').read()
def carr(name):
    m = re.search(r'static const uint32_t %s\[\] = \{ ([^}]*) \}' % name, CD)
    return [int(x) for x in m.group(1).split(', ')] if m else []
SWAP = dict(zip(carr('Q4_SRC'), carr('Q4_HEAL')))

# ======================================================================== talents de la vraie classe (clés des mécaniques)
TALDBC = None
def talent_rank_spell(name, rank):
    # recherche par nom dans les sorts de talents générés (classes custom et 4es spés) puis dans Spell.dbc
    cands = [r[0] for r in SRT['spell'] if r[120] == name]
    if not cands:
        cands = [int(k) for k, v in IDX['names'].items() if v[0] == name]
    talents = set()
    sys.path.insert(0, '/home/claude/wow/fr')
    from dbc import DBC
    global TALDBC
    if TALDBC is None:
        TALDBC = DBC('/home/claude/wow/classes/out/Talent.dbc').rows
    for t in TALDBC:
        rk = [x for x in t[4:13] if x]
        if any(c in rk for c in cands):
            if rank <= len(rk):
                return rk[rank - 1]
            return rk[-1]
    if cands:
        return min(cands)
    raise SystemExit('talent introuvable : ' + name)

# ======================================================================== canaux de statistiques (une aura cachée par canal)
# (clé, aura, misc, nom)
CANAUX = [('degats', 79, 127, "Dégâts"), ('soins', 136, 0, "Soins"), ('pv', 133, 0, "Points de vie"),
          ('endu_pct', 137, 2, "Endurance"), ('int_pct', 137, 3, "Intelligence"), ('armure_pct', 101, 1, "Armure"),
          ('menace', 10, 127, "Menace"), ('crit', 52, 0, "Critique"), ('crit_sorts', 57, 127, "Critique des sorts"),
          ('esquive', 49, 0, "Esquive"), ('parade', 47, 0, "Parade"), ('blocage', 51, 0, "Blocage"),
          ('subis', 87, 127, "Dégâts subis"), ('subis_mag', 87, 126, "Dégâts magiques subis"), ('cout', 72, 127, "Coût des sorts"),
          ('hate', 138, 0, "Vitesse d'attaque"), ('hate_dist', 140, 0, "Vitesse de tir"), ('incant', 65, 0, "Vitesse d'incantation"),
          ('resist', 22, 126, "Résistances"), ('epines', 15, 3, "Épines"), ('ombre', 79, 32, "Dégâts d'Ombre"),
          ('sacre', 79, 2, "Dégâts du Sacré"), ('givre', 79, 16, "Dégâts de Givre"), ('regen_combat', 134, 0, "Régénération en combat"),
          ('regen_pct', 110, 3, "Régénération"), ('rage_pct', 110, 1, "Rage"), ('recul', 149, 0, "Recul"),
          ('stat_for', 29, 0, "Force"), ('stat_agi', 29, 1, "Agilité"), ('stat_endu', 29, 2, "Endurance"), ('stat_int', 29, 3, "Intelligence"),
          ('pa', 99, 0, "Puissance d'attaque"), ('pa_dist', 124, 0, "Puissance d'attaque à distance"), ('ps', 13, 126, "Puissance des sorts"),
          ('soin_bonus', 135, 0, "Bonus aux soins"), ('defense', 30, 95, "Défense"), ('armure', 22, 1, "Armure"),
          ('toucher', 54, 0, "Toucher"), ('toucher_sorts', 55, 0, "Toucher des sorts"), ('crit_degats', 163, 127, "Dégâts des critiques")]
CAN = {k: i for i, (k, a, m, n) in enumerate(CANAUX)}
# effets spéciaux codés dans le module : (clé)
SPECIAUX = ['volvie', 'mana_coup', 'combo', 'poison', 'bete_soin', 'ferveur', 'cible_etourdie', 'cible_basse', 'elite', 'marquee',
            'fils2', 'pacte']
SPE = {k: i for i, k in enumerate(SPECIAUX)}

GEN = Gen(0, [])
SID = [46000]
def nid():
    SID[0] += 1
    return SID[0] - 1
AFFECT = []                          # (sort, effet, masque)
PASSIF = {'Attributes': 0x40 | 0x80 | 0x100, 'AttributesEx3': 0x100000, 'DurationIndex': DUR[-1], 'CastingTimeIndex': 1,
          'RecoveryTime': 0, 'Category': 0, 'CategoryRecoveryTime': 0, 'ManaCost': 0, 'ManaCostPercentage': 0, 'PowerType': 0,
          'SpellLevel': 0, 'BaseLevel': 0, 'MaxLevel': 0, 'ProcFlags': 0, 'ProcChance': 101, 'ProcCharges': 0, 'StackAmount': 0,
          'Stances': 0, 'StancesNot': 0, 'Reagent1': 0, 'ReagentCount1': 0, 'EquippedItemClass': -1, 'EquippedItemSubClassMask': 0,
          'StartRecoveryTime': 0, 'StartRecoveryCategory': 0, 'TargetAuraState': 0, 'CasterAuraState': 0, 'SpellVisual': 0,
          'SpellFamilyName': 0, 'SpellFamilyFlags': 0}

def eff(n, effect=0, aura=0, misc=0, bp=0, target=1, **extra):
    d = {'Effect%d' % n: effect, 'EffectApplyAuraName%d' % n: aura, 'EffectMiscValue%d' % n: misc, 'EffectBasePoints%d' % n: bp - 1 if effect else 0,
         'EffectDieSides%d' % n: 1 if effect else 0, 'EffectImplicitTargetA%d' % n: target if effect else 0, 'EffectImplicitTargetB%d' % n: 0,
         'EffectRealPointsPerLevel%d' % n: 0, 'EffectBonusCoefficient%d' % n: 0, 'EffectRadiusIndex%d' % n: 0, 'EffectAmplitude%d' % n: 0,
         'EffectTriggerSpell%d' % n: 0, 'EffectChainTarget%d' % n: 0, 'EffectItemType%d' % n: 0}
    for k, v in extra.items():
        d['Effect%s%d' % (k, n)] = v
    return d

def merge(*ds):
    o = {}
    for d in ds:
        o.update(d)
    return o

CANAL_ID = []
for k, a, m, n in CANAUX:
    sid = nid()
    GEN.add(sid, 12042, "Compagnon : " + n, "", family=False, sets=merge(PASSIF, eff(1, 6, a, m, 1), eff(2), eff(3), {'SpellIconID': icon(12042)}))
    CANAL_ID.append(sid)

# sort de dégâts supplémentaires (bonus conditionnels des talents), un par école
EXTRA = []
for school in range(7):
    sid = nid()
    GEN.add(sid, 585, "Compagnon : coup", "", family=False,
            sets=merge(PASSIF, {'Attributes': 0x100, 'AttributesEx3': 0, 'School': school, 'DurationIndex': 0, 'DmgClass': 1,
                                'RangeIndex': RANGE[100]}, eff(1, 2, 0, 0, 1, target=6), eff(2), eff(3)))
    EXTRA.append(sid)

# ======================================================================== lecture des talents
def num(s):
    return float(s.replace(',', '.').replace(' ', ''))

def spell_family(sid):
    r = ROWS[sid]
    return r[160], (r[161] & 0xffffffff) | ((r[162] & 0xffffffff) << 32)

def mod_spell(name, sid_cible, typ, flat, cname):
    fam, mask = spell_family(sid_cible)
    if not mask:
        return None
    sid = nid()
    GEN.add(sid, 12042, cname, "", family=False,
            sets=merge(PASSIF, {'SpellFamilyName': fam, 'SpellFamilyFlags': 0},
                       eff(1, 6, 107 if flat else 108, typ, 1), eff(2), eff(3), {'SpellIconID': ROWS[sid_cible][117]}))
    AFFECT.append((sid, 0, mask))
    return sid

def find_spell(c, text):
    """sort du compagnon cité dans un texte (nom le plus long qui y apparaît)"""
    best = None
    for n, sid in c['sorts_ids'] + c.get('extra', []):
        if n.lower() in text.lower() and (best is None or len(n) > len(best[0])):
            best = (n, sid)
    return best

CASTER = {'int'}

def talent_effects(c, pal, nom, txt):
    """-> liste d'effets (genre, a, b, valeur par rang) : ('canal', idx, pet, v) / ('mod', sort, 0, v) / ('special', idx, 0, v)"""
    t = txt.strip()
    m = re.search(r'([+-]?\d+(?:,\d+)?) ?(%|s|m)?\s*$', t)
    v = num(m.group(1)) if m else 0
    unit = m.group(2) if m else ''
    low = t.lower()
    pet = any(w in low for w in ('familier', 'invocation', 'bêtes', 'fantôme', 'abomination'))
    def canal(k, val=None):
        return [('canal', CAN[k], 1 if pet else 0, val if val is not None else v)]
    # sort précis : « Nom +x % », « incantation de Nom -0,1 s », « Nom +1 s », « recharge de Nom -1 s »
    sp = find_spell(c, t) or find_spell(c, nom)
    if sp and not pet:
        n_sp, sid = sp
        if 'incantation' in low:
            r = mod_spell(nom, sid, 10, True, nom)
            return [('mod', r, 0, int(round(v * 1000)))] if r else canal('incant', 3)
        if 'recharge' in low:
            r = mod_spell(nom, sid, 11, True, nom)
            return [('mod', r, 0, int(round(v * 1000)))] if r else [('canal', CAN['hate'], 0, 1), ('canal', CAN['incant'], 0, 1)]
        if unit == 's':
            r = mod_spell(nom, sid, 1, True, nom)
            return [('mod', r, 0, int(round(v * 1000)))] if r else [('canal', CAN['degats'], 0, 1)]
        if 'coups de grâce' in low or 'critique' in low:
            r = mod_spell(nom, sid, 7, True, nom)
            return [('mod', r, 0, v)] if r else canal('crit')
        r = mod_spell(nom, sid, 0, False, nom)
        if r:
            return [('mod', r, 0, v)]
        # sort sans masque de famille : bonus général réduit
        return [('canal', CAN['soins' if c['role'] == 1 else 'degats'], 0, max(1, int(v // 2)))]
    if t.startswith('incantation') and not sp:
        return [('canal', CAN['incant'], 0, int(v * 20))]          # -0,05 s environ 2 % d'un sort de 2,5 s
    if 'pacte' in low:
        return [('special', SPE['pacte'], 0, 1)]
    if 'poison' in low:
        return [('special', SPE['poison'], 0, v)]
    if 'mana par coup reçu' in low:
        return [('special', SPE['mana_coup'], 0, v)]
    if 'point de combo' in low:
        return [('special', SPE['combo'], 0, v)]
    if "chances d'empoisonner" in low:
        return [('special', SPE['poison'], 0, v)]
    if 'critique d' in low and 'bête' in low:
        return [('special', SPE['bete_soin'], 0, v)]
    if 'ferveur' in low:
        return [('special', SPE['ferveur'], 0, v)]
    if 'étourdie' in low:
        return [('special', SPE['cible_etourdie'], 0, v)]
    if 'sous 30' in low:
        return [('special', SPE['cible_basse'], 0, v)]
    if 'élites' in low:
        return [('special', SPE['elite'], 0, v)]
    if 'marquée' in low:
        return [('special', SPE['marquee'], 0, v)]
    if '2 fils' in low:
        return [('special', SPE['fils2'], 0, v)]
    if 'rendus en pv' in low:
        return [('special', SPE['volvie'], 0, v)]
    if 'renvoyés' in low:
        return canal('epines')
    if 'rayon' in low:
        return [('canal', CAN['menace'], 0, 2)]
    if 'recul' in low:
        return [('canal', CAN['recul'], 0, abs(v) * 14)]
    if 'dégâts des critiques' in low:
        return canal('crit_degats')
    if "dégâts d'ombre" in low:
        return canal('ombre')
    if 'dégâts du sacré' in low:
        return canal('sacre')
    if 'dégâts de givre' in low:
        return canal('givre')
    if 'magiques subis' in low:
        return canal('subis_mag')
    if 'subis' in low:
        return canal('subis')
    if 'esquive et parade' in low:
        return canal('esquive') + canal('parade')
    for w, k in (('esquive', 'esquive'), ('parade', 'parade'), ('blocage', 'blocage'), ('menace', 'menace'), ('armure', 'armure_pct'),
                 ('résistances', 'resist'), ('coût', 'cout'), ('mana en combat', 'regen_combat'), ('énergie', 'regen_pct'),
                 ('rage', 'rage_pct'), ('endurance', 'endu_pct'), ('mana', 'int_pct'), ('pv', 'pv')):
        if w in low:
            return canal(k)
    if 'critique des soins' in low or 'critique des sorts' in low:
        return canal('crit_sorts')
    if 'critique' in low:
        return canal('crit_sorts' if c['stat'] in CASTER and c['role'] != 2 else 'crit')
    if "vitesse d'incantation" in low:
        return canal('incant')
    if 'vitesse de tir' in low:
        return canal('hate_dist')
    if 'vitesse' in low:
        if c['stat'] in CASTER and not pet:
            return canal('incant')
        return canal('hate') + ([] if pet else canal('hate_dist'))
    if 'soins' in low or 'soin de zone' in low:
        return canal('soins')
    if 'dégâts' in low:
        return canal('degats')
    raise SystemExit('effet de talent non reconnu : %s / %s / %s' % (c['nom'], nom, t))

# ======================================================================== ultimes
ECOLE_BASE = {0: (1680, 12294), 1: (20473, 26573), 2: (2120, 133), 3: (8045, 403), 4: (122, 116), 5: (17877, 686), 6: (1449, 3044)}
ECOLE_FR = {0: "physiques", 1: "du Sacré", 2: "de Feu", 3: "de Nature", 4: "de Givre", 5: "d'Ombre", 6: "d'Arcanes"}

def lin(v60):
    return int(round(v60 * 0.05)) - 1, v60 * 0.95 / 60.0

def ult_spells(c, u):
    """-> (sort principal, [sorts secondaires lancés sur soi], sort de soin de groupe ou 0, description)"""
    nom = c['ultime_nom']
    zone = u['cible']
    r = RADIUS.get(u.get('r', 8), RADIUS[8])
    desc = c['ultime_txt']
    main = nid()
    sets = merge(PASSIF, {'Attributes': 0x10000, 'AttributesEx3': 0, 'DurationIndex': 0, 'RecoveryTime': 180000, 'DmgClass': 2,
                          'RangeIndex': RANGE[40] if zone in ('cible', 'zone_cible', 'chaine') else RANGE[0], 'SpellLevel': 1, 'BaseLevel': 1,
                          'MaxLevel': 60, 'SpellIconID': icon(12042)})
    tA, tB = {'cible': (6, 0), 'zone': (22, 15), 'zone_cible': (53, 16), 'chaine': (6, 0)}[zone]
    if 'arme' in u:
        base = 1680 if zone == 'zone' else 12294
        sets.update({'School': 0, 'DmgClass': 2, 'SpellIconID': icon(base), 'SpellVisual': visual(base)})
        sets.update(eff(1, 121 if zone == 'zone' else 31, 0, 0, u['arme'], target=tA, ImplicitTargetB=tB, RadiusIndex=r if tB else 0))
        sets['RangeIndex'] = RANGE[0] if zone == 'zone' else RANGE[5]
    else:
        school, v60 = u['sort']
        base = ECOLE_BASE[school][0 if zone == 'zone' else 1]
        b, pl = lin(v60)
        sets.update({'School': school, 'SpellIconID': icon(base), 'SpellVisual': visual(base)})
        sets.update(eff(1, 2, 0, 0, 1, target=tA, ImplicitTargetB=tB, RadiusIndex=r if tB else 0))
        sets.update({'EffectBasePoints1': b, 'EffectDieSides1': 1, 'EffectRealPointsPerLevel1': pl, 'EffectBonusCoefficient1': 0.5})
        if zone == 'chaine':
            sets['EffectChainTarget1'] = u.get('n', 3)
    # contrôle sur les mêmes cibles
    n2 = 2
    if u.get('stun'):
        sets.update(eff(n2, 6, 12, 0, 1, target=tA, ImplicitTargetB=tB, RadiusIndex=r if tB else 0))
        sets['DurationIndex'] = DUR[u['stun'] * 1000]
        n2 += 1
    elif u.get('ralenti'):
        sets.update(eff(n2, 6, 33, 0, -u['ralenti'], target=tA, ImplicitTargetB=tB, RadiusIndex=r if tB else 0))
        sets['DurationIndex'] = DUR[6000]
        n2 += 1
    elif u.get('saigne'):
        b, pl = lin(u['saigne'] / 5)
        sets.update(eff(n2, 6, 3, 0, 1, target=tA, Amplitude=3000))
        sets.update({'EffectBasePoints%d' % n2: b, 'EffectRealPointsPerLevel%d' % n2: pl})
        sets['DurationIndex'] = DUR[15000]
        n2 += 1
    for n in range(n2, 4):
        sets.update(eff(n))
    GEN.add(main, base, nom, desc, family=False, sets=sets)
    extra = []
    # provocation des ennemis touchés
    if u.get('taunt'):
        sid = nid()
        GEN.add(sid, 1161, nom, "", family=False,
                sets={'RecoveryTime': 0, 'Category': 0, 'CategoryRecoveryTime': 0, 'ManaCost': 0, 'ManaCostPercentage': 0, 'PowerType': 0,
                      'Stances': 0, 'StancesNot': 0, 'EffectRadiusIndex1': r, 'DurationIndex': DUR[u['taunt'] * 1000], 'StartRecoveryTime': 0})
        extra.append(sid)
    # bonus sur soi
    d = u.get('dur', 10) * 1000
    effs = []
    for b in u.get('buff', []):
        k = b[0]
        if k == 'subis': effs.append((87, 127, b[1]))
        elif k == 'degats': effs.append((79, 127, b[1]))
        elif k == 'vitesse': effs.append((138, 0, b[1])); effs.append((140, 0, b[1]))
        elif k == 'crit': effs.append((52, 0, b[1]))
        elif k == 'ecole': effs.append((79, b[1], b[2]))
        elif k == 'taille': effs.append((61, 0, b[1]))
        elif k == 'immun': effs.append((77, 12, 1)); effs.append((77, 5, 1))
        elif k == 'bouclier': effs.append((69, 127, 0))          # valeur fixée par le module (15 % des PV)
        elif k in ('betes', 'invoc', 'fantomes', 'invoc_subis', 'volvie', 'energie', 'demon'):
            effs.append((4, 0, b[1]))                               # effet factice : le module applique le bonus
    for i in range(0, len(effs), 3):
        sid = nid()
        part = effs[i:i + 3]
        s2 = merge(PASSIF, {'Attributes': 0, 'AttributesEx3': 0, 'DurationIndex': DUR.get(d, DUR[10000]), 'SpellIconID': icon(12042)})
        for j in range(3):
            if j < len(part):
                a, misc, val = part[j]
                s2.update(eff(j + 1, 6, a, misc, val))
            else:
                s2.update(eff(j + 1))
        GEN.add(sid, 12042, nom, desc, tooltip=nom, family=False, sets=s2)
        extra.append(sid)
    soin = 0
    if u.get('soin'):
        pct, sec = u['soin']
        soin = nid()
        ticks = max(1, sec)
        GEN.add(soin, 8936, nom, desc, tooltip="Récupère des points de vie.", family=False,
                sets=merge(PASSIF, {'Attributes': 0, 'AttributesEx3': 0, 'DurationIndex': DUR.get(sec * 1000, DUR[1000]), 'SpellIconID': icon(8936),
                                    'SpellVisual': visual(8936)},
                           eff(1, 6, 20, 0, max(1, int(round(pct / ticks))), target=20, Amplitude=1000), eff(2), eff(3)))
    return main, extra, soin

# ======================================================================== objets
ITEM = [1001000]
def iid():
    ITEM[0] += 1
    return ITEM[0] - 1

ITEM_COLS = [r[0] for r in q("describe item_template")]
ITEMS = []                                 # (entrée, base, {colonne: valeur})
def item(base, **sets):
    e = iid()
    ITEMS.append((e, base, sets))
    return e

ARMES = {  # genre : (classe, sous-classe, InventoryType, vitesse ms, 2 mains, modèle par défaut)
    'm1': (2, 4, 13, 2600, False, 23618), 'e1': (2, 7, 13, 2600, False, 8090), 'h1': (2, 0, 13, 2600, False, 19137),
    'd': (2, 15, 13, 1800, False, 31864), 'm2': (2, 5, 17, 3400, True, 32162), 'e2': (2, 8, 17, 3400, True, 20185),
    'h2': (2, 1, 17, 3400, True, 23904), 'bat': (2, 10, 17, 3000, True, 20298), 'hast': (2, 6, 17, 3400, True, 22792),
    'fusil': (2, 3, 26, 2800, False, 28636), 'arc': (2, 2, 15, 2800, False, 30926), 'bouclier': (4, 6, 14, 0, False, 30993),
}
ARME_NOM = {'m1': 'Masse', 'e1': 'Épée', 'h1': 'Hache', 'd': 'Dague', 'm2': 'Grande masse', 'e2': 'Grande épée', 'h2': 'Grande hache',
            'bat': 'Bâton', 'hast': "Arme d'hast", 'fusil': 'Fusil', 'arc': 'Arc', 'bouclier': 'Bouclier'}
BRACKETS = list(range(1, 61, 5))           # niveaux requis 1, 6, ..., 56
ARME_ITEMS = {}                            # (genre, modèle) -> [entrée par tranche]

def arme(genre, disp):
    key = (genre, disp)
    if key in ARME_ITEMS:
        return ARME_ITEMS[key]
    cls, sub, inv, spd, deux, _d = ARMES[genre]
    ids = []
    for lv in BRACKETS:
        L = lv + 4
        sets = dict(name="%s de compagnon" % ARME_NOM[genre], class_=cls, subclass=sub, InventoryType=inv, displayid=disp, Quality=3,
                    ItemLevel=L, RequiredLevel=lv, bonding=1, SellPrice=0, BuyPrice=0, armor=0, MaxDurability=0)
        if cls == 2:
            dps = (50.0 if deux else 38.0) * (L + 3) / 63.0
            avg = dps * spd / 1000.0
            sets.update(dmg_min1=round(avg * 0.8), dmg_max1=round(avg * 1.2), delay=spd, dmg_type1=0)
        ids.append(item(19019 if cls == 2 else 1168, **sets))
    ARME_ITEMS[key] = ids
    return ids

TENUE_ITEMS = {}
SLOT_INV = {1: 'Heaume', 3: 'Épaulières', 5: 'Plastron', 20: 'Robe', 9: 'Brassards', 10: 'Gants', 6: 'Ceinture', 7: 'Jambières', 8: 'Bottes'}
def tenue(cle, nom):
    out = []
    for src in TENUES[cle]:
        r = q("SELECT InventoryType, displayid FROM item_template WHERE entry=%d" % src)[0]
        inv, disp = int(r[0]), int(r[1])
        out.append(item(src, name="%s de %s" % (SLOT_INV.get(inv, 'Pièce'), nom), class_=4, subclass=1, displayid=disp, Quality=4,
                        RequiredLevel=1, ItemLevel=1, bonding=1, SellPrice=0, BuyPrice=0, armor=0, MaxDurability=0, InventoryType=inv))
    return out

# pierres d'invocation (une par compagnon) : le module intercepte l'utilisation (le sort n'est jamais lancé)
PIERRE_SORT = 46990
GEN.add(PIERRE_SORT, 8690, "Appel du compagnon", "Appelle ton compagnon à tes côtés, ou le renvoie s'il est déjà là.", family=False,
        sets=merge(PASSIF, {'Attributes': 0x10000, 'AttributesEx3': 0, 'DurationIndex': 0, 'CastingTimeIndex': 1, 'RangeIndex': RANGE[0],
                            'SpellIconID': icon(8690), 'SpellVisual': 0}, eff(1, 3, 0, 0, 1), eff(2), eff(3)))
def pierre(c):
    return item(6948, name="Pierre de %s" % c['nom'], displayid=6418, Quality=[0, 2, 3, 4, 5][c['r']], bonding=1, RequiredLevel=1,
                ItemLevel=1, SellPrice=0, BuyPrice=0, stackable=1, maxcount=1, description="Invoque ou renvoie %s." % c['nom'],
                spellid_1=PIERRE_SORT, spelltrigger_1=0, spellcooldown_1=1000)

# orbes du compagnon : 5 couleurs, un objet par niveau 10 à 60 (stats doublées du doc : 2x le budget d'origine)
ORBES = [('bleue', "Orbe bleue", 'tank'), ('rouge', "Orbe rouge", 'sorts'), ('verte', "Orbe verte", 'agi'),
         ('noire', "Orbe noire", 'for'), ('blanche', "Orbe blanche", 'soin')]
ORBE_DISP = [7798, 7805, 7807, 7812, 7800]
ORBE_ITEMS = {}
def orbe_stats(couleur, L):
    f = L / 60.0
    pct = max(1, int(round(2 * f))) if L >= 15 else 1
    if couleur == 'bleue':
        return [('stat_endu', round(40 * f)), ('defense', round(20 * f)), ('toucher', pct), ('resist', round(20 * f))]
    if couleur == 'rouge':
        return [('stat_int', round(30 * f)), ('stat_endu', round(16 * f)), ('crit_sorts', pct), ('ps', round(40 * f))]
    if couleur == 'verte':
        return [('stat_agi', round(30 * f)), ('stat_endu', round(16 * f)), ('toucher', pct), ('pa', round(60 * f))]
    if couleur == 'noire':
        return [('stat_for', round(30 * f)), ('stat_endu', round(16 * f)), ('toucher', pct), ('pa', round(60 * f))]
    return [('stat_int', round(30 * f)), ('stat_endu', round(16 * f)), ('crit_sorts', pct), ('soin_bonus', round(70 * f))]

STAT_FR = {'stat_endu': 'Endurance', 'defense': 'Défense', 'toucher': 'Toucher', 'resist': 'Résistance à toutes les magies',
           'stat_int': 'Intelligence', 'crit_sorts': 'Critique des sorts', 'ps': 'Puissance des sorts', 'stat_agi': 'Agilité',
           'pa': "Puissance d'attaque", 'stat_for': 'Force', 'soin_bonus': 'Soins'}
for ci, (cle, nom, _r) in enumerate(ORBES):
    ORBE_ITEMS[cle] = []
    for L in range(10, 61):
        st = orbe_stats(cle, L)
        txt = ", ".join(("+%d %%" % v if k in ('toucher', 'crit_sorts') else "+%d" % v) + " " + STAT_FR[k] for k, v in st)
        ORBE_ITEMS[cle].append(item(7811, name="%s du compagnon" % nom, displayid=ORBE_DISP[ci], Quality=3, ItemLevel=L, RequiredLevel=1,
                                    bonding=1, SellPrice=L * 100, BuyPrice=0, stackable=1, maxcount=0, class_=15, subclass=0, InventoryType=0,
                                    description="Pour un compagnon seulement : %s." % txt, spellid_1=0, spelltrigger_1=0))

# ======================================================================== compagnons
CLS_ARMURE = {1: 'plaques', 2: 'plaques', 3: 'mailles', 4: 'cuir', 5: 'tissu', 6: 'tissu', 7: 'mailles', 8: 'tissu', 9: 'tissu',
              10: 'cuir', 11: 'cuir', 12: 'tissu', 13: 'cuir', 14: 'plaques'}
ARMURE60 = {'tissu': 600, 'cuir': 1300, 'mailles': 2700, 'plaques': 4800}

def ascii_letters(s):
    s = unicodedata.normalize('NFD', s)
    return ''.join(ch for ch in s if ch.isalpha() and ord(ch) < 128)

ALLIANCE = {1, 3, 4, 7}
CLS_RACES = {int(c): [int(x) for x in r.split(',')] for c, r in q("SELECT class, GROUP_CONCAT(race) FROM playercreateinfo GROUP BY class")}

COMP = []
for i, d in enumerate(DEFS):
    doc = DOCN[d['doc']]
    c = dict(d)
    c['id'] = i + 1
    c['r'] = RARETES.index(doc['rarete'])
    c['cls'] = doc['cls']
    c['spe_txt'] = doc['spe']
    c['role_txt'] = doc['role']
    noms = d.get('sorts') or [n for n, _ in doc['res']]
    c['sorts_ids'] = [(n, resolve(c['cls'], n)) for n in noms]
    c['extra'] = d.get('extra', [])
    # sorts autorisés : tous les rangs, plus les versions corrompues (spé Corrompu)
    allowed = []
    for n, sid in c['sorts_ids']:
        for s, lv in chain(sid):
            allowed.append((s, lv))
            if s in SWAP:
                allowed.append((SWAP[s], lv))
    c['allowed'] = allowed
    c['cles_ids'] = [talent_rank_spell(n, r) for n, r in d.get('cles', [])]
    # races : modèle de PNJ -> une race autorisée de chaque faction ; sinon race naturelle (l'autre faction passe par le changement de faction)
    races = CLS_RACES[c['cls']]
    if d.get('npc'):
        disp, scale = [x for x in q("SELECT DisplayId1, Scale FROM creature_template WHERE Entry=%d" % d['npc'])[0]]
        c['display'] = int(disp)
        c['scale'] = min(1.2, float(scale)) if float(scale) > 0 else 1.0
        c['raceA'] = next(r for r in races if r in ALLIANCE)
        c['raceH'] = next(r for r in races if r not in ALLIANCE)
        c['genre'] = 0
    else:
        c['display'] = 0
        c['scale'] = 1.0
        c['raceA'] = c['raceH'] = RACE[d['race']]
        c['genre'] = d.get('genre', 0)
        assert c['raceA'] in races, (c['nom'], races)
    # armes (une liste d'entrées par tranche de niveau, par emplacement)
    c['armes_ids'] = []
    for a in d['armes']:
        g, disp = (a if isinstance(a, tuple) else (a, ARMES[a][5]))
        c['armes_ids'].append((g, arme(g, disp)))
    c['tenue_ids'] = tenue(d['tenue'], d['nom']) if d.get('tenue') else []
    c['pierre'] = pierre(c)
    # talents
    tal = []
    for k, (pal, nom, txt) in enumerate(doc['tal']):
        txt = d.get('tal', {}).get(k, txt)
        tal.append(dict(pal=pal, nom=nom, txt=doc['tal'][k][2], effets=talent_effects(c, pal, nom, txt)))
    c['talents'] = tal
    # ultime
    un, ut = doc['ultime'].split(' : ', 1)
    c['ultime_nom'], c['ultime_txt'] = un, ut
    c['ult'] = ult_spells(c, ULT[d['cle']])
    c['armure'] = CLS_ARMURE[c['cls']]
    COMP.append(c)
    print('%2d %-12s %-10s sorts %d (%d rangs) clés %s talents %s' % (c['id'], c['cle'], RARETES[c['r']], len(c['sorts_ids']), len(allowed),
          c['cles_ids'], [len(t['effets']) for t in tal]))

# ======================================================================== sorties
# --- SQL monde
L = ["-- Généré par wow/compagnons/gen/gen_compagnons.py : compagnons (sorts, objets, butin des orbes)"]
L += GEN.sql(46000, 46999)
L.append("DELETE FROM spell_affect WHERE entry BETWEEN 46000 AND 46999;")
for sid, e, m in AFFECT:
    L.append("INSERT INTO spell_affect (entry, effectId, SpellFamilyMask) VALUES (%d, %d, %d);" % (sid, e, m))
L.append("DELETE FROM item_template WHERE entry BETWEEN 1001000 AND 1009999;")
L.append("DROP TEMPORARY TABLE IF EXISTS tmp_it;")
L.append("CREATE TEMPORARY TABLE tmp_it LIKE item_template;")
STAT_ZERO = ", ".join("stat_type%d=0, stat_value%d=0" % (n, n) for n in range(1, 11))
SPELL_ZERO = ", ".join("spellid_%d=0, spelltrigger_%d=0" % (n, n) for n in range(2, 6))
for e, base, sets in ITEMS:
    L.append("INSERT INTO tmp_it SELECT * FROM item_template WHERE entry=%d;" % base)
    parts = ["entry=%d" % e, STAT_ZERO, SPELL_ZERO, "RandomProperty=0, itemset=0, holy_res=0, fire_res=0, nature_res=0, frost_res=0, shadow_res=0, arcane_res=0",
             "AllowableClass=-1, AllowableRace=-1, RequiredSkill=0, RequiredSkillRank=0, requiredspell=0, RequiredReputationFaction=0, "
             "RequiredReputationRank=0, startquest=0, lockid=0, PageText=0, area=0, Map=0, ScriptName='', Flags=0, block=0"]
    if 'description' not in sets:
        parts.append("description=''")
    for k, v in sets.items():
        col = 'class' if k == 'class_' else k
        parts.append("`%s`=%s" % (col, ("'%s'" % esc(v)) if isinstance(v, str) else v))
    L.append("UPDATE tmp_it SET %s WHERE entry=%d;" % (", ".join(parts), base))
L.append("INSERT INTO item_template SELECT * FROM tmp_it;")
L.append("DROP TEMPORARY TABLE tmp_it;")
open(OUT + 'compagnons.sql', 'w', encoding='utf-8').write("\n".join(L) + "\n")

# --- client
json.dump({'spell': GEN.dbc_rows()}, open(OUT + 'compagnons_rows.json', 'w', encoding='utf-8'), ensure_ascii=False)

# --- C++
H = ["// Généré par wow/compagnons/gen/gen_compagnons.py : ne pas modifier à la main", "#pragma once", "#include <cstdint>", "",
     "namespace compagnons_data", "{"]
H.append("    static const uint32_t CANAL_SORT[] = { %s };" % ", ".join(str(x) for x in CANAL_ID))
H.append("    static const uint32_t CANAUX_N = %d;" % len(CANAL_ID))
for k, i in CAN.items():
    H.append("    static const uint32_t CA_%s = %d;" % (k.upper(), i))
for k, i in SPE.items():
    H.append("    static const uint32_t SP_%s = %d;" % (k.upper(), i))
H.append("    static const uint32_t EXTRA_SORT[] = { %s };" % ", ".join(str(x) for x in EXTRA))
H.append("    static const int32_t PUISSANCE[] = { %s };" % ", ".join(str(x) for x in PUISSANCE))
H.append("    static const int32_t STUFF[] = { %s };" % ", ".join(str(x) for x in STUFF))
H.append("    static const uint32_t PRIX[] = { %s };" % ", ".join(str(x) for x in PRIX))
H.append("    struct EffetTalent { uint8_t genre; uint32_t a; uint8_t pet; int32_t valeur; };   // genre 1 canal, 2 sort modificateur, 3 spécial")
H.append("    struct Talent { uint8_t palier; const char* nom; uint8_t n; EffetTalent effets[3]; };")
H.append("    struct Sort { uint32_t id; uint8_t niveau; };")
H.append("    struct Compagnon")
H.append("    {")
H.append("        uint32_t id; const char* cle; const char* nom; uint8_t rarete, cls, tab, role, raceA, raceH, genre, stat, bonus, armure;")
H.append("        uint32_t display; float scale; uint32_t pierre; bool poison;")
H.append("        const Sort* sorts; uint32_t nSorts; const uint32_t* premiers; uint32_t nPremiers; const uint32_t* cles; uint32_t nCles;")
H.append("        const Talent* talents; uint32_t ultime; const uint32_t* ultExtra; uint32_t nUltExtra; uint32_t ultSoin; uint8_t ultCible;")
H.append("        uint32_t ultBuff;     // bonus géré par le module (0 aucun, 1 bêtes, 2 invocations, 3 fantômes, 4 dégâts subis des invocations, 5 vol de vie, 6 énergie, 7 démon, 8 bouclier)")
H.append("        int32_t ultBuffVal; uint32_t ultBuffDur; uint8_t ultFils; bool ultGeant;")
H.append("        const uint32_t* armes; uint32_t nArmes;   // par emplacement : 12 entrées (tranches de 5 niveaux)")
H.append("        const uint8_t* armesGenre; const uint32_t* tenue; uint32_t nTenue;")
H.append("    };")
STATK = {'for': 0, 'agi': 1, 'int': 3}
BONUSK = {'pa': 0, 'ps': 1, 'soin': 2, 'def': 3}
ARMK = {'tissu': 0, 'cuir': 1, 'mailles': 2, 'plaques': 3}
GENREK = {g: i for i, g in enumerate(ARMES)}
ULTB = {'betes': 1, 'invoc': 2, 'fantomes': 3, 'invoc_subis': 4, 'volvie': 5, 'energie': 6, 'demon': 7, 'bouclier': 8}
for c in COMP:
    k = c['cle'].upper()
    H.append("    static const Sort S_%s[] = { %s };" % (k, ", ".join("{%d, %d}" % (s, lv) for s, lv in c['allowed'])))
    H.append("    static const uint32_t P_%s[] = { %s };" % (k, ", ".join(str(s) for _, s in c['sorts_ids'])))
    H.append("    static const uint32_t K_%s[] = { %s };" % (k, ", ".join(str(s) for s in c['cles_ids']) or "0"))
    tl = []
    for t in c['talents']:
        effs = []
        for g, a, pet, v in t['effets'][:3]:
            effs.append("{%d, %d, %d, %d}" % ({'canal': 1, 'mod': 2, 'special': 3}[g], a, pet, int(round(v))))
        while len(effs) < 3:
            effs.append("{0, 0, 0, 0}")
        tl.append('{%d, "%s", %d, {%s}}' % (t['pal'], t['nom'].replace('"', '\\"'), min(3, len(t['effets'])), ", ".join(effs)))
    H.append("    static const Talent T_%s[] = { %s };" % (k, ", ".join(tl)))
    main, extra, soin = c['ult']
    H.append("    static const uint32_t U_%s[] = { %s };" % (k, ", ".join(str(x) for x in extra) or "0"))
    H.append("    static const uint32_t A_%s[] = { %s };" % (k, ", ".join(str(x) for _, ids in c['armes_ids'] for x in ids)))
    H.append("    static const uint8_t G_%s[] = { %s };" % (k, ", ".join(str(GENREK[g]) for g, _ in c['armes_ids'])))
    H.append("    static const uint32_t W_%s[] = { %s };" % (k, ", ".join(str(x) for x in c['tenue_ids']) or "0"))
H.append("    static const Compagnon COMPAGNONS[] =")
H.append("    {")
for c in COMP:
    k = c['cle'].upper()
    u = ULT[c['cle']]
    ub, ubv = 0, 0
    for b in u.get('buff', []):
        if b[0] in ULTB:
            ub, ubv = ULTB[b[0]], b[1] if len(b) > 1 else 0
    main, extra, soin = c['ult']
    ucible = {'cible': 0, 'zone': 1, 'zone_cible': 2, 'chaine': 3}[u['cible']]
    H.append('        { %d, "%s", "%s", %d, %d, %d, %d, %d, %d, %d, %d, %d, %d, %d, %sf, %d, %s, S_%s, %d, P_%s, %d, K_%s, %d, T_%s, %d, U_%s, %d, %d, %d, %d, %d, %d, %d, %s, A_%s, %d, G_%s, W_%s, %d },'
             % (c['id'], c['cle'], c['nom'].replace('"', '\\"'), c['r'], c['cls'], c['tab'], c['role'], c['raceA'], c['raceH'], c['genre'],
                STATK[c['stat']], BONUSK[c['bonus']], ARMK[c['armure']], c['display'], repr(float(c['scale'])), c['pierre'],
                'true' if c.get('poison') else 'false', k, len(c['allowed']), k, len(c['sorts_ids']), k, len(c['cles_ids']), k, main, k,
                len(extra), soin, ucible, ub, ubv, u.get('dur', 10) * 1000, u.get('fils', 0), 'true' if u.get('depuis') == 'geant' else 'false',
                k, len(c['armes_ids']), k, k, len(c['tenue_ids'])))
H.append("    };")
H.append("    static const uint32_t COMPAGNONS_N = %d;" % len(COMP))
# sorts de classe gardés même s'ils ne sont pas sur la fiche (buffs de service utilisés par l'IA des bots)
_CD = open('/home/claude/wow/classes/ClassesData.h', encoding='utf-8').read()
def _arr(n):
    m = re.search(r"static const uint32_t %s\[\] = \{ ([0-9, ]+) \};" % n, _CD)
    return [int(x) for x in m.group(1).split(',')] if m else []
IMPL = [(10, x) for x in _arr('BS_FAUVE') + _arr('S_BALLE_FEU')] + [(6, x) for x in _arr('BN_ARMURE')] + [(11, x) for x in _arr('BM_LIEN')]
H.append("    struct Implicite { uint8_t cls; uint32_t sort; };")
H.append("    static const Implicite IMPLICITE[] = { %s };" % ", ".join("{%d, %d}" % t for t in IMPL))
H.append("    static const uint32_t IMPLICITE_N = %d;" % len(IMPL))
H.append("    static const uint32_t PIERRE_SORT = %d;" % PIERRE_SORT)
H.append("    // orbes : couleur (0 bleue, 1 rouge, 2 verte, 3 noire, 4 blanche), niveau 10 à 60 -> entrée")
H.append("    static const uint32_t ORBE_PREMIER = %d;     // entrée = ORBE_PREMIER + couleur * 51 + (niveau - 10)" % ORBE_ITEMS['bleue'][0])
H.append("    static const uint32_t ORBE_DERNIER = %d;" % ORBE_ITEMS['blanche'][-1])
H.append("    static const uint32_t PIERRE_PREMIERE = %d, PIERRE_DERNIERE = %d;" % (COMP[0]['pierre'], COMP[-1]['pierre']))
H.append("}")
import os
os.makedirs(SRV, exist_ok=True)
open(SRV + 'CompagnonsData.h', 'w', encoding='utf-8').write("\n".join(H) + "\n")

# --- Lua (addon)
def lua(s):
    return '"%s"' % s.replace('\\', '\\\\').replace('"', '\\"')
A = ["-- Généré par gen_compagnons.py", "Compagnons_Donnees = {"]
for c in COMP:
    tl = ", ".join("{%d, %s, %s}" % (t['pal'], lua(t['nom']), lua(t['txt'])) for t in c['talents'])
    A.append("  [%d] = { cle = %s, nom = %s, nomComplet = %s, rarete = %d, classe = %d, spe = %s, role = %s, prix = %d, sorts = { %s }, talents = { %s }, ultime = %s, ultimeTxt = %s, pierre = %d, st = %d, bonus = %d, armure = %d, bouclier = %s }," % (
        c['id'], lua(c['cle']), lua(c['nom']), lua(c['doc']), c['r'], c['cls'], lua(c['spe_txt']), lua(c['role_txt']), PRIX[c['r']],
        ", ".join(lua(n) for n, _ in c['sorts_ids']), tl, lua(c['ultime_nom']), lua(c['ultime_txt']), c['pierre'],
        STATK[c['stat']], BONUSK[c['bonus']], ARMK[c['armure']], 'true' if any(g == 11 for g, _ in c['armes_ids']) else 'false'))
A.append("}")
os.makedirs(ADDON, exist_ok=True)
open(ADDON + 'Donnees.lua', 'w', encoding='utf-8').write("\n".join(A) + "\n")
print('sorts', len(GEN.spells), 'objets', len(ITEMS), 'affect', len(AFFECT))

# --- portail : articles de la boutique (catégorie Compagnons, type 2 = compagnon, item = identifiant du compagnon)
QUAL = ['commun', 'peu', 'rare', 'epique', 'legendaire']
RARN = ['Gris', 'Vert', 'Bleu', 'Épique', 'Légendaire']
ART = []
for c in COMP:
    ART.append({'id': 'cpg_%s' % c['cle'], 'categorie': 'Compagnons', 'nom': c['nom'],
                'desc': '%s (%s). Compagnon %s : %d sorts, talents et ultime. Il te suit, combat avec toi et monte de niveau avec toi.' % (
                    c['spe_txt'], c['role_txt'], RARN[c['r']].lower(), len(c['sorts_ids'])),
                'item': c['id'], 'type': 2, 'prix': PRIX[c['r']], 'qualite': QUAL[c['r']]})
json.dump(ART, open(OUT + 'compagnons_boutique.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
