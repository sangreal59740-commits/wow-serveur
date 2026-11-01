# Classes custom, étape A : création des personnages.
#   Nécromancien = classe 6 (Humain, Troll), base démoniste
#   Sniper       = classe 10 (Nain, Orc), base chasseur, mana
#   Métamorphe   = classe 11 (remplace le druide) : Humain, Nain, Elfe de la nuit, Gnome, Orc, Troll, Tauren, Mort-vivant
# Sorties : out/*.dbc (client et serveur), classes.sql (base world)
import sys, struct, subprocess, os
sys.path.insert(0, '/home/claude/wow/fr')
from dbc import DBC, append_rows

SRV = '/home/claude/wow/classes/srv/'
OUT = '/home/claude/wow/classes/out/'
os.makedirs(OUT, exist_ok=True)

def q(sql):
    r = subprocess.run(['mysql', '-N', '-B', 'classicmangos', '-e', sql], capture_output=True, text=True, check=True)
    return [l.split('\t') for l in r.stdout.splitlines()]

HUMAN, ORC, DWARF, NE, UD, TAUREN, GNOME, TROLL = 1, 2, 3, 4, 5, 6, 7, 8
RACEMASK = {r: 1 << (r - 1) for r in range(1, 9)}
NECRO, SNIPER, META = 6, 10, 11
# nouvelle classe -> (classe de base, race de base, races)
NEW = {
    NECRO: (9, HUMAN, [HUMAN, TROLL, UD]),
    SNIPER: (3, DWARF, [DWARF, ORC]),
    META: (11, NE, [NE, GNOME, TROLL, TAUREN]),
}
NAMES = {NECRO: "Nécromancien", SNIPER: "Sniper", META: "Métamorphe"}
# classes vanilla ouvertes à une race de plus : (race, classe, race modèle de la classe)
EXTRA = [(3, 7, 2), (5, 2, 1)]       # Nain chaman (modèle : Orc), Mort-vivant paladin (modèle : Humain)
# paires vanilla retirées (race, classe) : Elfe de la nuit et Troll guerriers, Humain voleur, Nain prêtre
REMOVED = [(4, 1), (8, 1), (1, 4), (3, 5), (8, 3), (5, 1), (3, 4)]   # + Troll chasseur, Mort-vivant guerrier, Nain voleur
CBIT = {c: 1 << (c - 1) for c in range(1, 12)}

# ---------------------------------------------------------------- ChrClasses
d = DBC(SRV + 'ChrClasses.dbc')
rows = {r[0]: r for r in d.rows}
def clone_class(cid, base, name, power):
    r = list(rows[base])
    r[0] = cid
    r[3] = power
    r[4] = d.str(r[4])
    r[5] = name
    for c in range(6, 13):
        r[c] = 0
    r[14] = d.str(r[14])
    return r
new_rows = [clone_class(NECRO, 9, NAMES[NECRO], 0), clone_class(SNIPER, 3, NAMES[SNIPER], 0)]
# Métamorphe : on renomme la ligne du druide (le texte est ajouté au bloc de chaînes)
data = open(SRV + 'ChrClasses.dbc', 'rb').read()
nrec, nf, rs, ss = struct.unpack('<4I', data[4:20])
body = bytearray(data[20:20 + nrec * rs])
sb = bytearray(data[20 + nrec * rs:])
for i in range(nrec):
    if struct.unpack_from('<I', body, i * rs)[0] == META:
        off = len(sb)
        sb += NAMES[META].encode('utf-8') + b'\0'
        struct.pack_into('<I', body, i * rs + 5 * 4, off)
data = b'WDBC' + struct.pack('<4I', nrec, nf, rs, len(sb)) + bytes(body) + bytes(sb)
data = append_rows(data, new_rows)
open(OUT + 'ChrClasses.dbc', 'wb').write(data)

# ---------------------------------------------------------------- CharBaseInfo (paires race / classe, 1 octet chacune)
b = open(SRV + 'CharBaseInfo.dbc', 'rb').read()
nrec, nf, rs, ss = struct.unpack('<4I', b[4:20])
pairs = [tuple(b[20 + i * rs:20 + i * rs + rs]) for i in range(nrec)]
for c, (_, _, races) in NEW.items():
    for r in races:
        if (r, c) not in pairs:
            pairs.append((r, c))
for r, c, _ in EXTRA:
    if (r, c) not in pairs:
        pairs.append((r, c))
