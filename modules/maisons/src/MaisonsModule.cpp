#include "MaisonsModule.h"

#include "Chat/Chat.h"
#include "Database/DatabaseEnv.h"
#include "Entities/Creature.h"
#include "Entities/Player.h"
#include "Log/Log.h"
#include "Maps/Map.h"
#include "Server/DBCStores.h"
#include "Server/WorldSession.h"

#include <cstdio>
#include <sstream>

namespace cmangos_module
{
    MaisonsModule::MaisonsModule() : Module("Maisons", nullptr)
    {
    }

    void MaisonsModule::OnInitialize()
    {
        // statut : 0 à vérifier, 1 validée, 2 rejetée ; origine : 0 détectée par Claude, 1 ajoutée en jeu
        WorldDatabase.DirectExecute(
            "CREATE TABLE IF NOT EXISTS `custom_maison` ("
            " `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,"
            " `zone` VARCHAR(64) NOT NULL DEFAULT '',"
            " `map` SMALLINT UNSIGNED NOT NULL,"
            " `x` FLOAT NOT NULL, `y` FLOAT NOT NULL, `z` FLOAT NOT NULL, `o` FLOAT NOT NULL DEFAULT 0,"
            " `taille` VARCHAR(32) NOT NULL DEFAULT '',"
            " `origine` TINYINT UNSIGNED NOT NULL DEFAULT 0,"
            " `statut` TINYINT UNSIGNED NOT NULL DEFAULT 0,"
            " `note` VARCHAR(255) NOT NULL DEFAULT '',"
            " PRIMARY KEY (`id`)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4");
        // PNJ à sortir : position d'origine et destination (dest_ok = 1 quand .maison dehors a été fait)
        WorldDatabase.DirectExecute(
            "CREATE TABLE IF NOT EXISTS `custom_maison_pnj` ("
            " `guid` INT UNSIGNED NOT NULL,"
            " `entry` INT UNSIGNED NOT NULL,"
            " `map` SMALLINT UNSIGNED NOT NULL,"
            " `x` FLOAT NOT NULL, `y` FLOAT NOT NULL, `z` FLOAT NOT NULL, `o` FLOAT NOT NULL,"
            " `dest_ok` TINYINT UNSIGNED NOT NULL DEFAULT 0,"
            " `dx` FLOAT NOT NULL DEFAULT 0, `dy` FLOAT NOT NULL DEFAULT 0, `dz` FLOAT NOT NULL DEFAULT 0, `do` FLOAT NOT NULL DEFAULT 0,"
            " `note` VARCHAR(255) NOT NULL DEFAULT '',"
            " PRIMARY KEY (`guid`)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4");
        // les PNJ déjà sortis restent dehors après un redémarrage
        if (auto result = WorldDatabase.Query("SELECT COUNT(*) FROM `custom_maison_pnj` WHERE `dest_ok` = 1"))
            sLog.outString("Maisons : %u PNJ sortis des maisons", result->Fetch()[0].GetUInt32());
    }

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
        };
        return &commandTable;
    }

    // prochaine maison à vérifier (filtre optionnel sur le nom de zone), dans l'ordre de la liste
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

    // maison sur laquelle on a été téléporté, sinon la plus proche à moins de 40 m
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
        std::string msg = std::string(c->GetName()) + " marqué à sortir. Va à l'endroit voulu dehors et tape .maison dehors";
        Message(session, msg);
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
        // enregistré pour la mise en place définitive, et appliqué tout de suite au PNJ et à sa position en base
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
        char buf[256];
        snprintf(buf, sizeof(buf), "Maisons : %u à vérifier, %u validées (dont %u ajoutées), %u rejetées. PNJ : %u marqués, %u sortis.", v, ok, aj, non, pnj, dehors);
        Message(session, buf);
        return true;
    }
}
