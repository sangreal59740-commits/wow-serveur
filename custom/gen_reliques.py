# Objets des cases Artefacts et Mascotte (module reliques, addon Reliques) -> reliques.sql (base world)
# Niveaux 10 à 60, budget d'un casque bleu du niveau (budget = niveau) :
#   bleu : Endurance ; rouge : Force ou Intelligence ; vert : critique ou toucher ; jaune : défense, puissance des sorts ou d'attaque
#   mascotte : autant de points de statistiques qu'un casque, répartis sur deux statistiques
# Les effets en % (vert, jaune) sont des sorts « Équipé » générés par gen_sorts.py (confort.py, 65600-65699).
import json

R = json.load(open('/home/claude/wow/classes/reliques_sorts.json', encoding='utf-8'))
NIV = R['niveaux']
SORTS = R['sorts']
VAL = R['valeurs']
ADJ_M = ['brut', 'taillé', 'poli', 'parfait', 'éclatant', 'royal']
ADJ_F = ['brute', 'taillée', 'polie', 'parfaite', 'éclatante', 'royale']
ADJ_PET = ['curieux', 'joueur', 'vaillant', 'robuste', 'fier', 'légendaire']
QUAL = [2, 2, 3, 3, 4, 4]
STAT = {'agi': 3, 'for': 4, 'int': 5, 'esp': 6, 'end': 7}

# (type, nom, genre, complément, affichage, statistique directe ou effet)
ARTEFACTS = [
    (1, "Saphir", 'm', "de vigueur", 1659, ('stat', 'end')),
    (2, "Rubis", 'm', "de puissance", 4777, ('stat', 'for')),
    (2, "Rubis", 'm', "de sagesse", 4777, ('stat', 'int')),
    (3, "Émeraude", 'f', "du tranchant", 6851, ('sort', 'cc')),
    (3, "Émeraude", 'f', "de précision", 6851, ('sort', 'tm')),
    (4, "Topaze", 'f', "du rempart", 7339, ('sort', 'def')),
    (4, "Topaze", 'f', "des arcanes", 7339, ('sort', 'ps')),
    (4, "Topaze", 'f', "du guerrier", 7339, ('sort', 'pa')),
]
MASCOTTES = [
    ("Ourson", 16536, ('for', 'end')),
    ("Chaton", 20629, ('agi', 'end')),
    ("Dragonnet", 20655, ('int', 'end')),
    ("Feu follet", 15788, ('int', 'esp')),
]
COULEUR = {1: "bleu", 2: "rouge", 3: "vert", 4: "jaune"}
COULEUR_F = {1: "bleue", 2: "rouge", 3: "verte", 4: "jaune"}


def esc(s):
    return s.replace("\\", "\\\\").replace("'", "\\'")


L = ["-- Objets des cases Artefacts et Mascotte (généré par gen_reliques.py)", "SET NAMES utf8mb4;",
     "CREATE TABLE IF NOT EXISTS `custom_relique_objet` (`entry` INT UNSIGNED NOT NULL, `type` TINYINT UNSIGNED NOT NULL,"
     " PRIMARY KEY (`entry`)) ENGINE=InnoDB DEFAULT CHARSET=utf8;",
     "DELETE FROM custom_relique_objet WHERE entry BETWEEN 992000 AND 992199;",
     "DELETE FROM item_template WHERE entry BETWEEN 992000 AND 992199;",
     "DROP TEMPORARY TABLE IF EXISTS tmp_it;", "CREATE TEMPORARY TABLE tmp_it LIKE item_template;"]
codes = []


def objet(entry, typ, nom, disp, i, stats, sort, desc):
    lv = NIV[i]
    sets = ["entry=%d" % entry, "class=15", "subclass=0", "name='%s'" % esc(nom), "displayid=%d" % disp, "Quality=%d" % QUAL[i],
            "Flags=0", "BuyCount=1", "BuyPrice=%d" % (lv * lv * 20), "SellPrice=%d" % (lv * lv * 5), "InventoryType=0",
            "AllowableClass=-1", "AllowableRace=-1", "ItemLevel=%d" % lv, "RequiredLevel=%d" % lv, "maxcount=0", "stackable=1",
            "bonding=0", "description='%s'" % esc(desc), "spellid_1=%d" % sort, "spelltrigger_1=%d" % (1 if sort else 0),
            "spellcharges_1=0", "spellcooldown_1=-1", "spellcategory_1=0", "spellcategorycooldown_1=-1", "Material=0",
            "DisenchantID=0", "ScriptName=''", "ExtraFlags=0"]
    for n in range(1, 11):
        st = stats[n - 1] if n <= len(stats) else (0, 0)
        sets += ["stat_type%d=%d" % (n, st[0]), "stat_value%d=%d" % (n, st[1])]
    L.append("INSERT INTO tmp_it SELECT * FROM item_template WHERE entry=8491;")
    L.append("UPDATE tmp_it SET %s WHERE entry=8491;" % ", ".join(sets))
    L.append("INSERT INTO custom_relique_objet (entry, type) VALUES (%d, %d);" % (entry, typ))
    codes.append((entry, nom, lv))


e = 992000
for typ, nom, genre, comp, disp, (k, v) in ARTEFACTS:
    for i, lv in enumerate(NIV):
        adj = (ADJ_M if genre == 'm' else ADJ_F)[i]
        desc = "Artefact %s : se place dans la case %s de la fiche du personnage." % (COULEUR[typ], COULEUR_F[typ])
        if k == 'stat':
            objet(e, typ, "%s %s %s" % (nom, adj, comp), disp, i, [(STAT[v], lv)], 0, desc)
        else:
            objet(e, typ, "%s %s %s" % (nom, adj, comp), disp, i, [], SORTS['%s%d' % (v, VAL[v][str(lv)])], desc)
        e += 1
e = 992100
for nom, disp, (a, b) in MASCOTTES:
    for i, lv in enumerate(NIV):
        objet(e, 5, "%s %s" % (nom, ADJ_PET[i]), disp, i, [(STAT[a], (lv + 1) // 2), (STAT[b], lv // 2)], 0,
              "Mascotte : se place dans la case Mascotte de la fiche du personnage.")
        e += 1
L.append("INSERT INTO item_template SELECT * FROM tmp_it;")
L.append("DROP TEMPORARY TABLE tmp_it;")
open('/home/claude/wow-serveur/custom/reliques.sql', 'w', encoding='utf-8').write("\n".join(L) + "\n")
with open('/home/claude/wow-serveur/custom/reliques_codes.txt', 'w', encoding='utf-8') as f:
    for c in codes:
        f.write(".additem %d   %s (niv. %d)\n" % c)
print('objets', len(codes))
