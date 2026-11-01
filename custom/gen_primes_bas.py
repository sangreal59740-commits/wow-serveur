# Primes des zones de départ : les cibles de niveau < 5 (vallée de départ) sont remplacées par des monstres de niveau 5 à 10
# autour de la première ville (où se trouve le tableau). Les numéros de quête ne changent pas.
import math, subprocess
from collections import defaultdict
def q(sql):
    r = subprocess.run(['mysql', '--default-character-set=utf8mb4', '-N', '-B', 'classicmangos', '-e', sql], capture_output=True, text=True, check=True)
    return [l.split('\t') for l in r.stdout.splitlines()]
low = q("select entry, ZoneOrSort, ReqCreatureOrGOId1, ReqItemId1, ReqItemCount1, ReqCreatureOrGOCount1 from quest_template "
        "where entry between 991400 and 991999 and QuestLevel < 5 and (ReqCreatureOrGOId1 between 1 and 989999 or ReqItemId1 > 0)")
board_q = defaultdict(set)
for e, z, c, i in q("select entry, ZoneOrSort, ReqCreatureOrGOId1, ReqItemId1 from quest_template where entry between 991400 and 991999"):
    board_q[z].add((int(c), int(i)))
xpl = {int(lv): (float(a), float(b)) for lv, a, b in q(
    "select QuestLevel, avg(RewMoneyMaxLevel), avg(greatest(RewOrReqMoney,0)) from quest_template where Type=0 and QuestLevel between 1 and 60 "
    "and RewMoneyMaxLevel>0 and entry < 990000 group by QuestLevel")}
# tableaux : position (pour chercher les monstres autour de la ville)
boards = {}
for gid, m, x, y in q("select g.id, g.map, g.position_x, g.position_y from gameobject g where g.id between 990500 and 990599"):
    boards.setdefault(int(gid), (int(m), float(x), float(y)))
zone_board = {}
for z, gid in q("select q.ZoneOrSort, r.id from quest_template q join gameobject_questrelation r on r.quest=q.entry where q.entry between 991400 and 991999 group by q.ZoneOrSort, r.id"):
    zone_board[z] = int(gid)
def cands(m, x, y, need_loot):
    rows = q("select c.id, count(*) n, t.MaxLevel, t.LootId from creature c join creature_template t on t.Entry=c.id "
             "where c.map=%d and pow(c.position_x-(%f),2)+pow(c.position_y-(%f),2) < 900*900 and t.MaxLevel between 5 and 10 and t.Rank=0 "
             "and t.NpcFlags=0 and t.LootId>0 and (t.UnitFlags & (2|256|33554432))=0 and c.id < 990000 "
             "and t.Faction in (7,14,16,22,24,38,44,48,54,90,130,190,310,311,415,416,1554) group by c.id having n >= 6 order by t.MaxLevel, n desc" % (m, x, y))
    return [(int(e), int(n), int(lv), int(lt)) for e, n, lv, lt in rows]
L = ["-- Primes des zones de départ remontées au niveau 5+ (généré par gen_primes_bas.py)"]
done = []
for e, z, c, i, ic, cc in low:
    m, x, y = boards[zone_board[z]]
    used = board_q[z]
    lst = cands(m, x, y, int(i) > 0)
    pick = None
    for ce, n, lv, lt in lst:
        if int(i) > 0:
            items = [int(it) for (it,) in q("select l.item from creature_loot_template l join item_template t on t.entry=l.item where l.entry=%d "
                     "and l.mincountOrRef>0 and l.ChanceOrQuestChance>=25 and l.groupid=0 and t.class in (7,15) and t.Quality<=1 and t.bonding=0 "
                     "and t.startquest=0 and t.name not like '%%Deprecated%%'" % lt)]
            items = [it for it in items if all(it != u[1] for u in used)]
            if items:
                pick = (ce, lv, items[0]); break
        elif all(ce != u[0] for u in used):
            pick = (ce, lv, 0); break
    if not pick:
        print('pas de remplaçant pour', e); continue
    ce, lv, it = pick
    used.add((ce, it))
    rmm, money = xpl.get(lv, (lv * 40.0, lv * 50.0))
    rmm, money = int(rmm * 0.8), int(max(money, lv * 30) * 0.8)
    if it:
        L.append("UPDATE quest_template SET ReqItemId1=%d, QuestLevel=%d, MinLevel=%d, RewOrReqMoney=%d, RewMoneyMaxLevel=%d WHERE entry=%s;"
                 % (it, lv, max(1, lv - 6), money, rmm, e))
    else:
        L.append("UPDATE quest_template SET ReqCreatureOrGOId1=%d, ReqCreatureOrGOCount1=%d, QuestLevel=%d, MinLevel=%d, RewOrReqMoney=%d, RewMoneyMaxLevel=%d WHERE entry=%s;"
                 % (ce, max(6, min(12, int(cc))), lv, max(1, lv - 6), money, rmm, e))
    done.append(e)
ids = ','.join(done)
L.append("UPDATE quest_template q JOIN creature_template c ON c.Entry=q.ReqCreatureOrGOId1 SET q.Title=CONCAT('Prime : ', c.Name), "
         "q.Objectives=CONCAT('Tuez ', q.ReqCreatureOrGOCount1, ' x ', c.Name, '.'), "
         "q.Details=CONCAT(SUBSTRING_INDEX(q.Details, ' : les ', 1), ' : les ', c.Name, ' deviennent trop nombreux. ',"
         "'Une prime est offerte à qui en éliminera ', q.ReqCreatureOrGOCount1, '.$B$BRevenez au tableau une fois le travail fait.') "
         "WHERE q.entry IN (%s) AND q.ReqCreatureOrGOId1>0;" % ids)
L.append("UPDATE quest_template q JOIN item_template i ON i.entry=q.ReqItemId1 SET q.Title=CONCAT('Récolte : ', i.name), "
         "q.Objectives=CONCAT('Rapportez ', q.ReqItemCount1, ' x ', i.name, '.'), "
         "q.Details=CONCAT(SUBSTRING_INDEX(q.Details, ' paie bien pour ', 1), ' paie bien pour ', q.ReqItemCount1, ' x ', i.name, '. ',"
         "'On en trouve sur les créatures des environs.$B$BRapportez-les au tableau de primes.') "
         "WHERE q.entry IN (%s) AND q.ReqItemId1>0;" % ids)
L.append("SELECT 'Primes OK' AS resultat;")
open('/home/claude/wow/monde/primes_bas.sql', 'w', encoding='utf-8').write('\n'.join(L) + '\n')
print('modifiées', len(done))
for l in L[1:len(done)+1]: print(l[:140])
