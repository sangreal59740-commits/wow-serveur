#include "DonjonsModule.h"

#include "AI/ScriptDevAI/include/sc_gossip.h"
#include "Chat/Chat.h"
#include "Database/DatabaseEnv.h"
#include "Entities/Creature.h"
#include "Entities/GossipDef.h"
#include "Entities/ObjectGuid.h"
#include "Entities/Player.h"
#include "Globals/ObjectMgr.h"
#include "Groups/Group.h"
#include "Log/Log.h"
#include "Loot/LootMgr.h"
#include "Maps/Map.h"
#include "Mails/Mail.h"
#include "Server/WorldPacket.h"
#include "Entities/Item.h"
#include "Server/WorldSession.h"
#include "Util/Util.h"
#include "World/World.h"

#include <algorithm>
#include <cctype>
#include <cstdlib>
#include <functional>
#include <cmath>

namespace cmangos_module
{
    // Les 13 donjons de moins de 40. Coordonnees = arrivee dans l'instance (areatrigger_teleport).
    // Le Monastere est un seul map (189) : l'aile est deduite de l'entree la plus proche du PNJ.
    static const DonjonInfo DONJONS[] =
    {
        {  0, 389,     0.8f,    -8.2f,  -15.5f, 16, 11520, "Gouffre de Ragefeu" },
        {  1,  36,   -14.6f,  -385.5f,   62.5f, 21,   639, "Les Mortemines" },
        {  2,  43,  -158.4f,   131.6f,  -74.3f, 22,  3654, "Cavernes des Lamentations" },
        {  3,  33,  -228.2f,  2111.4f,   76.9f, 26,  4275, "Donjon d'Ombrecroc" },
        {  4,  34,    49.0f,     0.5f,  -16.4f, 29,  1716, "La Prison" },
        {  5,  48,  -150.2f,   106.6f,  -39.8f, 28,  4829, "Profondeurs de Brassenoire" },
        {  6,  90,  -329.1f,    -3.2f, -152.9f, 34,  7800, "Gnomeregan" },
        {  6,  90,  -733.6f,     1.9f, -249.1f, 34,  7800, "Gnomeregan" },
        {  7,  47,  1942.3f,  1544.2f,   83.3f, 33,  4421, "Kraal de Tranchebauge" },
        {  8, 189,  1687.3f,  1050.1f,   18.7f, 34,  4543, "Monastère : Cimetière" },
        {  9, 189,   253.7f,  -206.6f,   18.7f, 37,  6487, "Monastère : Bibliothèque" },
        { 10, 189,  1608.1f,  -318.9f,   18.7f, 40,  3975, "Monastère : Armurerie" },
        { 11, 189,   853.2f,  1319.2f,   18.7f, 42,  3977, "Monastère : Cathédrale" },
        { 12, 129,  2593.7f,  1111.2f,   51.0f, 41,  7358, "Souilles de Tranchebauge" },
        // donjons de haut niveau : mode mythique seulement
        { 13,  70,  -228.9f,    46.1f,  -46.0f, 47,  2748, "Uldaman" },
        { 14, 209,  1212.7f,   842.0f,    8.9f, 48,  7267, "Zul'Farrak" },
        { 15, 349,  1016.8f,  -458.5f,  -43.5f, 51, 12201, "Maraudon" },
        { 15, 349,   755.1f,  -617.7f,  -32.9f, 51, 12201, "Maraudon" },
        { 16, 109,  -315.9f,   100.2f, -131.8f, 55,  5709, "Temple englouti" },
        { 17, 230,   456.9f,    34.1f,  -68.1f, 59,  9019, "Profondeurs de Rochenoire" },
        { 18, 229,    78.4f,  -226.8f,   49.8f, 60,  9568, "Pic Rochenoire" },
        { 19, 429,    47.5f,  -153.7f,   -2.7f, 58, 11492, "Hache-Tripes Est" },
        { 20, 429,   -65.7f,   159.6f,   -3.5f, 61, 11486, "Hache-Tripes Ouest" },
        { 21, 429,   254.9f,   -19.5f,   -2.6f, 62, 11501, "Hache-Tripes Nord" },
        { 22, 329,  3392.9f, -3395.0f,  143.1f, 62, 10813, "Stratholme : quartier écarlate" },
        { 23, 329,  3590.9f, -3643.2f,  138.5f, 62, 10440, "Stratholme : quartier mort-vivant" },
        { 24, 289,   190.8f,   126.3f,  137.2f, 61,  1853, "Scholomance" },
    };
    static const uint32 DONJONS_COUNT = sizeof(DONJONS) / sizeof(DONJONS[0]);

    enum DonjonsActions
    {
        ACTION_INFO     = GOSSIP_ACTION_INFO_DEF + 1,
        ACTION_CLASSEMENT = GOSSIP_ACTION_INFO_DEF + 2,
        ACTION_NORMAL   = GOSSIP_ACTION_INFO_DEF + 100,
        ACTION_NIV40    = GOSSIP_ACTION_INFO_DEF + 140,
        ACTION_NIV50    = GOSSIP_ACTION_INFO_DEF + 150,
        ACTION_MYTH     = GOSSIP_ACTION_INFO_DEF + 200,     // + niveau M (0 a 10)
    };

