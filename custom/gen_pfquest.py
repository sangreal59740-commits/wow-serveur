# Génère l'addon pfQuest-Custom : ajoute à la base de pfQuest les quêtes custom du serveur (entrées >= 990000),
# leurs donneurs, objectifs (monstres, objets, objets du monde) et les positions sur la carte.
import re, struct, subprocess, sys, os
PF = '/mnt/user-data/uploads/wow/Interface/AddOns/pfQuest/db/'
DBC = '/home/claude/wow/classes/dbc/'
OUT = '/home/claude/wow/pfquest/pfQuest-Custom/'

def q(sql):
    r = subprocess.run(['mysql', '--default-character-set=utf8mb4', '-N', '-B', 'classicmangos', '-e', sql],
                       capture_output=True, text=True, check=True)
    return [l.split('\t') for l in r.stdout.splitlines()]

def keys(path, table):
    s = open(path, encoding='utf-8', errors='replace').read()
    i = s.index('pfDB["%s"]["data"]' % table) if table else 0
    return set(int(m) for m in re.findall(r'^  \[(\d+)\] = ', s[i:], re.M))
KU, KO, KI = keys(PF + 'units.lua', 'units'), keys(PF + 'objects.lua', 'objects'), keys(PF + 'items.lua', 'items')

# ------------------------------------------------------------ cartes : coordonnées monde -> % de la carte de zone
d = open(DBC + 'WorldMapArea.dbc', 'rb').read()
n, f, rs, ss = struct.unpack('<4I', d[4:20])
WMA = []
for i in range(n):
    rec = d[20 + i * rs:20 + (i + 1) * rs]
    wid, mapid, area = struct.unpack('<3I', rec[:12])
    left, right, top, bottom = struct.unpack('<4f', rec[16:32])
    if area:
        WMA.append((mapid, area, left, right, top, bottom))

def zone_coords(mapid, x, y):
    best = None
    for m, area, left, right, top, bottom in WMA:
        if m != mapid or not (right <= y <= left and bottom <= x <= top):
            continue
        size = (left - right) * (top - bottom)
        if best is None or size < best[0]:
            best = (size, area, (left - y) / (left - right) * 100, (top - x) / (top - bottom) * 100)
    return None if best is None else (best[1], round(best[2], 1), round(best[3], 1))

def spawns(table, ids):
    out = {}
    if not ids:
        return out
    for gid, mp, x, y, rt in q("SELECT id, map, position_x, position_y, %s FROM %s WHERE id IN (%s)"
                                % ('spawntimesecsmin', table, ','.join(map(str, ids)))):
        zc = zone_coords(int(mp), float(x), float(y))
        if zc:
            out.setdefault(int(gid), []).append((zc[1], zc[2], zc[0], int(rt)))
    return out

# ------------------------------------------------------------ quêtes
cols = ("entry, Title, Objectives, Details, QuestLevel, MinLevel, RequiredRaces, PrevQuestId, "
        "ReqCreatureOrGOId1, ReqCreatureOrGOId2, ReqCreatureOrGOId3, ReqCreatureOrGOId4, ReqItemId1, ReqItemId2, ReqItemId3, ReqItemId4, "
        "ReqCreatureOrGOCount1, ReqItemCount1")
QUESTS = {}
for r in q("SELECT %s FROM quest_template WHERE entry >= 990000" % cols):
    e = int(r[0])
    QUESTS[e] = dict(T=r[1], O=r[2], D=r[3], lvl=int(r[4]), min=int(r[5]), race=int(r[6]), pre=int(r[7]),
                     cgo=[int(v) for v in r[8:12] if int(v)], items=[int(v) for v in r[12:16] if int(v)],
                     ccount=int(r[16]), icount=int(r[17]),
                     start={}, end={}, obj={})
for table, side, kind in (('creature_questrelation', 'start', 'U'), ('gameobject_questrelation', 'start', 'O'),
                          ('creature_involvedrelation', 'end', 'U'), ('gameobject_involvedrelation', 'end', 'O')):
    for gid, qu in q("SELECT id, quest FROM %s WHERE quest >= 990000" % table):
        if int(qu) in QUESTS:
            QUESTS[int(qu)][side].setdefault(kind, []).append(int(gid))
for e, Q in QUESTS.items():
    for v in Q['cgo']:
        Q['obj'].setdefault('U' if v > 0 else 'O', []).append(abs(v))
    if Q['items']:
        Q['obj']['I'] = Q['items']

# ------------------------------------------------------------ unités, objets et objets du monde manquants dans pfQuest
units, objects, items = set(), set(), set()
for Q in QUESTS.values():
    for side in ('start', 'end', 'obj'):
        units |= set(Q[side].get('U', []))
        objects |= set(Q[side].get('O', []))
    items |= set(Q['obj'].get('I', []))
