#include "MaisonsModule.h"

#include "AI/ScriptDevAI/include/sc_gossip.h"
#include "Chat/Chat.h"
#include "Database/DatabaseEnv.h"
#include "Entities/Creature.h"
#include "Entities/GameObject.h"
#include "Entities/GossipDef.h"
#include "Entities/Player.h"
#include "Globals/ObjectMgr.h"
#include "Log/Log.h"
#include "Maps/Map.h"
#include "Maps/MapManager.h"
#include "Server/DBCStores.h"
#include "Server/WorldSession.h"

#include <cmath>
#include <cstdio>
#include <set>
#include <sstream>

namespace cmangos_module
{
    static MaisonsModule* instance = nullptr;

    static bool VisibiliteMaisons(GameObject const* go, Player const* viewer)
    {
        return instance ? instance->Visible(go, viewer) : true;
    }

    enum
    {
        ACTION_INFO = 1,
        ACTION_ACHETER = 2,
        ACTION_VENDRE = 3,
    };

    MaisonsModule::MaisonsModule() : Module("Maisons", nullptr)
    {
    }

    void MaisonsModule::OnInitialize()
    {
        instance = this;
        // repérage : statut 0 à vérifier, 1 validée, 2 rejetée ; origine 0 détectée, 1 ajoutée en jeu
        WorldDatabase.DirectExecute(
            "CREATE TABLE IF NOT EXISTS `custom_maison` ("
            " `id` INT UNSIGNED NOT NULL AUTO_INCREMENT, `zone` VARCHAR(64) NOT NULL DEFAULT '', `map` SMALLINT UNSIGNED NOT NULL,"
            " `x` FLOAT NOT NULL, `y` FLOAT NOT NULL, `z` FLOAT NOT NULL, `o` FLOAT NOT NULL DEFAULT 0,"
            " `taille` VARCHAR(32) NOT NULL DEFAULT '', `origine` TINYINT UNSIGNED NOT NULL DEFAULT 0,"
            " `statut` TINYINT UNSIGNED NOT NULL DEFAULT 0, `note` VARCHAR(255) NOT NULL DEFAULT '',"
            " PRIMARY KEY (`id`)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4");
        WorldDatabase.DirectExecute(
            "CREATE TABLE IF NOT EXISTS `custom_maison_pnj` ("
            " `guid` INT UNSIGNED NOT NULL, `entry` INT UNSIGNED NOT NULL, `map` SMALLINT UNSIGNED NOT NULL,"
            " `x` FLOAT NOT NULL, `y` FLOAT NOT NULL, `z` FLOAT NOT NULL, `o` FLOAT NOT NULL,"
            " `dest_ok` TINYINT UNSIGNED NOT NULL DEFAULT 0,"
            " `dx` FLOAT NOT NULL DEFAULT 0, `dy` FLOAT NOT NULL DEFAULT 0, `dz` FLOAT NOT NULL DEFAULT 0, `do` FLOAT NOT NULL DEFAULT 0,"
            " `note` VARCHAR(255) NOT NULL DEFAULT '', PRIMARY KEY (`guid`)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4");
        // propriétaires et meubles
        CharacterDatabase.DirectExecute(
            "CREATE TABLE IF NOT EXISTS `custom_maison_proprio` (`guid` INT UNSIGNED NOT NULL, `maison` INT UNSIGNED NOT NULL,"
            " `achat` INT UNSIGNED NOT NULL DEFAULT 0, PRIMARY KEY (`guid`)) ENGINE=InnoDB DEFAULT CHARSET=utf8");
        CharacterDatabase.DirectExecute(
            "CREATE TABLE IF NOT EXISTS `custom_maison_meuble` (`id` INT UNSIGNED NOT NULL, `guid` INT UNSIGNED NOT NULL,"
            " `maison` INT UNSIGNED NOT NULL, `entry` INT UNSIGNED NOT NULL,"
            " `x` FLOAT NOT NULL, `y` FLOAT NOT NULL, `z` FLOAT NOT NULL, `o` FLOAT NOT NULL,"
            " PRIMARY KEY (`id`), KEY `maison` (`maison`)) ENGINE=InnoDB DEFAULT CHARSET=utf8");
        ChargerMaisons();
        gMaisonsVisibilite = &VisibiliteMaisons;
    }

