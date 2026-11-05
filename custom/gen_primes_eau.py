# Primes et avis de recherche dont la cible ne vit que dans l'eau (requins, poissons...) : souvent au large, loin du tableau.
# La cible est remplacée par un monstre terrestre courant de la même zone, de niveau proche -> primes_eau.sql (après primes_evenements.sql)
#   prime : nouvelle créature à tuer
#   avis de recherche (alpha 9921xx) : l'alpha prend l'apparence et le nom d'un monstre terrestre et apparaît à l'un de ses emplacements
# Écrit aussi primes_eau.json (alpha -> nouvelle source) pour gen_pfquest.py.
import json
import struct
import subprocess
from collections import defaultdict


def q(sql):
    r = subprocess.run(['mysql', '--default-character-set=utf8mb4', '-N', '-B', 'classicmangos', '-e', sql], capture_output=True, text=True, check=True)
    return [l.split('\t') for l in r.stdout.splitlines()]


d = open('/mnt/user-data/uploads/SPP_Classics V2/SPP_Classics_V2/SPP_Server/Server/Modules/vanilla/dbc/FactionTemplate.dbc', 'rb').read()
n, f, rs, ss = struct.unpack('<4I', d[4:20])
FT = {}
for i in range(n):
    r = struct.unpack('<%dI' % f, d[20 + i * rs:20 + (i + 1) * rs])
    FT[r[0]] = r


def amical(fac):
    r = FT.get(fac)
    return (not r) or bool((r[3] | r[4]) & 6)


perm = defaultdict(lambda: defaultdict(int))
for e, z, cnt in q("select c.id, z.ZoneId, count(*) from creature c join creature_zone z on z.Guid=c.guid "
                   "where c.map in (0,1) and c.guid not in (select guid from game_event_creature) group by c.id, z.ZoneId"):
    perm[int(z)][int(e)] = int(cnt)
T = {int(r[0]): r for r in q("select Entry, MaxLevel, Rank, NpcFlags, LootId, UnitFlags, Faction, InhabitType, CreatureType from creature_template")}


def valide(e):
    t = T.get(e)
    if not t:
        return False
    _, mx, rk, npc, loot, uf, fac, inh, typ = t
    return (int(rk) == 0 and int(npc) == 0 and int(loot) > 0 and (int(uf) & (2 | 256 | 33554432)) == 0 and not amical(int(fac))
            and e < 990000 and (int(inh) & 1))


quests = q("select q.entry, q.ZoneOrSort, q.QuestLevel, q.ReqCreatureOrGOId1, r.id from quest_template q "
           "join gameobject_questrelation r on r.quest=q.entry where q.entry between 991400 and 991999")
used = defaultdict(set)
for e, z, lv, c, b in quests:
    used[b].add(int(c))
eau = {int(r[0]) for r in q("select Entry from creature_template where (InhabitType & 1)=0")}
alpha_src = {}
for a, s in q("select Entry, 0 from creature_template where Entry between 992100 and 992199"):
    alpha_src[int(a)] = None
L = ["-- Primes dont la cible ne vit que dans l'eau : cible remplacée par un monstre terrestre (généré par gen_primes_eau.py)", "SET NAMES utf8mb4;"]
primes, alphas, sources = [], [], {}
for e, z, lv, c, b in quests:
    e, z, lv, c = int(e), int(z), int(lv), int(c)
    if c not in eau:
        continue
    cands = []
    for ecart in (3, 5, 8):
        cands = [(abs(int(T[ce][1]) - lv), -cnt, ce) for ce, cnt in perm[z].items()
                 if cnt >= 6 and valide(ce) and ce not in used[b] and abs(int(T[ce][1]) - lv) <= ecart]
        if cands:
            break
    if not cands:
        print('pas de remplaçant pour', e)
        continue
    _, _, ce = min(cands)
    used[b].add(ce)
    if c >= 990000:
        # alpha : apparence, nom et emplacement d'un monstre terrestre
        sp = q("select c.map, c.position_x, c.position_y, c.position_z from creature c join creature_zone z on z.Guid=c.guid "
               "where c.id=%d and z.ZoneId=%d limit 1" % (ce, z))[0]
        L.append("UPDATE creature_template a JOIN creature_template s ON s.Entry=%d SET a.Name=s.Name, a.DisplayId1=s.DisplayId1, "
                 "a.DisplayId2=s.DisplayId2, a.DisplayId3=s.DisplayId3, a.DisplayId4=s.DisplayId4, "
                 "a.DisplayIdProbability1=s.DisplayIdProbability1, a.DisplayIdProbability2=s.DisplayIdProbability2, "
                 "a.DisplayIdProbability3=s.DisplayIdProbability3, a.DisplayIdProbability4=s.DisplayIdProbability4, "
                 "a.InhabitType=s.InhabitType, a.CreatureType=s.CreatureType, a.Family=s.Family, a.SpeedWalk=s.SpeedWalk, "
                 "a.SpeedRun=s.SpeedRun WHERE a.Entry=%d;" % (ce, c))
        L.append("UPDATE creature SET map=%s, position_x=%s, position_y=%s, position_z=%s, spawndist=20, MovementType=1 WHERE id=%d;"
                 % (sp[0], sp[1], sp[2], sp[3], c))
        L.append("UPDATE quest_template q JOIN creature_template s ON s.Entry=%d SET q.Title=CONCAT('Avis de recherche : ', s.Name, ' alpha'), "
                 "q.Objectives=CONCAT('Abattez ', s.Name, ' alpha.'), "
                 "q.Details=CONCAT(s.Name, ' alpha', SUBSTRING(q.Details, LOCATE(' terrorise', q.Details))) WHERE q.entry=%d;" % (ce, e))
        sources[c] = ce
        alphas.append(e)
        print(e, 'alpha', c, ': source', ce, 'niv', T[ce][1])
    else:
        L.append("UPDATE quest_template SET ReqCreatureOrGOId1=%d WHERE entry=%d;" % (ce, e))
        primes.append(e)
        print(e, 'prime :', c, '->', ce, 'niv', T[ce][1], 'spawns', perm[z][ce])
if primes:
    L.append("UPDATE quest_template q JOIN creature_template c ON c.Entry=q.ReqCreatureOrGOId1 SET q.Title=CONCAT('Prime : ', c.Name), "
             "q.Objectives=CONCAT('Tuez ', q.ReqCreatureOrGOCount1, ' x ', c.Name, '.'), "
             "q.Details=CONCAT(SUBSTRING_INDEX(q.Details, ' : les ', 1), ' : les ', c.Name, ' deviennent trop nombreux. ',"
             "'Une prime est offerte à qui en éliminera ', q.ReqCreatureOrGOCount1, '.$B$BRevenez au tableau une fois le travail fait.') "
             "WHERE q.entry IN (%s);" % ",".join(map(str, primes)))
L.append("SELECT 'Primes eau OK' AS resultat;")
open('/home/claude/wow-serveur/custom/primes_eau.sql', 'w', encoding='utf-8').write("\n".join(L) + "\n")
json.dump({str(k): v for k, v in sources.items()}, open('/home/claude/wow-serveur/custom/primes_eau.json', 'w'))
print(len(primes), 'primes', len(alphas), 'alphas')
