-- Suppression des bots aléatoires actuels (faite par le serveur à son prochain démarrage)
INSERT INTO ai_playerbot_random_bots (owner, bot, time, validIn, event, value, data) VALUES (0, 0, UNIX_TIMESTAMP(), 0, 'bot_delete', 1, '');
SELECT 'Purge des bots programmée' AS resultat;