pairs = [p for p in pairs if p not in REMOVED]
pairs.sort()
out = b'WDBC' + struct.pack('<4I', len(pairs), nf, rs, 1) + b''.join(bytes(p) for p in pairs) + b'\0'
open(OUT + 'CharBaseInfo.dbc', 'wb').write(out)

# ---------------------------------------------------------------- CharStartOutfit (tenue de départ affichée à la création)
b = open(SRV + 'CharStartOutfit.dbc', 'rb').read()
nrec, nf, rs, ss = struct.unpack('<4I', b[4:20])
recs = [bytearray(b[20 + i * rs:20 + (i + 1) * rs]) for i in range(nrec)]
strings = b[20 + nrec * rs:]
have = {(r[4], r[5], r[6]) for r in recs}
nextid = max(struct.unpack_from('<I', r, 0)[0] for r in recs) + 1
def outfit(race, cls, gender):
    for r in recs:
        if (r[4], r[5], r[6]) == (race, cls, gender):
            return r
TROLL_BASE = {NECRO: (TROLL, 8)}           # le troll n'a pas de démoniste : tenue de mage
for c, (bc, br, races) in NEW.items():
    for race in races:
        for g in (0, 1):
            if (race, c, g) in have:
                continue
            src = outfit(race, bc, g) or outfit(br, bc, g)
            if c in TROLL_BASE and race == TROLL_BASE[c][0]:
                src = outfit(TROLL, TROLL_BASE[c][1], g) or src
            r = bytearray(src)
            struct.pack_into('<I', r, 0, nextid)
            r[4], r[5], r[6] = race, c, g
            recs.append(r)
            nextid += 1
for race, c, src in EXTRA:
    for g in (0, 1):
        if (race, c, g) in have:
            continue
        r = bytearray(outfit(src, c, g))
        struct.pack_into('<I', r, 0, nextid)
        r[4], r[5], r[6] = race, c, g
        recs.append(r)
        nextid += 1
out = b'WDBC' + struct.pack('<4I', len(recs), nf, rs, len(strings)) + b''.join(bytes(r) for r in recs) + strings
open(OUT + 'CharStartOutfit.dbc', 'wb').write(out)

# ---------------------------------------------------------------- SkillRaceClassInfo (compétences : armes, armures, langues)
s = DBC(SRV + 'SkillRaceClassInfo.dbc')
ALLRACES = 511
srows = [list(r) for r in s.rows]
extra = []
nid = max(r[0] for r in srows) + 1
for r in srows:
    cm = r[3]
    if cm in (1503, 1535, 0xffffffff):               # toutes les classes
        r[3] = cm | CBIT[NECRO] | CBIT[SNIPER]
        continue
    if cm & CBIT[9]:
        r[3] |= CBIT[NECRO]
    if cm & CBIT[3]:
        r[3] |= CBIT[SNIPER]
    if cm & CBIT[META] and r[2] != ALLRACES:
        # compétences du druide réservées à une race : ouvertes aux nouvelles races du Métamorphe
        nr = list(r)
        nr[0] = nid; nid += 1
        nr[2] = sum(RACEMASK[x] for x in NEW[META][2]) & ~(RACEMASK[NE] | RACEMASK[TAUREN])
        nr[3] = CBIT[META]
        extra.append(nr)
# Sniper : plaques au niveau 40 (la maille vient du bit chasseur)
for r in srows:
    if r[1] == 293 and r[2] == ALLRACES:
        r[3] |= CBIT[SNIPER]
for race, c, src in EXTRA:
    for r in srows:
        if r[3] & CBIT[c] and r[2] != ALLRACES and r[2] & RACEMASK[src] and not r[2] & RACEMASK[race]:
            r[2] |= RACEMASK[race]
# onglets de sorts : les classes custom ont leurs propres lignes de compétence (900 à 905)
for r in srows:
    if r[1] in (354, 355, 593):
        r[3] &= ~CBIT[NECRO]
    if r[1] in (50, 51, 163):
        r[3] &= ~CBIT[SNIPER]
for skill, c in ((900, NECRO), (901, NECRO), (902, NECRO), (903, SNIPER), (904, SNIPER), (905, SNIPER)):
    extra.append([nid, skill, ALLRACES, CBIT[c], 1040, 0, 0, 0]); nid += 1
