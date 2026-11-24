# Choix de l'équipement niveau 15 (objets de niveau 15 minimum, portables au niveau 15)
# pour les 4 compagnons et le coffre du voleur. Pas d'anneau, de bijou ni d'artefact.
import subprocess, json, sys
NIV = 15
def q(sql):
    r = subprocess.run(['mysql', '-N', '--default-character-set=utf8', 'classicmangos', '-e', sql], capture_output=True, text=True)
    return [l.split('\t') for l in r.stdout.splitlines()]

# objets réellement obtenables : butin, vendeurs, quêtes
src = set()
for t in ['creature_loot_template', 'gameobject_loot_template', 'reference_loot_template', 'item_loot_template', 'npc_vendor', 'npc_vendor_template']:
    src |= {int(r[0]) for r in q(f'SELECT DISTINCT item FROM {t}')}
cols = ','.join([f'RewChoiceItemId{i}' for i in range(1, 7)] + [f'RewItemId{i}' for i in range(1, 5)])
for r in q(f'SELECT {cols} FROM quest_template'):
    src |= {int(x) for x in r if x != '0'}

champs = ('entry,name,class,subclass,InventoryType,Quality,ItemLevel,RequiredLevel,AllowableClass,AllowableRace,armor,block,dmg_min1,dmg_max1,delay,'
          + ','.join(f'stat_type{i},stat_value{i}' for i in range(1, 11)) + ',RandomProperty,Flags,RequiredSkill,RequiredReputationFaction,spellid_1,spelltrigger_1')
rows = q(f"""SELECT {champs} FROM item_template WHERE ItemLevel >= {NIV} AND ItemLevel <= {NIV + 8} AND RequiredLevel <= {NIV} AND RequiredLevel >= {NIV - 6}
  AND Quality IN (2,3) AND class IN (2,4) AND RandomProperty = 0 AND RequiredSkill = 0 AND RequiredReputationFaction = 0
  AND name NOT LIKE '%Monster%' AND name NOT LIKE '%Test%' AND name NOT LIKE '%Deprecated%' AND name NOT LIKE '%[PH]%' AND (entry < 990000 OR entry IN (994097, 994098))""")
items = []
for r in rows:
    d = dict(zip(champs.split(','), r))
    for k in d:
        if k != 'name':
            d[k] = float(d[k]) if '.' in d[k] else int(d[k])
    if d['entry'] not in src and d['entry'] not in (994097, 994098):
        continue
    d['stats'] = {}
    for i in range(1, 11):
        if d[f'stat_value{i}']:
            d['stats'][d[f'stat_type{i}']] = d['stats'].get(d[f'stat_type{i}'], 0) + d[f'stat_value{i}']
    d['dps'] = (d['dmg_min1'] + d['dmg_max1']) / 2 / (d['delay'] / 1000) if d['delay'] else 0
    items.append(d)

AGI, STR, INT, SPI, STA = 3, 4, 5, 6, 7
# classe: masque, poids, armures permises (sous-classe : bonus), config armes
PROFILS = {
    'guerrier_tank': dict(cls=1, w={STA: 1.5, STR: 1.0, AGI: 1.0, INT: 0, SPI: 0.1}, armor=0.06, arm={3: 3, 2: 0},
                          armes='mh+bouclier', mh=(0, 4, 7, 15, 13), dps=3.0, ranged=(2, 3, 18, 16)),
    'paladin_vindicte': dict(cls=2, w={STR: 1.5, STA: 0.8, AGI: 0.7, INT: 0.3, SPI: 0.1}, armor=0.03, arm={3: 3, 2: 0},
                             armes='2m', deuxm=(1, 5, 8), dps=4.0, ranged=()),
    'pretre_soin': dict(cls=5, w={INT: 1.2, SPI: 1.0, STA: 0.5}, armor=0.005, arm={1: 0},
                        armes='baton|mh+main', baton=(10,), mh=(4, 15), dps=0.3, ranged=(19,)),
    'mage_givre': dict(cls=8, w={INT: 1.2, STA: 0.7, SPI: 0.5}, armor=0.005, arm={1: 0},
                       armes='baton|mh+main', baton=(10,), mh=(7, 15), dps=0.3, ranged=(19,)),
    'voleur': dict(cls=4, w={AGI: 1.6, STR: 0.6, STA: 0.8}, armor=0.02, arm={2: 0},
                   armes='2armes', mh=(15, 7, 4, 13), dps=3.0, ranged=(2, 3, 18, 16)),
}
SLOTS = {'tête': (1,), 'cou': (2,), 'épaules': (3,), 'dos': (16,), 'torse': (5, 20), 'poignets': (9,), 'mains': (10,),
         'taille': (6,), 'jambes': (7,), 'pieds': (8,)}

