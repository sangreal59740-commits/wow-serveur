-- Primes dont la cible n'apparaît que pendant un événement : cible remplacée (généré par gen_primes_evenements.py)
UPDATE quest_template SET ReqCreatureOrGOId1=3242 WHERE entry=991517;
UPDATE quest_template SET ReqCreatureOrGOId1=5856 WHERE entry=991617;
UPDATE quest_template SET ReqCreatureOrGOId1=1553 WHERE entry=991630;
UPDATE quest_template SET ReqCreatureOrGOId1=4142 WHERE entry=991755;
UPDATE quest_template SET ReqCreatureOrGOId1=11882 WHERE entry=991827;
UPDATE quest_template q JOIN creature_template c ON c.Entry=q.ReqCreatureOrGOId1 SET q.Title=CONCAT('Prime : ', c.Name), q.Objectives=CONCAT('Tuez ', q.ReqCreatureOrGOCount1, ' x ', c.Name, '.'), q.Details=CONCAT(SUBSTRING_INDEX(q.Details, ' : les ', 1), ' : les ', c.Name, ' deviennent trop nombreux. ','Une prime est offerte à qui en éliminera ', q.ReqCreatureOrGOCount1, '.$B$BRevenez au tableau une fois le travail fait.') WHERE q.entry IN (991517,991617,991630,991755,991827);
SELECT 'Primes evenements OK' AS resultat;