data = open(SRV + 'SkillRaceClassInfo.dbc', 'rb').read()
nrec, nf, rs, ss = struct.unpack('<4I', data[4:20])
body = b''.join(struct.pack('<%dI' % nf, *[v & 0xffffffff for v in r]) for r in srows)
data = b'WDBC' + struct.pack('<4I', nrec, nf, rs, ss) + body + data[20 + nrec * rs:]
data = append_rows(data, extra)
open(OUT + 'SkillRaceClassInfo.dbc', 'wb').write(data)

# ---------------------------------------------------------------- SQL serveur : création, sorts, barres, objets, compétences, stats
def rows_of(table, race, cls, cols):
    return q("select %s from %s where race=%d and class=%d" % (cols, table, race, cls))
spells = {}
for r, c, sp in q("select race, class, Spell from playercreateinfo_spell"):
    spells.setdefault((int(r), int(c)), set()).add(int(sp))
def racial(race):
    sets = [v for (r, c), v in spells.items() if r == race]
    common = set.intersection(*sets) if sets else set()
    return common

L = []
w = L.append
# stats : classe et race de référence (le document : démoniste, chasseur, chaman)
STATBASE = {NECRO: (9, HUMAN), SNIPER: (3, DWARF), META: (7, ORC)}
w("-- Classes custom : création des personnages (généré)")
w("SET NAMES utf8mb4;")
for c in (NECRO, SNIPER):
    for t in ('playercreateinfo', 'playercreateinfo_spell', 'playercreateinfo_action', 'playercreateinfo_item'):
        w("DELETE FROM %s WHERE class=%d;" % (t, c))
for t in ('playercreateinfo', 'playercreateinfo_spell', 'playercreateinfo_action', 'playercreateinfo_item'):
    w("DELETE FROM %s WHERE class=%d AND race NOT IN (%d, %d);" % (t, META, NE, TAUREN))
w("DELETE FROM player_levelstats WHERE class IN (%d, %d, %d);" % (NECRO, SNIPER, META))
w("DELETE FROM player_classlevelstats WHERE class IN (%d, %d, %d);" % (NECRO, SNIPER, META))

for c, (bc, br, races) in NEW.items():
    sc, sr = STATBASE[c]
    w("INSERT INTO player_classlevelstats (class, level, basehp, basemana) SELECT %d, level, basehp, basemana FROM player_classlevelstats WHERE class=%d;" % (c, sc))
    classSpells = spells[(br, bc)] - racial(br)
    for race in races:
        # stats : classe de référence (race de référence) - guerrier (race de référence) + guerrier (race)
        w("INSERT INTO player_levelstats (race, class, level, str, agi, sta, inte, spi) "
          "SELECT %d, %d, b.level, GREATEST(1, CAST(b.str AS SIGNED) + CAST(wr.str AS SIGNED) - CAST(wb.str AS SIGNED)), GREATEST(1, CAST(b.agi AS SIGNED) + CAST(wr.agi AS SIGNED) - CAST(wb.agi AS SIGNED)), GREATEST(1, CAST(b.sta AS SIGNED) + CAST(wr.sta AS SIGNED) - CAST(wb.sta AS SIGNED)), "
          "GREATEST(1, CAST(b.inte AS SIGNED) + CAST(wr.inte AS SIGNED) - CAST(wb.inte AS SIGNED)), GREATEST(1, CAST(b.spi AS SIGNED) + CAST(wr.spi AS SIGNED) - CAST(wb.spi AS SIGNED)) FROM player_levelstats b "
          "JOIN player_levelstats wb ON wb.race=%d AND wb.class=1 AND wb.level=b.level "
          "JOIN player_levelstats wr ON wr.race=%d AND wr.class=1 AND wr.level=b.level WHERE b.race=%d AND b.class=%d;"
          % (race, c, sr, race, sr, sc))
        if c == META and race in (NE, TAUREN):
            continue                                   # druides existants : création inchangée
        w("INSERT INTO playercreateinfo (race, class, map, zone, position_x, position_y, position_z, orientation) "
          "SELECT %d, %d, map, zone, position_x, position_y, position_z, orientation FROM playercreateinfo WHERE race=%d AND class<>%d ORDER BY class LIMIT 1;" % (race, c, race, c))
        for sp in sorted(racial(race) | classSpells):
            w("INSERT IGNORE INTO playercreateinfo_spell (race, class, Spell, Note) VALUES (%d, %d, %d, 'Custom');" % (race, c, sp))
        w("INSERT INTO playercreateinfo_action (race, class, button, action, type) SELECT %d, %d, button, action, type FROM playercreateinfo_action WHERE race=%d AND class=%d;" % (race, c, br, bc))
        w("INSERT INTO playercreateinfo_item (race, class, itemid, amount) SELECT %d, %d, itemid, amount FROM playercreateinfo_item WHERE race=%d AND class=%d;" % (race, c, br, bc))
