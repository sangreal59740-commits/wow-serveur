#include "RaidsModule.h"

#include "AI/ScriptDevAI/include/sc_gossip.h"
#include "Chat/Chat.h"
#include "Database/DatabaseEnv.h"
#include "Entities/Creature.h"
#include "Entities/GossipDef.h"
#include "Entities/Item.h"
#include "Entities/ObjectGuid.h"
#include "Entities/Player.h"
#include "Globals/ObjectMgr.h"
#include "Groups/Group.h"
#include "Log/Log.h"
#include "Loot/LootMgr.h"
#include "Mails/Mail.h"
#include "Maps/Map.h"
#include "Util/Util.h"
#include "World/World.h"

#include <algorithm>
#include <cmath>
#include <ctime>

namespace cmangos_module
{
    static const RaidInfo RAIDS[RAIDS_COUNT] =
    {
        { 0, 309, 20, 14834, "Zul'Gurub" },
        { 1, 509, 20, 15339, "Ruines d'Ahn'Qiraj" },
        { 2, 409, 40, 11502, "Cœur du Magma" },
        { 3, 249, 40, 10184, "Repaire d'Onyxia" },
        { 4, 469, 40, 11583, "Repaire de l'Aile noire" },
        { 5, 531, 40, 15727, "Temple d'Ahn'Qiraj" },
        { 6, 533, 40, 15990, "Naxxramas" },
    };

    enum RaidsActions
    {
        ACTION_INFO = GOSSIP_ACTION_INFO_DEF + 1,
        ACTION_R10  = GOSSIP_ACTION_INFO_DEF + 10,
        ACTION_R20  = GOSSIP_ACTION_INFO_DEF + 20,
    };

    static bool IsGardien(uint32 entry) { return entry >= RAIDS_NPC_BASE && entry < RAIDS_NPC_BASE + RAIDS_COUNT; }
    static bool IsLegendary(uint32 entry) { return entry >= RAIDS_LEG_BASE && entry < RAIDS_LEG_BASE + RAIDS_COUNT; }

    RaidsModule::RaidsModule() : Module("Raids", nullptr)
    {
    }

    void RaidsModule::OnInitialize()
    {
        CharacterDatabase.Execute(
            "CREATE TABLE IF NOT EXISTS `custom_raid_size` ("
            " `instance_id` INT UNSIGNED NOT NULL, `size` TINYINT UNSIGNED NOT NULL DEFAULT 20,"
            " `locked` TINYINT UNSIGNED NOT NULL DEFAULT 0, `legendary` TINYINT UNSIGNED NOT NULL DEFAULT 0,"
            " PRIMARY KEY (`instance_id`)) ENGINE=InnoDB DEFAULT CHARSET=utf8");
        CharacterDatabase.Execute("DELETE FROM `custom_raid_size` WHERE `instance_id` NOT IN (SELECT `id` FROM `instance`)");
        CharacterDatabase.Execute(
            "CREATE TABLE IF NOT EXISTS `custom_raid_fragment` ("
            " `guid` INT UNSIGNED NOT NULL, `raid` INT UNSIGNED NOT NULL,"
            " PRIMARY KEY (`guid`, `raid`)) ENGINE=InnoDB DEFAULT CHARSET=utf8");

        if (auto result = CharacterDatabase.Query("SELECT `instance_id`, `size`, `locked`, `legendary` FROM `custom_raid_size`"))
        {
            do
            {
                Field* f = result->Fetch();
                RaidMode& mode = instances[f[0].GetUInt32()];
                mode.size = f[1].GetUInt32() == 10 ? 10 : 20;
                mode.locked = f[2].GetUInt32() != 0;
                mode.legendarySpawned = f[3].GetUInt32() != 0;
            }
            while (result->NextRow());
        }
        if (auto result = CharacterDatabase.Query("SELECT `guid`, `raid` FROM `custom_raid_fragment`"))
        {
            do
            {
                Field* f = result->Fetch();
                fragments.insert((uint64(f[0].GetUInt32()) << 8) | uint64(f[1].GetUInt32()));
            }
            while (result->NextRow());
        }
        if (auto result = WorldDatabase.Query("SELECT `entry`, `raid`, `loot10`, `loot20`, `final` FROM `custom_raid_boss`"))
        {
            do
            {
                Field* f = result->Fetch();
                RaidBoss& b = bosses[f[0].GetUInt32()];
                b.raid = f[1].GetUInt32();
                b.loot10 = f[2].GetUInt32();
                b.loot20 = f[3].GetUInt32();
                b.final = f[4].GetUInt32() != 0;
            }
            while (result->NextRow());
        }
        sLog.outString("Raids : %u boss, %u instance(s) enregistree(s)", uint32(bosses.size()), uint32(instances.size()));
    }

