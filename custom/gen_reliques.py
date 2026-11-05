# Artefacts et mascottes (module reliques, addon Reliques) -> reliques.sql (base world)
#   Artefacts : 4 couleurs, une statistique au budget d'un casque du palier (10 à 60 en bleu, 60 épique en violet) :
#     bleu Endurance ; rouge Force ou Intelligence ; vert critique ou toucher ; jaune défense, puissance des sorts ou d'attaque
#     butin : coffret d'artefact (couleur au hasard) en récompense des quêtes élites du tableau des primes ;
#             un artefact par boss de donjon (couleur tirée au hasard), au taux d'un objet bleu de ce boss ; les raids donnent le 60 épique
#     machine à artefacts près des hôtels des ventes : couleur + palier contre des composants (table custom_relique_recette)
#   Mascottes : les compagnons du jeu, deux statistiques au budget d'un casque bleu du niveau du joueur (calcul dans le module) ;
#     butin : 20 % sur les boss rares des donjons, mascotte au hasard
import json
import math
import random
import subprocess

R = json.load(open('/home/claude/wow/classes/reliques_sorts.json', encoding='utf-8'))
BUDGETS = R['niveaux']                      # 10 20 30 40 50 60 89
SORTS = R['sorts']
VAL = R['valeurs']
PALIERS = [10, 20, 30, 40, 50, 60, 60]      # niveau requis par palier
QUAL = [3, 3, 3, 3, 3, 3, 4]
ADJ_M = ['brut', 'taillé', 'poli', 'parfait', 'éclatant', 'royal', 'ancestral']
ADJ_F = ['brute', 'taillée', 'polie', 'parfaite', 'éclatante', 'royale', 'ancestrale']
STAT = {'agi': 3, 'for': 4, 'int': 5, 'esp': 6, 'end': 7}
COULEUR = {1: "bleu", 2: "rouge", 3: "vert", 4: "jaune"}
COULEUR_F = {1: "bleue", 2: "rouge", 3: "verte", 4: "jaune"}
RAIDS = {409, 469, 309, 509, 531, 533, 249}
HORS_DONJON = {0, 1, 30, 489, 529}


def q(sql):
    r = subprocess.run(['mysql', '-N', '--default-character-set=utf8mb4', 'classicmangos', '-e', sql], capture_output=True, text=True, check=True)
    return [l.split('\t') for l in r.stdout.splitlines() if l]


def esc(s):
    return s.replace("\\", "\\\\").replace("'", "\\'")


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


def entree_artefact(v, i):
    return 992000 + v * 6 + i if i < 6 else 992060 + v