# compétences de départ
w("DELETE FROM playercreateinfo_skills WHERE classMask IN (%d, %d);" % (CBIT[NECRO], CBIT[SNIPER]))
w("INSERT INTO playercreateinfo_skills (raceMask, classMask, skill, step, note) SELECT 0, %d, skill, step, CONCAT(note, ' (necro)') "
  "FROM playercreateinfo_skills WHERE classMask=%d;" % (CBIT[NECRO], CBIT[9]))
for sk, note in ((46, 'Weapon: Guns (Sniper)'),
                 (44, 'Weapon: Axes (Sniper)'), (414, 'Armor: Leather (Sniper)')):
    w("INSERT INTO playercreateinfo_skills (raceMask, classMask, skill, step, note) VALUES (0, %d, %d, 0, '%s');" % (CBIT[SNIPER], sk, note))
w("DELETE FROM playercreateinfo_skills WHERE classMask=%d AND skill IN (354, 355, 593);" % CBIT[NECRO])
for sk, note in ((900, 'Necro: Invocateur'), (901, 'Necro: Malediction'), (902, 'Necro: Magicien')):
    w("INSERT INTO playercreateinfo_skills (raceMask, classMask, skill, step, note) VALUES (0, %d, %d, 0, '%s');" % (CBIT[NECRO], sk, note))
w("DELETE FROM playercreateinfo_skills WHERE classMask=%d AND skill IN (50, 51, 163);" % CBIT[SNIPER])
for sk, note in ((903, 'Sniper: Tireur'), (904, 'Sniper: Bestial'), (905, 'Sniper: Mecanisme')):
    w("INSERT INTO playercreateinfo_skills (raceMask, classMask, skill, step, note) VALUES (0, %d, %d, 0, '%s');" % (CBIT[SNIPER], sk, note))
w("UPDATE playercreateinfo_skills SET raceMask=0 WHERE classMask=%d AND raceMask<>0;" % CBIT[META])
# Nain chaman, Mort-vivant paladin : création, sorts, barres, stats, totems
for race, c, src in EXTRA:
    for t in ('playercreateinfo', 'playercreateinfo_spell', 'playercreateinfo_action', 'playercreateinfo_item', 'player_levelstats'):
        w("DELETE FROM %s WHERE race=%d AND class=%d;" % (t, race, c))
    w("INSERT INTO playercreateinfo (race, class, map, zone, position_x, position_y, position_z, orientation) "
      "SELECT %d, %d, map, zone, position_x, position_y, position_z, orientation FROM playercreateinfo WHERE race=%d AND class<>%d ORDER BY class LIMIT 1;" % (race, c, race, c))
    for sp in sorted(racial(race) | (spells[(src, c)] - racial(src))):
        w("INSERT IGNORE INTO playercreateinfo_spell (race, class, Spell, Note) VALUES (%d, %d, %d, 'Custom race');" % (race, c, sp))
    w("INSERT INTO playercreateinfo_action (race, class, button, action, type) SELECT %d, %d, button, action, type FROM playercreateinfo_action WHERE race=%d AND class=%d;" % (race, c, src, c))
    w("INSERT INTO player_levelstats (race, class, level, str, agi, sta, inte, spi) "
      "SELECT %d, %d, b.level, GREATEST(1, CAST(b.str AS SIGNED) + CAST(wr.str AS SIGNED) - CAST(wb.str AS SIGNED)), "
      "GREATEST(1, CAST(b.agi AS SIGNED) + CAST(wr.agi AS SIGNED) - CAST(wb.agi AS SIGNED)), "
      "GREATEST(1, CAST(b.sta AS SIGNED) + CAST(wr.sta AS SIGNED) - CAST(wb.sta AS SIGNED)), "
      "GREATEST(1, CAST(b.inte AS SIGNED) + CAST(wr.inte AS SIGNED) - CAST(wb.inte AS SIGNED)), "
      "GREATEST(1, CAST(b.spi AS SIGNED) + CAST(wr.spi AS SIGNED) - CAST(wb.spi AS SIGNED)) FROM player_levelstats b "
      "JOIN player_levelstats wb ON wb.race=%d AND wb.class=1 AND wb.level=b.level "
      "JOIN player_levelstats wr ON wr.race=%d AND wr.class=1 AND wr.level=b.level WHERE b.race=%d AND b.class=%d;"
      % (race, c, src, race, src, c))