    void MaisonsModule::ChargerMaisons()
    {
        std::lock_guard<std::recursive_mutex> guard(lock);
        lieux.clear(); proprio.clear(); meubles.clear(); vitrine.clear(); catalogue.clear();
        if (auto r = WorldDatabase.Query("SELECT `id`, `ville`, `map`, `x`, `y`, `z`, `x0`, `y0`, `z0`, `x1`, `y1`, `z1`, `taille`, `prix` FROM `custom_maison_lieu`"))
        {
            do
            {
                Field* f = r->Fetch();
                MaisonLieu l;
                l.id = f[0].GetUInt32(); l.ville = f[1].GetCppString(); l.map = f[2].GetUInt32();
                l.x = f[3].GetFloat(); l.y = f[4].GetFloat(); l.z = f[5].GetFloat();
                for (int i = 0; i < 6; ++i)
                    l.b[i] = f[6 + i].GetFloat();
                l.taille = f[12].GetCppString(); l.prix = f[13].GetUInt32();
                lieux[l.id] = l;
            }
            while (r->NextRow());
        }
        if (auto r = WorldDatabase.Query("SELECT `entry`, `nom` FROM `custom_maison_catalogue` ORDER BY `entry`"))
        {
            do { catalogue[r->Fetch()[0].GetUInt32()] = r->Fetch()[1].GetCppString(); } while (r->NextRow());
        }
        if (auto r = CharacterDatabase.Query("SELECT `guid`, `maison` FROM `custom_maison_proprio`"))
        {
            do { proprio[r->Fetch()[0].GetUInt32()] = r->Fetch()[1].GetUInt32(); } while (r->NextRow());
        }
        if (auto r = CharacterDatabase.Query("SELECT `id`, `guid`, `maison`, `entry`, `x`, `y`, `z`, `o` FROM `custom_maison_meuble`"))
        {
            do
            {
                Field* f = r->Fetch();
                MaisonMeuble m;
                m.id = f[0].GetUInt32(); m.owner = f[1].GetUInt32(); m.maison = f[2].GetUInt32(); m.entry = f[3].GetUInt32();
                m.x = f[4].GetFloat(); m.y = f[5].GetFloat(); m.z = f[6].GetFloat(); m.o = f[7].GetFloat();
                meubles[m.id] = m;
                prochainMeuble = std::max(prochainMeuble, m.id + 1);
            }
            while (r->NextRow());
        }
        for (auto const& l : lieux)
            CalculerVitrine(l.first);
        sLog.outString("Maisons : %u maisons, %u propriétaires, %u meubles", uint32(lieux.size()), uint32(proprio.size()), uint32(meubles.size()));
    }

    // ------------------------------------------------------------------ visibilité et entretien des meubles

    uint32 MaisonsModule::NombreMeubles(uint32 maison, uint32 owner) const
    {
        uint32 n = 0;
        for (auto const& m : meubles)
            if (m.second.maison == maison && m.second.owner == owner && !m.second.retirer)
                ++n;
        return n;
    }

    // maison la mieux classée : le propriétaire qui a le plus de meubles (à égalité, le premier arrivé)
    void MaisonsModule::CalculerVitrine(uint32 maison)
    {
        std::map<uint32, uint32> compte;
        for (auto const& m : meubles)
            if (m.second.maison == maison && !m.second.retirer)
                ++compte[m.second.owner];
        uint32 best = 0, n = 0;
        for (auto const& c : compte)
            if (c.second > n)
            {
                best = c.first;
                n = c.second;
            }
        if (best)
            vitrine[maison] = best;
        else
            vitrine.erase(maison);
    }

    bool MaisonsModule::Visible(GameObject const* go, Player const* viewer)
    {
        std::lock_guard<std::recursive_mutex> guard(lock);
        auto it = goMeuble.find(go->GetObjectGuid().GetRawValue());
        if (it == goMeuble.end())
            return true;
        auto mt = meubles.find(it->second);
        if (mt == meubles.end() || mt->second.retirer)
            return false;
        MaisonMeuble const& m = mt->second;
        uint32 v = viewer->GetGUIDLow();
        if (m.owner == v)
            return true;
        auto p = proprio.find(v);
        if (p != proprio.end() && p->second == m.maison)
            return false;                       // propriétaire de cette maison : il ne voit que ses meubles
        auto vt = vitrine.find(m.maison);
        return vt != vitrine.end() && vt->second == m.owner;
    }

