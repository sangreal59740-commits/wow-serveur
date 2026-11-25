# Lit les compagnons validés dans le doc et en sort une structure (sorts, talents, ultime)
import re, json
DOC = '/home/claude/wow/Nouvelles_classes_et_soutiens.md'
txt = open(DOC, encoding='utf-8').read()
part = txt[txt.index('### Gris (validés'):txt.index('### Équipement des compagnons')]
RAR = None
out = []
lines = part.split('\n')
i = 0
while i < len(lines):
    l = lines[i]
    m = re.match(r'### (Gris|Verts|Bleus|Épiques|Légendaires)', l)
    if m:
        RAR = {'Gris': 'gris', 'Verts': 'vert', 'Bleus': 'bleu', 'Épiques': 'epique', 'Légendaires': 'legendaire'}[m.group(1)]
    m = re.match(r'\*\*(.+?)\*\* \((.+?), (.+?)\)\. (.*)$', l)
    if m and RAR:
        nom, spe, role, rest = m.groups()
        sm = re.search(r'Sorts : (.+?)\.?$', rest)
        sorts = sm.group(1) if sm else ''
        tl = lines[i + 1]
        out.append(dict(nom=nom, spe=spe, role=role, rarete=RAR, intro=rest, sorts=sorts, talents=tl))
        i += 2
        continue
    i += 1
for c in out:
    t = c['talents']
    pal = re.split(r'(?:^|\. )P(\d) ', t)
    P = {}
    for k in range(1, len(pal), 2):
        P[int(pal[k])] = pal[k + 1].rstrip('.')
    c['P'] = P
    tal = []
    for n in range(1, 6):
        s = P.get(n, '')
        ult = None
        if n == 5 and ' / Ultime ' in s:
            s, ult = s.split(' / Ultime ', 1)
            c['ultime'] = ult
        for part in re.split(r' / (?![^()]*\))', s):
            mm = re.match(r'(.+?) \((.+)\)$', part.strip())
            tal.append((n, mm.group(1) if mm else part.strip(), mm.group(2) if mm else ''))
    c['tal'] = tal
json.dump(out, open('doc.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(len(out))
for c in out:
    print(c['rarete'], c['nom'], '|', c['spe'], '|', len(c['tal']), '|', c.get('ultime', '')[:40])