    // mythique : nombre de monstres et multiplicateur PV / dégâts par niveau M
    static const float MYTH_COUNT[DONJONS_MYTHIC_MAX + 1] = { 1.2f, 1.6f, 2.0f, 2.3f, 2.7f, 3.1f, 3.5f, 3.9f, 4.2f, 4.6f, 5.0f };
    static const float MYTH_POWER[DONJONS_MYTHIC_MAX + 1] = { 1.2f, 1.58f, 1.96f, 2.34f, 2.72f, 3.10f, 3.48f, 3.86f, 4.24f, 4.62f, 5.0f };

    static bool IsMythic(uint32 level) { return level >= DONJONS_MYTHIC; }
    static uint32 MythicOf(uint32 level) { return std::min<uint32>(level - DONJONS_MYTHIC, DONJONS_MYTHIC_MAX); }

    static bool IsDonjonMap(uint32 mapId)
    {
        for (uint32 i = 0; i < DONJONS_COUNT; ++i)
            if (DONJONS[i].mapId == mapId)
                return true;
        return false;
    }

    static bool IsGardien(uint32 entry)
    {
        return entry >= DONJONS_NPC_BASE && entry <= DONJONS_NPC_LAST;
    }

    static std::string NomMode(uint32 level)
    {
        if (IsMythic(level))
        {
            uint32 m = MythicOf(level);
            return m == 0 ? std::string("Mythique M0") : "Mythique M+" + std::to_string(m);
        }
        if (level >= 50) return "Niveau 50";
        if (level >= 40) return "Niveau 40";
        return "Normal";
    }

    static std::string Duree(uint32 s)
    {
        char buf[32];
        if (s >= 3600)
            snprintf(buf, sizeof(buf), "%u h %02u min %02u s", s / 3600, (s / 60) % 60, s % 60);
        else
            snprintf(buf, sizeof(buf), "%u min %02u s", s / 60, s % 60);
        return buf;
    }

    static const char* NomDonjon(int32 idx)
    {
        for (uint32 i = 0; i < DONJONS_COUNT; ++i)
            if (int32(DONJONS[i].index) == idx)
                return DONJONS[i].nom;
        return "Donjon";
    }

    static std::string NiveauM(int32 m)
    {
        return m == 0 ? std::string("M0") : "M+" + std::to_string(m);
    }

    static void EnvoyerATous(const std::string& text)
    {
        WorldPacket data;
        ChatHandler::BuildChatPacket(data, CHAT_MSG_SYSTEM, text.c_str(), LANG_UNIVERSAL);
        sWorld.SendGlobalMessage(data);
    }

    DonjonsModule::DonjonsModule() : Module("Donjons", nullptr)
    {
    }

