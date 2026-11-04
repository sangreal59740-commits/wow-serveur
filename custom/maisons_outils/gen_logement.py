# Logement : maisons retenues après le repérage en jeu (export maisons_export.tsv), panneaux de vente, catalogue de meubles,
# retrait des objets de décoration du serveur à l'intérieur des maisons. Sortie : custom/logement.sql
import sys, csv, math, json, subprocess
sys.path.insert(0, '/home/claude/wow-serveur/custom/maisons_outils')
from boites import boite
EXPORT = '/mnt/user-data/uploads/SPP_Classics V2/Custom/maisons_export.tsv'
def q(sql):
    r = subprocess.run(['mysql', '--default-character-set=utf8mb4', '-N', '-B', 'classicmangos', '-e', sql], capture_output=True, text=True, check=True)
    return [l.split('\t') for l in r.stdout.splitlines()]
esc = lambda s: s.replace("\\", "\\\\").replace("'", "''")
VILLE = {'Stormwind City': 'Hurlevent', 'Hurlevent': 'Hurlevent', 'Ironforge': 'Forgefer', 'Forgefer': 'Forgefer', 'Orgrimmar': 'Orgrimmar',
         'Undercity': 'Fossoyeuse', 'Fossoyeuse': 'Fossoyeuse', 'Thunder Bluff': 'Pitons-du-Tonnerre', 'Pitons-du-Tonnerre': 'Pitons-du-Tonnerre',
         'Darnassus': 'Darnassus', 'Elwynn Forest': "Comté-de-l'Or", 'Tirisfal Glades': 'Brill', 'Dun Morogh': 'Kharanos',
         'Teldrassil': 'Dolanaar', 'Mulgore': 'Sabot-de-Sang'}
rows = [r for r in csv.DictReader(open(EXPORT, encoding='utf-8'), delimiter='\t') if r['statut'] == '1']
RETIRER = {'191', '15'}                      # demandé par Alexis : 191 à supprimer, 14 et 15 = la même maison
rows = [r for r in rows if r['id'] not in RETIRER]
for r in rows:
    for k in 'xyzo':
        r[k] = float(r[k])
# doublons (même maison validée deux fois : point à moins de 12 m, même étage)
garde = []
for r in sorted(rows, key=lambda r: int(r['id'])):
    if any(g['map'] == r['map'] and math.hypot(g['x'] - r['x'], g['y'] - r['y']) < 12 and abs(g['z'] - r['z']) < 6 for g in garde):
        continue
    garde.append(r)
maisons = []
for i, r in enumerate(garde, 1):
    m = int(r['map'])
    b, trouve = boite(m, r['x'], r['y'], r['z'])
    surf = (b[3] - b[0]) * (b[4] - b[1])
    prix = 500000 if surf < 300 else 1500000 if surf < 800 else 4000000      # 50 po, 150 po, 400 po
    taille = 'petite' if prix == 500000 else 'moyenne' if prix == 1500000 else 'grande'
    maisons.append(dict(id=i, src=r['id'], ville=VILLE.get(r['zone'], r['zone']), map=m, x=r['x'], y=r['y'], z=r['z'], o=r['o'],
                        b=b, prix=prix, taille=taille, trouve=trouve))
