-- Textes du serveur en français (frFR = loc2), base classicmangos
-- Sauvegarde des textes anglais dans des tables bak_en_*, puis remplacement
SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS `bak_en_creature_template` AS SELECT * FROM `creature_template`;
CREATE TABLE IF NOT EXISTS `bak_en_gameobject_template` AS SELECT * FROM `gameobject_template`;
CREATE TABLE IF NOT EXISTS `bak_en_item_template` AS SELECT * FROM `item_template`;
CREATE TABLE IF NOT EXISTS `bak_en_quest_template` AS SELECT * FROM `quest_template`;
CREATE TABLE IF NOT EXISTS `bak_en_npc_text` AS SELECT * FROM `npc_text`;
CREATE TABLE IF NOT EXISTS `bak_en_page_text` AS SELECT * FROM `page_text`;
CREATE TABLE IF NOT EXISTS `bak_en_points_of_interest` AS SELECT * FROM `points_of_interest`;
CREATE TABLE IF NOT EXISTS `bak_en_gossip_menu_option` AS SELECT * FROM `gossip_menu_option`;
CREATE TABLE IF NOT EXISTS `bak_en_creature_ai_texts` AS SELECT * FROM `creature_ai_texts`;
CREATE TABLE IF NOT EXISTS `bak_en_dbscript_string` AS SELECT * FROM `dbscript_string`;
CREATE TABLE IF NOT EXISTS `bak_en_gossip_texts` AS SELECT * FROM `gossip_texts`;
CREATE TABLE IF NOT EXISTS `bak_en_script_texts` AS SELECT * FROM `script_texts`;
CREATE TABLE IF NOT EXISTS `bak_en_mangos_string` AS SELECT * FROM `mangos_string`;
CREATE TABLE IF NOT EXISTS `bak_en_broadcast_text` AS SELECT * FROM `broadcast_text`;

UPDATE `creature_template` b JOIN `locales_creature` l ON b.`entry` = l.`entry` SET
  b.`Name` = COALESCE(NULLIF(TRIM(l.`name_loc2`),''), b.`Name`),
  b.`SubName` = COALESCE(NULLIF(TRIM(l.`subname_loc2`),''), b.`SubName`);
UPDATE `gameobject_template` b JOIN `locales_gameobject` l ON b.`entry` = l.`entry` SET
  b.`name` = COALESCE(NULLIF(TRIM(l.`name_loc2`),''), b.`name`);
UPDATE `item_template` b JOIN `locales_item` l ON b.`entry` = l.`entry` SET
  b.`name` = COALESCE(NULLIF(TRIM(l.`name_loc2`),''), b.`name`),
  b.`description` = COALESCE(NULLIF(TRIM(l.`description_loc2`),''), b.`description`);
UPDATE `quest_template` b JOIN `locales_quest` l ON b.`entry` = l.`entry` SET
  b.`Title` = COALESCE(NULLIF(TRIM(l.`Title_loc2`),''), b.`Title`),
  b.`Details` = COALESCE(NULLIF(TRIM(l.`Details_loc2`),''), b.`Details`),
  b.`Objectives` = COALESCE(NULLIF(TRIM(l.`Objectives_loc2`),''), b.`Objectives`),
  b.`OfferRewardText` = COALESCE(NULLIF(TRIM(l.`OfferRewardText_loc2`),''), b.`OfferRewardText`),
  b.`RequestItemsText` = COALESCE(NULLIF(TRIM(l.`RequestItemsText_loc2`),''), b.`RequestItemsText`),
  b.`EndText` = COALESCE(NULLIF(TRIM(l.`EndText_loc2`),''), b.`EndText`),
  b.`ObjectiveText1` = COALESCE(NULLIF(TRIM(l.`ObjectiveText1_loc2`),''), b.`ObjectiveText1`),
  b.`ObjectiveText2` = COALESCE(NULLIF(TRIM(l.`ObjectiveText2_loc2`),''), b.`ObjectiveText2`),
  b.`ObjectiveText3` = COALESCE(NULLIF(TRIM(l.`ObjectiveText3_loc2`),''), b.`ObjectiveText3`),
  b.`ObjectiveText4` = COALESCE(NULLIF(TRIM(l.`ObjectiveText4_loc2`),''), b.`ObjectiveText4`);
