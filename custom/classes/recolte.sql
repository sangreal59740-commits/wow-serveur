-- Récolte : herboristerie et minage x3, dépeçage x2 (composants d artisanat communs : classe 7, qualité commune ou moins, hors gemmes)
-- Les valeurs d'origine sont sauvegardées une fois, le script peut être relancé sans cumuler.
SET NAMES utf8mb4;
CREATE TABLE IF NOT EXISTS custom_backup_recolte_go SELECT gl.* FROM gameobject_loot_template gl
  WHERE gl.entry IN (SELECT DISTINCT data1 FROM gameobject_template WHERE type=3 AND data0 IN (8,9,10,11,26,27,29,30,31,32,33,34,35,45,47,48,49,50,51,259,439,440,441,442,443,444,519,521,1119,1120,1121,1122,1123,1124,18,19,20,21,22,25,38,39,40,41,42,379,380,399,400,719,939));
CREATE TABLE IF NOT EXISTS custom_backup_recolte_skin SELECT * FROM skinning_loot_template;
UPDATE gameobject_loot_template gl
  JOIN custom_backup_recolte_go b ON b.entry=gl.entry AND b.item=gl.item AND b.groupid=gl.groupid
  JOIN item_template it ON it.entry=gl.item
  SET gl.mincountOrRef=b.mincountOrRef*3, gl.maxcount=LEAST(255, b.maxcount*3)
  WHERE b.mincountOrRef>0 AND it.class=7 AND it.Quality<=1;
UPDATE skinning_loot_template sl
  JOIN custom_backup_recolte_skin b ON b.entry=sl.entry AND b.item=sl.item AND b.groupid=sl.groupid
  JOIN item_template it ON it.entry=sl.item
  SET sl.mincountOrRef=b.mincountOrRef*2, sl.maxcount=LEAST(255, b.maxcount*2)
  WHERE b.mincountOrRef>0 AND it.class=7 AND it.Quality<=1;
SELECT 'Recolte OK' AS resultat;
