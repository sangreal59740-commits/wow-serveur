# Points d'interrogation et d'exclamation au-dessus des tableaux de primes -> marqueurs.sql (base world, après tableaux.sql)
# Le client 1.12 n'affiche pas l'état des quêtes au-dessus des objets : une créature invisible (modèle 11686, non sélectionnable)
# flotte 2,2 m au-dessus de chaque tableau et donne les mêmes quêtes, le client affiche donc ! ou ? au-dessus d'elle.
L = ["-- Marqueurs de quête des tableaux de primes (généré par gen_marqueurs.py)", "SET NAMES utf8mb4;",
     "DELETE FROM creature WHERE guid BETWEEN 9910000 AND 9912999;",
     "DELETE FROM creature_questrelation WHERE id BETWEEN 990900 AND 990999;",
     "DELETE FROM creature_involvedrelation WHERE id BETWEEN 990900 AND 990999;",
     "DELETE FROM creature_template WHERE Entry BETWEEN 990900 AND 990999;",
     "DROP TEMPORARY TABLE IF EXISTS tmp_ct;", "CREATE TEMPORARY TABLE tmp_ct LIKE creature_template;"]
for e in range(990500, 990600):
    c = e - 990500 + 990900
    L.append("INSERT INTO tmp_ct SELECT * FROM creature_template WHERE Entry=11494 AND EXISTS (SELECT 1 FROM gameobject_template WHERE entry=%d);" % e)
    L.append("UPDATE tmp_ct SET Entry=%d, Name='Tableau des primes', SubName='', MinLevel=1, MaxLevel=1, Faction=35, NpcFlags=2, "
             "UnitFlags=33554434, InhabitType=4, Scale=1, GossipMenuId=0, LootId=0, AIName='', ScriptName='' WHERE Entry=11494;" % c)
L += ["INSERT INTO creature_template SELECT * FROM tmp_ct;", "DROP TEMPORARY TABLE tmp_ct;",
      "INSERT INTO creature_questrelation (id, quest) SELECT id - 990500 + 990900, quest FROM gameobject_questrelation WHERE id BETWEEN 990500 AND 990599;",
      "INSERT INTO creature_involvedrelation (id, quest) SELECT id - 990500 + 990900, quest FROM gameobject_involvedrelation WHERE id BETWEEN 990500 AND 990599;",
      "INSERT INTO creature (guid, id, map, spawnMask, position_x, position_y, position_z, orientation, spawntimesecsmin, spawntimesecsmax, "
      "spawndist, MovementType) SELECT guid - 9905000 + 9910000, id - 990500 + 990900, map, 1, position_x, position_y, position_z + 2.2, "
      "orientation, 30, 30, 0, 0 FROM gameobject WHERE id BETWEEN 990500 AND 990599;",
      "SELECT 'Marqueurs OK' AS resultat;"]
open('/home/claude/wow-serveur/custom/marqueurs.sql', 'w', encoding='utf-8').write("\n".join(L) + "\n")
print(len(L))