ITEM_SRC = {}
new_items = sorted(i for i in items if i not in KI)
if new_items:
    for gid, it, ch in q("SELECT entry, item, ChanceOrQuestChance FROM creature_loot_template WHERE item IN (%s)" % ','.join(map(str, new_items))):
        ITEM_SRC.setdefault(int(it), {}).setdefault('U', {})[int(gid)] = abs(float(ch))
        units.add(int(gid))
    for gid, it, ch in q("SELECT g.entry, l.item, l.ChanceOrQuestChance FROM gameobject_loot_template l JOIN gameobject_template g "
                         "ON g.data1 = l.entry AND g.type = 3 WHERE l.item IN (%s)" % ','.join(map(str, new_items))):
        ITEM_SRC.setdefault(int(it), {}).setdefault('O', {})[int(gid)] = abs(float(ch))
        objects.add(int(gid))
new_units = sorted(u for u in units if u not in KU)
new_objects = sorted(o for o in objects if o not in KO)
USP = spawns('creature', new_units)
OSP = spawns('gameobject', new_objects)
UNAME, ULVL = {}, {}
if new_units:
    for e, nm, lmin, lmax, rank in q("SELECT Entry, Name, MinLevel, MaxLevel, Rank FROM creature_template WHERE Entry IN (%s)" % ','.join(map(str, new_units))):
        UNAME[int(e)] = nm; ULVL[int(e)] = (lmin if lmin == lmax else '%s-%s' % (lmin, lmax), int(rank))
    for e, nm in q("SELECT entry, name_loc2 FROM locales_creature WHERE entry IN (%s) AND name_loc2 <> ''" % ','.join(map(str, new_units))):
        UNAME[int(e)] = nm
ONAME = {}
if new_objects:
    for e, nm in q("SELECT entry, name FROM gameobject_template WHERE entry IN (%s)" % ','.join(map(str, new_objects))):
        ONAME[int(e)] = nm
INAME = {}
if new_items:
    for e, nm in q("SELECT entry, name FROM item_template WHERE entry IN (%s)" % ','.join(map(str, new_items))):
        INAME[int(e)] = nm

# chefs de zone et alphas : copies d'un monstre de la zone (le nom en jeu vient du nom français de la source)
_ms = open('/home/claude/wow-serveur/custom/monde.sql', encoding='utf-8').read()
BOSS_SRC = {int(b): int(a) for a, b in re.findall(r"INSERT INTO tmp_ct SELECT \* FROM creature_template WHERE Entry=(\d+);\s*UPDATE tmp_ct SET Entry=(\d+),", _ms)}

# ------------------------------------------------------------ écriture Lua (5.0)
def s(v):
    return '"' + v.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '$B').replace('\r', '') + '"'
def ids(l):
    return '{ ' + ', '.join(str(x) for x in l) + ' }'
L = ['-- Généré par gen_pfquest.py : quêtes custom du serveur pour pfQuest. Ne pas modifier à la main.',
     'if not pfDB then return end',
     'local function ajout(dst, src) if dst then for k, v in pairs(src) do dst[k] = v end end end',
     '-- oublie les quêtes que pfQuest avait mémorisées comme inconnues (avant cet addon), pour qu\'il les reconnaisse',
     'local function purge() if pfQuest_questcache then for k, v in pairs(pfQuest_questcache) do if type(v) == "table" and type(v[1]) == "string" then pfQuest_questcache[k] = nil end end end end',
     'purge()',
     'local f = CreateFrame("Frame") f:RegisterEvent("VARIABLES_LOADED") f:SetScript("OnEvent", function() purge() end)',
     'ajout(pfDB["quests"]["data"], {']
for e in sorted(QUESTS):
    Q = QUESTS[e]
    parts = ['["lvl"] = %d' % Q['lvl'], '["min"] = %d' % Q['min']]
    if Q['race']:
        parts.append('["race"] = %d' % Q['race'])
    if Q['pre'] > 0:
        parts.append('["pre"] = { %d }' % Q['pre'])
    for side in ('start', 'end', 'obj'):
        if Q[side]:
            parts.append('["%s"] = { %s }' % (side, ', '.join('["%s"] = %s' % (k, ids(sorted(set(v)))) for k, v in sorted(Q[side].items()))))
    L.append('  [%d] = { %s },' % (e, ', '.join(parts)))
L.append('})')
L.append('ajout(pfDB["quests"]["frFR"], {')
PRIMES = []
for e in sorted(QUESTS):
    Q = QUESTS[e]
    if 991400 <= e <= 991999:
        if Q['items']:
            PRIMES.append('{ %d, "I", %d, %d }' % (e, Q['items'][0], Q['icount']))
        elif Q['cgo']:
            c = Q['cgo'][0]
            if c in BOSS_SRC:
                PRIMES.append('{ %d, "%s", %d, 1 }' % (e, 'C' if c < 992100 else 'A', BOSS_SRC[c]))
            else:
                PRIMES.append('{ %d, "U", %d, %d }' % (e, c, Q['ccount']))
        continue
    L.append('  [%d] = { ["T"] = %s, ["O"] = %s, ["D"] = %s },' % (e, s(Q['T']), s(Q['O']), s(Q['D'])))
