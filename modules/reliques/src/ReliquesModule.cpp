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
    static const char* AIDE_COULEUR[5] = { "", "Endurance", "Force, Agilité ou Intelligence", "critique ou toucher", "défense, puissance des sorts ou d'attaque" };

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

    // gain par amélioration réussie, par palier (10, 20, 30, 40, 50, 60, 60 épique)
    static const float PAS_PA_PS[RELIQUES_PALIERS] = { 2, 5, 8, 10, 12, 15, 20 };
    static const float PAS_CC_TM[RELIQUES_PALIERS] = { 0.5f, 1.0f, 1.25f, 1.5f, 1.75f, 2.0f, 2.5f };
    static const float PAS_ARMURE[RELIQUES_PALIERS] = { 20, 50, 80, 100, 120, 150, 200 };
    static const char* NOM_STAT[5] = { "puissance d'attaque", "puissance des sorts", "% de critique", "% de toucher", "armure" };
    static const uint32 ESSAIS_MAX = 5;            // améliorations réussies cumulables par artefact (essais illimités)
    static const uint32 REUSSITE = 75;

    static float Pas(uint32 stat, uint32 palier)
    {
        if (stat <= 1) return PAS_PA_PS[palier];
        if (stat <= 3) return PAS_CC_TM[palier];
        return PAS_ARMURE[palier];
    }

    static std::string Nombre(float v)
    {
        char buf[32];
        if (std::fabs(v - std::round(v)) < 0.01f)
            snprintf(buf, sizeof(buf), "%d", int(std::lround(v)));
        else
            snprintf(buf, sizeof(buf), "%.2f", v);
        std::string r = buf;
        while (r.find('.') != std::string::npos && (r.back() == '0'))
            r.pop_back();
        for (char& ch : r)
            if (ch == '.')
                ch = ',';
        return r;
    }

    static std::string Or(uint32 cuivre)
    {
        char buf[64];
        if (cuivre >= 10000 && cuivre % 10000 == 0)
            snprintf(buf, sizeof(buf), "%u po", cuivre / 10000);
        else if (cuivre >= 10000)
            snprintf(buf, sizeof(buf), "%u po %u pa", cuivre / 10000, (cuivre % 10000) / 100);
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
        CharacterDatabase.DirectExecute(
            "CREATE TABLE IF NOT EXISTS `custom_relique_amelioration` (`guid` INT UNSIGNED NOT NULL, `emplacement` TINYINT UNSIGNED NOT NULL,"
            " `essais` TINYINT UNSIGNED NOT NULL DEFAULT 0, `pa` FLOAT NOT NULL DEFAULT 0, `ps` FLOAT NOT NULL DEFAULT 0, `cc` FLOAT NOT NULL DEFAULT 0,"
            " `tm` FLOAT NOT NULL DEFAULT 0, `armure` FLOAT NOT NULL DEFAULT 0, PRIMARY KEY (`guid`, `emplacement`)) ENGINE=InnoDB DEFAULT CHARSET=utf8");
        if (auto r = CharacterDatabase.Query("SELECT `guid`, `emplacement`, `essais`, `pa`, `ps`, `cc`, `tm`, `armure` FROM `custom_relique_amelioration`"))
        {
            do
            {
                Field* f = r->Fetch();
                uint32 e = f[1].GetUInt32();
                if (e >= 4)
                    continue;
                Amelioration& a = amels[f[0].GetUInt32()][e];
                a.essais = f[2].GetUInt32();
                for (int i = 0; i < 5; ++i)
                    a.v[i] = f[3 + i].GetFloat();
            }
            while (r->NextRow());
        }
        gBonusReliques = [](Player const* player, uint8 type) -> float { return instance ? instance->BonusFractionnaire(player, type) : 0.0f; };
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
        for (uint32 i = 0; i < RELIQUES_CASES; ++i)
            if (it->second[i])
            {
                Bonus(player, it->second[i], true);
                if (i < 4)
                    Ameliorations(player, i, true);
            }
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
        fractions.erase(player->GetGUIDLow());
    }

    void ReliquesModule::OnDeleteFromDB(uint32 playerId)
    {
        std::lock_guard<std::recursive_mutex> guard(lock);
        cases.erase(playerId);
        appliques.erase(playerId);
        CharacterDatabase.PExecute("DELETE FROM `custom_relique` WHERE `guid` = %u", playerId);
        CharacterDatabase.PExecute("DELETE FROM `custom_relique_amelioration` WHERE `guid` = %u", playerId);
        amels.erase(playerId);
    }

    void ReliquesModule::Liste(Player* player)
    {
        std::lock_guard<std::recursive_mutex> guard(lock);
        auto& c = Cases(player->GetGUIDLow());
        char buf[160];
        // améliorations d'abord : « ##RELIQA 1=essais,pa,ps,cc,tm,armure;... »
        std::string am = "##RELIQA ";
        auto ia = amels.find(player->GetGUIDLow());
        for (uint32 i = 0; i < 4; ++i)
        {
            Amelioration a;
            if (ia != amels.end())
                a = ia->second[i];
            char m[96];
            snprintf(m, sizeof(m), "%s%u=%u,%g,%g,%g,%g,%g", i ? ";" : "", i + 1, a.essais, a.v[0], a.v[1], a.v[2], a.v[3], a.v[4]);
            am += m;
        }
        ChatHandler(player->GetSession()).SendSysMessage(am.c_str());
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
        if (ancien && num <= 4 && !Perte(p, num - 1, ch))
            return true;
        // l'ancien objet revient dans les sacs, à la place du nouveau
        p->DestroyItem(bag, slot, true);
        if (ancien)
        {
            if (num <= 4)
                Ameliorations(p, num - 1, false);
            Bonus(p, ancien, false);
            ItemPosCountVec dest;
            if (p->CanStoreNewItem(NULL_BAG, NULL_SLOT, dest, ancien, 1) == EQUIP_ERR_OK)
            {
                if (Item* it = p->StoreNewItem(dest, ancien, true))
                    p->SendNewItem(it, 1, true, false, false, false);
            }
        }
        c[num - 1] = entry;
        if (ancien && num <= 4)
        {
            amels[p->GetGUIDLow()][num - 1] = Amelioration();
            CharacterDatabase.PExecute("DELETE FROM `custom_relique_amelioration` WHERE `guid` = %u AND `emplacement` = %u", p->GetGUIDLow(), uint32(num - 1));
        }
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
        if (num <= 4 && !Perte(p, num - 1, ch))
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
        if (num <= 4)
        {
            Ameliorations(p, num - 1, false);
            amels[p->GetGUIDLow()][num - 1] = Amelioration();
            CharacterDatabase.PExecute("DELETE FROM `custom_relique_amelioration` WHERE `guid` = %u AND `emplacement` = %u", p->GetGUIDLow(), uint32(num - 1));
        }
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
        std::lock_guard<std::recursive_mutex> guard(lock);
        Initialiser(player);
        GossipMenu& menu = player->GetPlayerMenu()->GetGossipMenu();
        auto& c = Cases(player->GetGUIDLow());
        auto& am = amels[player->GetGUIDLow()];
        bool un = false;
        for (uint32 i = 0; i < 4; ++i)
        {
            if (!c[i])
                continue;
            ItemPrototype const* pr = sObjectMgr.GetItemPrototype(c[i]);
            std::string t = "Améliorer " + std::string(pr ? pr->Name1 : "?") + " (" + std::to_string(am[i].essais) + "/" + std::to_string(ESSAIS_MAX) + " améliorations)";
            menu.AddMenuItem(GOSSIP_ICON_INTERACT_1, t, GOSSIP_SENDER_MAIN, 100 + i, "", false);
            un = true;
        }
        if (!un)
            menu.AddMenuItem(GOSSIP_ICON_CHAT, "Aucun artefact équipé : placez-en un dans les cases de la fiche du personnage.", GOSSIP_SENDER_MAIN, 98, "", false);
    }

    uint32 ReliquesModule::Palier(uint32 entry) const
    {
        ItemPrototype const* proto = sObjectMgr.GetItemPrototype(entry);
        if (!proto)
            return 0;
        return proto->Quality >= 4 ? 6 : std::min<uint32>(std::max<uint32>(proto->RequiredLevel / 10, 1), 6) - 1;
    }

    void ReliquesModule::MenuAmelioration(Player* player, GameObject* go, uint32 i)
    {
        std::lock_guard<std::recursive_mutex> guard(lock);
        PlayerMenu* pm = player->GetPlayerMenu();
        pm->ClearMenus();
        GossipMenu& menu = pm->GetGossipMenu();
        auto& c = Cases(player->GetGUIDLow());
        Amelioration const& a = amels[player->GetGUIDLow()][i];
        if (c[i] && a.essais < ESSAIS_MAX)
        {
            uint32 palier = Palier(c[i]);
            auto r = recettes.find((i + 1) * 10 + palier);
            std::string cout;
            if (r != recettes.end())
            {
                for (int k = 0; k < 4; ++k)
                {
                    if (!r->second.objet[k] || !r->second.nombre[k])
                        continue;
                    ItemPrototype const* pr = sObjectMgr.GetItemPrototype(r->second.objet[k]);
                    cout += (cout.empty() ? "" : ", ") + std::to_string(r->second.nombre[k]) + " x " + (pr ? pr->Name1 : std::string("?"));
                }
                if (r->second.argent)
                    cout += (cout.empty() ? "" : ", ") + Or(r->second.argent);
            }
            ItemPrototype const* pr = sObjectMgr.GetItemPrototype(c[i]);
            for (uint32 st = 0; st < 5; ++st)
            {
                std::string gain = "+" + Nombre(Pas(st, palier)) + (st == 2 || st == 3 ? " " : " ") + NOM_STAT[st];
                std::string confirme = "Tenter " + gain + " sur " + (pr ? pr->Name1 : std::string("?")) + " ?\n" + std::to_string(REUSSITE)
                    + " % de réussite (amélioration " + std::to_string(a.essais + 1) + "/" + std::to_string(ESSAIS_MAX) + ").\nCoût : " + cout;
                menu.AddMenuItem(GOSSIP_ICON_VENDOR, gain, GOSSIP_SENDER_MAIN, 1000 + i * 10 + st, confirme, false);
            }
        }
        else
            menu.AddMenuItem(GOSSIP_ICON_CHAT, "Cet artefact a déjà ses 5 améliorations.", GOSSIP_SENDER_MAIN, 99, "", false);
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
        if (action >= 100 && action < 104)
        {
            MenuAmelioration(player, gameObject, action - 100);
            return true;
        }
        player->GetPlayerMenu()->CloseGossip();
        if (action >= 1000 && action < 1040 && (action % 10) < 5)
            Ameliorer(player, (action - 1000) / 10, action % 10);
        return true;
    }

    // applique ou retire les améliorations de l'artefact de la case c (0 à 3)
    void ReliquesModule::Ameliorations(Player* p, uint32 c, bool apply)
    {
        std::lock_guard<std::recursive_mutex> guard(lock);
        auto ia = amels.find(p->GetGUIDLow());
        if (ia == amels.end() || c >= 4)
            return;
        Amelioration const& a = ia->second[c];
        if (a.v[0])
        {
            p->HandleStatModifier(UNIT_MOD_ATTACK_POWER, TOTAL_VALUE, a.v[0], apply);
            p->HandleStatModifier(UNIT_MOD_ATTACK_POWER_RANGED, TOTAL_VALUE, a.v[0], apply);
        }
        if (a.v[1])
            p->ApplySpellPowerBonus(int32(std::lround(a.v[1])), apply);
        if (a.v[4])
            p->HandleStatModifier(UNIT_MOD_ARMOR, TOTAL_VALUE, a.v[4], apply);
        if (a.v[2] || a.v[3])
        {
            // critique : mêlée et distance directement, sorts et toucher par le correctif 05 (valeurs fractionnaires)
            if (a.v[2])
            {
                p->HandleBaseModValue(CRIT_PERCENTAGE, FLAT_MOD, a.v[2], apply);
                p->HandleBaseModValue(OFFHAND_CRIT_PERCENTAGE, FLAT_MOD, a.v[2], apply);
                p->HandleBaseModValue(RANGED_CRIT_PERCENTAGE, FLAT_MOD, a.v[2], apply);
            }
            auto& f = fractions[p->GetGUIDLow()];
            float s = apply ? 1.0f : -1.0f;
            f[0] += s * a.v[3];
            f[1] += s * a.v[3];
            f[2] += s * a.v[2];
            p->UpdateWeaponHitChances(BASE_ATTACK);
            p->UpdateWeaponHitChances(OFF_ATTACK);
            p->UpdateWeaponHitChances(RANGED_ATTACK);
            p->UpdateSpellHitChances();
            p->UpdateAllSpellCritChances();
        }
    }

    float ReliquesModule::BonusFractionnaire(Player const* player, uint8 type)
    {
        std::lock_guard<std::recursive_mutex> guard(lock);
        auto f = fractions.find(player->GetGUIDLow());
        return (f == fractions.end() || type > 2) ? 0.0f : f->second[type];
    }

    // les améliorations sont perdues si l'artefact quitte sa case : il faut refaire l'action dans les 15 s pour confirmer
    bool ReliquesModule::Perte(Player* p, uint32 c, ChatHandler& ch)
    {
        auto ia = amels.find(p->GetGUIDLow());
        if (ia == amels.end() || !ia->second[c].essais)
            return true;
        auto cf = confirmation.find(p->GetGUIDLow());
        time_t now = time(nullptr);
        if (cf != confirmation.end() && cf->second.first == c && now - cf->second.second <= 15)
        {
            confirmation.erase(cf);
            return true;
        }
        confirmation[p->GetGUIDLow()] = { c, now };
        ch.PSendSysMessage("Cet artefact a %u amélioration(s) : elles seront perdues. Refais la même action dans les 15 s pour confirmer.",
                           ia->second[c].essais);
        return false;
    }

    void ReliquesModule::Ameliorer(Player* player, uint32 i, uint32 stat)
    {
        std::lock_guard<std::recursive_mutex> guard(lock);
        ChatHandler ch(player->GetSession());
        auto& c = Cases(player->GetGUIDLow());
        if (i >= 4 || !c[i] || stat >= 5)
            return;
        Amelioration& a = amels[player->GetGUIDLow()][i];
        if (a.essais >= ESSAIS_MAX)
        {
            ch.SendSysMessage("Cet artefact a déjà ses 5 améliorations.");
            return;
        }
        uint32 palier = Palier(c[i]);
        auto r = recettes.find((i + 1) * 10 + palier);
        if (r == recettes.end())
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
        for (int k = 0; k < 4; ++k)
            if (rc.objet[k] && rc.nombre[k])
                player->DestroyItemCount(rc.objet[k], rc.nombre[k], true);
        if (rc.argent)
            player->ModifyMoney(-int32(rc.argent));
        bool ok = urand(1, 100) <= REUSSITE;
        if (ok)
        {
            Ameliorations(player, i, false);
            ++a.essais;                                 // nombre d'améliorations réussies (5 au maximum)
            a.v[stat] += Pas(stat, palier);
            Ameliorations(player, i, true);
        }
        CharacterDatabase.PExecute("REPLACE INTO `custom_relique_amelioration` (`guid`, `emplacement`, `essais`, `pa`, `ps`, `cc`, `tm`, `armure`) "
                                   "VALUES (%u, %u, %u, %f, %f, %f, %f, %f)", player->GetGUIDLow(), i, a.essais, a.v[0], a.v[1], a.v[2], a.v[3], a.v[4]);
        std::string msg = ok ? "La machine vrombit : réussite ! +" + Nombre(Pas(stat, palier)) + " " + NOM_STAT[stat] + "."
                             : std::string("La machine crachote : échec, les composants sont perdus.");
        msg += " Améliorations : " + std::to_string(a.essais) + "/" + std::to_string(ESSAIS_MAX) + ".";
        ch.SendSysMessage(msg.c_str());
        Liste(player);
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
        uint32 entry = ArtefactAdapte(player, couleur, palier);
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

    // ---------------------------------------------------------------- artefact adapté au personnage (coffrets et machine)
    // rouge : Intelligence si le personnage a plus d'Intelligence que de Force, sinon Agilité ou Force (la plus haute) ; jaune : puissance des sorts pour un lanceur de sorts,
    // défense pour un guerrier ou un paladin avec bouclier, sinon puissance d'attaque ; vert : critique ou toucher au hasard
    static std::string Variante(ItemPrototype const* proto)
    {
        if (proto->ItemStat[0].ItemStatType == ITEM_MOD_INTELLECT) return "int";
        if (proto->ItemStat[0].ItemStatType == ITEM_MOD_STRENGTH) return "for";
        if (proto->ItemStat[0].ItemStatType == ITEM_MOD_STAMINA) return "end";
        if (proto->ItemStat[0].ItemStatType == ITEM_MOD_AGILITY) return "agi";
        if (SpellEntry const* sp = sSpellTemplate.LookupEntry<SpellEntry>(proto->Spells[0].SpellId))
        {
            switch (sp->EffectApplyAuraName[0])
            {
                case SPELL_AURA_MOD_CRIT_PERCENT: return "cc";
                case SPELL_AURA_MOD_HIT_CHANCE: return "tm";
                case SPELL_AURA_MOD_SKILL: return "def";
                case SPELL_AURA_MOD_DAMAGE_DONE: return "ps";
                case SPELL_AURA_MOD_ATTACK_POWER: return "pa";
                default: break;
            }
        }
        return "";
    }

    uint32 ReliquesModule::ArtefactAdapte(Player* player, uint32 couleur, uint32 palier)
    {
        auto a = artefacts.find(couleur * 10 + palier);
        if (a == artefacts.end() || a->second.empty())
            return 0;
        bool lanceur = player->GetStat(STAT_INTELLECT) > player->GetStat(STAT_STRENGTH);
        bool bouclier = false;
        if (Item* g = player->GetItemByPos(INVENTORY_SLOT_BAG_0, EQUIPMENT_SLOT_OFFHAND))
            bouclier = g->GetProto()->InventoryType == INVTYPE_SHIELD;
        uint8 cls = player->getClass();
        std::string voulu;
        if (couleur == 2)
            voulu = lanceur ? "int" : (player->GetStat(STAT_AGILITY) > player->GetStat(STAT_STRENGTH) ? "agi" : "for");
        else if (couleur == 3)
            voulu = urand(0, 1) ? "cc" : "tm";
        else if (couleur == 4)
            voulu = lanceur ? "ps" : ((bouclier && (cls == CLASS_WARRIOR || cls == CLASS_PALADIN)) ? "def" : "pa");
        std::vector<uint32> bons;
        for (uint32 e : a->second)
            if (ItemPrototype const* pr = sObjectMgr.GetItemPrototype(e))
                if (voulu.empty() || Variante(pr) == voulu)
                    bons.push_back(e);
        if (bons.empty())
            bons = a->second;
        return bons[urand(0, uint32(bons.size()) - 1)];
    }

    // coffret d'artefact : une couleur au hasard, l'artefact adapté au personnage
    bool ReliquesModule::OnUseItem(Player* player, Item* item)
    {
        if (!player || !item || item->GetEntry() < RELIQUES_COFFRET || item->GetEntry() >= RELIQUES_COFFRET + RELIQUES_PALIERS)
            return false;
        uint32 palier = item->GetEntry() - RELIQUES_COFFRET;
        uint32 entry;
        {
            std::lock_guard<std::recursive_mutex> guard(lock);
            entry = ArtefactAdapte(player, urand(1, 4), palier);
        }
        if (!entry)
            return true;
        ItemPosCountVec dest;
        if (player->CanStoreNewItem(NULL_BAG, NULL_SLOT, dest, entry, 1) != EQUIP_ERR_OK)
        {
            // le coffret prend une place qui se libère : on le retire d'abord
            uint32 coffret = item->GetEntry();
            player->DestroyItemCount(coffret, 1, true);
            if (player->CanStoreNewItem(NULL_BAG, NULL_SLOT, dest, entry, 1) != EQUIP_ERR_OK)
            {
                player->StoreNewItemInInventorySlot(coffret, 1);
                ChatHandler(player->GetSession()).SendSysMessage("Vos sacs sont pleins.");
                return true;
            }
        }
        else
            player->DestroyItemCount(item->GetEntry(), 1, true);
        if (Item* it = player->StoreNewItem(dest, entry, true))
            player->SendNewItem(it, 1, true, false, false, false);
        return true;
    }
}