    void DonjonsModule::OnInitialize()
    {
        CharacterDatabase.Execute(
            "CREATE TABLE IF NOT EXISTS `custom_instance_mode` ("
            " `instance_id` INT UNSIGNED NOT NULL,"
            " `map` INT UNSIGNED NOT NULL DEFAULT 0,"
            " `dungeon` INT NOT NULL DEFAULT -1,"
            " `level` TINYINT UNSIGNED NOT NULL DEFAULT 0,"
            " `locked` TINYINT UNSIGNED NOT NULL DEFAULT 0,"
            " PRIMARY KEY (`instance_id`)) ENGINE=InnoDB DEFAULT CHARSET=utf8");
        CharacterDatabase.Execute("DELETE FROM `custom_instance_mode` WHERE `instance_id` NOT IN (SELECT `id` FROM `instance`)");

        uint32 count = 0;
        if (auto result = CharacterDatabase.Query("SELECT `instance_id`, `map`, `dungeon`, `level`, `locked` FROM `custom_instance_mode`"))
        {
            do
            {
                Field* fields = result->Fetch();
                InstanceMode& mode = instances[fields[0].GetUInt32()];
                mode.mapId = fields[1].GetUInt32();
                mode.dungeon = fields[2].GetInt32();
                mode.level = fields[3].GetUInt32();
                mode.locked = fields[4].GetUInt32() != 0;
                ++count;
            }
            while (result->NextRow());
        }
        sLog.outString("Donjons : %u instance(s) avec un mode enregistre", count);

        CharacterDatabase.Execute(
            "CREATE TABLE IF NOT EXISTS `custom_mythic_best` ("
            " `guid` INT UNSIGNED NOT NULL,"
            " `dungeon` INT NOT NULL,"
            " `best` INT NOT NULL DEFAULT -1,"
            " PRIMARY KEY (`guid`, `dungeon`)) ENGINE=InnoDB DEFAULT CHARSET=utf8");
        if (auto result = CharacterDatabase.Query("SELECT `guid`, `dungeon`, `best` FROM `custom_mythic_best`"))
        {
            do
            {
                Field* fields = result->Fetch();
                bestLevels[(uint64(fields[0].GetUInt32()) << 8) | uint64(fields[1].GetInt32() & 0xFF)] = fields[2].GetInt32();
            }
            while (result->NextRow());
        }
        CharacterDatabase.Execute(
            "CREATE TABLE IF NOT EXISTS `custom_mythic_record` ("
            " `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,"
            " `dungeon` INT NOT NULL,"
            " `level` INT NOT NULL,"
            " `seconds` INT UNSIGNED NOT NULL,"
            " `names` VARCHAR(255) NOT NULL DEFAULT '',"
            " `date` INT UNSIGNED NOT NULL DEFAULT 0,"
            " PRIMARY KEY (`id`), KEY `dungeon` (`dungeon`)) ENGINE=InnoDB DEFAULT CHARSET=utf8");
        CharacterDatabase.Execute(
            "CREATE TABLE IF NOT EXISTS `custom_mythic_reward` ("
            " `guid` INT UNSIGNED NOT NULL, PRIMARY KEY (`guid`)) ENGINE=InnoDB DEFAULT CHARSET=utf8");
        if (auto result = CharacterDatabase.Query(
            "SELECT r.`dungeon`, r.`level`, r.`seconds`, r.`names` FROM `custom_mythic_record` r "
            "ORDER BY r.`dungeon`, r.`level` DESC, r.`seconds` ASC"))
        {
            do
            {
                Field* fields = result->Fetch();
                Record& rec = records[fields[0].GetInt32()];
                if (rec.level >= 0)
                    continue;           // le premier de chaque donjon est le meilleur
                rec.level = fields[1].GetInt32();
                rec.seconds = fields[2].GetUInt32();
                rec.names = fields[3].GetCppString();
            }
            while (result->NextRow());
        }
        if (auto result = CharacterDatabase.Query("SELECT `guid` FROM `custom_mythic_reward`"))
        {
            do
                rewarded.insert(result->Fetch()[0].GetUInt32());
            while (result->NextRow());
        }
        sLog.outString("Donjons : %u record(s) mythique(s)", uint32(records.size()));

        if (auto result = WorldDatabase.Query("SELECT `entry` FROM `custom_mythic_boss`"))
        {
            do
                bossEntries.insert(result->Fetch()[0].GetUInt32());
            while (result->NextRow());
        }
        for (uint32 i = 0; i < DONJONS_COUNT; ++i)
            bossEntries.insert(DONJONS[i].finalBoss);
        for (uint32 e = DONJONS_RARE_BASE; e <= DONJONS_RARE_LAST; ++e)
            bossEntries.insert(e);
        sLog.outString("Donjons : %u boss pour le butin mythique", uint32(bossEntries.size()));
    }

    const DonjonInfo* DonjonsModule::FindDonjon(uint32 mapId, float x, float y, float z) const
    {
        const DonjonInfo* best = nullptr;
        float bestDist = 0.0f;
        for (uint32 i = 0; i < DONJONS_COUNT; ++i)
        {
            const DonjonInfo& d = DONJONS[i];
            if (d.mapId != mapId)
                continue;
            float dx = d.x - x, dy = d.y - y, dz = d.z - z;
            float dist = dx * dx + dy * dy + dz * dz;
            if (!best || dist < bestDist)
            {
                best = &d;
                bestDist = dist;
            }
        }
        return best;
    }

    const DonjonInfo* DonjonsModule::GetDonjon(const InstanceMode& mode) const
    {
        if (mode.dungeon < 0)
            return nullptr;
        for (uint32 i = 0; i < DONJONS_COUNT; ++i)
            if (int32(DONJONS[i].index) == mode.dungeon && DONJONS[i].mapId == mode.mapId)
                return &DONJONS[i];
        return nullptr;
    }

    bool DonjonsModule::IsScalable(Creature* creature) const
    {
        if (!creature || creature->IsPet() || creature->IsTotem())
            return false;
        if (IsGardien(creature->GetEntry()))
            return false;
        if (creature->GetOwnerGuid().IsPlayer() || creature->HasCharmer())
            return false;
        return true;
    }

    float DonjonsModule::DamageRatio(uint32 from, uint32 to)
    {
        CreatureClassLvlStats const* a = sObjectMgr.GetCreatureClassLvlStats(from, 1);
        CreatureClassLvlStats const* b = sObjectMgr.GetCreatureClassLvlStats(to, 1);
        if (!a || !b)
            return 1.0f;
        float va = a->BaseDamage + a->BaseMeleeAttackPower / 14.0f;
        float vb = b->BaseDamage + b->BaseMeleeAttackPower / 14.0f;
        if (va <= 0.0f)
            return 1.0f;
        return std::max(1.0f, std::min(8.0f, vb / va));
    }

