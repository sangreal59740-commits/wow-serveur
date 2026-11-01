-- Remise à zéro des talents des classes custom (après un changement de numérotation des talents).
-- Les points sont rendus à la connexion.
DELETE FROM character_spell WHERE spell BETWEEN 63500 AND 64499;
DELETE FROM custom_spec_talent WHERE spell BETWEEN 63500 AND 64499;
SELECT 'Talents custom remis a zero' AS resultat;