# catalogue de meubles : (modèle client, nom, type 5 objet / 7 siège, places)
CAT = [
 (39, "Chaise simple", 7, 1), (91, "Chaise rembourrée", 7, 1), (92, "Chaise de noble", 7, 1), (648, "Fauteuil nain", 7, 1),
 (2088, "Chaise naine", 7, 1), (4678, "Chaise gnome", 7, 1), (1569, "Chaise en rondins", 7, 1), (138, "Chaise de ferme", 7, 1),
 (2810, "Trône", 7, 1), (682, "Banc en bois", 7, 2), (603, "Banc d'auberge", 7, 2), (622, "Banc de Hurlevent", 7, 2),
 (234, "Table en bois", 5, 0), (221, "Table d'auberge", 5, 0), (581, "Petite table", 5, 0), (3372, "Table naine ornée", 5, 0),
 (3371, "Table de lecture", 5, 0), (4091, "Table gnome", 5, 0), (3471, "Lit", 5, 0), (463, "Lits superposés", 5, 0),
 (392, "Lit à baldaquin", 5, 0), (188, "Bibliothèque", 5, 0), (187, "Grande bibliothèque", 5, 0), (137, "Bibliothèque garnie", 5, 0),
 (189, "Étagère", 5, 0), (4, "Armoire", 5, 0), (4031, "Armoire naine", 5, 0), (1227, "Armoire naine ornée", 5, 0),
 (1568, "Commode elfique", 5, 0), (10, "Coffre", 5, 0), (41, "Coffre ferré", 5, 0), (51, "Coffre des Titans", 5, 0),
 (32, "Tonneau", 5, 0), (288, "Tonneau cerclé", 5, 0), (1727, "Fût de bière", 5, 0), (31, "Caisse", 5, 0),
 (347, "Caisse de grain", 5, 0), (457, "Tonneau orc", 5, 0), (602, "Brasero de Hurlevent", 5, 0), (194, "Brasero magique", 5, 0),
 (201, "Petit brasero", 5, 0), (655, "Grand brasero", 5, 0), (754, "Brasero de Lordaeron", 5, 0), (100, "Bougie", 5, 0),
 (4152, "Bougie noire", 5, 0), (438, "Lanterne elfique", 5, 0), (348, "Poêle", 5, 0), (159, "Tapis", 5, 0),
 (2850, "Tableau", 5, 0), (4731, "Tableau ancien", 5, 0), (624, "Bannière du griffon", 5, 0), (632, "Bannière sacrée", 5, 0),
 (634, "Bannière magique", 5, 0), (4715, "Bannière de Lordaeron", 5, 0), (2552, "Bannière de clan", 5, 0), (130, "Râtelier d'armes", 5, 0),
 (63, "Bouquet de fleurs", 5, 0), (256, "Poterie elfique", 5, 0), (52, "Vase des Titans", 5, 0), (139, "Statue de Khadgar", 5, 0),
 (6, "Statue de lion", 5, 0), (216, "Chaudron", 5, 0), (4391, "Table d'alchimiste", 5, 0),
]
L = ["-- Logement (généré par gen_logement.py) : maisons, panneaux de vente, catalogue de meubles, décoration retirée des maisons"]
L.append("CREATE TABLE IF NOT EXISTS `custom_maison_lieu` (`id` INT UNSIGNED NOT NULL, `ville` VARCHAR(64) NOT NULL, `map` SMALLINT UNSIGNED NOT NULL,"
         " `x` FLOAT NOT NULL, `y` FLOAT NOT NULL, `z` FLOAT NOT NULL, `o` FLOAT NOT NULL,"
         " `x0` FLOAT NOT NULL, `y0` FLOAT NOT NULL, `z0` FLOAT NOT NULL, `x1` FLOAT NOT NULL, `y1` FLOAT NOT NULL, `z1` FLOAT NOT NULL,"
         " `taille` VARCHAR(16) NOT NULL, `prix` INT UNSIGNED NOT NULL, PRIMARY KEY (`id`)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;")
L.append("DELETE FROM `custom_maison_lieu`;")
L.append("INSERT INTO `custom_maison_lieu` VALUES\n" + ",\n".join(
    "(%d, '%s', %d, %.2f, %.2f, %.2f, %.3f, %.2f, %.2f, %.2f, %.2f, %.2f, %.2f, '%s', %d)" % (
        m['id'], esc(m['ville']), m['map'], m['x'], m['y'], m['z'], m['o'], *m['b'], m['taille'], m['prix']) for m in maisons) + ";")
L.append("CREATE TABLE IF NOT EXISTS `custom_maison_catalogue` (`entry` INT UNSIGNED NOT NULL, `num` SMALLINT UNSIGNED NOT NULL, `nom` VARCHAR(64) NOT NULL,"
         " PRIMARY KEY (`entry`)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;")