    const RaidInfo* RaidsModule::GetRaid(uint32 mapId) const
    {
        for (uint32 i = 0; i < RAIDS_COUNT; ++i)
            if (RAIDS[i].mapId == mapId)
                return &RAIDS[i];
        return nullptr;
    }

    bool RaidsModule::IsScalable(Creature* creature) const
    {
        if (!creature || creature->IsPet() || creature->IsTotem() || IsGardien(creature->GetEntry()))
            return false;
        if (creature->GetOwnerGuid().IsPlayer() || creature->HasCharmer())
            return false;
        return true;
    }

    void RaidsModule::Apply(Creature* creature, const RaidInfo& raid, RaidMode& mode)
    {
        if (!IsScalable(creature) || !creature->IsAlive() || creature->IsInCombat())
            return;
        uint64 key = creature->GetObjectGuid().GetRawValue();
        auto it = mode.applied.find(key);
        if (it != mode.applied.end() && it->second == mode.size)
            return;

        const float hp = float(mode.size) / float(raid.origSize);
        const float dmg = std::sqrt(hp);
        creature->SelectLevel(creature->GetLevel());
        if (hp != 1.0f)
        {
            creature->SetCreateHealth(std::max<uint32>(1, uint32(creature->GetCreateHealth() * hp)));
            for (WeaponAttackType att : { BASE_ATTACK, OFF_ATTACK, RANGED_ATTACK })
            {
                creature->SetBaseWeaponDamage(att, MINDAMAGE, creature->GetBaseWeaponDamage(att, MINDAMAGE) * dmg);
                creature->SetBaseWeaponDamage(att, MAXDAMAGE, creature->GetBaseWeaponDamage(att, MAXDAMAGE) * dmg);
            }
            creature->UpdateAllStats();
            creature->SetHealth(creature->GetMaxHealth());
        }
        creature->SetCustomSpellMult(dmg);
        mode.applied[key] = mode.size;
    }

    void RaidsModule::ApplyToInstance(Map* map, const RaidInfo& raid, RaidMode& mode)
    {
        std::vector<uint64> keys;
        for (auto const& kv : mode.applied)
            keys.push_back(kv.first);
        for (uint64 key : keys)
            if (Creature* creature = map->GetCreature(ObjectGuid(key)))
                Apply(creature, raid, mode);
    }

    void RaidsModule::Save(uint32 instanceId, const RaidMode& mode)
    {
        CharacterDatabase.PExecute("REPLACE INTO `custom_raid_size` (`instance_id`, `size`, `locked`, `legendary`) VALUES (%u, %u, %u, %u)",
            instanceId, mode.size, mode.locked ? 1 : 0, mode.legendarySpawned ? 1 : 0);
    }

    void RaidsModule::Announce(Map* map, const std::string& text)
    {
        for (auto const& ref : map->GetPlayers())
            if (Player* player = ref.getSource())
                ChatHandler(player).SendSysMessage(text.c_str());
    }

    void RaidsModule::OnAddToWorld(Creature* creature)
    {
        std::lock_guard<std::recursive_mutex> guard(lock);
        if (!creature || !creature->IsInWorld())
            return;
        Map* map = creature->GetMap();
        if (!map || !map->IsRaid())
            return;
        const RaidInfo* raid = GetRaid(map->GetId());
        if (!raid || !IsScalable(creature))
            return;
        RaidMode& mode = instances[map->GetInstanceId()];
        uint64 key = creature->GetObjectGuid().GetRawValue();
        mode.applied.erase(key);    // nouvel objet (chargement de la grille ou apparition) : stats de base
        Apply(creature, *raid, mode);
    }