# mascottes du jeu : objet -> (statistique 1, statistique 2) ; chaque couple possible apparaît au moins une fois
MASCOTTES = {
    8485: ('agi', 'pa'), 8486: ('agi', 'cc'), 8487: ('agi', 'tm'), 8488: ('agi', 'end'), 8489: ('agi', 'esp'), 8490: ('agi', 'int'),
    8491: ('for', 'agi'), 11903: ('agi', 'ps'),                                                     # chats
    8498: ('int', 'esp'), 8499: ('int', 'ps'), 10822: ('ps', 'cc'), 19054: ('ps', 'tm'), 19055: ('esp', 'ps'), 11474: ('int', 'cc'),  # dragonnets
    8492: ('esp', 'tm'), 8494: ('int', 'tm'), 8495: ('esp', 'cc'), 8496: ('end', 'esp'), 8500: ('end', 'int'), 8501: ('cc', 'tm'),
    11110: ('for', 'esp'), 11023: ('esp', 'def'), 12185: ('pa', 'cc'),                              # oiseaux
    18963: ('end', 'def'), 18964: ('for', 'def'), 18965: ('agi', 'def'), 18966: ('tm', 'def'), 18967: ('cc', 'def'),  # tortues
    13583: ('for', 'end'), 12264: ('for', 'pa'), 13582: ('pa', 'tm'), 13584: ('for', 'ps'), 12529: ('end', 'cc'),
    10360: ('end', 'tm'), 10361: ('for', 'cc'), 10392: ('for', 'tm'),                              # serpents
    20371: ('int', 'pa'), 20651: ('end', 'ps'), 22114: ('esp', 'pa'), 22780: ('ps', 'pa'),          # murlocs
    4401: ('pa', 'def'), 10398: ('ps', 'def'), 11825: ('for', 'int'), 11826: ('int', 'def'), 21277: ('end', 'pa'),  # mécaniques
    8497: ('agi', 'esp'), 10394: ('end', 'esp'), 10393: ('end', 'def'), 11026: ('int', 'esp'), 11027: ('agi', 'int'), 15996: ('end', 'int'),
    18153: ('for', 'cc'), 18155: ('int', 'esp'), 18156: ('agi', 'tm'), 18157: ('ps', 'cc'), 18158: ('pa', 'tm'), 18159: ('esp', 'ps'),
    18597: ('for', 'end'), 18598: ('end', 'esp'), 19450: ('agi', 'cc'), 20769: ('end', 'ps'), 21168: ('agi', 'pa'),
    21301: ('int', 'ps'), 21305: ('for', 'pa'), 21308: ('agi', 'end'), 21309: ('end', 'def'), 22235: ('int', 'cc'),
    22781: ('for', 'end'), 23002: ('end', 'def'), 23007: ('for', 'end'), 23015: ('agi', 'tm'), 23083: ('int', 'ps'),
    23712: ('agi', 'pa'), 23713: ('agi', 'esp'),
}
_S = ['for', 'agi', 'end', 'int', 'esp', 'ps', 'pa', 'cc', 'tm', 'def']
_manque = [(a, b) for i, a in enumerate(_S) for b in _S[i + 1:] if (a, b) not in MASCOTTES.values() and (b, a) not in MASCOTTES.values()]
assert not _manque, _manque
_existe = {int(r[0]) for r in q("SELECT entry FROM item_template WHERE entry IN (%s)" % ",".join(map(str, MASCOTTES)))}
assert _existe == set(MASCOTTES), set(MASCOTTES) - _existe

L = ["-- Artefacts et mascottes (généré par gen_reliques.py)", "SET NAMES utf8mb4;",
     "CREATE TABLE IF NOT EXISTS `custom_relique_objet` (`entry` INT UNSIGNED NOT NULL, `type` TINYINT UNSIGNED NOT NULL,"
     " PRIMARY KEY (`entry`)) ENGINE=InnoDB DEFAULT CHARSET=utf8;",
     "DROP TABLE IF EXISTS `custom_relique_mascotte`;",
     "CREATE TABLE `custom_relique_mascotte` (`entry` INT UNSIGNED NOT NULL, `stat1` VARCHAR(4) NOT NULL, `stat2` VARCHAR(4) NOT NULL,"
     " PRIMARY KEY (`entry`)) ENGINE=InnoDB DEFAULT CHARSET=utf8;",
     "DROP TABLE IF EXISTS `custom_relique_recette`;",
     "CREATE TABLE `custom_relique_recette` (`couleur` TINYINT UNSIGNED NOT NULL, `palier` TINYINT UNSIGNED NOT NULL,"
     " `objet1` INT UNSIGNED NOT NULL DEFAULT 0, `nombre1` INT UNSIGNED NOT NULL DEFAULT 0,"
     " `objet2` INT UNSIGNED NOT NULL DEFAULT 0, `nombre2` INT UNSIGNED NOT NULL DEFAULT 0,"
     " `objet3` INT UNSIGNED NOT NULL DEFAULT 0, `nombre3` INT UNSIGNED NOT NULL DEFAULT 0,"
     " `objet4` INT UNSIGNED NOT NULL DEFAULT 0, `nombre4` INT UNSIGNED NOT NULL DEFAULT 0,"
     " `argent` INT UNSIGNED NOT NULL DEFAULT 0, PRIMARY KEY (`couleur`, `palier`)) ENGINE=InnoDB DEFAULT CHARSET=utf8;",
     "DELETE FROM custom_relique_objet;",
     "DELETE FROM item_template WHERE entry BETWEEN 992000 AND 992299;",
     "DELETE FROM item_loot_template WHERE entry BETWEEN 992000 AND 992299;",
     "DELETE FROM reference_loot_template WHERE entry BETWEEN 99300 AND 99309;",
     "DELETE FROM creature_loot_template WHERE item BETWEEN 992000 AND 992299 OR item BETWEEN 99300 AND 99309;",
     "DROP TEMPORARY TABLE IF EXISTS tmp_it;", "CREATE TEMPORARY TABLE tmp_it LIKE item_template;"]
