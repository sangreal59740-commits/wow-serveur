#include "ReliquesModule.h"

#include "AI/ScriptDevAI/include/sc_gossip.h"
#include "Chat/Chat.h"
#include "Database/DatabaseEnv.h"
#include "Entities/Item.h"
#include "Entities/GameObject.h"
#include "Entities/GossipDef.h"
#include "Entities/ItemPrototype.h"
#include "Entities/Pet.h"
#include "Entities/Player.h"
#include "Globals/ObjectAccessor.h"
#include "Globals/ObjectMgr.h"
#include "Log/Log.h"
#include "Maps/Map.h"
#include "Server/WorldSession.h"
#include "Spells/SpellMgr.h"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <sstream>

namespace cmangos_module
{
    static ReliquesModule* instance = nullptr;
    static const char* NOM_COULEUR[5] = { "", "bleu", "rouge", "vert", "jaune" };
    static const char* AIDE_COULEUR[5] = { "", "Endurance", "Force ou Intelligence", "critique ou toucher", "défense, puissance des sorts ou d'attaque" };

    // sorts passifs des mascottes (valeur donnée au lancement) : 65690 Force ... 65699 Défense
    static uint32 SortMascotte(std::string const& s)
    {
        static const char* cles[10] = { "for", "agi", "end", "int", "esp", "ps", "pa", "cc", "tm", "def" };
        for (uint32 i = 0; i < 10; ++i)
            if (s == cles[i])
                return 65690 + i;
        return 0;
    }

    // moitié du budget d'un casque bleu du niveau (budget = niveau) pour chacune des deux statistiques
    static int32 ValeurMascotte(std::string const& s, uint32 niveau)
    {
        float b = niveau / 2.0f;
        float v = b;
        if (s == "ps") v = b * 1.16f;
        else if (s == "pa") v = b * 2.0f;
        else if (s == "cc") v = b / 14.0f;
        else if (s == "tm") v = b / 10.0f;
        else if (s == "def") v = b / 1.5f;
        return std::max(1, int32(std::lround(v)));
    }

    static std::string Or(uint32 cuivre)
    {
        char buf[64];
        if (cuivre >= 10000)
            snprintf(buf, sizeof(buf), "%u po", cuivre / 10000);
        else
            snprintf(buf, sizeof(buf), "%u pa", cuivre / 100);
        return buf;
    }

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
        if (auto r = WorldDatabase.Query("SELECT `entry`, `stat1`, `stat2` FROM `custom_relique_mascotte`"))
        {
            do
            {
                Field* f = r->Fetch();
                mascottes[f[0].GetUInt32()] = { f[1].GetCppString(), f[2].GetCppString() };
            }
            while (r->NextRow());
        }
        if (auto r = WorldDatabase.Query("SELECT `couleur`, `palier`, `objet1`, `nombre1`, `objet2`, `nombre2`, `objet3`, `nombre3`, "
                                         "`objet4`, `nombre4`, `argent` FROM `custom_relique_recette`"))
        {
            do
            {
                Field* f = r->Fetch();
                Recette& rc = recettes[f[0].GetUInt32() * 10 + f[1].GetUInt32()];
                for (int i = 0; i < 4; ++i)
                {
                    rc.objet[i] = f[2 + i * 2].GetUInt32();
                    rc.nombre[i] = f[3 + i * 2].GetUInt32();
                }
                rc.argent = f[10].GetUInt32();
            }
            while (r->NextRow());
        }
        for (auto const& t : types)
        {
            if (t.second < 1 || t.second > 4)
                continue;
            if (ItemPrototype const* proto = sObjectMgr.GetItemPrototype(t.first))
            {
                uint32 palier = proto->Quality >= 4 ? 6 : std::min<uint32>(std::max<uint32>(proto->RequiredLevel / 10, 1), 6) - 1;
                artefacts[t.second * 10 + palier].push_back(t.first);
            }
        }
        if (auto r = CharacterDatabase.Query("SELECT `guid`, `emplacement`, `entry` FROM `custom_relique`"))
        {
            do
            {
                Field* f = r->Fetch();
                uint32 e = f[1].GetUInt32();
                if (e < RELIQUES_CASES && types.count(f[2].GetUInt32()))
                    Cases(f[0].GetUInt32())[e] = f[2].GetUInt32();
            }
            while (r->NextRow());
        }
        // objets qui n'existent plus (anciennes mascottes d'essai)
        CharacterDatabase.DirectExecute("DELETE FROM `custom_relique` WHERE `entry` BETWEEN 992100 AND 992199");
        // pierre de foyer sans temps de recharge : on efface ceux déjà enregistrés
        CharacterDatabase.DirectExecute("DELETE FROM `character_spell_cooldown` WHERE `SpellId` = 8690");
        sLog.outString("Reliques : %u objets autorises dont %u mascottes, %u recettes, %u personnages", uint32(types.size()),
                       uint32(mascottes.size()), uint32(recettes.size()), uint32(cases.size()));
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