    void DonjonsModule::ApplyToCreature(Creature* creature, InstanceMode& mode)
    {
        if (!IsScalable(creature) || !creature->IsAlive() || creature->IsInCombat())
            return;

        uint64 key = creature->GetObjectGuid().GetRawValue();
        auto it = mode.origLevels.find(key);
        uint32 orig = (it != mode.origLevels.end()) ? it->second : creature->GetLevel();
        mode.origLevels[key] = orig;

        const DonjonInfo* d = GetDonjon(mode);
        if (mode.level == 0 || !d)
        {
            auto am = mode.appliedMult.find(key);
            if (creature->GetLevel() != orig || (am != mode.appliedMult.end() && am->second != 1.0f))
                creature->SelectLevel(orig);
            mode.appliedMult[key] = 1.0f;
            creature->SetCustomSpellMult(1.0f);
            return;
        }

        int32 level;
        float mult = 1.0f;
        if (IsMythic(mode.level))
        {
            // tout au niveau 60 environ : monstres 58 a 60, boss 61 (62 au plus)
            level = int32(orig) + 61 - int32(d->refLevel);
            level = std::max(58, std::min(62, level));
            mult = MYTH_POWER[MythicOf(mode.level)];
        }
        else
        {
            level = int32(orig) + int32(mode.level) + 1 - int32(d->refLevel);
            level = std::max(1, std::min(63, level));
        }

        auto am = mode.appliedMult.find(key);
        if (creature->GetLevel() != uint32(level) || am == mode.appliedMult.end() || am->second != mult)
        {
            creature->SelectLevel(uint32(level));
            if (mult != 1.0f)
            {
                creature->SetCreateHealth(uint32(creature->GetCreateHealth() * mult));
                for (WeaponAttackType att : { BASE_ATTACK, OFF_ATTACK, RANGED_ATTACK })
                {
                    creature->SetBaseWeaponDamage(att, MINDAMAGE, creature->GetBaseWeaponDamage(att, MINDAMAGE) * mult);
                    creature->SetBaseWeaponDamage(att, MAXDAMAGE, creature->GetBaseWeaponDamage(att, MAXDAMAGE) * mult);
                }
                creature->UpdateAllStats();
                creature->SetHealth(creature->GetMaxHealth());
            }
            mode.appliedMult[key] = mult;
        }
        creature->SetCustomSpellMult(DamageRatio(orig, uint32(level)) * mult);

        if (IsMythic(mode.level) && !creature->IsCustomCloned() && !creature->IsTemporarySummon() && CanClone(creature))
        {
            creature->SetCustomCloned(true);
            QueueClones(creature, MythicOf(mode.level));
        }
    }

    bool DonjonsModule::CanClone(Creature* creature) const
    {
        CreatureInfo const* info = creature->GetCreatureInfo();
        if (!info || IsBoss(creature->GetEntry()) || info->Rank >= 2 || info->HealthMultiplier >= 4.0f)
            return false;
        if (!creature->GetScriptName().empty())
            return false;
        if (info->NpcFlags || info->CreatureType == CREATURE_TYPE_CRITTER || info->MaxLevel <= 5)
            return false;
        if (creature->HasFlag(UNIT_FIELD_FLAGS, UNIT_FLAG_UNINTERACTIBLE | UNIT_FLAG_SPAWNING))
            return false;
        if (creature->GetEntry() >= DONJONS_RARE_BASE && creature->GetEntry() <= DONJONS_RARE_LAST + 20)
            return false;
        return true;
    }

    // Clones : créés au prochain passage du thread de la carte (pas pendant le chargement de la grille)
    void DonjonsModule::QueueClones(Creature* creature, uint32 mythic)
    {
        float total = MYTH_COUNT[mythic] - 1.0f;
        uint32 count = uint32(total);
        if (rand_norm_f() < total - float(count))
            ++count;
        if (!count)
            return;
        ObjectGuid guid = creature->GetObjectGuid();
        creature->GetMap()->GetMessager().AddMessage([guid, count](Map* map)
        {
            Creature* src = map->GetCreature(guid);
            if (!src || !src->IsAlive() || src->IsInCombat())
                return;
            for (uint32 i = 0; i < count; ++i)
            {
                float angle = rand_norm_f() * 6.2831853f;
                float dist = 2.0f + rand_norm_f() * 1.5f;
                float x = src->GetPositionX() + dist * std::cos(angle);
                float y = src->GetPositionY() + dist * std::sin(angle);
                float z = src->GetPositionZ();
                src->UpdateAllowedPositionZ(x, y, z);
                src->SummonCreature(src->GetEntry(), x, y, z, src->GetOrientation(), TEMPSPAWN_CORPSE_TIMED_DESPAWN, 300000);
            }
        });
    }

    int32 DonjonsModule::GetBest(Player* player, int32 dungeon) const
    {
        auto it = bestLevels.find((uint64(player->GetGUIDLow()) << 8) | uint64(dungeon & 0xFF));
        return it == bestLevels.end() ? -1 : it->second;
    }

    void DonjonsModule::SetBest(Player* player, int32 dungeon, int32 value)
    {
        bestLevels[(uint64(player->GetGUIDLow()) << 8) | uint64(dungeon & 0xFF)] = value;
        CharacterDatabase.PExecute("REPLACE INTO `custom_mythic_best` (`guid`, `dungeon`, `best`) VALUES (%u, %i, %i)",
            player->GetGUIDLow(), dungeon, value);
    }