codes = []


def objet(entry, typ, nom, disp, i, stats, sort, desc, flags=0, base=8491):
    lv = PALIERS[i]
    sets = ["entry=%d" % entry, "class=15", "subclass=0", "name='%s'" % esc(nom), "displayid=%d" % disp, "Quality=%d" % QUAL[i],
            "Flags=%d" % flags, "BuyCount=1", "BuyPrice=%d" % (lv * lv * 20), "SellPrice=%d" % (lv * lv * 5), "InventoryType=0",
            "AllowableClass=-1", "AllowableRace=-1", "ItemLevel=%d" % (lv + (5 if i == 6 else 0)), "RequiredLevel=%d" % lv, "maxcount=0",
            "stackable=1", "bonding=0", "description='%s'" % esc(desc), "spellid_1=%d" % sort, "spelltrigger_1=%d" % (1 if sort else 0),
            "spellcharges_1=0", "spellcooldown_1=-1", "spellcategory_1=0", "spellcategorycooldown_1=-1",
            "spellid_2=0", "spelltrigger_2=0", "Material=0", "DisenchantID=0", "ScriptName=''", "ExtraFlags=0"]
    for n in range(1, 11):
        st = stats[n - 1] if n <= len(stats) else (0, 0)
        sets += ["stat_type%d=%d" % (n, st[0]), "stat_value%d=%d" % (n, st[1])]
    L.append("INSERT INTO tmp_it SELECT * FROM item_template WHERE entry=%d;" % base)
    L.append("UPDATE tmp_it SET %s WHERE entry=%d;" % (", ".join(sets), base))
    if typ:
        L.append("INSERT INTO custom_relique_objet (entry, type) VALUES (%d, %d);" % (entry, typ))
    codes.append((entry, nom, lv))


# ---------------------------------------------------------------- artefacts
for v, (typ, nom, genre, comp, disp, (k, s)) in enumerate(ARTEFACTS):
    for i, budget in enumerate(BUDGETS):
        adj = (ADJ_M if genre == 'm' else ADJ_F)[i]
        desc = "Artefact %s : se place dans la case %s de la fiche du personnage." % (COULEUR[typ], COULEUR_F[typ])
        nomc = "%s %s %s" % (nom, adj, comp)
        if k == 'stat':
            objet(entree_artefact(v, i), typ, nomc, disp, i, [(STAT[s], budget)], 0, desc)
        else:
            objet(entree_artefact(v, i), typ, nomc, disp, i, [], SORTS['%s%d' % (s, VAL[s][str(budget)])], desc)

# coffrets : un artefact au hasard du palier, chaque couleur a 25 % de chance
COFFRET = [992200 + i for i in range(7)]
_par_couleur = {}
for v, a in enumerate(ARTEFACTS):
    _par_couleur.setdefault(a[0], []).append(v)
for i in range(7):
    nom = "Coffret d'artefact épique" if i == 6 else "Coffret d'artefact (niveau %d)" % PALIERS[i]
    objet(COFFRET[i], 0, nom, 16028, i, [], 0, "Un artefact de couleur au hasard, adapté à votre personnage.", base=9541)
    L.append("UPDATE tmp_it SET spellid_1=65590, spelltrigger_1=0, spellcharges_1=-1 WHERE entry=%d;" % COFFRET[i])
    for c, vs in _par_couleur.items():
        for v in vs:
            L.append("INSERT INTO item_loot_template (entry, item, ChanceOrQuestChance, groupid, mincountOrRef, maxcount) "
                     "VALUES (%d, %d, %.4f, 1, 1, 1);" % (COFFRET[i], entree_artefact(v, i), 25.0 / len(vs)))

# ---------------------------------------------------------------- mascottes
for e, (a, b) in sorted(MASCOTTES.items()):
    L.append("INSERT INTO custom_relique_objet (entry, type) VALUES (%d, 5);" % e)
    L.append("INSERT INTO custom_relique_mascotte (entry, stat1, stat2) VALUES (%d, '%s', '%s');" % (e, a, b))
L.append("INSERT INTO item_template SELECT * FROM tmp_it;")
L.append("DROP TEMPORARY TABLE tmp_it;")


