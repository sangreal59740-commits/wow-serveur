# Équipement des groupes de compagnons (.bots groupe 1 à 5) : niveau 20, objets bleus obtenables (vert si aucun bleu),
# pas d'anneau, de bijou ni d'artefact. Sortie : choix20.json + bloc C++ (compagnons_data.inc)
import subprocess, json
NIV = 20
def q(sql):
    r = subprocess.run(['mysql', '-N', '--default-character-set=utf8', 'classicmangos', '-e', sql], capture_output=True, text=True)
    return [l.split('\t') for l in r.stdout.splitlines()]

src = set()
for t in ['creature_loot_template', 'gameobject_loot_template', 'reference_loot_template', 'item_loot_template', 'npc_vendor', 'npc_vendor_template']:
    src |= {int(r[0]) for r in q(f'SELECT DISTINCT item FROM {t}')}
cols = ','.join([f'RewChoiceItemId{i}' for i in range(1, 7)] + [f'RewItemId{i}' for i in range(1, 5)])
for r in q(f'SELECT {cols} FROM quest_template'):
    src |= {int(x) for x in r if x != '0'}

champs = ('entry,name,class,subclass,InventoryType,Quality,ItemLevel,RequiredLevel,AllowableClass,AllowableRace,armor,block,dmg_min1,dmg_max1,delay,'
          + ','.join(f'stat_type{i},stat_value{i}' for i in range(1, 11)) + ',RandomProperty,RequiredSkill,RequiredReputationFaction,spellid_1,spelltrigger_1,spellid_2,spelltrigger_2')
rows = q(f"""SELECT {champs} FROM item_template WHERE RequiredLevel <= {NIV} AND RequiredLevel >= {NIV - 8} AND ItemLevel <= {NIV + 12}
  AND Quality IN (2,3) AND class IN (2,4) AND RandomProperty = 0 AND RequiredSkill = 0 AND RequiredReputationFaction = 0
  AND name NOT LIKE '%Monster%' AND name NOT LIKE '%Test%' AND name NOT LIKE '%Deprecated%' AND name NOT LIKE '%[PH]%' AND entry < 990000""")
items = []
for r in rows:
    d = dict(zip(champs.split(','), r))
    for k in d:
        if k != 'name':
            d[k] = float(d[k]) if '.' in d[k] else int(d[k])
    if d['entry'] not in src:
        continue
    d['stats'] = {}
    for i in range(1, 11):
        if d[f'stat_value{i}']:
            d['stats'][d[f'stat_type{i}']] = d['stats'].get(d[f'stat_type{i}'], 0) + d[f'stat_value{i}']
    d['dps'] = (d['dmg_min1'] + d['dmg_max1']) / 2 / (d['delay'] / 1000) if d['delay'] else 0
    items.append(d)

AGI, STR, INT, SPI, STA = 3, 4, 5, 6, 7
CLOTH, LEATHER, MAIL = 1, 2, 3
# sous-classes d'armes : 0 hache 1M, 1 hache 2M, 2 arc, 3 fusil, 4 masse 1M, 5 masse 2M, 6 hast, 7 épée 1M, 8 épée 2M, 10 bâton,
# 13 pugilat, 15 dague, 16 jet, 18 arbalète, 19 baguette
TANK = {STA: 1.5, STR: 1.0, AGI: 1.0, SPI: 0.1}
HEAL = {INT: 1.2, SPI: 1.0, STA: 0.5}
CAST = {INT: 1.2, STA: 0.8, SPI: 0.4}
PROFILS = {
    # clé : classe du jeu, masque de classe (bit), poids, poids armure, armures (sous-classe: bonus), armes
    'guerrier_tank':     dict(cls=1, w=TANK, armor=0.06, arm={MAIL: 3, LEATHER: 0}, armes='mh+bouclier', mh=(0, 4, 7, 15), dps=3.0, ranged=(2, 3, 18, 16)),
    'guerrier_berserk':  dict(cls=1, w={STR: 1.5, AGI: 1.0, STA: 0.6}, armor=0.02, arm={MAIL: 2, LEATHER: 0}, armes='2m', deuxm=(1, 5, 8), dps=4.5, ranged=(2, 3, 18, 16)),
    'paladin_soleil':    dict(cls=2, w={INT: 1.2, STR: 0.6, STA: 0.8, SPI: 0.3}, armor=0.02, arm={MAIL: 2, LEATHER: 0}, armes='mh+bouclier', mh=(4, 7, 0), dps=0.5, ranged=()),
    'voleur_fantome':    dict(cls=4, w={AGI: 1.6, STR: 0.6, STA: 0.8}, armor=0.02, arm={LEATHER: 0}, armes='2armes', mh=(15, 7, 4, 13), dps=3.0, ranged=(2, 3, 18, 16)),
    'pretre_soin':       dict(cls=5, w=HEAL, armor=0.005, arm={CLOTH: 0}, armes='baton|mh+main', baton=(10,), mh=(4, 15), dps=0.3, ranged=(19,)),
    'necro':             dict(cls=6, mask=9, w=CAST, armor=0.005, arm={CLOTH: 0}, armes='baton|mh+main', baton=(10,), mh=(15, 7), dps=0.3, ranged=(19,)),
    'sniper':            dict(cls=10, mask=3, w={AGI: 1.6, STA: 0.8, INT: 0.3, STR: 0.2}, armor=0.02, arm={LEATHER: 0}, armes='2m', deuxm=(1, 8, 6, 10), dps=0.8, ranged=(2, 3, 18), rdps=4.0),
    'meta_soin':         dict(cls=11, w=HEAL, armor=0.01, arm={LEATHER: 0}, armes='baton|mh+main', baton=(10,), mh=(4, 15), dps=0.3, ranged=()),
    'meta_tank':         dict(cls=11, w={STA: 1.5, AGI: 1.2, STR: 0.8}, armor=0.06, arm={LEATHER: 0}, armes='2m', deuxm=(10, 5), dps=0.5, ranged=()),
    'meta_dps':          dict(cls=11, w={AGI: 1.3, STR: 1.3, STA: 0.6}, armor=0.02, arm={LEATHER: 0}, armes='2m', deuxm=(10, 5), dps=0.5, ranged=()),
    'chaman_tank':       dict(cls=7, w=TANK, armor=0.06, arm={LEATHER: 0}, armes='mh+bouclier', mh=(0, 4), dps=3.0, ranged=()),
    'mage_soin':         dict(cls=8, w=HEAL, armor=0.005, arm={CLOTH: 0}, armes='baton|mh+main', baton=(10,), mh=(7, 15), dps=0.3, ranged=(19,)),
}
SLOTS = [('tête', 0, (1,)), ('cou', 1, (2,)), ('épaules', 2, (3,)), ('torse', 4, (5, 20)), ('taille', 5, (6,)), ('jambes', 6, (7,)),
         ('pieds', 7, (8,)), ('poignets', 8, (9,)), ('mains', 9, (10,)), ('dos', 14, (16,))]

