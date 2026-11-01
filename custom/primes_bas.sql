-- Primes des zones de départ remontées au niveau 5+ (généré par gen_primes_bas.py)
UPDATE quest_template SET ReqCreatureOrGOId1=1128, ReqCreatureOrGOCount1=12, QuestLevel=6, MinLevel=1, RewOrReqMoney=144, RewMoneyMaxLevel=178 WHERE entry=991400;
UPDATE quest_template SET ReqItemId1=4865, QuestLevel=6, MinLevel=1, RewOrReqMoney=144, RewMoneyMaxLevel=178 WHERE entry=991408;
UPDATE quest_template SET ReqCreatureOrGOId1=30, ReqCreatureOrGOCount1=12, QuestLevel=6, MinLevel=1, RewOrReqMoney=144, RewMoneyMaxLevel=178 WHERE entry=991460;
UPDATE quest_template SET ReqCreatureOrGOId1=3106, ReqCreatureOrGOCount1=12, QuestLevel=6, MinLevel=1, RewOrReqMoney=144, RewMoneyMaxLevel=178 WHERE entry=991472;
UPDATE quest_template SET ReqCreatureOrGOId1=1547, ReqCreatureOrGOCount1=12, QuestLevel=6, MinLevel=1, RewOrReqMoney=144, RewMoneyMaxLevel=178 WHERE entry=991628;
UPDATE quest_template SET ReqCreatureOrGOId1=1998, ReqCreatureOrGOCount1=12, QuestLevel=6, MinLevel=1, RewOrReqMoney=144, RewMoneyMaxLevel=178 WHERE entry=991664;
UPDATE quest_template SET ReqItemId1=5465, QuestLevel=6, MinLevel=1, RewOrReqMoney=144, RewMoneyMaxLevel=178 WHERE entry=991670;
UPDATE quest_template SET ReqCreatureOrGOId1=2959, ReqCreatureOrGOCount1=12, QuestLevel=8, MinLevel=2, RewOrReqMoney=192, RewMoneyMaxLevel=320 WHERE entry=991688;
UPDATE quest_template q JOIN creature_template c ON c.Entry=q.ReqCreatureOrGOId1 SET q.Title=CONCAT('Prime : ', c.Name), q.Objectives=CONCAT('Tuez ', q.ReqCreatureOrGOCount1, ' x ', c.Name, '.'), q.Details=CONCAT(SUBSTRING_INDEX(q.Details, ' : les ', 1), ' : les ', c.Name, ' deviennent trop nombreux. ','Une prime est offerte à qui en éliminera ', q.ReqCreatureOrGOCount1, '.$B$BRevenez au tableau une fois le travail fait.') WHERE q.entry IN (991400,991408,991460,991472,991628,991664,991670,991688) AND q.ReqCreatureOrGOId1>0;
UPDATE quest_template q JOIN item_template i ON i.entry=q.ReqItemId1 SET q.Title=CONCAT('Récolte : ', i.name), q.Objectives=CONCAT('Rapportez ', q.ReqItemCount1, ' x ', i.name, '.'), q.Details=CONCAT(SUBSTRING_INDEX(q.Details, ' paie bien pour ', 1), ' paie bien pour ', q.ReqItemCount1, ' x ', i.name, '. ','On en trouve sur les créatures des environs.$B$BRapportez-les au tableau de primes.') WHERE q.entry IN (991400,991408,991460,991472,991628,991664,991670,991688) AND q.ReqItemId1>0;
SELECT 'Primes OK' AS resultat;
