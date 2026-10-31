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
#include "Util/Util.h"
#include "World/World.h"

#include <algorithm>
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
    };
    static const uint32 DONJONS_COUNT = sizeof(DONJONS) / sizeof(DONJONS[0]);

    enum DonjonsActions
    {
        ACTION_INFO     = GOSSIP_ACTION_INFO_DEF + 1,
        ACTION_NORMAL   = GOSSIP_ACTION_INFO_DEF + 100,
        ACTION_NIV40    = GOSSIP_ACTION_INFO_DEF + 140,
        ACTION_NIV50    = GOSSIP_ACTION_INFO_DEF + 150,
    };

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
        if (level >= 50) return "Niveau 50";
        if (level >= 40) return "Niveau 40";
        return "Normal";
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
            if (creature->GetLevel() != orig)
                creature->SelectLevel(orig);
            creature->SetCustomSpellMult(1.0f);
            return;
        }

        int32 level = int32(orig) + int32(mode.level) + 1 - int32(d->refLevel);
        level = std::max(1, std::min(63, level));
        if (creature->GetLevel() != uint32(level))
            creature->SelectLevel(uint32(level));
        creature->SetCustomSpellMult(DamageRatio(orig, uint32(level)));
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

        if (mode.level != 0)
            menu.AddMenuItem(GOSSIP_ICON_BATTLE, "Mode normal", GOSSIP_SENDER_MAIN, ACTION_NORMAL, "", false);
        if (mode.level != 40)
            menu.AddMenuItem(GOSSIP_ICON_BATTLE, "Mode niveau 40 (monstres niveau 40, boss niveau 41)", GOSSIP_SENDER_MAIN, ACTION_NIV40, "Passer le donjon en mode niveau 40 ?", false);
        if (mode.level != 50)
            menu.AddMenuItem(GOSSIP_ICON_BATTLE, "Mode niveau 50 (monstres niveau 50, boss niveau 51)", GOSSIP_SENDER_MAIN, ACTION_NIV50, "Passer le donjon en mode niveau 50 ?", false);
    }

    bool DonjonsModule::OnGossipSelect(Player* player, Creature* creature, uint32 sender, uint32 action, const std::string& code, uint32 gossipListId)
    {
        if (!player || !creature || !IsGardien(creature->GetEntry()))
            return false;
        if (action != ACTION_INFO && action != ACTION_NORMAL && action != ACTION_NIV40 && action != ACTION_NIV50)
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

    void DonjonsModule::OnKill(Unit* unit, Unit* victim)
    {
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
            SaveMode(map->GetInstanceId(), mode);
        }

        const DonjonInfo* d = GetDonjon(mode);
        if (!d || mode.level == 0 || creature->GetEntry() != d->finalBoss)
            return;

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
}
