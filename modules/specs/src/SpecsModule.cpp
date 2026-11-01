#include "SpecsModule.h"

#include "AI/ScriptDevAI/include/sc_gossip.h"
#include "Chat/Chat.h"
#include "Database/DatabaseEnv.h"
#include "Entities/Creature.h"
#include "Entities/GossipDef.h"
#include "Entities/Pet.h"
#include "Entities/Player.h"
#include "Globals/ObjectMgr.h"
#include "Log/Log.h"
#include "Maps/Map.h"
#include "Server/DBCStores.h"
#include "Spells/Spell.h"
#include "Spells/SpellMgr.h"
#include "World/World.h"

#include <ctime>

namespace cmangos_module
{
    enum SpecsActions
    {
        ACTION_INFO     = GOSSIP_ACTION_INFO_DEF + 300,
        ACTION_UNLOCK   = GOSSIP_ACTION_INFO_DEF + 310,     // + numero de la spe (1 ou 2)
        ACTION_SWITCH   = GOSSIP_ACTION_INFO_DEF + 320,     // + numero de la spe (0 a 2)
    };

    static SpecsModule* instance = nullptr;

    SpecsModule::SpecsModule() : Module("Specs", nullptr)
    {
        instance = this;
    }

    void SpecsModule::OnInitialize()
    {
        CharacterDatabase.Execute(
            "CREATE TABLE IF NOT EXISTS `custom_spec_status` (`guid` INT UNSIGNED NOT NULL, `count` TINYINT UNSIGNED NOT NULL DEFAULT 1,"
            " `active` TINYINT UNSIGNED NOT NULL DEFAULT 0, PRIMARY KEY (`guid`)) ENGINE=InnoDB DEFAULT CHARSET=utf8");
        CharacterDatabase.Execute(
            "CREATE TABLE IF NOT EXISTS `custom_spec_talent` (`guid` INT UNSIGNED NOT NULL, `spec` TINYINT UNSIGNED NOT NULL,"
            " `spell` INT UNSIGNED NOT NULL, PRIMARY KEY (`guid`, `spec`, `spell`)) ENGINE=InnoDB DEFAULT CHARSET=utf8");
        CharacterDatabase.Execute(
            "CREATE TABLE IF NOT EXISTS `custom_spec_action` (`guid` INT UNSIGNED NOT NULL, `spec` TINYINT UNSIGNED NOT NULL,"
            " `button` TINYINT UNSIGNED NOT NULL, `action` INT UNSIGNED NOT NULL, `type` TINYINT UNSIGNED NOT NULL,"
            " PRIMARY KEY (`guid`, `spec`, `button`)) ENGINE=InnoDB DEFAULT CHARSET=utf8");
        if (auto result = CharacterDatabase.Query("SELECT `guid`, `count`, `active` FROM `custom_spec_status`"))
        {
            do
            {
                Field* f = result->Fetch();
                SpecStatus& st = status[f[0].GetUInt32()];
                st.count = std::max<uint8>(1, std::min<uint8>(SPECS_MAX, f[1].GetUInt8()));
                st.active = std::min<uint8>(st.count - 1, f[2].GetUInt8());
            }
            while (result->NextRow());
        }
        sLog.outString("Specs : %u personnage(s) avec plusieurs specialisations", uint32(status.size()));
    }

    std::vector<ModuleChatCommand>* SpecsModule::GetCommandTable()
    {
        static std::vector<ModuleChatCommand> commandTable =
        {
            { "1", [this](WorldSession* s, const std::string&) { return HandleSpec(s, 0); }, SEC_PLAYER },
            { "2", [this](WorldSession* s, const std::string&) { return HandleSpec(s, 1); }, SEC_PLAYER },
            { "3", [this](WorldSession* s, const std::string&) { return HandleSpec(s, 2); }, SEC_PLAYER },
            { "info", std::bind(&SpecsModule::HandleInfo, this, std::placeholders::_1, std::placeholders::_2), SEC_PLAYER },
        };
        return &commandTable;
    }

    SpecStatus& SpecsModule::GetStatus(uint32 guid)
    {
        return status[guid];
    }

    void SpecsModule::SaveStatus(uint32 guid, const SpecStatus& st)
    {
        CharacterDatabase.PExecute("REPLACE INTO `custom_spec_status` (`guid`, `count`, `active`) VALUES (%u, %u, %u)",
            guid, uint32(st.count), uint32(st.active));
    }

    void SpecsModule::Message(Player* player, const std::string& text)
    {
        ChatHandler(player).SendSysMessage(("|cff66ccff[Spé]|r " + text).c_str());
    }