    void DonjonsModule::ApplyToInstance(Map* map, InstanceMode& mode)
    {
        std::vector<uint64> keys;
        keys.reserve(mode.origLevels.size());
        for (auto const& kv : mode.origLevels)
            keys.push_back(kv.first);
        for (uint64 key : keys)
        {
            if (Creature* creature = map->GetCreature(ObjectGuid(key)))
                ApplyToCreature(creature, mode);
        }
    }

    void DonjonsModule::SaveMode(uint32 instanceId, const InstanceMode& mode)
    {
        CharacterDatabase.PExecute("REPLACE INTO `custom_instance_mode` (`instance_id`, `map`, `dungeon`, `level`, `locked`) VALUES (%u, %u, %i, %u, %u)",
            instanceId, mode.mapId, mode.dungeon, mode.level, mode.locked ? 1 : 0);
    }

    void DonjonsModule::Announce(Map* map, const std::string& text)
    {
        for (auto const& ref : map->GetPlayers())
        {
            if (Player* player = ref.getSource())
                ChatHandler(player).SendSysMessage(text.c_str());
        }
    }

    void DonjonsModule::OnAddToWorld(Creature* creature)
    {
        std::lock_guard<std::recursive_mutex> guard(lock);
        if (!creature || !creature->IsInWorld())
            return;
        Map* map = creature->GetMap();
        if (!map || !map->IsDungeon() || !IsDonjonMap(map->GetId()))
            return;
        if (!IsScalable(creature))
            return;

        InstanceMode& mode = instances[map->GetInstanceId()];
        mode.mapId = map->GetId();

        uint64 key = creature->GetObjectGuid().GetRawValue();
        if (mode.origLevels.find(key) == mode.origLevels.end())
            mode.origLevels[key] = creature->GetLevel();

        if (mode.level > 0)
            ApplyToCreature(creature, mode);
    }

    void DonjonsModule::OnGossipHello(Player* player, Creature* creature)
    {
        std::lock_guard<std::recursive_mutex> guard(lock);
        if (!player || !creature || !IsGardien(creature->GetEntry()))
            return;
        Map* map = creature->GetMap();
        if (!map || !map->IsDungeon())
            return;

        InstanceMode& mode = instances[map->GetInstanceId()];
        mode.mapId = map->GetId();
        if (mode.dungeon < 0)
            mode.dungeon = int32(creature->GetEntry() - DONJONS_NPC_BASE);

        GossipMenu& menu = player->GetPlayerMenu()->GetGossipMenu();
        menu.AddMenuItem(GOSSIP_ICON_CHAT, "Classement mythique de ce donjon", GOSSIP_SENDER_MAIN, ACTION_CLASSEMENT, "", false);
        std::string info = "Mode actuel : " + NomMode(mode.level);
        if (mode.locked)
            info += " (verrouillé, le donjon est entamé)";
        menu.AddMenuItem(GOSSIP_ICON_CHAT, info, GOSSIP_SENDER_MAIN, ACTION_INFO, "", false);

        if (mode.locked)
            return;

        Group* group = player->GetGroup();
        if (group && !group->IsLeader(player->GetObjectGuid()))
        {
            menu.AddMenuItem(GOSSIP_ICON_CHAT, "Seul le chef de groupe peut choisir le mode.", GOSSIP_SENDER_MAIN, ACTION_INFO, "", false);
            return;
        }

        const int32 idx = int32(creature->GetEntry() - DONJONS_NPC_BASE);
        if (mode.level != 0)
            menu.AddMenuItem(GOSSIP_ICON_BATTLE, "Mode normal", GOSSIP_SENDER_MAIN, ACTION_NORMAL, "", false);
        if (idx < DONJONS_MODES_4050)
        {
            if (mode.level != 40)
                menu.AddMenuItem(GOSSIP_ICON_BATTLE, "Mode niveau 40 (monstres niveau 40, boss niveau 41)", GOSSIP_SENDER_MAIN, ACTION_NIV40, "Passer le donjon en mode niveau 40 ?", false);
            if (mode.level != 50)
                menu.AddMenuItem(GOSSIP_ICON_BATTLE, "Mode niveau 50 (monstres niveau 50, boss niveau 51)", GOSSIP_SENDER_MAIN, ACTION_NIV50, "Passer le donjon en mode niveau 50 ?", false);
        }
        // mythique : jusqu'au meilleur niveau réussi par le chef + 1
        const int32 bestLevel = GetBest(player, idx);
        const int32 maxM = std::min<int32>(DONJONS_MYTHIC_MAX, bestLevel + 1);
        menu.AddMenuItem(GOSSIP_ICON_CHAT, bestLevel < 0 ? std::string("Mythique : aucun niveau réussi") :
            "Mythique : meilleur niveau réussi " + NomMode(DONJONS_MYTHIC + bestLevel).substr(9), GOSSIP_SENDER_MAIN, ACTION_INFO, "", false);
        for (int32 m = 0; m <= maxM; ++m)
        {
            if (mode.level == uint32(DONJONS_MYTHIC + m))
                continue;
            char buf[160];
            snprintf(buf, sizeof(buf), "%s (niveau 60, monstres x%.1f, PV et dégâts x%.2f)",
                NomMode(DONJONS_MYTHIC + m).c_str(), MYTH_COUNT[m], MYTH_POWER[m]);
            menu.AddMenuItem(GOSSIP_ICON_BATTLE, buf, GOSSIP_SENDER_MAIN, ACTION_MYTH + m,
                "Passer le donjon en " + NomMode(DONJONS_MYTHIC + m) + " ?", false);
        }
    }

