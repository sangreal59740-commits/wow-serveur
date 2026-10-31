import json, sys
sys.path.insert(0, '/home/claude/wow/fr')
def rows(flags):
    out = []
    for s in json.load(open('/home/claude/wow/donjons/itemsets.json', encoding='utf-8')):
        r = [0] * 45
        r[0] = s['id']; r[1] = s['name']; r[9] = flags
        for i, it in enumerate(s['items']): r[10 + i] = it
        for i, sp in enumerate(s['spells']): r[27 + i] = sp
        for i, t in enumerate(s['thresholds']): r[35 + i] = t
        out.append(r)
    return out
