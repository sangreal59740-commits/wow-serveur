#include "ReliquesModule.h"

#include "Chat/Chat.h"
#include "Database/DatabaseEnv.h"
#include "Entities/Item.h"
#include "Entities/ItemPrototype.h"
#include "Entities/Player.h"
#include "Globals/ObjectAccessor.h"
#include "Globals/ObjectMgr.h"
#include "Log/Log.h"
#include "Maps/Map.h"
#include "Server/WorldSession.h"
#include "Spells/SpellMgr.h"

#include <algorithm>
#include <cstdio>
#include <sstream>

namespace cmangos_module
{
    static ReliquesModule* instance = nullptr;
    static const char* NOM_CASE[RELIQUES_CASES] = { "Artefact bleu", "Artefact rouge", "Artefact vert", "Artefact jaune", "Mascotte" };

    std::vector<ModuleChatCommand>* ReliquesModule::GetCommandTable()
    {
        static std::vector<ModuleChatCommand> commandTable =
        {
            { "liste", std::bind(&ReliquesModule::HandleListe, this, std::placeholders::_1, std::placeholders::_2), SEC_PLAYER },
            { "equiper", std::bind(&ReliquesModule::HandleEquiper, this, std::placeholders::_1, std::placeholders::_2), SEC_PLAYER },
            { "retirer", std::bind(&ReliquesModule::HandleRetirer, this, std::placeholders::_1, std::placeholders::_2), SEC_PLAYER },
        };
        return &commandTable;
    }

    void ReliquesModule::OnInitialize()
    {
        instance = this;
        CharacterDatabase.DirectExecute(
            "CREATE TABLE IF NOT EXISTS `custom_relique` (`guid` INT UNSIGNED NOT NULL, `emplacement` TINYINT UNSIGNED NOT NULL,"
            " `entry` INT UNSIGNED NOT NULL, PRIMARY KEY (`guid`, `emplacement`)) ENGINE=InnoDB DEFAULT CHARSET=utf8");
        WorldDatabase.DirectExecute(
            "CREATE TABLE IF NOT EXISTS `custom_relique_objet` (`entry` INT UNSIGNED NOT NULL, `type` TINYINT UNSIGNED NOT NULL,"
            " PRIMARY KEY (`entry`)) ENGINE=InnoDB DEFAULT CHARSET=utf8");
        std::lock_guard<std::recursive_mutex> guard(lock);
        if (auto r = WorldDatabase.Query("SELECT `entry`, `type` FROM `custom_relique_objet`"))
        {
            do
            {
                Field* f = r->Fetch();
                types[f[0].GetUInt32()] = uint8(f[1].GetUInt32());
            }
            while (r->NextRow());
        }
        if (auto r = CharacterDatabase.Query("SELECT `guid`, `emplacement`, `entry` FROM `custom_relique`"))
        {
            do
            {
                Field* f = r->Fetch();
                uint32 e = f[1].GetUInt32();
                if (e < RELIQUES_CASES)
                    Cases(f[0].GetUInt32())[e] = f[2].GetUInt32();
            }
            while (r->NextRow());
        }
        sLog.outString("Reliques : %u objets autorises, %u personnages", uint32(types.size()), uint32(cases.size()));
    }

    std::array<uint32, RELIQUES_CASES>& ReliquesModule::Cases(uint32 guid)
    {
        auto it = cases.find(guid);
        if (it == cases.end())
        {
            std::array<uint32, RELIQUES_CASES> vide{};
            it = cases.emplace(guid, vide).first;
        }
        return it->second;
    }

    void ReliquesModule::Bonus(Player* player, uint32 entry, bool apply)
    {
        ItemPrototype const* proto = sObjectMgr.GetItemPrototype(entry);
        if (!proto)
            return;
        player->_ApplyItemBonuses(proto, EQUIPMENT_SLOT_NECK, apply);       // emplacement sans arme : statistiques, armure, résistances
        for (auto const& s : proto->Spells)
        {
            if (!s.SpellId || s.SpellTrigger != ITEM_SPELLTRIGGER_ON_EQUIP)
                continue;
            if (SpellEntry const* sp = sSpellTemplate.LookupEntry<SpellEntry>(s.SpellId))
                player->ApplyEquipSpell(sp, nullptr, apply);
        }
    }