UPDATE `npc_text` b JOIN `locales_npc_text` l ON b.`ID` = l.`entry` SET
  b.`text0_0` = COALESCE(NULLIF(TRIM(l.`Text0_0_loc2`),''), b.`text0_0`),
  b.`text0_1` = COALESCE(NULLIF(TRIM(l.`Text0_1_loc2`),''), b.`text0_1`),
  b.`text1_0` = COALESCE(NULLIF(TRIM(l.`Text1_0_loc2`),''), b.`text1_0`),
  b.`text1_1` = COALESCE(NULLIF(TRIM(l.`Text1_1_loc2`),''), b.`text1_1`),
  b.`text2_0` = COALESCE(NULLIF(TRIM(l.`Text2_0_loc2`),''), b.`text2_0`),
  b.`text2_1` = COALESCE(NULLIF(TRIM(l.`Text2_1_loc2`),''), b.`text2_1`),
  b.`text3_0` = COALESCE(NULLIF(TRIM(l.`Text3_0_loc2`),''), b.`text3_0`),
  b.`text3_1` = COALESCE(NULLIF(TRIM(l.`Text3_1_loc2`),''), b.`text3_1`),
  b.`text4_0` = COALESCE(NULLIF(TRIM(l.`Text4_0_loc2`),''), b.`text4_0`),
  b.`text4_1` = COALESCE(NULLIF(TRIM(l.`Text4_1_loc2`),''), b.`text4_1`),
  b.`text5_0` = COALESCE(NULLIF(TRIM(l.`Text5_0_loc2`),''), b.`text5_0`),
  b.`text5_1` = COALESCE(NULLIF(TRIM(l.`Text5_1_loc2`),''), b.`text5_1`),
  b.`text6_0` = COALESCE(NULLIF(TRIM(l.`Text6_0_loc2`),''), b.`text6_0`),
  b.`text6_1` = COALESCE(NULLIF(TRIM(l.`Text6_1_loc2`),''), b.`text6_1`),
  b.`text7_0` = COALESCE(NULLIF(TRIM(l.`Text7_0_loc2`),''), b.`text7_0`),
  b.`text7_1` = COALESCE(NULLIF(TRIM(l.`Text7_1_loc2`),''), b.`text7_1`);
UPDATE `page_text` b JOIN `locales_page_text` l ON b.`entry` = l.`entry` SET
  b.`text` = COALESCE(NULLIF(TRIM(l.`Text_loc2`),''), b.`text`);
UPDATE `points_of_interest` b JOIN `locales_points_of_interest` l ON b.`entry` = l.`entry` SET
  b.`icon_name` = COALESCE(NULLIF(TRIM(l.`icon_name_loc2`),''), b.`icon_name`);
UPDATE `gossip_menu_option` b JOIN `locales_gossip_menu_option` l ON b.`menu_id` = l.`menu_id` AND b.`id` = l.`id` SET
  b.`option_text` = COALESCE(NULLIF(TRIM(l.`option_text_loc2`),''), b.`option_text`),
  b.`box_text` = COALESCE(NULLIF(TRIM(l.`box_text_loc2`),''), b.`box_text`);
UPDATE `creature_ai_texts` SET `content_default` = COALESCE(NULLIF(TRIM(`content_loc2`),''), `content_default`);
UPDATE `dbscript_string` SET `content_default` = COALESCE(NULLIF(TRIM(`content_loc2`),''), `content_default`);
UPDATE `gossip_texts` SET `content_default` = COALESCE(NULLIF(TRIM(`content_loc2`),''), `content_default`);
UPDATE `script_texts` SET `content_default` = COALESCE(NULLIF(TRIM(`content_loc2`),''), `content_default`);
UPDATE `mangos_string` SET `content_default` = COALESCE(NULLIF(TRIM(`content_loc2`),''), `content_default`);
UPDATE `broadcast_text` b JOIN `broadcast_text_locale` l ON b.`Id` = l.`Id` AND l.`Locale` = 'frFR' SET
  b.`Text` = COALESCE(NULLIF(TRIM(l.`Text_lang`),''), b.`Text`),
  b.`Text1` = COALESCE(NULLIF(TRIM(l.`Text1_lang`),''), b.`Text1`);