def permis(d, p):
    m = d['AllowableClass']
    if m not in (-1, 0) and m & 0x7FFF != 0x7FFF and not (m & (1 << (p['cls'] - 1))):
        return False
    r = d['AllowableRace']
    if r not in (-1, 0) and r & 0xFF != 0xFF and not (r & 1):   # humain
        return False
    return True

def score(d, p):
    s = sum(p['w'].get(t, 0) * v for t, v in d['stats'].items())
    s += d['armor'] * p['armor']
    if d['class'] == 2:
        s += d['dps'] * p['dps']
    if d['spellid_1'] and d['spelltrigger_1'] == 1:
        s += 4      # effet passif (sorts, soins, crit) : léger bonus
    if d['class'] == 4 and d['InventoryType'] not in (2, 16, 14, 23):
        s += p['arm'].get(d['subclass'], 0)
    return s + d['Quality'] * 0.5

def meilleur(p, filtre):
    c = [d for d in items if permis(d, p) and filtre(d)]
    return max(c, key=lambda d: score(d, p)) if c else None

def choisir(nom):
    p = PROFILS[nom]
    res = {}
    for slot, inv in SLOTS.items():
        if slot == 'cou':
            b = meilleur(p, lambda d: d['InventoryType'] == 2)
        elif slot == 'dos':
            b = meilleur(p, lambda d: d['InventoryType'] == 16)
        else:
            b = meilleur(p, lambda d: d['InventoryType'] in inv and d['class'] == 4 and d['subclass'] in p['arm'])
        if b:
            res[slot] = b
    A = p['armes']
    if A == 'mh+bouclier':
        res['main droite'] = meilleur(p, lambda d: d['InventoryType'] in (13, 21) and d['class'] == 2 and d['subclass'] in p['mh'])
        res['main gauche'] = meilleur(p, lambda d: d['InventoryType'] == 14)
    elif A == '2m':
        res['deux mains'] = meilleur(p, lambda d: d['InventoryType'] == 17 and d['class'] == 2 and d['subclass'] in p['deuxm'])
    elif A == '2armes':
        res['main droite'] = meilleur(p, lambda d: d['InventoryType'] in (13, 21) and d['class'] == 2 and d['subclass'] in p['mh'])
        res['main gauche'] = meilleur(p, lambda d: d['InventoryType'] in (13, 22) and d['class'] == 2 and d['subclass'] in p['mh'] and d['entry'] != res['main droite']['entry'])
    else:
        bat = meilleur(p, lambda d: d['InventoryType'] == 17 and d['class'] == 2 and d['subclass'] in p['baton'])
        mh = meilleur(p, lambda d: d['InventoryType'] in (13, 21) and d['class'] == 2 and d['subclass'] in p['mh'])
        oh = meilleur(p, lambda d: d['InventoryType'] == 23)
        if bat and (not mh or score(bat, p) >= score(mh, p) + (score(oh, p) if oh else 0)):
            res['deux mains'] = bat
        else:
            res['main droite'] = mh
            if oh:
                res['main gauche'] = oh
    if p['ranged']:
        r = meilleur(p, lambda d: d['InventoryType'] in (15, 25, 26) and d['class'] == 2 and d['subclass'] in p['ranged'])
        if r:
            res['distance'] = r
    return {k: v for k, v in res.items() if v}

if __name__ == '__main__':
    out = {}
    for n in PROFILS:
        r = choisir(n)
        out[n] = [(k, v['entry'], v['name'], v['RequiredLevel'], v['ItemLevel'], v['Quality']) for k, v in r.items()]
        print('==', n)
        for x in out[n]:
            print('  ', *x)
    json.dump(out, open('/home/claude/wow/compagnons/choix.json', 'w'), ensure_ascii=False, indent=1)
