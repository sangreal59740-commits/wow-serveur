import json, re
D = json.load(open('doc.json', encoding='utf-8'))
I = json.load(open('index.json', encoding='utf-8'))
CL = {'Guerrier': 1, 'Paladin': 2, 'Chasseur': 3, 'Voleur': 4, 'Prêtre': 5, 'Nécromancien': 6, 'Chaman': 7, 'Mage': 8, 'Démoniste': 9,
      'Sniper': 10, 'Métamorphe': 11, 'Tisserand': 12, 'Fossoyeur': 13, 'Martyr': 14}
def split_sorts(s):
    s = re.sub(r'\(.*?\)', '', s)
    s = s.replace('Invocation de squelette, de goule, de chien squelettique, de squelette de givre et d\'abomination',
                  'Invocation : Squelette, Invocation : Goule, Invocation : Chien squelettique, Invocation : Squelette de givre, Invocation : Abomination')
    return [x.strip().rstrip('.') for x in s.split(', ') if x.strip()]
miss = 0
for c in D:
    cls = CL[c['spe'].split()[0]]
    c['cls'] = cls
    res = []
    for n in split_sorts(c['sorts']):
        ids = I['byclass'].get(str(cls), {}).get(n.lower())
        if not ids:
            print('  ??', c['nom'], cls, '«%s»' % n); miss += 1
        res.append((n, ids))
    c['res'] = res
print('manquants', miss)
json.dump(D, open('doc2.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