    bool SpecsModule::IsClassTrainerFor(Player* player, Creature* creature)
    {
        CreatureInfo const* info = creature->GetCreatureInfo();
        return info && (info->NpcFlags & UNIT_NPC_FLAG_TRAINER) && info->TrainerType == TRAINER_TYPE_CLASS
            && info->TrainerClass == player->getClass();
    }

    bool SpecsModule::HandleInfo(WorldSession* session, const std::string& /*args*/)
    {
        Player* player = session ? session->GetPlayer() : nullptr;
        if (!player)
            return true;
        std::lock_guard<std::recursive_mutex> guard(lock);
        SpecStatus& st = GetStatus(player->GetGUIDLow());
        Message(player, "spé active : " + std::to_string(st.active + 1) + " sur " + std::to_string(st.count)
            + " débloquée(s). Changer : sorts Spécialisation 1/2/3 ou .spe 1, .spe 2, .spe 3 (5 s d'incantation hors combat).");
        return true;
    }

    bool SpecsModule::HandleSpec(WorldSession* session, uint8 spec)
    {
        Player* player = session ? session->GetPlayer() : nullptr;
        if (!player)
            return true;
        std::lock_guard<std::recursive_mutex> guard(lock);
        RequestSwitch(player, spec);
        return true;
    }

    // fin de l'incantation : le changement se fait au tick suivant de la carte (le sort en cours est terminé)
    static void SwitchNextTick(Map* map, ObjectGuid guid, uint8 spec)
    {
        map->GetMessager().AddMessage([=](Map* m)
        {
            if (Player* player = m->GetPlayer(guid))
                if (instance)
                    instance->FinishSwitch(player, spec);
        });
    }

    bool SpecsModule::CanSwitch(Player* player, uint8 spec)
    {
        SpecStatus& st = GetStatus(player->GetGUIDLow());
        if (spec >= st.count)
        {
            Message(player, "cette spé n'est pas débloquée (2e au niveau 20, 3e au niveau 30, chez votre maître de classe).");
            return false;
        }
        if (spec == st.active)
        {
            Message(player, "c'est déjà votre spé active.");
            return false;
        }
        if (player->IsInCombat() || !player->IsAlive())
        {
            Message(player, "impossible en combat ou mort.");
            return false;
        }
        return true;
    }

    // .spe N et maître de classe : lance le sort Spécialisation N (barre d'incantation de 5 s)
    bool SpecsModule::RequestSwitch(Player* player, uint8 spec)
    {
        if (!CanSwitch(player, spec))
            return false;
        if (player->IsNonMeleeSpellCasted(false))
        {
            Message(player, "vous êtes déjà en train d'incanter.");
            return false;
        }
        player->CastSpell(player, SPECS_SPELL + spec, TRIGGERED_NONE);
        return true;
    }

    void SpecsModule::OnCast(Spell* spell, Unit* caster, Unit* /*victim*/)
    {
        if (!spell || !caster || caster->GetTypeId() != TYPEID_PLAYER)
            return;
        const uint32 id = spell->m_spellInfo->Id;
        if (id < SPECS_SPELL || id >= SPECS_SPELL + SPECS_MAX)
            return;
        Player* player = static_cast<Player*>(caster);
        std::lock_guard<std::recursive_mutex> guard(lock);
        const uint8 spec = uint8(id - SPECS_SPELL);
        if (CanSwitch(player, spec))
            SwitchNextTick(player->GetMap(), player->GetObjectGuid(), spec);
    }

    void SpecsModule::LearnSpecSpells(Player* player, uint8 count)
    {
        if (count < 2)
            return;
        for (uint8 s = 0; s < count && s < SPECS_MAX; ++s)
            if (!player->HasSpell(SPECS_SPELL + s) && sSpellTemplate.LookupEntry<SpellEntry>(SPECS_SPELL + s))
                player->learnSpell(SPECS_SPELL + s, false, false);
    }

    void SpecsModule::OnLoadFromDB(Player* player)
    {
        if (!player)
            return;
        std::lock_guard<std::recursive_mutex> guard(lock);
        auto it = status.find(player->GetGUIDLow());
        if (it != status.end())
            LearnSpecSpells(player, it->second.count);
    }