    bool DonjonsModule::OnGossipSelect(Player* player, Creature* creature, uint32 sender, uint32 action, const std::string& code, uint32 gossipListId)
    {
        std::lock_guard<std::recursive_mutex> guard(lock);
        if (!player || !creature || !IsGardien(creature->GetEntry()))
            return false;
        const bool myth = action >= ACTION_MYTH && action <= ACTION_MYTH + DONJONS_MYTHIC_MAX;
        if (action == ACTION_CLASSEMENT)
        {
            player->GetPlayerMenu()->CloseGossip();
            ShowDonjon(player, int32(creature->GetEntry() - DONJONS_NPC_BASE));
            return true;
        }
        if (action != ACTION_INFO && action != ACTION_NORMAL && action != ACTION_NIV40 && action != ACTION_NIV50 && !myth)
            return false;

        player->GetPlayerMenu()->CloseGossip();
        if (action == ACTION_INFO)
            return true;

        Map* map = creature->GetMap();
        if (!map || !map->IsDungeon())
            return true;

        InstanceMode& mode = instances[map->GetInstanceId()];
        if (mode.locked)
        {
            ChatHandler(player).SendSysMessage("Le mode ne peut plus être changé : le donjon est déjà entamé.");
            return true;
        }
        Group* group = player->GetGroup();
        if (group && !group->IsLeader(player->GetObjectGuid()))
            return true;

        uint32 level = action == ACTION_NIV50 ? 50 : (action == ACTION_NIV40 ? 40 : 0);
        const int32 idx = int32(creature->GetEntry() - DONJONS_NPC_BASE);
        if (myth)
        {
            int32 m = int32(action - ACTION_MYTH);
            if (m > GetBest(player, idx) + 1)
                return true;
            level = DONJONS_MYTHIC + uint32(m);
        }
        else if (level && idx >= DONJONS_MODES_4050)
            return true;
        mode.mapId = map->GetId();
        if (mode.dungeon < 0)
            mode.dungeon = int32(creature->GetEntry() - DONJONS_NPC_BASE);
        mode.level = level;
        ApplyToInstance(map, mode);
        SaveMode(map->GetInstanceId(), mode);

        const DonjonInfo* d = GetDonjon(mode);
        std::string text = "|cffffd100" + std::string(d ? d->nom : "Donjon") + "|r : mode " + NomMode(level) + " activé.";
        Announce(map, text);
        return true;
    }

    void DonjonsModule::RecordRun(Map* map, const DonjonInfo* d, uint32 m, uint32 seconds)
    {
        std::string names;
        std::vector<Player*> players;
        for (auto const& ref : map->GetPlayers())
        {
            if (Player* player = ref.getSource())
            {
                players.push_back(player);
                if (!names.empty())
                    names += ", ";
                names += player->GetName();
            }
        }
        if (names.size() > 250)
            names = names.substr(0, 250);
        std::string esc = names;
        CharacterDatabase.escape_string(esc);
        CharacterDatabase.PExecute("INSERT INTO `custom_mythic_record` (`dungeon`, `level`, `seconds`, `names`, `date`) VALUES (%i, %u, %u, '%s', %u)",
            int32(d->index), m, seconds, esc.c_str(), uint32(time(nullptr)));

        Record& rec = records[int32(d->index)];
        const bool nouveau = rec.level < int32(m) || (rec.level == int32(m) && seconds < rec.seconds);
        if (!nouveau)
            return;
        rec.level = int32(m);
        rec.seconds = seconds;
        rec.names = names;
        EnvoyerATous("|cffff8000Nouveau record mythique|r : |cffffd100" + std::string(d->nom) + "|r " + NiveauM(int32(m)) +
            " en " + Duree(seconds) + " par " + names + " !");

        // monture de record : une fois par personnage
        for (Player* player : players)
        {
            if (rewarded.count(player->GetGUIDLow()))
                continue;
            rewarded.insert(player->GetGUIDLow());
            CharacterDatabase.PExecute("REPLACE INTO `custom_mythic_reward` (`guid`) VALUES (%u)", player->GetGUIDLow());
            if (Item* item = Item::CreateItem(DONJONS_RECORD_MOUNT, 1, player))
            {
                CharacterDatabase.BeginTransaction();
                item->SaveToDB();
                CharacterDatabase.CommitTransaction();
                MailDraft("Record mythique", "Félicitations pour votre premier record mythique ! Voici votre monture.")
                    .AddItem(item).SendMailTo(player, MailSender(MAIL_CREATURE, DONJONS_NPC_BASE + d->index), MAIL_CHECK_MASK_COPIED);
                ChatHandler(player).SendSysMessage("Premier record mythique : une monture vous attend dans la boîte aux lettres.");
            }
        }
    }

