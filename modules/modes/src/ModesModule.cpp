#include "ModesModule.h"

#include "AI/ScriptDevAI/include/sc_gossip.h"
#include "Chat/Chat.h"
#include "Database/DatabaseEnv.h"
#include "Entities/Creature.h"
#include "Entities/GossipDef.h"
#include "Entities/Item.h"
#include "Entities/Player.h"
#include "Globals/ObjectAccessor.h"
#include "Globals/ObjectMgr.h"
#include "Log/Log.h"
#include "Mails/Mail.h"
#include "Maps/Map.h"
#include "Server/DBCStores.h"
#include "Server/WorldSession.h"
#include "Spells/SpellMgr.h"

#include <cstdio>

namespace cmangos_module
{
    static ModesModule* instance = nullptr;

    static uint32 BonusArgentPrestige(Player* player, uint32 money)
    {
        return instance && player ? instance->BonusArgent(player, money) : money;
    }

    enum
    {
        ACTION_INFO = 1,
        ACTION_MODE = 10,           // 10 + mode
        ACTION_PRESTIGE = 20,
    };

    ModesModule::ModesModule() : Module("Modes", nullptr)
    {
    }

    void ModesModule::OnInitialize()
    {
        instance = this;
        CharacterDatabase.DirectExecute(
            "CREATE TABLE IF NOT EXISTS `custom_mode` (`guid` INT UNSIGNED NOT NULL, `mode` TINYINT UNSIGNED NOT NULL DEFAULT 0,"
            " `mort` TINYINT UNSIGNED NOT NULL DEFAULT 0, `prestige` INT UNSIGNED NOT NULL DEFAULT 0,"
            " PRIMARY KEY (`guid`)) ENGINE=InnoDB DEFAULT CHARSET=utf8");
        std::lock_guard<std::recursive_mutex> guard(lock);
        if (auto r = CharacterDatabase.Query("SELECT `guid`, `mode`, `mort`, `prestige` FROM `custom_mode`"))
        {
            do
            {
                Field* f = r->Fetch();
                EtatMode& e = etats[f[0].GetUInt32()];
                e.mode = uint8(f[1].GetUInt32());
                e.mort = f[2].GetUInt32() != 0;
                e.prestige = f[3].GetUInt32();
            }
            while (r->NextRow());
        }
        gBonusArgent = &BonusArgentPrestige;
        sLog.outString("Modes : %u personnages avec un mode ou un prestige", uint32(etats.size()));
    }

    EtatMode ModesModule::Etat(uint32 guid)
    {
        std::lock_guard<std::recursive_mutex> guard(lock);
        auto it = etats.find(guid);
        return it != etats.end() ? it->second : EtatMode();
    }

    void ModesModule::Sauver(uint32 guid, EtatMode const& e)
    {
        std::lock_guard<std::recursive_mutex> guard(lock);
        etats[guid] = e;
        CharacterDatabase.PExecute("REPLACE INTO `custom_mode` (`guid`, `mode`, `mort`, `prestige`) VALUES (%u, %u, %u, %u)",
                                   guid, uint32(e.mode), e.mort ? 1u : 0u, e.prestige);
    }

    void ModesModule::OnDeleteFromDB(uint32 playerId)
    {
        std::lock_guard<std::recursive_mutex> guard(lock);
        etats.erase(playerId);
        CharacterDatabase.PExecute("DELETE FROM `custom_mode` WHERE `guid` = %u", playerId);
    }

    std::string ModesModule::NomMode(uint8 mode)
    {
        switch (mode)
        {
            case MODE_JCJ: return "JcJ";
            case MODE_HARDCORE: return "Hardcore";
            case MODE_TERRIFIANT: return "Terrifiant";
            default: return "Normal";
        }
    }

    // ------------------------------------------------------------------ entretien : JcJ permanent, buff de prestige

