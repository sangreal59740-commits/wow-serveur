# PNJ des modes de jeu (au point de départ de chaque race) et du prestige (près des banques des capitales), montés.
# Sortie : custom/modes.sql
import math
esc = lambda s: s.replace("'", "''")
# race : (PNJ de base pour l'apparence, créature de monture, nom de lieu)
MONTURE = {'humain': 2404, 'nain': 2736, 'elfe': 6448, 'orc': 247, 'mort': 10670, 'tauren': 12246}
BASE = {'humain': 823, 'nain': 658, 'elfe': 2079, 'orc': 3143, 'mort': 1568, 'tauren': 2981}
# points de départ (playercreateinfo) : x, y, z, orientation du joueur, carte
DEPART = [('humain', 0, -8950.0, -132.5, 83.5, 0.0), ('nain', 0, -6240.3, 331.0, 382.8, 6.17716), ('elfe', 1, 10311.3, 831.5, 1326.4, 5.48033),
          ('orc', 1, -618.5, -4251.7, 38.7, 0.0), ('mort', 0, 1676.3, 1677.4, 121.7, 2.70526), ('tauren', 1, -2917.6, -258.0, 53.0, 0.0)]
# banquier du milieu de chaque capitale : x, y, z, orientation
BANQUE = [('humain', 0, -8935.3, 613.1, 99.6, 0.4538), ('nain', 0, -4886.5, -997.6, 504.0, 2.2340), ('elfe', 1, 9942.0, 2519.2, 1317.7, 4.3284),
          ('orc', 1, 1627.3, -4376.1, 11.8, 3.4383), ('mort', 0, 1591.5, 240.3, -52.1, 3.0369), ('tauren', 1, -1257.6, 19.6, 128.3, 1.7279)]
MODE_ENTRY, PRESTIGE_ENTRY = 990800, 990810
RACES = ['humain', 'nain', 'elfe', 'orc', 'mort', 'tauren']
L = ["-- Modes de jeu et prestige (généré par gen_modes.py)",
     "DELETE FROM creature WHERE id BETWEEN 990800 AND 990819;",
     "DELETE FROM creature_template_addon WHERE entry BETWEEN 990800 AND 990819;",
     "DELETE FROM creature_template WHERE Entry BETWEEN 990800 AND 990819;",
     "DROP TEMPORARY TABLE IF EXISTS tmp_ct;", "CREATE TEMPORARY TABLE tmp_ct LIKE creature_template;"]
def pnj(entry, base, nom, sous):
    L.append("DELETE FROM tmp_ct; INSERT INTO tmp_ct SELECT * FROM creature_template WHERE Entry=%d;" % base)
    L.append("UPDATE tmp_ct SET Entry=%d, Name='%s', SubName='%s', MinLevel=60, MaxLevel=60, Faction=35, NpcFlags=1, UnitFlags=0, "
             "TrainerType=0, TrainerSpell=0, TrainerClass=0, TrainerRace=0, TrainerTemplateId=0, VendorTemplateId=0, GossipMenuId=0, "
             "MovementType=0, AIName='', ScriptName='', Civilian=1, KillCredit1=0, KillCredit2=0, LootId=0, StringId1=0, StringId2=0;"
             % (entry, esc(nom), esc(sous)))
    L.append("INSERT INTO creature_template SELECT * FROM tmp_ct;")
for i, r in enumerate(RACES):
    pnj(MODE_ENTRY + i, BASE[r], "Héraut des Épreuves", "Modes de jeu")
    pnj(PRESTIGE_ENTRY + i, BASE[r], "Maître du Renouveau", "Prestige")
    for e in (MODE_ENTRY + i, PRESTIGE_ENTRY + i):
        L.append("INSERT INTO creature_template_addon (entry, mount, stand_state, sheath_state, emote, moveflags, auras) VALUES (%d, %d, 0, 0, 0, 0, NULL);" % (e, MONTURE[r]))
L.append("DROP TEMPORARY TABLE tmp_ct;")
spawns = []
for r, m, x, y, z, o in DEPART:            # 5 m devant le joueur qui apparaît, tourné vers lui
    spawns.append((MODE_ENTRY + RACES.index(r), m, x + 5 * math.cos(o), y + 5 * math.sin(o), z, (o + math.pi) % (2 * math.pi)))
for r, m, x, y, z, o in BANQUE:            # 5 m devant le banquier du milieu, côté clients
    spawns.append((PRESTIGE_ENTRY + RACES.index(r), m, x + 5 * math.cos(o), y + 5 * math.sin(o), z, o))
for i, (e, m, x, y, z, o) in enumerate(spawns):
    L.append("INSERT INTO creature (guid, id, map, spawnMask, position_x, position_y, position_z, orientation, spawntimesecsmin, spawntimesecsmax, spawndist, MovementType) "
             "VALUES (%d, %d, %d, 1, %.2f, %.2f, %.2f, %.4f, 300, 300, 0, 0);" % (9930000 + i, e, m, x, y, z, o))
L.append("SELECT 'Modes OK' AS resultat;")
open('/home/claude/wow-serveur/custom/modes.sql', 'w', encoding='utf-8').write("\n".join(L) + "\n")
for s in spawns: print(s)