    void RaidsModule::OnGossipHello(Player* player, Creature* creature)
    {
        std::lock_guard<std::recursive_mutex> guard(lock);
        if (!player || !creature || !IsGardien(creature->GetEntry()))
            return;
        Map* map = creature->GetMap();
        if (!map || !map->IsRaid())
            return;
        RaidMode& mode = instances[map->GetInstanceId()];
        GossipMenu& menu = player->GetPlayerMenu()->GetGossipMenu();
        std::string info = "Taille actuelle : " + std::to_string(mode.size) + " joueurs";
        if (mode.locked)
            info += " (verrouillée, le raid est entamé)";
        menu.AddMenuItem(GOSSIP_ICON_CHAT, info, GOSSIP_SENDER_MAIN, ACTION_INFO, "", false);
        if (mode.locked)
            return;
        Group* group = player->GetGroup();
        if (group && !group->IsLeader(player->GetObjectGuid()))
        {
            menu.AddMenuItem(GOSSIP_ICON_CHAT, "Seul le chef de groupe peut choisir la taille.", GOSSIP_SENDER_MAIN, ACTION_INFO, "", false);
            return;
        }
        if (mode.size != 10)
            menu.AddMenuItem(GOSSIP_ICON_BATTLE, "Raid à 10 joueurs", GOSSIP_SENDER_MAIN, ACTION_R10, "Passer le raid à 10 joueurs ?", false);
        if (mode.size != 20)
            menu.AddMenuItem(GOSSIP_ICON_BATTLE, "Raid à 20 joueurs", GOSSIP_SENDER_MAIN, ACTION_R20, "Passer le raid à 20 joueurs ?", false);
    }

    bool RaidsModule::OnGossipSelect(Player* player, Creature* creature, uint32 sender, uint32 action, const std::string& code, uint32 gossipListId)
    {
        std::lock_guard<std::recursive_mutex> guard(lock);
        if (!player || !creature || !IsGardien(creature->GetEntry()))
            return false;
        if (action != ACTION_INFO && action != ACTION_R10 && action != ACTION_R20)
            return false;
        player->GetPlayerMenu()->CloseGossip();
        if (action == ACTION_INFO)
            return true;
        Map* map = creature->GetMap();
        const RaidInfo* raid = map ? GetRaid(map->GetId()) : nullptr;
        if (!raid)
            return true;
        RaidMode& mode = instances[map->GetInstanceId()];
        if (mode.locked)
        {
            ChatHandler(player).SendSysMessage("La taille ne peut plus être changée : le raid est déjà entamé.");
            return true;
        }
        Group* group = player->GetGroup();
        if (group && !group->IsLeader(player->GetObjectGuid()))
            return true;
        mode.size = action == ACTION_R10 ? 10 : 20;
        ApplyToInstance(map, *raid, mode);
        Save(map->GetInstanceId(), mode);
        Announce(map, "|cffffd100" + std::string(raid->nom) + "|r : raid à " + std::to_string(mode.size) + " joueurs.");
        return true;
    }

    // apparition du boss legendaire, 30 s apres la mort du boss final (dans le thread de la carte)
    static void SpawnLater(Map* map, uint32 entry, float x, float y, float z, float o, time_t at)
    {
        if (time(nullptr) < at)
        {
            map->GetMessager().AddMessage([=](Map* m) { SpawnLater(m, entry, x, y, z, o, at); });
            return;
        }
        WorldObject::SummonCreature(TempSpawnSettings(nullptr, entry, x, y, z, o, TEMPSPAWN_CORPSE_TIMED_DESPAWN, 1800000), map);
    }