    void MaisonsModule::OnUpdate(uint32 elapsed)
    {
        timer += elapsed;
        if (timer < 2000)
            return;
        timer = 0;
        std::set<uint32> maps;
        {
            std::lock_guard<std::recursive_mutex> guard(lock);
            for (auto const& l : lieux)
                maps.insert(l.second.map);
        }
        for (uint32 id : maps)
            if (Map* map = sMapMgr.FindMap(id, 0))
                map->GetMessager().AddMessage([](Map* m) { if (instance) instance->Entretien(m); });
    }

    // dans le fil de la carte : fait apparaître les meubles des zones chargées, retire ceux qui ont été enlevés
    void MaisonsModule::Entretien(Map* map)
    {
        std::lock_guard<std::recursive_mutex> guard(lock);
        for (auto it = meubles.begin(); it != meubles.end();)
        {
            MaisonMeuble& m = it->second;
            auto l = lieux.find(m.maison);
            if (l == lieux.end() || l->second.map != map->GetId())
            {
                ++it;
                continue;
            }
            GameObject* go = m.go ? map->GetGameObject(m.go) : nullptr;
            if (m.retirer)
            {
                if (go)
                {
                    goMeuble.erase(m.go.GetRawValue());
                    go->SetRespawnTime(0);
                    go->Delete();
                }
                else if (m.go)
                    goMeuble.erase(m.go.GetRawValue());
                it = meubles.erase(it);
                continue;
            }
            if (!go)
            {
                if (m.go)
                {
                    goMeuble.erase(m.go.GetRawValue());
                    m.go = ObjectGuid();
                }
                if (map->IsLoaded(m.x, m.y))
                {
                    GameObject* obj = new GameObject;
                    uint32 low = map->GenerateLocalLowGuid(HIGHGUID_GAMEOBJECT);
                    if (obj->Create(low, low, m.entry, map, m.x, m.y, m.z, m.o, 0.0f, 0.0f, std::sin(m.o / 2.0f), std::cos(m.o / 2.0f)))
                    {
                        obj->SetRespawnTime(0);
                        m.go = obj->GetObjectGuid();
                        goMeuble[m.go.GetRawValue()] = m.id;
                        map->Add(obj);
                    }
                    else
                        delete obj;
                }
            }
            ++it;
        }
    }

    // après un achat, une vente ou un meuble posé : chacun recalcule ce qu'il voit dans cette maison
    void MaisonsModule::Rafraichir(uint32 maison)
    {
        auto l = lieux.find(maison);
        if (l == lieux.end())
            return;
        if (Map* map = sMapMgr.FindMap(l->second.map, 0))
            map->GetMessager().AddMessage([maison](Map* m)
            {
                if (!instance)
                    return;
                std::vector<ObjectGuid> gos;
                {
                    std::lock_guard<std::recursive_mutex> guard(instance->lock);
                    for (auto const& mb : instance->meubles)
                        if (mb.second.maison == maison && mb.second.go)
                            gos.push_back(mb.second.go);
                }
                for (ObjectGuid const& g : gos)
                    if (GameObject* go = m->GetGameObject(g))
                        go->UpdateVisibilityAndView();
            });
    }

    bool MaisonsModule::Dedans(MaisonLieu const& l, float x, float y, float z, float marge) const
    {
        return x >= l.b[0] - marge && x <= l.b[3] + marge && y >= l.b[1] - marge && y <= l.b[4] + marge && z >= l.b[2] - marge && z <= l.b[5] + marge;
    }

    // ------------------------------------------------------------------ panneau « Maison à vendre »

    std::string MaisonsModule::Or(uint32 cuivre)
    {
        char buf[32];
        snprintf(buf, sizeof(buf), "%u po", cuivre / 10000);
        return buf;
    }