    void ReliquesModule::Initialiser(Player* player)
    {
        std::lock_guard<std::recursive_mutex> guard(lock);
        uint32 guid = player->GetGUIDLow();
        if (appliques.count(guid))
            return;
        appliques.insert(guid);
        auto it = cases.find(guid);
        if (it == cases.end())
            return;
        for (uint32 e : it->second)
            if (e)
                Bonus(player, e, true);
    }

    void ReliquesModule::OnUpdate(uint32 elapsed)
    {
        timer += elapsed;
        if (timer < 1000)
            return;
        timer = 0;
        std::vector<std::pair<Map*, ObjectGuid>> todo;
        {
            std::lock_guard<std::recursive_mutex> guard(lock);
            HashMapHolder<Player>::ReadGuard g(HashMapHolder<Player>::GetLock());
            for (auto const& kv : HashMapHolder<Player>::GetContainer())
            {
                Player* p = kv.second;
                if (!p || !p->IsInWorld() || appliques.count(p->GetGUIDLow()))
                    continue;
                if (Map* map = p->GetMap())
                    todo.emplace_back(map, p->GetObjectGuid());
            }
        }
        for (auto const& t : todo)
        {
            ObjectGuid guid = t.second;
            t.first->GetMessager().AddMessage([guid](Map* map)
            {
                if (Player* p = map->GetPlayer(guid))
                    if (instance && p->IsInWorld())
                        instance->Initialiser(p);
            });
        }
    }

    void ReliquesModule::OnLogOut(Player* player)
    {
        std::lock_guard<std::recursive_mutex> guard(lock);
        appliques.erase(player->GetGUIDLow());
    }

    void ReliquesModule::OnDeleteFromDB(uint32 playerId)
    {
        std::lock_guard<std::recursive_mutex> guard(lock);
        cases.erase(playerId);
        appliques.erase(playerId);
        CharacterDatabase.PExecute("DELETE FROM `custom_relique` WHERE `guid` = %u", playerId);
    }

    void ReliquesModule::Liste(Player* player)
    {
        std::lock_guard<std::recursive_mutex> guard(lock);
        auto& c = Cases(player->GetGUIDLow());
        char buf[160];
        snprintf(buf, sizeof(buf), "##RELIQ 1=%u;2=%u;3=%u;4=%u;5=%u", c[0], c[1], c[2], c[3], c[4]);
        ChatHandler(player->GetSession()).SendSysMessage(buf);
    }

    bool ReliquesModule::HandleListe(WorldSession* session, const std::string& /*args*/)
    {
        if (Player* p = session ? session->GetPlayer() : nullptr)
        {
            Initialiser(p);
            // objets qui vont dans les cases (pour le clic droit dans les sacs) : « ##RELIQO début-fin,... »
            {
                std::lock_guard<std::recursive_mutex> guard(lock);
                std::vector<uint32> ids;
                for (auto const& kv : types)
                    ids.push_back(kv.first);
                std::sort(ids.begin(), ids.end());
                std::string ligne;
                for (size_t i = 0; i < ids.size();)
                {
                    size_t j = i;
                    while (j + 1 < ids.size() && ids[j + 1] == ids[j] + 1)
                        ++j;
                    std::string morceau = std::to_string(ids[i]) + (j > i ? "-" + std::to_string(ids[j]) : "");
                    if (ligne.size() + morceau.size() > 200)
                    {
                        ChatHandler(session).SendSysMessage(("##RELIQO " + ligne).c_str());
                        ligne.clear();
                    }
                    ligne += (ligne.empty() ? "" : ",") + morceau;
                    i = j + 1;
                }
                if (!ligne.empty())
                    ChatHandler(session).SendSysMessage(("##RELIQO " + ligne).c_str());
            }
            Liste(p);
            return true;
        }
        return false;
    }