    void ModesModule::OnUpdate(uint32 elapsed)
    {
        timer += elapsed;
        if (timer < 3000)
            return;
        timer = 0;
        std::vector<std::pair<Map*, ObjectGuid>> todo;
        {
            std::lock_guard<std::recursive_mutex> guard(lock);
            HashMapHolder<Player>::ReadGuard g(HashMapHolder<Player>::GetLock());
            for (auto const& kv : HashMapHolder<Player>::GetContainer())
            {
                Player* p = kv.second;
                if (!p || !p->IsInWorld())
                    continue;
                auto it = etats.find(p->GetGUIDLow());
                if (it == etats.end() || (!JcJ(it->second.mode) && !it->second.prestige))
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
                        instance->Entretien(p);
            });
        }
    }

    void ModesModule::Entretien(Player* player)
    {
        EtatMode e = Etat(player->GetGUIDLow());
        if (JcJ(e.mode) && (!player->IsPvP() || !player->HasFlag(PLAYER_FLAGS, PLAYER_FLAGS_PVP_DESIRED)))
        {
            player->SetFlag(PLAYER_FLAGS, PLAYER_FLAGS_PVP_DESIRED);
            player->UpdatePvP(true, true);
        }
        if (e.prestige && player->IsAlive() && !player->HasAura(MODES_SORT_PRESTIGE))
            player->CastSpell(player, MODES_SORT_PRESTIGE, TRIGGERED_OLD_TRIGGERED);
    }

    // ------------------------------------------------------------------ bonus du prestige

    bool ModesModule::OnPreGiveXP(Player* player, uint32& xp, Creature* /*victim*/)
    {
        if (!player || !xp || player->GetPlayerbotAI())
            return false;
        if (Etat(player->GetGUIDLow()).prestige)
            xp = uint32(xp * MODES_BONUS_PRESTIGE + 0.5f);
        return false;
    }

    uint32 ModesModule::BonusArgent(Player* player, uint32 money)
    {
        if (!money || player->GetPlayerbotAI() || !Etat(player->GetGUIDLow()).prestige)
            return money;
        return uint32(money * MODES_BONUS_PRESTIGE + 0.5f);
    }

    // ------------------------------------------------------------------ mort définitive

    void ModesModule::MortDefinitive(Player* player)
    {
        if (!player || player->GetPlayerbotAI())
            return;
        EtatMode e = Etat(player->GetGUIDLow());
        if (!Permadeath(e.mode) || e.mort)
            return;
        e.mort = true;
        Sauver(player->GetGUIDLow(), e);
        char buf[256];
        snprintf(buf, sizeof(buf), "|cffff2020%s est mort définitivement (mode %s, niveau %u).|r", player->GetName(), NomMode(e.mode).c_str(), player->GetLevel());
        HashMapHolder<Player>::ReadGuard g(HashMapHolder<Player>::GetLock());
        for (auto const& kv : HashMapHolder<Player>::GetContainer())
            if (Player* p = kv.second)
                if (p->GetSession() && !p->GetPlayerbotAI())
                    ChatHandler(p->GetSession()).SendSysMessage(buf);
    }

    void ModesModule::OnDeath(Player* player, Unit* /*killer*/) { MortDefinitive(player); }
    void ModesModule::OnDeath(Player* player, uint8 /*environmentalDamageType*/) { MortDefinitive(player); }

    bool ModesModule::OnPreResurrect(Player* player)
    {
        if (!player)
            return false;
        std::lock_guard<std::recursive_mutex> guard(lock);
        auto it = etats.find(player->GetGUIDLow());
        if (it == etats.end() || !it->second.mort)
            return false;
        if (releve.erase(player->GetGUIDLow()))
            return false;                       // relevé par un MJ
        if (player->GetSession())
            ChatHandler(player->GetSession()).SendSysMessage("Votre personnage est mort définitivement : il ne peut plus revenir à la vie.");
        return true;
    }

    // ------------------------------------------------------------------ PNJ

    void ModesModule::OnGossipHello(Player* player, Creature* creature)
    {
        if (!player || !creature)
            return;
        uint32 entry = creature->GetEntry();
        GossipMenu& menu = player->GetPlayerMenu()->GetGossipMenu();
        EtatMode e = Etat(player->GetGUIDLow());
        char buf[256];
        if (entry >= MODES_HERAUT_MIN && entry <= MODES_HERAUT_MAX)
        {
            snprintf(buf, sizeof(buf), "Votre mode de jeu : %s.", NomMode(e.mode).c_str());
            menu.AddMenuItem(GOSSIP_ICON_CHAT, buf, GOSSIP_SENDER_MAIN, ACTION_INFO, "", false);
            if (e.mort || player->GetLevel() > MODES_NIVEAU_CHOIX)
            {
                menu.AddMenuItem(GOSSIP_ICON_CHAT, "Le mode se choisit jusqu'au niveau 5 : il est maintenant définitif.", GOSSIP_SENDER_MAIN, ACTION_INFO, "", false);
                return;
            }
            static const char* texte[4] =
            {
                "Normal : l'aventure classique.",
                "JcJ : JcJ activé en permanence, même au niveau 1.",
                "Hardcore : une seule vie. À la mort, le personnage est perdu pour toujours.",
                "Terrifiant : JcJ permanent et une seule vie.",
            };
            static const char* confirme[4] =
            {
                "Jouer en mode Normal ?",
                "Jouer en mode JcJ ? Vous serez attaquable partout, tout le temps.",
                "Jouer en mode Hardcore ? À la mort, votre personnage ne pourra plus jamais revenir à la vie.",
                "Jouer en mode Terrifiant ? JcJ permanent, et à la mort votre personnage sera perdu pour toujours.",
            };
            for (uint8 m = 0; m < 4; ++m)
                if (m != e.mode)
                    menu.AddMenuItem(m >= MODE_HARDCORE ? GOSSIP_ICON_BATTLE : GOSSIP_ICON_CHAT, texte[m], GOSSIP_SENDER_MAIN, ACTION_MODE + m, confirme[m], false);
        }
        else if (entry >= MODES_RENOUVEAU_MIN && entry <= MODES_RENOUVEAU_MAX)
        {
            if (e.prestige)
                snprintf(buf, sizeof(buf), "Prestige %u : +30 %% d'expérience et d'or.", e.prestige);
            else
                snprintf(buf, sizeof(buf), "Au niveau 60, recommencez au niveau 1 avec +30 %% d'expérience et d'or, en gardant tous vos objets.");
            menu.AddMenuItem(GOSSIP_ICON_CHAT, buf, GOSSIP_SENDER_MAIN, ACTION_INFO, "", false);
            if (player->GetLevel() < 60)
                menu.AddMenuItem(GOSSIP_ICON_CHAT, "Revenez me voir au niveau 60.", GOSSIP_SENDER_MAIN, ACTION_INFO, "", false);
            else
            {
                snprintf(buf, sizeof(buf), "Passer prestige %u", e.prestige + 1);
                menu.AddMenuItem(GOSSIP_ICON_BATTLE, buf, GOSSIP_SENDER_MAIN, ACTION_PRESTIGE,
                    "Revenir au niveau 1, au point de départ de votre race ? Vous gardez tous vos objets (l'équipement va dans vos sacs), "
                    "vos sorts de classe et vos talents sont réinitialisés.", false);
            }
        }
    }

    bool ModesModule::OnGossipSelect(Player* player, Creature* creature, uint32 /*sender*/, uint32 action, const std::string& /*code*/, uint32 /*gossipListId*/)
    {
        if (!player || !creature)
            return false;
        uint32 entry = creature->GetEntry();
        bool heraut = entry >= MODES_HERAUT_MIN && entry <= MODES_HERAUT_MAX;
        bool renouveau = entry >= MODES_RENOUVEAU_MIN && entry <= MODES_RENOUVEAU_MAX;
        if (!heraut && !renouveau)
            return false;
        player->GetPlayerMenu()->CloseGossip();
        ChatHandler chat(player->GetSession());
        if (heraut && action >= ACTION_MODE && action <= ACTION_MODE + MODE_TERRIFIANT)
        {
            EtatMode e = Etat(player->GetGUIDLow());
            if (e.mort || player->GetLevel() > MODES_NIVEAU_CHOIX)
                return true;
            e.mode = uint8(action - ACTION_MODE);
            Sauver(player->GetGUIDLow(), e);
            if (!JcJ(e.mode) && player->IsPvP())
                player->RemoveFlag(PLAYER_FLAGS, PLAYER_FLAGS_PVP_DESIRED);
            chat.SendSysMessage(("Mode " + NomMode(e.mode) + " choisi. Vous pouvez encore changer jusqu'au niveau 5.").c_str());
            if (JcJ(e.mode))
                Entretien(player);
        }
        else if (renouveau && action == ACTION_PRESTIGE && player->GetLevel() >= 60)
            Prestige(player);
        return true;
    }

    // ------------------------------------------------------------------ prestige

    void ModesModule::Prestige(Player* player)
    {
        if (player->IsInCombat() || !player->IsAlive())
        {
            ChatHandler(player->GetSession()).SendSysMessage("Impossible en combat ou mort.");
            return;
        }
        // 1. l'équipement va dans les sacs (ou par courrier si les sacs sont pleins)
        uint32 courriers = 0;
        for (uint8 slot = EQUIPMENT_SLOT_START; slot < EQUIPMENT_SLOT_END; ++slot)
        {
            Item* item = player->GetItemByPos(INVENTORY_SLOT_BAG_0, slot);
            if (!item)
                continue;
            ItemPosCountVec dest;
            uint8 bagSlot = 0;
            if (player->CanStoreItem(NULL_BAG, NULL_SLOT, dest, item, bagSlot, false) == EQUIP_ERR_OK)
            {
                player->RemoveItem(INVENTORY_SLOT_BAG_0, slot, true);
                player->StoreItem(dest, item, true);
            }
            else
            {
                player->MoveItemFromInventory(INVENTORY_SLOT_BAG_0, slot, true);
                CharacterDatabase.BeginTransaction();
                item->DeleteFromInventoryDB();
                item->SaveToDB();
                CharacterDatabase.CommitTransaction();
                MailDraft("Prestige : votre équipement").AddItem(item).SendMailTo(player, MailSender(player, MAIL_STATIONERY_GM), MAIL_CHECK_MASK_COPIED);
                ++courriers;
            }
        }
        // 2. talents remis à zéro, sorts de classe au-dessus du niveau 1 oubliés
        player->resetTalents(true);
        std::vector<uint32> oublier;
        for (auto const& sp : player->GetSpellMap())
        {
            if (sp.second.state == PLAYERSPELL_REMOVED)
                continue;
            SpellEntry const* info = sSpellTemplate.LookupEntry<SpellEntry>(sp.first);
            if (!info || info->spellLevel <= 1)
                continue;
            SkillLineAbilityMapBounds bounds = sSpellMgr.GetSkillLineAbilityMapBoundsBySpellId(sp.first);
            for (auto it = bounds.first; it != bounds.second; ++it)
            {
                SkillLineEntry const* skill = sSkillLineStore.LookupEntry(it->second->skillId);
                if (skill && skill->categoryId == SKILL_CATEGORY_CLASS)
                {
                    oublier.push_back(sp.first);
                    break;
                }
            }
        }
        for (uint32 id : oublier)
            player->removeSpell(id, false, false);
        // 3. niveau 1
        player->GiveLevel(1);
        player->InitTalentForLevel();
        player->SetUInt32Value(PLAYER_XP, 0);
        // 4. prestige et buff
        EtatMode e = Etat(player->GetGUIDLow());
        ++e.prestige;
        Sauver(player->GetGUIDLow(), e);
        player->RemoveAurasDueToSpell(MODES_SORT_PRESTIGE);
        player->CastSpell(player, MODES_SORT_PRESTIGE, TRIGGERED_OLD_TRIGGERED);
        char buf[256];
        snprintf(buf, sizeof(buf), "Prestige %u ! Vous recommencez au niveau 1 avec +30 %% d'expérience et d'or.%s", e.prestige,
                 courriers ? " Vos sacs étant pleins, une partie de votre équipement vous attend dans votre boîte aux lettres." : "");
        ChatHandler(player->GetSession()).SendSysMessage(buf);
        // 5. point de départ de la race
        if (PlayerInfo const* info = sObjectMgr.GetPlayerInfo(player->getRace(), player->getClass()))
            player->TeleportTo(info->mapId, info->positionX, info->positionY, info->positionZ, info->orientation);
    }

    // ------------------------------------------------------------------ commandes

    std::vector<ModuleChatCommand>* ModesModule::GetCommandTable()
    {
        static std::vector<ModuleChatCommand> commandTable =
        {
            { "info", std::bind(&ModesModule::HandleInfo, this, std::placeholders::_1, std::placeholders::_2), SEC_PLAYER },
            { "relever", std::bind(&ModesModule::HandleRelever, this, std::placeholders::_1, std::placeholders::_2), SEC_GAMEMASTER },
        };
        return &commandTable;
    }

    bool ModesModule::HandleInfo(WorldSession* session, const std::string& /*args*/)
    {
        Player* player = session ? session->GetPlayer() : nullptr;
        if (!player)
            return false;
        EtatMode e = Etat(player->GetGUIDLow());
        char buf[160];
        snprintf(buf, sizeof(buf), "Mode %s%s, prestige %u.", NomMode(e.mode).c_str(), e.mort ? " (mort définitivement)" : "", e.prestige);
        ChatHandler(session).SendSysMessage(buf);
        return true;
    }

    // MJ : rend la vie à un personnage hardcore mort (cible), sans changer son mode
    bool ModesModule::HandleRelever(WorldSession* session, const std::string& /*args*/)
    {
        Player* gm = session ? session->GetPlayer() : nullptr;
        if (!gm)
            return false;
        Player* target = gm->GetMap()->GetPlayer(gm->GetSelectionGuid());
        if (!target)
        {
            ChatHandler(session).SendSysMessage("Ciblez le personnage à relever.");
            return true;
        }
        EtatMode e = Etat(target->GetGUIDLow());
        e.mort = false;
        Sauver(target->GetGUIDLow(), e);
        {
            std::lock_guard<std::recursive_mutex> guard(lock);
            releve.insert(target->GetGUIDLow());
        }
        if (!target->IsAlive())
        {
            target->ResurrectPlayer(1.0f);
            target->SpawnCorpseBones();
        }
        ChatHandler(session).SendSysMessage((std::string(target->GetName()) + " est relevé.").c_str());
        return true;
    }
}
