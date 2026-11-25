import json, sys, glob, re
sys.path.insert(0, '/home/claude/wow/fr')
from dbc import DBC
T = {}
for f in sorted(glob.glob('/home/claude/wow/fr/out/*.json')):
    if not f.endswith('ranks.json'):
        T.update(json.load(open(f, encoding='utf-8')))
SP = DBC('/home/claude/wow/fr/dbc_en/Spell.dbc')
names = {}      # id -> (fr name, spelllevel)
for r in SP.rows:
    en = SP.str(r[120])
    names[r[0]] = (T.get(en, en), r[33])
SRT = json.load(open('/home/claude/wow/classes/sorts_rows.json', encoding='utf-8'))
for r in SRT['spell']:
    names[r[0]] = (r[120], r[33])
sla = DBC('/home/claude/wow/classes/out/SkillLineAbility.dbc')
byclass = {}    # class -> {name: [ids]}
for r in sla.rows:
    sid, cm = r[2], r[4]
    if sid not in names:
        continue
    for c in range(1, 15):
        if cm & (1 << (c - 1)):
            byclass.setdefault(c, {}).setdefault(names[sid][0].lower(), set()).add(sid)
json.dump({'names': {k: v for k, v in names.items()}, 'byclass': {c: {n: sorted(s) for n, s in d.items()} for c, d in byclass.items()}},
          open('index.json', 'w', encoding='utf-8'), ensure_ascii=False)
print({c: len(d) for c, d in byclass.items()})
