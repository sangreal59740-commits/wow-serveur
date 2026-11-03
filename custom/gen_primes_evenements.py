# Primes dont la cible n'apparaît (presque) que pendant un événement (Invasion du Fléau, guerre d'AQ...) ou hors de la zone du tableau :
# la cible est remplacée par un monstre courant de la même zone, de niveau proche. Numéros de quête, niveau et récompenses inchangés.
import struct, subprocess
from collections import defaultdict
def q(sql):
    r = subprocess.run(['mysql', '--default-character-set=utf8mb4', '-N', '-B', 'classicmangos', '-e', sql], capture_output=True, text=True, check=True)
    return [l.split('\t') for l in r.stdout.splitlines()]
d = open('/mnt/user-data/uploads/SPP_Classics V2/SPP_Classics_V2/SPP_Server/Server/Modules/vanilla/dbc/FactionTemplate.dbc', 'rb').read()
n, f, rs, ss = struct.unpack('<4I', d[4:20])
FT = {}
for i in range(n):
    r = struct.unpack('<%dI' % f, d[20 + i * rs:20 + (i + 1) * rs]); FT[r[0]] = r
def amical(fac):
    r = FT.get(fac)
    return (not r) or bool((r[3] | r[4]) & 6)
# spawns permanents (hors événement) par zone et par créature
perm = defaultdict(lambda: defaultdict(int))
for e, z, cnt in q("select c.id, z.ZoneId, count(*) from creature c join creature_zone z on z.Guid=c.guid "
                   "where c.map in (0,1) and c.guid not in (select guid from game_event_creature) group by c.id, z.ZoneId"):
    perm[int(z)][int(e)] = int(cnt)
T = {int(r[0]): r for r in q("select Entry, MaxLevel, Rank, NpcFlags, LootId, UnitFlags, Faction from creature_template")}
def valide(e):
    t = T.get(e)
    if not t:
        return False
    _, mx, rk, npc, loot, uf, fac = t
    return int(rk) == 0 and int(npc) == 0 and int(loot) > 0 and (int(uf) & (2 | 256 | 33554432)) == 0 and not amical(int(fac)) and e < 990000
quests = q("select q.entry, q.ZoneOrSort, q.QuestLevel, q.ReqCreatureOrGOId1, q.ReqCreatureOrGOCount1, r.id from quest_template q "
           "join gameobject_questrelation r on r.quest=q.entry where q.entry between 991400 and 991999")
used = defaultdict(set)
for e, z, lv, c, cc, b in quests:
    used[b].add(int(c))
L = ["-- Primes dont la cible n'apparaît que pendant un événement : cible remplacée (généré par gen_primes_evenements.py)"]
done = []
for e, z, lv, c, cc, b in quests:
    z, lv, c = int(z), int(lv), int(c)
    if c <= 0 or c >= 990000 or perm[z].get(c, 0) > 0:      # boss du serveur et cibles présentes en permanence : inchangés
        continue
    cands = [(abs(int(T[ce][1]) - lv), -cnt, ce) for ce, cnt in perm[z].items()
             if cnt >= 6 and valide(ce) and ce not in used[b] and abs(int(T[ce][1]) - lv) <= 3]
    if not cands:
        print('pas de remplaçant pour', e); continue
    _, _, ce = min(cands)
    used[b].add(ce)
    print(e, 'zone', z, 'niv', lv, ':', c, '->', ce, 'niv', T[ce][1], 'spawns', perm[z][ce])
    L.append("UPDATE quest_template SET ReqCreatureOrGOId1=%d WHERE entry=%s;" % (ce, e))
    done.append(e)
if done:
    ids = ','.join(done)
    L.append("UPDATE quest_template q JOIN creature_template c ON c.Entry=q.ReqCreatureOrGOId1 SET q.Title=CONCAT('Prime : ', c.Name), "
             "q.Objectives=CONCAT('Tuez ', q.ReqCreatureOrGOCount1, ' x ', c.Name, '.'), "
             "q.Details=CONCAT(SUBSTRING_INDEX(q.Details, ' : les ', 1), ' : les ', c.Name, ' deviennent trop nombreux. ',"
             "'Une prime est offerte à qui en éliminera ', q.ReqCreatureOrGOCount1, '.$B$BRevenez au tableau une fois le travail fait.') "
             "WHERE q.entry IN (%s);" % ids)
L.append("SELECT 'Primes evenements OK' AS resultat;")
open('/home/claude/wow-serveur/custom/primes_evenements.sql', 'w', encoding='utf-8').write('\n'.join(L) + '\n')