# le chaman nain reçoit les 4 totems (leurs quêtes sont réservées à la Horde)
for item in (5175, 5176, 5177, 5178):
    w("INSERT INTO playercreateinfo_item (race, class, itemid, amount) VALUES (3, 7, %d, 1);" % item)
# maîtres : chaman à Forgefer et au Val d'Est-Gel, paladin à Fossoyeuse et à la Clairière de Tirisfal
w("DELETE FROM npc_trainer WHERE entry BETWEEN 990186 AND 990189;")
w("DELETE FROM creature WHERE guid BETWEEN 9903100 AND 9903109;")
w("DELETE FROM creature_template WHERE Entry BETWEEN 990186 AND 990189;")
w("DROP TEMPORARY TABLE IF EXISTS tmp_ct2;")
w("CREATE TEMPORARY TABLE tmp_ct2 LIKE creature_template;")
for i, (entry, nom, sous, cls, src_npc, src_list) in enumerate([
        (990186, "Brenna Totem-de-Pierre", "Maître chaman", 7, 5113, 3344),
        (990187, "Durgan Chant-du-Roc", "Maître chaman", 7, 912, 3344),
        (990188, "Sire Malroth", "Maître paladin", 2, 4593, 928),
        (990189, "Dame Ysera Nuitpâle", "Maître paladin", 2, 2119, 928)]):
    w("INSERT INTO tmp_ct2 SELECT * FROM creature_template WHERE Entry=%d;" % src_npc)
    w("UPDATE tmp_ct2 SET Entry=%d, Name='%s', SubName='%s', TrainerType=0, TrainerClass=%d, TrainerTemplateId=0, NpcFlags=17, "
      "GossipMenuId=0, ScriptName='' WHERE Entry=%d;" % (entry, nom.replace("'", "\\'"), sous, cls, src_npc))
    w("INSERT INTO npc_trainer (entry, spell, spellcost, reqskill, reqskillvalue, reqlevel) "
      "SELECT %d, spell, spellcost, reqskill, reqskillvalue, reqlevel FROM npc_trainer WHERE entry=%d;" % (entry, src_list))
    w("INSERT INTO creature (guid, id, map, spawnMask, position_x, position_y, position_z, orientation, spawntimesecsmin, "
      "spawntimesecsmax, spawndist, MovementType) SELECT %d, %d, map, spawnMask, position_x + 2 * COS(orientation - PI() / 2), "
      "position_y + 2 * SIN(orientation - PI() / 2), position_z + 0.3, orientation, 300, 300, 0, 0 FROM creature WHERE id=%d LIMIT 1;"
      % (9903100 + i, entry, src_npc))
w("INSERT INTO creature_template SELECT * FROM tmp_ct2;")
w("DROP TEMPORARY TABLE tmp_ct2;")
# paires vanilla retirées : sauvegarde puis suppression (les personnages déjà créés restent jouables)
w("CREATE TABLE IF NOT EXISTS custom_backup_playercreateinfo_retire SELECT * FROM playercreateinfo WHERE (race, class) IN (%s);"
  % ", ".join("(%d, %d)" % p for p in REMOVED))
for t in ('playercreateinfo', 'playercreateinfo_spell', 'playercreateinfo_action', 'playercreateinfo_item'):
    for r_, c_ in REMOVED:
        w("DELETE FROM %s WHERE race=%d AND class=%d;" % (t, r_, c_))
w("SELECT 'Classes OK' AS resultat;")
open('/home/claude/wow/classes/classes.sql', 'w', encoding='utf-8').write("\n".join(L) + "\n")
print('paires', len(pairs), 'tenues', len(recs), 'compétences ajoutées', len(extra))

# lignes ChrClasses pour le client (build.py les ajoute après traduction)
import json
json.dump({'chr_new': new_rows, 'rename': {str(META): NAMES[META]}}, open('/home/claude/wow/classes/classes_rows.json', 'w', encoding='utf-8'), ensure_ascii=False)