    bool ReliquesModule::HandleEquiper(WorldSession* session, const std::string& args)
    {
        Player* p = session ? session->GetPlayer() : nullptr;
        if (!p)
            return false;
        Initialiser(p);
        ChatHandler ch(session);
        int sac = -1, place = -1, num = -1;
        std::istringstream in(args);
        in >> sac >> place >> num;
        if (sac < 0 || sac > 4 || place < 1 || place > 36 || num < 1 || num > RELIQUES_CASES)
        {
            ch.SendSysMessage("Utilisation : .relique equiper <sac 0-4> <case du sac> <emplacement 1-5>");
            return true;
        }
        if (p->IsInCombat() || !p->IsAlive())
        {
            ch.SendSysMessage("Impossible en combat ou mort.");
            return true;
        }
        uint8 bag = sac == 0 ? uint8(INVENTORY_SLOT_BAG_0) : uint8(INVENTORY_SLOT_BAG_START + sac - 1);
        uint8 slot = sac == 0 ? uint8(INVENTORY_SLOT_ITEM_START + place - 1) : uint8(place - 1);
        Item* item = p->GetItemByPos(bag, slot);
        if (!item)
        {
            ch.SendSysMessage("Aucun objet à cet endroit.");
            return true;
        }
        uint32 entry = item->GetEntry();
        ItemPrototype const* proto = item->GetProto();
        std::lock_guard<std::recursive_mutex> guard(lock);
        auto t = types.find(entry);
        if (t == types.end() || t->second < 1 || t->second > RELIQUES_CASES)
        {
            ch.SendSysMessage("Cet objet n'est ni un artefact ni une mascotte.");
            return true;
        }
        num = t->second;                                // chaque objet va dans sa case : 1 bleue, 2 rouge, 3 verte, 4 jaune, 5 mascotte
        if (proto->RequiredLevel > p->GetLevel())
        {
            ch.PSendSysMessage("Niveau %u requis.", proto->RequiredLevel);
            return true;
        }
        if (proto->AllowableClass && !(proto->AllowableClass & p->getClassMask()))
        {
            ch.SendSysMessage("Votre classe ne peut pas utiliser cet objet.");
            return true;
        }
        auto& c = Cases(p->GetGUIDLow());
        for (int i = 0; i < RELIQUES_CASES; ++i)
            if (i != num - 1 && c[i] == entry)
            {
                ch.SendSysMessage("Cet objet est déjà placé dans une autre case.");
                return true;
            }
        uint32 ancien = c[num - 1];
        // l'ancien objet revient dans les sacs, à la place du nouveau
        p->DestroyItem(bag, slot, true);
        if (ancien)
        {
            Bonus(p, ancien, false);
            ItemPosCountVec dest;
            if (p->CanStoreNewItem(NULL_BAG, NULL_SLOT, dest, ancien, 1) == EQUIP_ERR_OK)
            {
                if (Item* it = p->StoreNewItem(dest, ancien, true))
                    p->SendNewItem(it, 1, true, false, false, false);
            }
        }
        c[num - 1] = entry;
        Bonus(p, entry, true);
        CharacterDatabase.PExecute("REPLACE INTO `custom_relique` (`guid`, `emplacement`, `entry`) VALUES (%u, %u, %u)",
                                   p->GetGUIDLow(), uint32(num - 1), entry);
        Liste(p);
        return true;
    }

    bool ReliquesModule::HandleRetirer(WorldSession* session, const std::string& args)
    {
        Player* p = session ? session->GetPlayer() : nullptr;
        if (!p)
            return false;
        Initialiser(p);
        ChatHandler ch(session);
        int num = atoi(args.c_str());
        if (num < 1 || num > RELIQUES_CASES)
        {
            ch.SendSysMessage("Utilisation : .relique retirer <emplacement 1-5>");
            return true;
        }
        if (p->IsInCombat())
        {
            ch.SendSysMessage("Impossible en combat.");
            return true;
        }
        std::lock_guard<std::recursive_mutex> guard(lock);
        auto& c = Cases(p->GetGUIDLow());
        uint32 entry = c[num - 1];
        if (!entry)
            return true;
        ItemPosCountVec dest;
        if (p->CanStoreNewItem(NULL_BAG, NULL_SLOT, dest, entry, 1) != EQUIP_ERR_OK)
        {
            ch.SendSysMessage("Vos sacs sont pleins.");
            return true;
        }
        Item* it = p->StoreNewItem(dest, entry, true);
        if (!it)
            return true;
        p->SendNewItem(it, 1, true, false, false, false);
        Bonus(p, entry, false);
        c[num - 1] = 0;
        CharacterDatabase.PExecute("DELETE FROM `custom_relique` WHERE `guid` = %u AND `emplacement` = %u", p->GetGUIDLow(), uint32(num - 1));
        Liste(p);
        return true;
    }
}