    void MaisonsModule::OnGossipHello(Player* player, GameObject* gameObject)
    {
        if (!player || !gameObject || gameObject->GetEntry() != MAISONS_PANNEAU)
            return;
        std::lock_guard<std::recursive_mutex> guard(lock);
        uint32 id = gameObject->GetDbGuid() - MAISONS_PANNEAU_GUID;
        auto l = lieux.find(id);
        if (l == lieux.end())
            return;
        GossipMenu& menu = player->GetPlayerMenu()->GetGossipMenu();
        uint32 nb = 0;
        for (auto const& p : proprio)
            if (p.second == id)
                ++nb;
        char buf[256];
        snprintf(buf, sizeof(buf), "Maison %u, %s : %s maison, %s. Propriétaires : %u.", id, l->second.ville.c_str(), l->second.taille.c_str(),
                 Or(l->second.prix).c_str(), nb);
        menu.AddMenuItem(GOSSIP_ICON_CHAT, buf, GOSSIP_SENDER_MAIN, ACTION_INFO, "", false);
        auto vt = vitrine.find(id);
        if (vt != vitrine.end())
        {
            std::string nom = "?";
            sObjectMgr.GetPlayerNameByGUID(ObjectGuid(HIGHGUID_PLAYER, vt->second), nom);
            snprintf(buf, sizeof(buf), "Plus belle maison ici : celle de %s (%u meubles).", nom.c_str(), NombreMeubles(id, vt->second));
            menu.AddMenuItem(GOSSIP_ICON_CHAT, buf, GOSSIP_SENDER_MAIN, ACTION_INFO, "", false);
        }
        auto p = proprio.find(player->GetGUIDLow());
        if (p != proprio.end() && p->second == id)
        {
            snprintf(buf, sizeof(buf), "C'est votre maison (%u meubles). .maison meubles pour la décorer.", NombreMeubles(id, player->GetGUIDLow()));
            menu.AddMenuItem(GOSSIP_ICON_CHAT, buf, GOSSIP_SENDER_MAIN, ACTION_INFO, "", false);
            menu.AddMenuItem(GOSSIP_ICON_MONEY_BAG, "Vendre ma maison (rembourse " + Or(l->second.prix / 2) + ", retire mes meubles)",
                             GOSSIP_SENDER_MAIN, ACTION_VENDRE, "Vendre cette maison et retirer tous vos meubles ?", false);
        }
        else if (p != proprio.end())
        {
            auto autre = lieux.find(p->second);
            snprintf(buf, sizeof(buf), "Vous avez déjà une maison (%s, n° %u). Vendez-la d'abord.", autre != lieux.end() ? autre->second.ville.c_str() : "?", p->second);
            menu.AddMenuItem(GOSSIP_ICON_CHAT, buf, GOSSIP_SENDER_MAIN, ACTION_INFO, "", false);
        }
        else
            menu.AddMenuItem(GOSSIP_ICON_MONEY_BAG, "Acheter cette maison pour " + Or(l->second.prix), GOSSIP_SENDER_MAIN, ACTION_ACHETER,
                             "Acheter cette maison pour " + Or(l->second.prix) + " ?", false);
    }

    bool MaisonsModule::OnGossipSelect(Player* player, GameObject* gameObject, uint32 /*sender*/, uint32 action, const std::string& /*code*/, uint32 /*gossipListId*/)
    {
        if (!player || !gameObject || gameObject->GetEntry() != MAISONS_PANNEAU)
            return false;
        player->GetPlayerMenu()->CloseGossip();
        uint32 maison = 0;
        {
            std::lock_guard<std::recursive_mutex> guard(lock);
            uint32 id = gameObject->GetDbGuid() - MAISONS_PANNEAU_GUID;
            auto l = lieux.find(id);
            if (l == lieux.end() || action == ACTION_INFO)
                return true;
            uint32 g = player->GetGUIDLow();
            auto p = proprio.find(g);
            if (action == ACTION_ACHETER)
            {
                if (p != proprio.end())
                    return true;
                if (player->GetMoney() < l->second.prix)
                {
                    ChatHandler(player->GetSession()).SendSysMessage(("Il vous faut " + Or(l->second.prix) + " pour acheter cette maison.").c_str());
                    return true;
                }
                player->ModifyMoney(-int32(l->second.prix));
                proprio[g] = id;
                CharacterDatabase.PExecute("REPLACE INTO `custom_maison_proprio` (`guid`, `maison`, `achat`) VALUES (%u, %u, UNIX_TIMESTAMP())", g, id);
                ChatHandler(player->GetSession()).SendSysMessage("Félicitations, cette maison est à vous ! Tapez .maison meubles pour la décorer.");
            }
            else if (action == ACTION_VENDRE)
            {
                if (p == proprio.end() || p->second != id)
                    return true;
                proprio.erase(p);
                for (auto& m : meubles)
                    if (m.second.owner == g && m.second.maison == id)
                        m.second.retirer = true;
                CharacterDatabase.PExecute("DELETE FROM `custom_maison_proprio` WHERE `guid` = %u", g);
                CharacterDatabase.PExecute("DELETE FROM `custom_maison_meuble` WHERE `guid` = %u AND `maison` = %u", g, id);
                player->ModifyMoney(int32(l->second.prix / 2));
                CalculerVitrine(id);
                ChatHandler(player->GetSession()).SendSysMessage(("Maison vendue, vous récupérez " + Or(l->second.prix / 2) + ".").c_str());
            }
            maison = id;
        }
        Rafraichir(maison);
        return true;
    }