L.append('})')
# primes des tableaux : titres construits avec les noms français de pfQuest (ceux que le serveur affiche)
L.append('local primes = {')
L += ['  ' + p + ',' for p in PRIMES]
L.append('}')
L.append('''local function nomU(id, en) return (pfDB["units"]["frFR"] and pfDB["units"]["frFR"][id]) or (pfDB["units"]["enUS"] and pfDB["units"]["enUS"][id]) or en or "?" end
local function nomI(id) return (pfDB["items"]["frFR"] and pfDB["items"]["frFR"][id]) or (pfDB["items"]["enUS"] and pfDB["items"]["enUS"][id]) or "?" end
for i = 1, table.getn(primes) do
  local q, genre, id, n = primes[i][1], primes[i][2], primes[i][3], primes[i][4]
  local t, o, d
  if genre == "I" then
    local nom = nomI(id)
    t = "Récolte : " .. nom
    o = "Rapportez " .. n .. " x " .. nom .. "."
  elseif genre == "U" then
    local nom = nomU(id)
    t = "Prime : " .. nom
    o = "Tuez " .. n .. " x " .. nom .. "."
  else
    local nom = (genre == "C") and ("Chef " .. nomU(id)) or (nomU(id) .. " alpha")
    t = "Avis de recherche : " .. nom
    o = "Abattez " .. nom .. "."
  end
  pfDB["quests"]["frFR"][q] = { ["T"] = t, ["O"] = o, ["D"] = "Prime du tableau de la région." }
end''')
L.append('ajout(pfDB["units"]["data"], {')
for u in new_units:
    c = ', '.join('{ %s, %s, %d, %d }' % sp for sp in USP.get(u, [])[:40])
    lv, rk = ULVL.get(u, ('1', 0))
    L.append('  [%d] = { ["coords"] = { %s }, ["lvl"] = "%s"%s },' % (u, c, lv, ', ["rnk"] = "%d"' % rk if rk else ''))
L.append('})')
L.append('ajout(pfDB["units"]["frFR"], {')
for u in new_units:
    if u in UNAME and u not in BOSS_SRC:
        L.append('  [%d] = %s,' % (u, s(UNAME[u])))
L.append('})')
L.append('local chefs = { ' + ', '.join('[%d] = %d' % (b, a) for b, a in sorted(BOSS_SRC.items())) + ' }')
L.append('for b, src in pairs(chefs) do pfDB["units"]["frFR"][b] = (b < 992100) and ("Chef " .. nomU(src)) or (nomU(src) .. " alpha") end')
L.append('ajout(pfDB["objects"]["data"], {')
for o in new_objects:
    c = ', '.join('{ %s, %s, %d, %d }' % sp for sp in OSP.get(o, [])[:40])
    L.append('  [%d] = { ["coords"] = { %s } },' % (o, c))
L.append('})')
L.append('ajout(pfDB["objects"]["frFR"], {')
for o in new_objects:
    if o in ONAME:
        L.append('  [%d] = %s,' % (o, s(ONAME[o])))
L.append('})')
L.append('ajout(pfDB["items"]["data"], {')
for it in new_items:
    src = ITEM_SRC.get(it, {})
    parts = ['["%s"] = { %s }' % (k, ', '.join('[%d] = %s' % (g, round(ch, 2)) for g, ch in sorted(v.items()))) for k, v in sorted(src.items())]
    L.append('  [%d] = { %s },' % (it, ', '.join(parts)))
L.append('})')
L.append('ajout(pfDB["items"]["frFR"], {')
for it in new_items:
    if it in INAME:
        L.append('  [%d] = %s,' % (it, s(INAME[it])))
L.append('})')
os.makedirs(OUT, exist_ok=True)
open(OUT + 'pfQuest-Custom.lua', 'w', encoding='utf-8').write('\n'.join(L) + '\n')
open(OUT + 'pfQuest-Custom.toc', 'w', encoding='utf-8').write(
    "## Interface: 11200\n## Title: pfQuest-Custom\n## Notes: Quetes ajoutees au serveur (tableaux de primes, donjons, raids) dans pfQuest\n"
    "## Dependencies: pfQuest\npfQuest-Custom.lua\n")
nc = sum(1 for u in new_units if USP.get(u)) + sum(1 for o in new_objects if OSP.get(o))
print('quetes', len(QUESTS), 'unites', len(new_units), 'objets', len(new_objects), 'items', len(new_items), 'avec position', nc)