    void SpecsModule::FinishSwitch(Player* player, uint8 spec)
    {
        std::lock_guard<std::recursive_mutex> guard(lock);
        const uint32 guid = player->GetGUIDLow();
        SpecStatus& st = GetStatus(guid);
        if (player->IsInCombat() || !player->IsAlive())
        {
            Message(player, "changement de spé annulé (combat).");
            return;
        }
        if (spec >= st.count || spec == st.active)
            return;

        if (player->IsNonMeleeSpellCasted(false))
            player->InterruptNonMeleeSpells(false);
        if (Pet* pet = player->GetPet())
            player->RemovePet(PET_SAVE_AS_CURRENT);
        player->UnsummonAllTotems();

        // 1. talents actuels -> spé active
        std::vector<uint32> current;
        for (uint32 talentId = 0; talentId < sTalentStore.GetNumRows(); ++talentId)
        {
            TalentEntry const* talent = sTalentStore.LookupEntry(talentId);
            if (!talent)
                continue;
            TalentTabEntry const* tab = sTalentTabStore.LookupEntry(talent->TalentTab);
            if (!tab || (player->getClassMask() & tab->ClassMask) == 0)
                continue;
            for (int8 rank = MAX_TALENT_RANK - 1; rank >= 0; --rank)
            {
                if (talent->RankID[rank] && player->HasSpell(talent->RankID[rank]))
                {
                    current.push_back(talent->RankID[rank]);
                    break;
                }
            }
        }
        CharacterDatabase.PExecute("DELETE FROM `custom_spec_talent` WHERE `guid` = %u AND `spec` = %u", guid, uint32(st.active));
        for (uint32 spell : current)
            CharacterDatabase.PExecute("INSERT INTO `custom_spec_talent` (`guid`, `spec`, `spell`) VALUES (%u, %u, %u)", guid, uint32(st.active), spell);

        // 2. barres actuelles -> spé active (capturées pendant la sauvegarde)
        capture.insert(guid);
        captured[guid].clear();
        player->SaveToDB();
        capture.erase(guid);
        std::vector<SpecButton> oldButtons = captured[guid];
        CharacterDatabase.PExecute("DELETE FROM `custom_spec_action` WHERE `guid` = %u AND `spec` = %u", guid, uint32(st.active));
        for (SpecButton const& b : oldButtons)
            CharacterDatabase.PExecute("INSERT INTO `custom_spec_action` (`guid`, `spec`, `button`, `action`, `type`) VALUES (%u, %u, %u, %u, %u)",
                guid, uint32(st.active), uint32(b.button), b.action, uint32(b.type));

        // 3. retirer tous les talents
        for (uint32 talentId = 0; talentId < sTalentStore.GetNumRows(); ++talentId)
        {
            TalentEntry const* talent = sTalentStore.LookupEntry(talentId);
            if (!talent)
                continue;
            TalentTabEntry const* tab = sTalentTabStore.LookupEntry(talent->TalentTab);
            if (!tab || (player->getClassMask() & tab->ClassMask) == 0)
                continue;
            for (int8 rank = 0; rank < MAX_TALENT_RANK; ++rank)
                if (talent->RankID[rank] && player->HasSpell(talent->RankID[rank]))
                    player->removeSpell(talent->RankID[rank], false, false);
        }

        // 4. talents de la nouvelle spé
        uint32 spent = 0;
        if (auto result = CharacterDatabase.PQuery("SELECT `spell` FROM `custom_spec_talent` WHERE `guid` = %u AND `spec` = %u", guid, uint32(spec)))
        {
            do
            {
                uint32 spell = result->Fetch()[0].GetUInt32();
                for (uint32 talentId = 0; talentId < sTalentStore.GetNumRows(); ++talentId)
                {
                    TalentEntry const* talent = sTalentStore.LookupEntry(talentId);
                    if (!talent)
                        continue;
                    for (int8 rank = 0; rank < MAX_TALENT_RANK; ++rank)
                    {
                        if (talent->RankID[rank] == spell)
                        {
                            player->learnSpell(spell, false, true);
                            spent += rank + 1;
                        }
                    }
                }
            }
            while (result->NextRow());
        }
        uint32 points = player->CalculateTalentsPoints();
        if (spent > points)
        {
            player->resetTalents(true);
            spent = 0;
        }
        player->SetFreeTalentPoints(points - spent);

        // 5. barres de la nouvelle spé (copie des barres actuelles si la spé est neuve)
        std::vector<SpecButton> newButtons;
        if (auto result = CharacterDatabase.PQuery("SELECT `button`, `action`, `type` FROM `custom_spec_action` WHERE `guid` = %u AND `spec` = %u", guid, uint32(spec)))
        {
            do
            {
                Field* f = result->Fetch();
                newButtons.push_back({ f[0].GetUInt8(), f[1].GetUInt32(), f[2].GetUInt8() });
            }
            while (result->NextRow());
        }
        else
            newButtons = oldButtons;
        for (SpecButton const& b : oldButtons)
            player->removeActionButton(b.button);
        for (SpecButton const& b : newButtons)
            player->addActionButton(b.button, b.action, b.type);
        player->SendInitialActionButtons();

        st.active = spec;
        SaveStatus(guid, st);
        player->SaveToDB();
        Message(player, "spé " + std::to_string(spec + 1) + " activée.");
    }