    // ------------------------------------------------------------------ meubles

    bool MaisonsModule::HandleMeubles(WorldSession* session, const std::string& /*args*/)
    {
        std::lock_guard<std::recursive_mutex> guard(lock);
        std::string ligne;
        for (auto const& c : catalogue)
        {
            std::string e = std::to_string(c.first - MAISONS_MEUBLE_MIN + 1) + " " + c.second;
            if (ligne.size() + e.size() > 230)
            {
                Message(session, ligne);
                ligne.clear();
            }
            ligne += (ligne.empty() ? "" : ", ") + e;
        }
        if (!ligne.empty())
            Message(session, ligne);
        Message(session, "Dans votre maison : .maison poser <numéro> (devant vous, dans votre direction), .maison retirer (le plus proche).");
        return true;
    }

    bool MaisonsModule::HandlePoser(WorldSession* session, const std::string& args)
    {
        Player* player = session ? session->GetPlayer() : nullptr;
        if (!player)
            return false;
        uint32 maison = 0;
        {
            std::lock_guard<std::recursive_mutex> guard(lock);
            uint32 num = uint32(atoi(args.c_str()));
            uint32 entry = MAISONS_MEUBLE_MIN + num - 1;
            if (!num || catalogue.find(entry) == catalogue.end())
            {
                Message(session, "Numéro de meuble inconnu. .maison meubles pour la liste.");
                return true;
            }
            auto p = proprio.find(player->GetGUIDLow());
            auto l = p != proprio.end() ? lieux.find(p->second) : lieux.end();
            if (l == lieux.end())
            {
                Message(session, "Vous n'avez pas de maison. Achetez-en une au panneau « Maison à vendre ».");
                return true;
            }
            if (player->GetMapId() != l->second.map || !Dedans(l->second, player->GetPositionX(), player->GetPositionY(), player->GetPositionZ(), 1.5f))
            {
                Message(session, "Placez-vous dans votre maison pour poser un meuble.");
                return true;
            }
            if (NombreMeubles(l->first, player->GetGUIDLow()) >= MAISONS_MEUBLES_MAX)
            {
                Message(session, "Votre maison a déjà le maximum de meubles.");
                return true;
            }
            MaisonMeuble m;
            m.id = prochainMeuble++;
            m.owner = player->GetGUIDLow();
            m.maison = l->first;
            m.entry = entry;
            m.o = player->GetOrientation();
            m.x = player->GetPositionX() + 1.5f * std::cos(m.o);
            m.y = player->GetPositionY() + 1.5f * std::sin(m.o);
            m.z = player->GetPositionZ();
            meubles[m.id] = m;
            CharacterDatabase.PExecute("INSERT INTO `custom_maison_meuble` (`id`, `guid`, `maison`, `entry`, `x`, `y`, `z`, `o`) VALUES (%u, %u, %u, %u, %f, %f, %f, %f)",
                                       m.id, m.owner, m.maison, m.entry, m.x, m.y, m.z, m.o);
            CalculerVitrine(m.maison);
            maison = m.maison;
            Message(session, catalogue[entry] + " posé.");
        }
        Rafraichir(maison);
        return true;
    }

    bool MaisonsModule::HandleRetirer(WorldSession* session, const std::string& /*args*/)
    {
        Player* player = session ? session->GetPlayer() : nullptr;
        if (!player)
            return false;
        uint32 maison = 0;
        {
            std::lock_guard<std::recursive_mutex> guard(lock);
            MaisonMeuble* best = nullptr;
            float bd = 25.0f;                   // 5 m
            for (auto& m : meubles)
            {
                if (m.second.owner != player->GetGUIDLow() || m.second.retirer)
                    continue;
                float dx = m.second.x - player->GetPositionX(), dy = m.second.y - player->GetPositionY(), dz = m.second.z - player->GetPositionZ();
                float d = dx * dx + dy * dy + dz * dz;
                if (d < bd)
                {
                    bd = d;
                    best = &m.second;
                }
            }
            if (!best)
            {
                Message(session, "Aucun de vos meubles à moins de 5 m.");
                return true;
            }
            best->retirer = true;
            CharacterDatabase.PExecute("DELETE FROM `custom_maison_meuble` WHERE `id` = %u", best->id);
            CalculerVitrine(best->maison);
            maison = best->maison;
            Message(session, catalogue[best->entry] + " retiré.");
        }
        Rafraichir(maison);
        return true;
    }