def palier(niveau):
    return min(max(int(niveau) // 10, 1), 6) - 1


# ---------------------------------------------------------------- quêtes élites du tableau des primes : coffret en récompense
_qe = q("SELECT entry, QuestLevel, RewItemId1, RewItemId2, RewItemId3, RewItemId4 FROM quest_template WHERE entry BETWEEN 991000 AND 991999 AND Type=1")
nq = 0
for r in _qe:
    e, lv = int(r[0]), int(r[1])
    libres = [n for n in range(1, 5) if int(r[1 + n]) == 0 or 992200 <= int(r[1 + n]) <= 992206]
    if not libres:
        continue
    n = libres[0]
    L.append("UPDATE quest_template SET RewItemId%d=%d, RewItemCount%d=1 WHERE entry=%d;" % (n, COFFRET[palier(lv)], n, e))
    nq += 1

# ---------------------------------------------------------------- boss de donjon : un artefact chacun, au taux d'un objet bleu
qualite = {int(a): int(b) for a, b in q("SELECT entry, Quality FROM item_template")}
loot = {}
for t in ('creature_loot_template', 'reference_loot_template'):
    for e, it, ch, g, mc in q("SELECT entry, item, ChanceOrQuestChance, groupid, mincountOrRef FROM %s" % t):
        loot.setdefault((t, int(e)), []).append((int(it), float(ch), int(g), int(mc)))


def probas(table, entry, facteur=1.0, prof=0):
    """objet -> probabilité dans la table de butin (références comprises)"""
    res = {}
    lignes = loot.get((table, entry), [])
    groupes = {}
    for it, ch, g, mc in lignes:
        groupes.setdefault(g, []).append((it, ch, mc))
    for g, ls in groupes.items():
        if g == 0:
            parts = [(it, abs(ch) / 100.0, mc) for it, ch, mc in ls]
        else:
            fixe = sum(abs(ch) for it, ch, mc in ls if ch != 0)
            nuls = [x for x in ls if x[1] == 0]
            reste = max(0.0, 100.0 - fixe) / len(nuls) if nuls else 0
            parts = [(it, (abs(ch) if ch != 0 else reste) / 100.0, mc) for it, ch, mc in ls]
        for it, p, mc in parts:
            if mc < 0 and prof < 3:
                for k2, p2 in probas('reference_loot_template', -mc, facteur * p, prof + 1).items():
                    res[k2] = res.get(k2, 0) + p2
            else:
                res[it] = res.get(it, 0) + facteur * p
    return res


rnd = random.Random(20261105)
_boss = q("SELECT DISTINCT ct.Entry, ct.MinLevel, ct.LootId, c.map FROM creature_template ct JOIN creature c ON c.id=ct.Entry "
          "WHERE ct.Rank=3 AND c.map NOT IN (%s) AND ct.LootId>0" % ",".join(map(str, HORS_DONJON)))
vus = set()
nb = 0
for e, niv, lootid, carte in _boss:
    e, niv, lootid, carte = int(e), int(niv), int(lootid), int(carte)
    if lootid in vus:
        continue
    vus.add(lootid)
    pr = probas('creature_loot_template', lootid)
    bleus = [p for it, p in pr.items() if qualite.get(it) == 3 and p > 0]
    taux = 100.0 * sum(bleus) / len(bleus) if bleus else 15.0
    taux = round(min(max(taux, 3.0), 50.0), 2)
    i = 6 if carte in RAIDS else palier(niv)
    couleur = rnd.choice([1, 2, 3, 4])
    v = rnd.choice(_par_couleur[couleur])
    L.append("INSERT INTO creature_loot_template (entry, item, ChanceOrQuestChance, groupid, mincountOrRef, maxcount, comments) "
             "VALUES (%d, %d, %.2f, 0, 1, 1, 'artefact');" % (lootid, entree_artefact(v, i), taux))
    nb += 1

# ---------------------------------------------------------------- boss rares des donjons : 20 % de mascotte au hasard
for e in sorted(MASCOTTES):
    L.append("INSERT INTO reference_loot_template (entry, item, ChanceOrQuestChance, groupid, mincountOrRef, maxcount) "
             "VALUES (99300, %d, 0, 1, 1, 1);" % e)
_rares = q("SELECT DISTINCT ct.Entry, ct.LootId FROM creature_template ct JOIN creature c ON c.id=ct.Entry "
           "WHERE ct.Rank IN (2, 4) AND c.map NOT IN (%s)" % ",".join(map(str, HORS_DONJON)))
for e, lootid in _rares:
    e, lootid = int(e), int(lootid)
    if not lootid:
        lootid = e
        L.append("UPDATE creature_template SET LootId=%d WHERE Entry=%d;" % (e, e))
    L.append("INSERT INTO creature_loot_template (entry, item, ChanceOrQuestChance, groupid, mincountOrRef, maxcount, comments) "
             "VALUES (%d, 99300, 20, 0, -99300, 1, 'mascotte');" % lootid)

# ---------------------------------------------------------------- machine à artefacts près des hôtels des ventes
GEMMES = {1: [1210, 1705, 7909, 7909, 12361, 12361, 12361], 2: [818, 1210, 3864, 7910, 7910, 7910, 7910],
          3: [774, 1206, 1529, 1529, 12364, 12364, 12364], 4: [818, 1705, 3864, 3864, 12799, 12799, 12799]}
NGEM = [1, 1, 1, 2, 1, 2, 3]
ESSENCES = [10938, 10939, 11082, 11135, 11175, 16203, 16203]
ARGENT = [10000, 50000, 100000, 200000, 400000, 600000, 1000000]
for c in (1, 2, 3, 4):
    for i in range(7):
        bonus = "12800, 1, 12363, 2" if i == 6 else "0, 0, 0, 0"      # 60 épique : diamant d'Azeroth et cristaux arcaniques
        L.append("INSERT INTO custom_relique_recette VALUES (%d, %d, %d, %d, %d, 2, %s, %d);"
                 % (c, i, GEMMES[c][i], NGEM[i], ESSENCES[i], bonus, ARGENT[i]))
L.append("DELETE FROM gameobject WHERE id=991000;")
L.append("DELETE FROM gameobject_template WHERE entry=991000;")
L.append("INSERT INTO gameobject_template (entry, type, displayId, name, faction, flags, size) VALUES "
         "(991000, 2, 356, 'Machine à artefacts', 35, 0, 0.7);")
# près d'un commissaire-priseur par ville : 4 m devant lui et 2,5 m sur le côté
VILLES = [8719, 8671, 15682, 8724, 8722, 8723, 9858, 8661, 9857]
guid = 9907000
for npc in VILLES:
    r = q("SELECT map, position_x, position_y, position_z, orientation FROM creature WHERE id=%d LIMIT 1" % npc)
    if not r:
        continue
    m, x, y, z, o = int(r[0][0]), float(r[0][1]), float(r[0][2]), float(r[0][3]), float(r[0][4])
    gx = x + 4 * math.cos(o) + 2.5 * math.cos(o + math.pi / 2)
    gy = y + 4 * math.sin(o) + 2.5 * math.sin(o + math.pi / 2)
    go = o + math.pi
    L.append("INSERT INTO gameobject (guid, id, map, position_x, position_y, position_z, orientation, rotation0, rotation1, rotation2, "
             "rotation3, spawntimesecsmin, spawntimesecsmax) VALUES (%d, 991000, %d, %.3f, %.3f, %.3f, %.4f, 0, 0, %.6f, %.6f, 0, 0);"
             % (guid, m, gx, gy, z, go, math.sin(go / 2), math.cos(go / 2)))
    guid += 1

open('/home/claude/wow-serveur/custom/reliques.sql', 'w', encoding='utf-8').write("\n".join(L) + "\n")
with open('/home/claude/wow-serveur/custom/reliques_codes.txt', 'w', encoding='utf-8') as f:
    for c in codes:
        f.write(".additem %d   %s (niv. %d)\n" % c)
# données de l'addon (statistiques des mascottes, calculées selon le niveau du joueur)
with open('/home/claude/wow/addons/Reliques/Mascottes.lua', 'w', encoding='utf-8') as f:
    f.write("-- Statistiques des mascottes (généré par gen_reliques.py)\nReliques_Mascottes = {\n")
    for e, (a, b) in sorted(MASCOTTES.items()):
        f.write("\t[%d] = { \"%s\", \"%s\" },\n" % (e, a, b))
    f.write("}\n")
print('objets', len(codes), 'quêtes', nq, 'boss', nb, 'boss rares', len(_rares), 'mascottes', len(MASCOTTES), 'machines', guid - 9907000)