    bool SpecsModule::OnSaveActionButtons(Player* player, ActionButtonList& actionButtons)
    {
        if (!player)
            return false;
        std::lock_guard<std::recursive_mutex> guard(lock);
        const uint32 guid = player->GetGUIDLow();
        if (capture.find(guid) == capture.end())
            return false;
        std::vector<SpecButton>& out = captured[guid];
        for (auto const& kv : actionButtons)
            if (kv.second.uState != ACTIONBUTTON_DELETED)
                out.push_back({ kv.first, kv.second.GetAction(), uint8(kv.second.GetType()) });
        return false;   // la sauvegarde normale continue
    }

    void SpecsModule::OnDeleteFromDB(uint32 playerId)
    {
        std::lock_guard<std::recursive_mutex> guard(lock);
        status.erase(playerId);
        CharacterDatabase.PExecute("DELETE FROM `custom_spec_status` WHERE `guid` = %u", playerId);
        CharacterDatabase.PExecute("DELETE FROM `custom_spec_talent` WHERE `guid` = %u", playerId);
        CharacterDatabase.PExecute("DELETE FROM `custom_spec_action` WHERE `guid` = %u", playerId);
    }

    void SpecsModule::OnGossipHello(Player* player, Creature* creature)
    {
        if (!player || !creature || !IsClassTrainerFor(player, creature))
            return;
        std::lock_guard<std::recursive_mutex> guard(lock);
        SpecStatus& st = GetStatus(player->GetGUIDLow());
        GossipMenu& menu = player->GetPlayerMenu()->GetGossipMenu();
        if (st.count < 2 && player->GetLevel() >= SPECS_LEVEL_2)
            menu.AddMenuItem(GOSSIP_ICON_TRAINER, "Débloquer la 2e spécialisation", GOSSIP_SENDER_MAIN, ACTION_UNLOCK + 1, "", false);
        else if (st.count == 2 && player->GetLevel() >= SPECS_LEVEL_3)
            menu.AddMenuItem(GOSSIP_ICON_TRAINER, "Débloquer la 3e spécialisation", GOSSIP_SENDER_MAIN, ACTION_UNLOCK + 2, "", false);
        if (st.count > 1)
        {
            for (uint8 s = 0; s < st.count; ++s)
            {
                if (s == st.active)
                    continue;
                menu.AddMenuItem(GOSSIP_ICON_BATTLE, "Passer à la spécialisation " + std::to_string(s + 1), GOSSIP_SENDER_MAIN,
                    ACTION_SWITCH + s, "", false);
            }
        }
    }

    bool SpecsModule::OnGossipSelect(Player* player, Creature* creature, uint32 /*sender*/, uint32 action, const std::string& /*code*/, uint32 /*gossipListId*/)
    {
        if (!player || !creature || !IsClassTrainerFor(player, creature))
            return false;
        if (action < ACTION_UNLOCK || action > ACTION_SWITCH + SPECS_MAX)
            return false;
        std::lock_guard<std::recursive_mutex> guard(lock);
        player->GetPlayerMenu()->CloseGossip();
        SpecStatus& st = GetStatus(player->GetGUIDLow());
        if (action == ACTION_UNLOCK + 1 && st.count < 2 && player->GetLevel() >= SPECS_LEVEL_2)
        {
            st.count = 2;
            SaveStatus(player->GetGUIDLow(), st);
            LearnSpecSpells(player, st.count);
            Message(player, "2e spécialisation débloquée. Elle commence sans talents. Les sorts Spécialisation 1 et 2 sont dans votre grimoire (onglet Général).");
        }
        else if (action == ACTION_UNLOCK + 2 && st.count == 2 && player->GetLevel() >= SPECS_LEVEL_3)
        {
            st.count = 3;
            SaveStatus(player->GetGUIDLow(), st);
            LearnSpecSpells(player, st.count);
            Message(player, "3e spécialisation débloquée. Elle commence sans talents. Le sort Spécialisation 3 est dans votre grimoire (onglet Général).");
        }
        else if (action >= ACTION_SWITCH && action < ACTION_SWITCH + SPECS_MAX)
            RequestSwitch(player, uint8(action - ACTION_SWITCH));
        return true;
    }
}