L.append("DELETE FROM `custom_maison_catalogue`;")
L.append("INSERT INTO `custom_maison_catalogue` VALUES\n" + ",\n".join("(%d, %d, '%s')" % (990600 + i, i + 1, esc(n)) for i, (d, n, t, p) in enumerate(CAT)) + ";")
# modèles d'objets : panneau (990590) et meubles (990600+)
L.append("DELETE FROM `gameobject_template` WHERE `entry` = 990590 OR `entry` BETWEEN 990600 AND 990999;")
L.append("DROP TEMPORARY TABLE IF EXISTS tmp_go;")
L.append("CREATE TEMPORARY TABLE tmp_go LIKE gameobject_template;")
L.append("INSERT INTO tmp_go SELECT * FROM gameobject_template WHERE entry = 2713;")
L.append("UPDATE tmp_go SET entry = 990590, type = 2, displayId = 26, name = 'Maison à vendre', faction = 35, flags = 0, size = 1, data0 = 0, data1 = 0, data2 = 0, data3 = 0;")
L.append("INSERT INTO gameobject_template SELECT * FROM tmp_go;")
for i, (d, n, t, p) in enumerate(CAT):
    L.append("DELETE FROM tmp_go; INSERT INTO tmp_go SELECT * FROM gameobject_template WHERE entry = 2413;")
    L.append("UPDATE tmp_go SET entry = %d, type = %d, displayId = %d, name = '%s', faction = 0, flags = 0, size = 1, data0 = %d, data1 = %d;"
             % (990600 + i, t, d, esc(n), p if t == 7 else 0, 1 if t == 7 else 0))
    L.append("INSERT INTO gameobject_template SELECT * FROM tmp_go;")
L.append("DROP TEMPORARY TABLE tmp_go;")
# panneaux de vente (placés au point repéré, à déplacer devant la porte avec .maison panneau)
L.append("DELETE FROM `gameobject` WHERE `guid` > %d AND `guid` <= 9906999;" % (9906000 + len(maisons)))   # panneaux déplacés avec .maison panneau conservés
L.append("INSERT IGNORE INTO `gameobject` (`guid`, `id`, `map`, `position_x`, `position_y`, `position_z`, `orientation`, `rotation0`, `rotation1`, `rotation2`, `rotation3`, `spawntimesecsmin`, `spawntimesecsmax`) VALUES\n" +
         ",\n".join("(%d, 990590, %d, %.2f, %.2f, %.2f, %.3f, 0, 0, %.5f, %.5f, 25, 25)" % (
             9906000 + m['id'], m['map'], m['x'], m['y'], m['z'], m['o'], math.sin(m['o'] / 2), math.cos(m['o'] / 2)) for m in maisons) + ";")
# décoration du serveur à l'intérieur des maisons : sauvegardée puis retirée (objets génériques et sièges uniquement)
cond = " OR ".join("(g.map = %d AND g.position_x BETWEEN %.2f AND %.2f AND g.position_y BETWEEN %.2f AND %.2f AND g.position_z BETWEEN %.2f AND %.2f)"
                   % (m['map'], m['b'][0], m['b'][3], m['b'][1], m['b'][4], m['b'][2], m['b'][5]) for m in maisons)
import re
_disp = json.load(open('/tmp/claude-0/godisp.json'))
_kw = re.compile(r'chair|table|bed|bookshel|wardrobe|rug|barrel|crate|keg|candle|bench|stool|dresser|shelf|cauldron|stove|flower|pottery|vase', re.I)
MEUBLES_DISP = sorted(int(k) for k, v in _disp.items() if 'passive' in v.lower() and _kw.search(v.split('\\')[-1]))
sel = ("SELECT g.* FROM gameobject g JOIN gameobject_template t ON t.entry = g.id WHERE (t.type = 7 OR (t.type = 5 AND t.displayId IN (%s))) AND g.guid < 9900000 " % ",".join(map(str, MEUBLES_DISP)) +
       "AND g.guid NOT IN (SELECT guid FROM game_event_gameobject) AND (%s)" % cond)
L.append("CREATE TABLE IF NOT EXISTS `custom_maison_deco_retiree` LIKE `gameobject`;")
L.append("INSERT IGNORE INTO `custom_maison_deco_retiree` " + sel + ";")
L.append("DELETE FROM `gameobject` WHERE `guid` IN (SELECT `guid` FROM `custom_maison_deco_retiree`);")
L.append("SELECT 'Logement OK' AS resultat;")
open('/home/claude/wow-serveur/custom/logement.sql', 'w', encoding='utf-8').write("\n".join(L) + "\n")
n = q(sel.replace("SELECT g.*", "SELECT COUNT(*)"))[0][0]
import collections
print('maisons', len(maisons), collections.Counter(m['ville'] for m in maisons), collections.Counter(m['taille'] for m in maisons))
print('boîte trouvée', sum(m['trouve'] for m in maisons), 'objets de déco retirés', n, 'meubles', len(CAT))
json.dump(maisons, open('/tmp/claude-0/maisons/maisons_final.json', 'w'))
