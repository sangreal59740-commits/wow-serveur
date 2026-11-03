-- Primes des tableaux : expérience x1,5 (l'XP d'une quête vient de RewMoneyMaxLevel)
-- Valeurs d'origine sauvegardées une fois : le script peut être relancé sans cumuler.
CREATE TABLE IF NOT EXISTS custom_backup_primes_xp SELECT entry, RewMoneyMaxLevel FROM quest_template WHERE entry BETWEEN 991400 AND 991999;
UPDATE quest_template q JOIN custom_backup_primes_xp b ON b.entry = q.entry SET q.RewMoneyMaxLevel = ROUND(b.RewMoneyMaxLevel * 1.5);
SELECT 'Primes XP OK' AS resultat;