def permis(d, p):
    m = d['AllowableClass']
    bit = 1 << ((p.get('mask') or p['cls']) - 1)
    if m not in (-1, 0) and (m & 0x7FFF) != 0x7FFF and not (m & bit):
        return False
    return True

def score(d, p):
    s = sum(p['w'].get(t, 0) * v for t, v in d['stats'].items())
    s += d['armor'] * p['armor']
    if d['class'] == 2:
        s += d['dps'] * (p.get('rdps', p['dps']) if d['InventoryType'] in (15, 25, 26) and d['subclass'] != 19 else p['dps'])
        if d['subclass'] == 19:
            s += d['dps'] * 0.5
    for k in (1, 2):
        if d[f'spellid_{k}'] and d[f'spelltrigger_{k}'] == 1:
            s += 4
    if d['class'] == 4 and d['InventoryType'] not in (2, 16, 14, 23):
        s += p['arm'].get(d['subclass'], 0)
    return s

def meilleur(p, filtre):
    c = [d for d in items if permis(d, p) and filtre(d)]
    bleus = [d for d in c if d['Quality'] == 3]
    pool = bleus or c
    return max(pool, key=lambda d: score(d, p)) if pool else None

def choisir(nom):
    p = PROFILS[nom]
    res = []
    for lib, slot, inv in SLOTS:
        if lib in ('cou', 'dos'):
            b = meilleur(p, lambda d: d['InventoryType'] in inv)
        else:
            b = meilleur(p, lambda d: d['InventoryType'] in inv and d['class'] == 4 and d['subclass'] in p['arm'])
        if b:
            res.append((lib, slot, b))
    A = p['armes']
    W = lambda invs, subs: (lambda d: d['InventoryType'] in invs and d['class'] == 2 and d['subclass'] in subs)
    if A == 'mh+bouclier':
        res.append(('main droite', 15, meilleur(p, W((13, 21), p['mh']))))
        res.append(('bouclier', 16, meilleur(p, lambda d: d['InventoryType'] == 14)))
    elif A == '2m':
        res.append(('deux mains', 15, meilleur(p, W((17,), p['deuxm']))))
    elif A == '2armes':
        mh = meilleur(p, W((13, 21), p['mh']))
        res.append(('main droite', 15, mh))
        res.append(('main gauche', 16, meilleur(p, lambda d: W((13, 22), p['mh'])(d) and d['entry'] != mh['entry'])))
    else:
        bat = meilleur(p, W((17,), p['baton']))
        mh = meilleur(p, W((13, 21), p['mh']))
        oh = meilleur(p, lambda d: d['InventoryType'] == 23)
        if bat and (not mh or score(bat, p) >= score(mh, p) + (score(oh, p) if oh else 0)):
            res.append(('deux mains', 15, bat))
        else:
            res.append(('main droite', 15, mh))
            if oh:
                res.append(('main gauche', 16, oh))
    if p['ranged']:
        r = meilleur(p, W((15, 25, 26), p['ranged']))
        if r:
            res.append(('distance', 17, r))
    return [(lib, slot, d) for lib, slot, d in res if d]

out = {}
cpp = []
for n in PROFILS:
    r = choisir(n)
    out[n] = [(lib, slot, d['entry'], d['name'], d['RequiredLevel'], d['Quality']) for lib, slot, d in r]
    print('==', n, sum(1 for x in r if x[2]['Quality'] == 3), 'bleus /', len(r))
    for x in out[n]:
        print('   ', x[0], x[2], x[3], 'niv', x[4], 'bleu' if x[5] == 3 else 'VERT')
    cpp.append('    static const ObjetCompagnon OBJ_%s[] = { %s };' % (n.upper(), ', '.join('{ %d, %d }' % (slot, d['entry']) for lib, slot, d in r)))
json.dump(out, open('/home/claude/wow/compagnons/choix20.json', 'w'), ensure_ascii=False, indent=1)
open('/home/claude/wow/compagnons/compagnons_data.inc', 'w').write('\n'.join(cpp) + '\n')