    void DonjonsModule::ShowDonjon(Player* player, int32 dungeon)
    {
        ChatHandler ch(player);
        ch.SendSysMessage(("|cffffd100Classement mythique : " + std::string(NomDonjon(dungeon)) + "|r").c_str());
        uint32 rang = 0;
        if (auto result = CharacterDatabase.PQuery(
            "SELECT `level`, `seconds`, `names` FROM `custom_mythic_record` WHERE `dungeon` = %i ORDER BY `level` DESC, `seconds` ASC LIMIT 5", dungeon))
        {
            do
            {
                Field* f = result->Fetch();
                ++rang;
                ch.SendSysMessage((std::to_string(rang) + ". " + NiveauM(f[0].GetInt32()) + " en " + Duree(f[1].GetUInt32()) +
                    " : " + f[2].GetCppString()).c_str());
            }
            while (result->NextRow());
        }
        if (!rang)
            ch.SendSysMessage("Aucun passage mythique enregistré pour ce donjon.");
        const int32 best = GetBest(player, dungeon);
        ch.SendSysMessage(best < 0 ? "Votre meilleur niveau : aucun." : ("Votre meilleur niveau : " + NiveauM(best) + ".").c_str());
    }

    std::vector<ModuleChatCommand>* DonjonsModule::GetCommandTable()
    {
        static std::vector<ModuleChatCommand> commandTable =
        {
            { "classement", std::bind(&DonjonsModule::HandleClassement, this, std::placeholders::_1, std::placeholders::_2), SEC_PLAYER },
            { "moi", std::bind(&DonjonsModule::HandleMoi, this, std::placeholders::_1, std::placeholders::_2), SEC_PLAYER },
        };
        return &commandTable;
    }

    bool DonjonsModule::HandleClassement(WorldSession* session, const std::string& args)
    {
        std::lock_guard<std::recursive_mutex> guard(lock);
        Player* player = session ? session->GetPlayer() : nullptr;
        if (!player)
            return false;
        // .myth classement <numéro> : top 5 d'un donjon
        if (!args.empty() && std::isdigit(static_cast<unsigned char>(args[0])))
        {
            ShowDonjon(player, std::atoi(args.c_str()));
            return true;
        }
        ChatHandler ch(player);
        ch.SendSysMessage("|cffff8000Records mythiques|r (.myth classement <numéro> pour le top 5 d'un donjon)");
        int32 last = -1;
        for (uint32 i = 0; i < DONJONS_COUNT; ++i)
        {
            const int32 idx = int32(DONJONS[i].index);
            if (idx == last)
                continue;
            last = idx;
            auto it = records.find(idx);
            std::string line = std::to_string(idx) + ". " + DONJONS[i].nom + " : ";
            if (it == records.end() || it->second.level < 0)
                line += "|cff808080aucun|r";
            else
                line += "|cff00ff00" + NiveauM(it->second.level) + "|r en " + Duree(it->second.seconds) + " (" + it->second.names + ")";
            ch.SendSysMessage(line.c_str());
        }
        return true;
    }

    bool DonjonsModule::HandleMoi(WorldSession* session, const std::string& /*args*/)
    {
        std::lock_guard<std::recursive_mutex> guard(lock);
        Player* player = session ? session->GetPlayer() : nullptr;
        if (!player)
            return false;
        ChatHandler ch(player);
        ch.SendSysMessage("|cffffd100Vos meilleurs niveaux mythiques|r");
        int32 last = -1;
        uint32 n = 0;
        for (uint32 i = 0; i < DONJONS_COUNT; ++i)
        {
            const int32 idx = int32(DONJONS[i].index);
            if (idx == last)
                continue;
            last = idx;
            const int32 best = GetBest(player, idx);
            if (best < 0)
                continue;
            ++n;
            ch.SendSysMessage((std::string(DONJONS[i].nom) + " : " + NiveauM(best)).c_str());
        }
        if (!n)
            ch.SendSysMessage("Aucun niveau mythique réussi pour l'instant.");
        return true;
    }

