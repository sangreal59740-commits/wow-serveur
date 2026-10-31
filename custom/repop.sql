-- Réapparition plus rapide des monstres du monde extérieur (Royaumes de l'Est + Kalimdor)
-- Monstres normaux et élites dont le délai est entre 1 et 30 min : délai x0,4 (5 min -> 2 min), 30 s minimum.
-- Rares, boss et monstres à long délai (événements, quêtes spéciales) : inchangés. Relançable sans risque.
CREATE TABLE IF NOT EXISTS bak_q1_creature_spawn AS SELECT guid, spawntimesecsmin, spawntimesecsmax FROM creature;
UPDATE creature c JOIN bak_q1_creature_spawn b ON b.guid=c.guid SET c.spawntimesecsmin=b.spawntimesecsmin, c.spawntimesecsmax=b.spawntimesecsmax;
UPDATE creature c JOIN bak_q1_creature_spawn b ON b.guid=c.guid JOIN creature_template t ON t.Entry=c.id
 SET c.spawntimesecsmin=GREATEST(30, ROUND(b.spawntimesecsmin*0.4)), c.spawntimesecsmax=GREATEST(30, ROUND(b.spawntimesecsmax*0.4))
 WHERE c.map IN (0,1) AND t.Rank IN (0,1) AND b.spawntimesecsmin BETWEEN 60 AND 1800 AND b.spawntimesecsmax <= 1800;
SELECT 'Repop OK' AS resultat;