    void ReliquesModule::Mascotte(Player* player, uint32 entry, bool apply)
    {
        auto m = mascottes.find(entry);
        if (m == mascottes.end())
            return;
        uint32 sorts[2] = { SortMascotte(m->second.first), SortMascotte(m->second.second) };
        for (uint32 s : sorts)
            if (s)
                player->RemoveAurasDueToSpell(s);
        if (!apply)
        {
            niveauMascotte.erase(player->GetGUIDLow());
            if (Pet* mini = player->GetMiniPet())
                mini->Unsummon(PET_SAVE_AS_DELETED, player);
            return;
        }
        uint32 niveau = player->GetLevel();
        std::string const* cles[2] = { &m->second.first, &m->second.second };
        for (int i = 0; i < 2; ++i)
        {
            if (!sorts[i])
                continue;
            int32 v = ValeurMascotte(*cles[i], niveau);
            player->CastCustomSpell(player, sorts[i], &v, &v, nullptr, TRIGGERED_OLD_TRIGGERED);
        }
        niveauMascotte[player->GetGUIDLow()] = niveau;
    }

    void ReliquesModule::Entretien(Player* player)
    {
        std::lock_guard<std::recursive_mutex> guard(lock);
        uint32 guid = player->GetGUIDLow();
        auto c = cases.find(guid);
        if (c == cases.end() || !c->second[RELIQUES_CASES - 1])
            return;
        uint32 entry = c->second[RELIQUES_CASES - 1];
        auto n = niveauMascotte.find(guid);
        if (n == niveauMascotte.end() || n->second != player->GetLevel())
            Mascotte(player, entry, true);
        // le compagnon suit le joueur
        if (player->IsAlive() && !player->IsTaxiFlying() && !player->GetMiniPet())
            if (ItemPrototype const* proto = sObjectMgr.GetItemPrototype(entry))
                if (uint32 s = proto->Spells[0].SpellId)
                    player->CastSpell(player, s, TRIGGERED_OLD_TRIGGERED);
    }

