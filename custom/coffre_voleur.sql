-- Coffre d'équipement du voleur niveau 15 : .additem 990760 (clic droit pour l'ouvrir)
DELETE FROM item_template WHERE entry = 990760;
DROP TEMPORARY TABLE IF EXISTS tmp_coffre;
CREATE TEMPORARY TABLE tmp_coffre SELECT * FROM item_template WHERE entry = 20602;
UPDATE tmp_coffre SET entry = 990760, name = 'Coffre d''équipement du voleur (niv. 15)', Quality = 2, Flags = 4, bonding = 0, description = 'Tenue complète de voleur niveau 15, armes comprises.', BuyPrice = 0, SellPrice = 0, RequiredLevel = 0, ItemLevel = 15, startquest = 0;
INSERT INTO item_template SELECT * FROM tmp_coffre;
DROP TEMPORARY TABLE tmp_coffre;
DELETE FROM item_loot_template WHERE entry = 990760;
INSERT INTO item_loot_template (entry, item, ChanceOrQuestChance, groupid, mincountOrRef, maxcount, condition_id, comments) VALUES
(990760, 994097, 100, 0, 1, 1, 0, 'coffre voleur niv 15'),
(990760, 6179, 100, 0, 1, 1, 0, 'coffre voleur niv 15'),
(990760, 3313, 100, 0, 1, 1, 0, 'coffre voleur niv 15'),
(990760, 14561, 100, 0, 1, 1, 0, 'coffre voleur niv 15'),
(990760, 1314, 100, 0, 1, 1, 0, 'coffre voleur niv 15'),
(990760, 14559, 100, 0, 1, 1, 0, 'coffre voleur niv 15'),
(990760, 10400, 100, 0, 1, 1, 0, 'coffre voleur niv 15'),
(990760, 4788, 100, 0, 1, 1, 0, 'coffre voleur niv 15'),
(990760, 12976, 100, 0, 1, 1, 0, 'coffre voleur niv 15'),
(990760, 935, 100, 0, 1, 1, 0, 'coffre voleur niv 15'),
(990760, 3040, 100, 0, 1, 1, 0, 'coffre voleur niv 15');