    void DonjonsModule::OnKill(Unit* unit, Unit* victim)
    {
        std::lock_guard<std::recursive_mutex> guard(lock);
        if (!victim || victim->GetTypeId() != TYPEID_UNIT)
            return;
        Creature* creature = static_cast<Creature*>(victim);
        Map* map = creature->GetMap();
        if (!map || !map->IsDungeon() || !IsDonjonMap(map->GetId()) || !IsScalable(creature))
            return;

        InstanceMode& mode = instances[map->GetInstanceId()];
        mode.mapId = map->GetId();
        if (!mode.locked)
        {
            mode.locked = true;
            mode.start = time(nullptr);
            SaveMode(map->GetInstanceId(), mode);
        }

        const DonjonInfo* d = GetDonjon(mode);
        if (!d || mode.level == 0 || creature->GetEntry() != d->finalBoss)
            return;

        if (IsMythic(mode.level))
        {
            const int32 m = int32(MythicOf(mode.level));
            for (auto const& ref : map->GetPlayers())
            {
                if (Player* player = ref.getSource())
                    if (GetBest(player, d->index) < m)
                        SetBest(player, d->index, m);
            }
            const uint32 seconds = mode.start ? uint32(time(nullptr) - mode.start) : 0;
            std::string text = "|cffffd100" + std::string(d->nom) + "|r : " + NomMode(mode.level) + " réussi";
            text += seconds ? " en " + Duree(seconds) + " !" : " !";
            if (m < DONJONS_MYTHIC_MAX)
                text += " " + NomMode(mode.level + 1) + " débloqué.";
            Announce(map, text);
            if (seconds)
                RecordRun(map, d, uint32(m), seconds);
            return;
        }

        uint32 credit = DONJONS_CREDIT_BASE + d->index * 2 + (mode.level >= 50 ? 1 : 0);
        for (auto const& ref : map->GetPlayers())
        {
            if (Player* player = ref.getSource())
                player->KilledMonsterCredit(credit);
        }
        Announce(map, "|cffffd100" + std::string(d->nom) + "|r : boss final vaincu en mode " + NomMode(mode.level) + " !");
    }

    bool DonjonsModule::OnGenerateMoneyLoot(Loot* loot, uint32& outMoney)
    {
        std::lock_guard<std::recursive_mutex> guard(lock);
        if (!loot || !loot->GetLootTarget() || loot->GetLootTarget()->GetTypeId() != TYPEID_UNIT)
            return false;
        Creature* creature = const_cast<Creature*>(static_cast<Creature const*>(loot->GetLootTarget()));
        Map* map = creature->GetMap();
        if (!map || !map->IsDungeon() || !IsDonjonMap(map->GetId()))
            return false;

        auto it = instances.find(map->GetInstanceId());
        if (it == instances.end() || it->second.level == 0)
            return false;
        auto lv = it->second.origLevels.find(creature->GetObjectGuid().GetRawValue());
        if (lv == it->second.origLevels.end() || lv->second == 0 || lv->second >= creature->GetLevel())
            return false;

        CreatureInfo const* info = creature->GetCreatureInfo();
        if (!info || info->MaxLootGold == 0)
            return false;

        uint32 minGold = std::min(info->MinLootGold, info->MaxLootGold);
        uint32 maxGold = info->MaxLootGold;
        float base = float(minGold == maxGold ? maxGold : urand(minGold, maxGold));
        float ratio = std::pow(float(creature->GetLevel()) / float(lv->second), 2.0f);
        ratio = std::min(ratio, 20.0f);
        outMoney = uint32(base * ratio * sWorld.getConfig(CONFIG_FLOAT_RATE_DROP_MONEY));
        return true;
    }

    // Boss rares : en mode 40 / 50, butin du niveau du mode (épique du monde a ce niveau)
    bool DonjonsModule::OnFillLoot(Loot* loot, Player* owner)
    {
        std::lock_guard<std::recursive_mutex> guard(lock);
        if (!loot || !owner || loot->GetLootType() != LOOT_CORPSE || !loot->GetLootTarget() || loot->GetLootTarget()->GetTypeId() != TYPEID_UNIT)
            return false;
        Creature const* creature = static_cast<Creature const*>(loot->GetLootTarget());
        const uint32 entry = creature->GetEntry();
        Map* map = creature->GetMap();
        if (!map || !map->IsDungeon())
            return false;
        auto it = instances.find(map->GetInstanceId());
        if (it == instances.end() || it->second.level == 0)
            return false;

        // mythique : butin mythique des boss (2 objets, 3 pour le boss final)
        if (IsMythic(it->second.level))
        {
            if (!IsBoss(entry))
                return false;
            const DonjonInfo* d = GetDonjon(it->second);
            const uint32 m = MythicOf(it->second.level);
            const uint32 id = DONJONS_MYTHIC_LOOT + ((d && entry == d->finalBoss) ? 100 : 0) + m;
            LootTemplate const* tab = LootTemplates_Creature.GetLootFor(id);
            if (!tab)
                return false;
            tab->Process(*loot, owner, LootTemplates_Creature.IsRatesAllowed());
            return true;
        }

        if (entry < DONJONS_RARE_BASE || entry > DONJONS_RARE_LAST)
            return false;

        const uint32 lootId = entry + (it->second.level >= 50 ? 40 : 20);
        LootTemplate const* tab = LootTemplates_Creature.GetLootFor(lootId);
        if (!tab)
            return false;
        tab->Process(*loot, owner, LootTemplates_Creature.IsRatesAllowed());
        return true;
    }
}