    void ReliquesModule::Bonus(Player* player, uint32 entry, bool apply)
    {
        if (mascottes.count(entry))
        {
            Mascotte(player, entry, apply);
            return;
        }
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
        timerEntretien += elapsed;
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
                if (!p || !p->IsInWorld())
                    continue;
                bool initialiser = !appliques.count(p->GetGUIDLow());
                bool entretien = false;
                if (!initialiser && timerEntretien >= 5000)
                {
                    auto c = cases.find(p->GetGUIDLow());
                    entretien = c != cases.end() && c->second[RELIQUES_CASES - 1];
                }
                if (initialiser || entretien)
                    if (Map* map = p->GetMap())
                        todo.emplace_back(map, p->GetObjectGuid());
            }
        }
        if (timerEntretien >= 5000)
            timerEntretien = 0;
        for (auto const& t : todo)
        {
            ObjectGuid guid = t.second;
            t.first->GetMessager().AddMessage([guid](Map* map)
            {
                if (Player* p = map->GetPlayer(guid))
                    if (instance && p->IsInWorld())
                    {
                        instance->Initialiser(p);
                        instance->Entretien(p);
                    }
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
        Entretien(p);
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

    // ---------------------------------------------------------------- machine à artefacts
    void ReliquesModule::OnGossipHello(Player* player, GameObject* gameObject)
    {
        if (!player || !gameObject || gameObject->GetEntry() != RELIQUES_MACHINE)
            return;
        GossipMenu& menu = player->GetPlayerMenu()->GetGossipMenu();
        for (uint32 c = 1; c <= 4; ++c)
        {
            std::string t = std::string("Artefact ") + NOM_COULEUR[c] + " (" + AIDE_COULEUR[c] + ")";
            menu.AddMenuItem(GOSSIP_ICON_INTERACT_1, t, GOSSIP_SENDER_MAIN, 100 + c, "", false);
        }
    }

    void ReliquesModule::MenuPaliers(Player* player, GameObject* go, uint32 couleur)
    {
        std::lock_guard<std::recursive_mutex> guard(lock);
        PlayerMenu* pm = player->GetPlayerMenu();
        pm->ClearMenus();
        GossipMenu& menu = pm->GetGossipMenu();
        for (uint32 i = 0; i < RELIQUES_PALIERS; ++i)
        {
            auto r = recettes.find(couleur * 10 + i);
            if (r == recettes.end() || !artefacts.count(couleur * 10 + i))
                continue;
            std::string cout;
            for (int k = 0; k < 4; ++k)
            {
                if (!r->second.objet[k] || !r->second.nombre[k])
                    continue;
                ItemPrototype const* pr = sObjectMgr.GetItemPrototype(r->second.objet[k]);
                cout += (cout.empty() ? "" : ", ") + std::to_string(r->second.nombre[k]) + " x " + (pr ? pr->Name1 : std::string("?"));
            }
            if (r->second.argent)
                cout += (cout.empty() ? "" : ", ") + Or(r->second.argent);
            std::string palier = i == 6 ? "niveau 60 épique" : "niveau " + std::to_string((i + 1) * 10);
            std::string t = std::string("Artefact ") + NOM_COULEUR[couleur] + ", " + palier;
            std::string confirme = "Fabriquer un artefact " + std::string(NOM_COULEUR[couleur]) + " de " + palier + " pour : " + cout + " ?";
            menu.AddMenuItem(GOSSIP_ICON_VENDOR, t, GOSSIP_SENDER_MAIN, 1000 + couleur * 10 + i, confirme, false);
        }
        menu.AddMenuItem(GOSSIP_ICON_CHAT, "Retour", GOSSIP_SENDER_MAIN, 99, "", false);
        pm->SendGossipMenu(player->GetGossipTextId(go), go->GetObjectGuid());
    }

    bool ReliquesModule::OnGossipSelect(Player* player, GameObject* gameObject, uint32 /*sender*/, uint32 action, const std::string& /*code*/, uint32 /*gossipListId*/)
    {
        if (!player || !gameObject || gameObject->GetEntry() != RELIQUES_MACHINE)
            return false;
        if (action == 99)
        {
            PlayerMenu* pm = player->GetPlayerMenu();
            pm->ClearMenus();
            OnGossipHello(player, gameObject);
            pm->SendGossipMenu(player->GetGossipTextId(gameObject), gameObject->GetObjectGuid());
            return true;
        }
        if (action > 100 && action <= 104)
        {
            MenuPaliers(player, gameObject, action - 100);
            return true;
        }
        player->GetPlayerMenu()->CloseGossip();
        if (action >= 1010 && action < 1050)
            Fabriquer(player, (action - 1000) / 10, (action - 1000) % 10);
        return true;
    }

    void ReliquesModule::Fabriquer(Player* player, uint32 couleur, uint32 palier)
    {
        std::lock_guard<std::recursive_mutex> guard(lock);
        ChatHandler ch(player->GetSession());
        auto r = recettes.find(couleur * 10 + palier);
        auto a = artefacts.find(couleur * 10 + palier);
        if (r == recettes.end() || a == artefacts.end() || a->second.empty())
            return;
        Recette const& rc = r->second;
        for (int k = 0; k < 4; ++k)
            if (rc.objet[k] && rc.nombre[k] && !player->HasItemCount(rc.objet[k], rc.nombre[k]))
            {
                ItemPrototype const* pr = sObjectMgr.GetItemPrototype(rc.objet[k]);
                ch.PSendSysMessage("Il vous manque : %u x %s.", rc.nombre[k], pr ? pr->Name1 : "?");
                return;
            }
        if (player->GetMoney() < rc.argent)
        {
            ch.PSendSysMessage("Il vous faut %s.", Or(rc.argent).c_str());
            return;
        }
        uint32 entry = a->second[urand(0, uint32(a->second.size()) - 1)];
        ItemPosCountVec dest;
        if (player->CanStoreNewItem(NULL_BAG, NULL_SLOT, dest, entry, 1) != EQUIP_ERR_OK)
        {
            ch.SendSysMessage("Vos sacs sont pleins.");
            return;
        }
        for (int k = 0; k < 4; ++k)
            if (rc.objet[k] && rc.nombre[k])
                player->DestroyItemCount(rc.objet[k], rc.nombre[k], true);
        if (rc.argent)
            player->ModifyMoney(-int32(rc.argent));
        if (Item* it = player->StoreNewItem(dest, entry, true))
            player->SendNewItem(it, 1, true, false, false, false);
    }
}