    // ------------------------------------------------------------------ commandes

    void MaisonsModule::Message(WorldSession* session, const std::string& text)
    {
        if (session)
            ChatHandler(session).SendSysMessage(text.c_str());
    }

    std::string MaisonsModule::Echappe(const std::string& s)
    {
        std::string out = s;
        WorldDatabase.escape_string(out);
        return out;
    }

    std::string MaisonsModule::NomZone(Player* player)
    {
        if (AreaTableEntry const* a = GetAreaEntryByAreaID(player->GetZoneId()))
        {
            int loc = player->GetSession()->GetSessionDbcLocale();
            if (a->area_name[loc] && *a->area_name[loc])
                return a->area_name[loc];
            if (a->area_name[0])
                return a->area_name[0];
        }
        return "";
    }

    std::vector<ModuleChatCommand>* MaisonsModule::GetCommandTable()
    {
        static std::vector<ModuleChatCommand> commandTable =
        {
            { "suivante", std::bind(&MaisonsModule::HandleSuivante, this, std::placeholders::_1, std::placeholders::_2), SEC_GAMEMASTER },
            { "ok", std::bind(&MaisonsModule::HandleOk, this, std::placeholders::_1, std::placeholders::_2), SEC_GAMEMASTER },
            { "non", std::bind(&MaisonsModule::HandleNon, this, std::placeholders::_1, std::placeholders::_2), SEC_GAMEMASTER },
            { "ajout", std::bind(&MaisonsModule::HandleAjout, this, std::placeholders::_1, std::placeholders::_2), SEC_GAMEMASTER },
            { "pnj", std::bind(&MaisonsModule::HandlePnj, this, std::placeholders::_1, std::placeholders::_2), SEC_GAMEMASTER },
            { "dehors", std::bind(&MaisonsModule::HandleDehors, this, std::placeholders::_1, std::placeholders::_2), SEC_GAMEMASTER },
            { "bilan", std::bind(&MaisonsModule::HandleBilan, this, std::placeholders::_1, std::placeholders::_2), SEC_GAMEMASTER },
            { "panneau", std::bind(&MaisonsModule::HandlePanneau, this, std::placeholders::_1, std::placeholders::_2), SEC_GAMEMASTER },
            { "meubles", std::bind(&MaisonsModule::HandleMeubles, this, std::placeholders::_1, std::placeholders::_2), SEC_PLAYER },
            { "poser", std::bind(&MaisonsModule::HandlePoser, this, std::placeholders::_1, std::placeholders::_2), SEC_PLAYER },
            { "retirer", std::bind(&MaisonsModule::HandleRetirer, this, std::placeholders::_1, std::placeholders::_2), SEC_PLAYER },
        };
        return &commandTable;
    }

    // déplace le panneau de la maison la plus proche (50 m) là où l'on se tient (pris en compte au redémarrage)
    bool MaisonsModule::HandlePanneau(WorldSession* session, const std::string& /*args*/)
    {
        Player* player = session ? session->GetPlayer() : nullptr;
        if (!player)
            return false;
        std::lock_guard<std::recursive_mutex> guard(lock);
        uint32 best = 0;
        float bd = 2500.0f;
        for (auto const& l : lieux)
        {
            if (l.second.map != player->GetMapId())
                continue;
            float dx = l.second.x - player->GetPositionX(), dy = l.second.y - player->GetPositionY();
            if (dx * dx + dy * dy < bd)
            {
                bd = dx * dx + dy * dy;
                best = l.first;
            }
        }
        if (!best)
        {
            Message(session, "Aucune maison à moins de 50 m.");
            return true;
        }
        float o = player->GetOrientation();
        WorldDatabase.DirectPExecute("UPDATE `gameobject` SET `position_x` = %f, `position_y` = %f, `position_z` = %f, `orientation` = %f, "
                                     "`rotation2` = %f, `rotation3` = %f WHERE `guid` = %u", player->GetPositionX(), player->GetPositionY(),
                                     player->GetPositionZ(), o, std::sin(o / 2.0f), std::cos(o / 2.0f), MAISONS_PANNEAU_GUID + best);
        char buf[128];
        snprintf(buf, sizeof(buf), "Panneau de la maison %u placé ici (visible après le prochain redémarrage).", best);
        Message(session, buf);
        return true;
    }

    // ------------------------------------------------------------------ repérage