    void RaidsModule::GiveFragment(Player* player, uint32 raid)
    {
        uint64 key = (uint64(player->GetGUIDLow()) << 8) | uint64(raid);
        if (fragments.find(key) != fragments.end())
            return;
        fragments.insert(key);
        CharacterDatabase.PExecute("REPLACE INTO `custom_raid_fragment` (`guid`, `raid`) VALUES (%u, %u)", player->GetGUIDLow(), raid);

        const uint32 itemId = RAIDS_FRAG_BASE + raid;
        if (player->StoreNewItemInBestSlots(itemId, 1))
        {
            ChatHandler(player).SendSysMessage("Vous recevez un fragment légendaire.");
            return;
        }
        // sacs pleins : par courrier
        if (Item* item = Item::CreateItem(itemId, 1, player))
        {
            CharacterDatabase.BeginTransaction();
            item->SaveToDB();
            CharacterDatabase.CommitTransaction();
            MailDraft("Fragment légendaire").AddItem(item).SendMailTo(player, MailSender(MAIL_CREATURE, RAIDS_LEG_BASE + raid), MAIL_CHECK_MASK_COPIED);
            ChatHandler(player).SendSysMessage("Sacs pleins : votre fragment légendaire vous attend dans la boîte aux lettres.");
        }
    }

    void RaidsModule::OnKill(Unit* unit, Unit* victim)
    {
        std::lock_guard<std::recursive_mutex> guard(lock);
        if (!victim || victim->GetTypeId() != TYPEID_UNIT)
            return;
        Creature* creature = static_cast<Creature*>(victim);
        Map* map = creature->GetMap();
        if (!map || !map->IsRaid())
            return;
        const RaidInfo* raid = GetRaid(map->GetId());
        if (!raid)
            return;
        RaidMode& mode = instances[map->GetInstanceId()];
        if (!mode.locked && IsScalable(creature))
        {
            mode.locked = true;
            Save(map->GetInstanceId(), mode);
        }

        if (creature->GetEntry() == raid->finalBoss && !mode.legendarySpawned)
        {
            mode.legendarySpawned = true;
            Save(map->GetInstanceId(), mode);
            WorldObject* where = (unit && unit->IsPlayerControlled()) ? static_cast<WorldObject*>(unit) : static_cast<WorldObject*>(creature);
            float o = where->GetOrientation();
            float x = where->GetPositionX() + 8.0f * std::cos(o);
            float y = where->GetPositionY() + 8.0f * std::sin(o);
            float z = where->GetPositionZ();
            where->UpdateAllowedPositionZ(x, y, z);
            SpawnLater(map, RAIDS_LEG_BASE + raid->index, x, y, z, o + 3.14159f, time(nullptr) + 30);
            Announce(map, "|cffff8000" + std::string(raid->nom) + "|r : la terre tremble... un boss légendaire arrive dans 30 secondes !");
            return;
        }

        if (IsLegendary(creature->GetEntry()))
        {
            for (auto const& ref : map->GetPlayers())
                if (Player* player = ref.getSource())
                    GiveFragment(player, creature->GetEntry() - RAIDS_LEG_BASE);
            Announce(map, "|cffff8000" + std::string(raid->nom) + "|r : boss légendaire vaincu !");
        }
    }

    bool RaidsModule::OnFillLoot(Loot* loot, Player* owner)
    {
        std::lock_guard<std::recursive_mutex> guard(lock);
        if (!loot || !owner || loot->GetLootType() != LOOT_CORPSE || !loot->GetLootTarget() || loot->GetLootTarget()->GetTypeId() != TYPEID_UNIT)
            return false;
        Creature const* creature = static_cast<Creature const*>(loot->GetLootTarget());
        Map* map = creature->GetMap();
        if (!map || !map->IsRaid() || !GetRaid(map->GetId()))
            return false;
        const RaidMode& mode = instances[map->GetInstanceId()];
        const uint32 entry = creature->GetEntry();

        uint32 lootId = 0;
        if (IsLegendary(entry))
            lootId = (mode.size == 10 ? RAIDS_LEGLOOT10 : RAIDS_LEGLOOT20) + (entry - RAIDS_LEG_BASE);
        else
        {
            auto it = bosses.find(entry);
            if (it == bosses.end())
                return false;
            lootId = mode.size == 10 ? it->second.loot10 : it->second.loot20;
        }
        LootTemplate const* tab = LootTemplates_Creature.GetLootFor(lootId);
        if (!tab)
            return false;
        tab->Process(*loot, owner, LootTemplates_Creature.IsRatesAllowed());
        return true;
    }
}