    bool MaisonsModule::HandleSuivante(WorldSession* session, const std::string& args)
    {
        Player* player = session ? session->GetPlayer() : nullptr;
        if (!player)
            return false;
        std::string filtre = args.empty() ? "" : " AND `zone` LIKE '%" + Echappe(args) + "%'";
        auto result = WorldDatabase.Query(("SELECT `id`, `zone`, `map`, `x`, `y`, `z`, `taille`, "
            "(SELECT COUNT(*) FROM `custom_maison` WHERE `statut` = 0" + filtre + ") "
            "FROM `custom_maison` WHERE `statut` = 0" + filtre + " ORDER BY `id` LIMIT 1").c_str());
        if (!result)
        {
            Message(session, args.empty() ? "Toutes les maisons de la liste sont vérifiées." : "Plus aucune maison à vérifier pour cette zone.");
            return true;
        }
        Field* f = result->Fetch();
        uint32 id = f[0].GetUInt32();
        actuelle[player->GetGUIDLow()] = id;
        char buf[256];
        snprintf(buf, sizeof(buf), "Maison %u (%s, %s), encore %u à vérifier. .maison ok ou .maison non", id, f[1].GetCppString().c_str(),
                 f[6].GetCppString().c_str(), f[7].GetUInt32());
        Message(session, buf);
        player->TeleportTo(f[2].GetUInt32(), f[3].GetFloat(), f[4].GetFloat(), f[5].GetFloat(), player->GetOrientation());
        return true;
    }

    uint32 MaisonsModule::MaisonActuelle(Player* player)
    {
        auto it = actuelle.find(player->GetGUIDLow());
        if (it != actuelle.end())
            if (auto r = WorldDatabase.PQuery("SELECT `id` FROM `custom_maison` WHERE `id` = %u AND `map` = %u AND "
                                              "POW(`x` - %f, 2) + POW(`y` - %f, 2) < 3600", it->second, player->GetMapId(),
                                              player->GetPositionX(), player->GetPositionY()))
                return it->second;
        if (auto r = WorldDatabase.PQuery("SELECT `id` FROM `custom_maison` WHERE `map` = %u AND "
                                          "POW(`x` - %f, 2) + POW(`y` - %f, 2) + POW(`z` - %f, 2) < 1600 "
                                          "ORDER BY POW(`x` - %f, 2) + POW(`y` - %f, 2) + POW(`z` - %f, 2) LIMIT 1",
                                          player->GetMapId(), player->GetPositionX(), player->GetPositionY(), player->GetPositionZ(),
                                          player->GetPositionX(), player->GetPositionY(), player->GetPositionZ()))
            return r->Fetch()[0].GetUInt32();
        return 0;
    }

    bool MaisonsModule::Statut(WorldSession* session, const std::string& args, uint32 statut)
    {
        Player* player = session ? session->GetPlayer() : nullptr;
        if (!player)
            return false;
        uint32 id = MaisonActuelle(player);
        if (!id)
        {
            Message(session, "Aucune maison de la liste ici (40 m). Pour en ajouter une : .maison ajout");
            return true;
        }
        if (args.empty())
            WorldDatabase.DirectPExecute("UPDATE `custom_maison` SET `statut` = %u WHERE `id` = %u", statut, id);
        else
            WorldDatabase.DirectPExecute("UPDATE `custom_maison` SET `statut` = %u, `note` = '%s' WHERE `id` = %u", statut, Echappe(args).c_str(), id);
        actuelle.erase(player->GetGUIDLow());
        char buf[128];
        snprintf(buf, sizeof(buf), "Maison %u %s. .maison suivante pour continuer", id, statut == 1 ? "validée" : "rejetée");
        Message(session, buf);
        return true;
    }

    bool MaisonsModule::HandleOk(WorldSession* session, const std::string& args) { return Statut(session, args, 1); }
    bool MaisonsModule::HandleNon(WorldSession* session, const std::string& args) { return Statut(session, args, 2); }

    bool MaisonsModule::HandleAjout(WorldSession* session, const std::string& args)
    {
        Player* player = session ? session->GetPlayer() : nullptr;
        if (!player)
            return false;
        WorldDatabase.DirectPExecute("INSERT INTO `custom_maison` (`zone`, `map`, `x`, `y`, `z`, `o`, `taille`, `origine`, `statut`, `note`) "
                                     "VALUES ('%s', %u, %f, %f, %f, %f, '', 1, 1, '%s')", Echappe(NomZone(player)).c_str(), player->GetMapId(),
                                     player->GetPositionX(), player->GetPositionY(), player->GetPositionZ(), player->GetOrientation(), Echappe(args).c_str());
        uint32 id = 0;
        if (auto r = WorldDatabase.Query("SELECT MAX(`id`) FROM `custom_maison`"))
            id = r->Fetch()[0].GetUInt32();
        char buf[160];
        snprintf(buf, sizeof(buf), "Maison %u ajoutée ici (%s).", id, NomZone(player).c_str());
        Message(session, buf);
        return true;
    }

    bool MaisonsModule::HandlePnj(WorldSession* session, const std::string& args)
    {
        Player* player = session ? session->GetPlayer() : nullptr;
        if (!player)
            return false;
        Creature* c = player->GetMap()->GetCreature(player->GetSelectionGuid());
        if (!c || !c->GetDbGuid())
        {
            Message(session, "Cible d'abord le PNJ à sortir de la maison.");
            return true;
        }
        float x, y, z, o;
        c->GetRespawnCoord(x, y, z, &o);
        WorldDatabase.DirectPExecute("INSERT INTO `custom_maison_pnj` (`guid`, `entry`, `map`, `x`, `y`, `z`, `o`, `note`) VALUES (%u, %u, %u, %f, %f, %f, %f, '%s') "
                                     "ON DUPLICATE KEY UPDATE `note` = VALUES(`note`)", c->GetDbGuid(), c->GetEntry(), c->GetMapId(), x, y, z, o, Echappe(args).c_str());
        dernierPnj[player->GetGUIDLow()] = c->GetDbGuid();
        Message(session, std::string(c->GetName()) + " marqué à sortir. Va à l'endroit voulu dehors et tape .maison dehors");
        return true;
    }

    bool MaisonsModule::HandleDehors(WorldSession* session, const std::string& /*args*/)
    {
        Player* player = session ? session->GetPlayer() : nullptr;
        if (!player)
            return false;
        auto it = dernierPnj.find(player->GetGUIDLow());
        if (it == dernierPnj.end())
        {
            Message(session, "Marque d'abord un PNJ avec .maison pnj (en le ciblant).");
            return true;
        }
        uint32 guid = it->second;
        float x = player->GetPositionX(), y = player->GetPositionY(), z = player->GetPositionZ(), o = player->GetOrientation();
        WorldDatabase.DirectPExecute("UPDATE `custom_maison_pnj` SET `dest_ok` = 1, `dx` = %f, `dy` = %f, `dz` = %f, `do` = %f WHERE `guid` = %u", x, y, z, o, guid);
        WorldDatabase.DirectPExecute("UPDATE `creature` SET `position_x` = %f, `position_y` = %f, `position_z` = %f, `orientation` = %f WHERE `guid` = %u", x, y, z, o, guid);
        Creature* moved = player->GetMap()->GetCreature(guid);
        if (moved)
        {
            moved->SetRespawnCoord(x, y, z, o);
            moved->NearTeleportTo(x, y, z, o);
        }
        dernierPnj.erase(it);
        Message(session, moved ? "PNJ déplacé ici." : "Position enregistrée : le PNJ sera ici après le prochain redémarrage.");
        return true;
    }

    bool MaisonsModule::HandleBilan(WorldSession* session, const std::string& /*args*/)
    {
        uint32 v = 0, ok = 0, non = 0, aj = 0, pnj = 0, dehors = 0;
        if (auto r = WorldDatabase.Query("SELECT SUM(`statut` = 0), SUM(`statut` = 1), SUM(`statut` = 2), SUM(`origine` = 1) FROM `custom_maison`"))
        {
            Field* f = r->Fetch();
            v = f[0].GetUInt32(); ok = f[1].GetUInt32(); non = f[2].GetUInt32(); aj = f[3].GetUInt32();
        }
        if (auto r = WorldDatabase.Query("SELECT COUNT(*), SUM(`dest_ok` = 1) FROM `custom_maison_pnj`"))
        {
            pnj = r->Fetch()[0].GetUInt32(); dehors = r->Fetch()[1].GetUInt32();
        }
        char buf[320];
        snprintf(buf, sizeof(buf), "Repérage : %u à vérifier, %u validées (dont %u ajoutées), %u rejetées. PNJ : %u marqués, %u sortis. "
                 "Logement : %u maisons, %u propriétaires, %u meubles.", v, ok, aj, non, pnj, dehors,
                 uint32(lieux.size()), uint32(proprio.size()), uint32(meubles.size()));
        Message(session, buf);
        return true;
    }
}
