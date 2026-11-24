#include "VaguesModule.h"

#include "Accounts/AccountMgr.h"
#include "Chat/Chat.h"
#include "Database/DatabaseEnv.h"
#include "Entities/Player.h"
#include "Globals/ObjectAccessor.h"
#include "Globals/ObjectMgr.h"
#include "Groups/Group.h"
#include "Guilds/Guild.h"
#include "Guilds/GuildMgr.h"
#include "Log/Log.h"
#include "Maps/Map.h"
#include "MotionGenerators/MotionMaster.h"
#include "Movement/MoveSpline.h"
#include "Server/WorldSession.h"
#include "Util/Util.h"

#include "playerbot/playerbot.h"
#include "playerbot/PlayerbotAI.h"
#include "playerbot/PlayerbotAIConfig.h"
#include "playerbot/RandomPlayerbotFactory.h"
#include "playerbot/RandomPlayerbotMgr.h"
#include "playerbot/PlayerbotMgr.h"
#include "playerbot/PlayerbotFactory.h"
#include "playerbot/strategy/actions/ChangeTalentsAction.h"

#include <cmath>
#include <cstdlib>
#include <unordered_set>
#include <functional>
#include <map>
#include <set>
#include <sstream>

namespace cmangos_module
{
    // Composition d'une vague (275 bots : 137 Alliance, 138 Horde), validée avec Alexis.
    // Spé imposée : soit une spé pré-faite d'aiplayerbot.conf (specNo), soit un arbre de talents (classes custom et 4e spé),
    // géré par le module classes (table custom_bot_arbre).
    struct Spe { int32 premade; int32 arbre; uint8 nombre; uint8 nombreAlliance; };
    #define PRE(id, n)      { id, -1, n, n }
    #define ARB(t, n)       { -1, t, n, n }
    #define ARB2(t, n, a)   { -1, t, n, a }

    static std::vector<Spe> SpesDeClasse(uint8 cls)
    {
        switch (cls)
        {
            case 1: return { PRE(0, 1), PRE(1, 1), PRE(2, 3), ARB(3, 1) };           // armes, fureur, protection (tank), Berserker
            case 2: return { PRE(2, 2), PRE(9, 3), PRE(0, 2), ARB(3, 1) };           // sacré, protection (tank), vindicte, Soleil
            case 3: return { PRE(3, 2), PRE(4, 2), PRE(5, 2), ARB(3, 1) };           // bêtes, précision, survie, Infirmier
            case 4: return { PRE(2, 1), PRE(0, 1), PRE(9, 1), ARB(3, 1) };           // assassinat, combat, finesse, Fantôme
            case 5: return { PRE(0, 2), PRE(1, 2), PRE(2, 2), ARB(3, 1) };           // discipline, sacré, ombre, Corrompu
            case 7: return { PRE(0, 2), PRE(8, 2), PRE(3, 2), ARB(3, 3) };           // élémentaire, amélioration, restauration, Ruines (tank)
            case 8: return { PRE(0, 2), PRE(1, 2), PRE(8, 2), ARB(3, 1) };           // arcanes, feu, givre, Nature
            case 9: return { PRE(4, 2), PRE(0, 2), PRE(2, 2), ARB(3, 3) };           // affliction, démonologie, destruction, Transfuge (tank)
            case 6: return { ARB2(0, 1, 2), ARB2(1, 1, 2), ARB2(2, 1, 2) };          // Nécromancien : Invocateur, Malédiction, Magicien
            case 10: return { ARB2(0, 1, 2), ARB2(1, 1, 2), ARB2(2, 1, 2) };         // Sniper : Bestial, Tireur d'élite, Mécanisme
            case 11: return { ARB2(0, 1, 2), ARB2(1, 1, 2), ARB(2, 3) };             // Métamorphe : Totémique, Druidique, Angélique (tank)
            default: return {};
        }
    }

    // paires race / classe jouables par faction (après les retraits : voir gen_classes.py)
    static const uint8 RACES_ALLIANCE[] = { 1, 3, 4, 7 };
    static const uint8 RACES_HORDE[] = { 2, 5, 6, 8 };
    static std::vector<uint8> ClassesDeRace(uint8 race)
    {
        switch (race)
        {
            case 1: return { 1, 2, 5, 8, 9, 6 };        // Humain : guerrier, paladin, prêtre, mage, démoniste, nécromancien
            case 3: return { 1, 2, 3, 7, 10 };          // Nain : guerrier, paladin, chasseur, chaman, sniper
            case 4: return { 3, 4, 5, 11 };             // Elfe de la nuit : chasseur, voleur, prêtre, métamorphe
            case 7: return { 1, 4, 8, 9, 11 };          // Gnome : guerrier, voleur, mage, démoniste, métamorphe
            case 2: return { 1, 3, 4, 7, 9, 10 };       // Orc : guerrier, chasseur, voleur, chaman, démoniste, sniper
            case 5: return { 2, 4, 5, 8, 9, 6 };        // Mort-vivant : paladin, voleur, prêtre, mage, démoniste, nécromancien
            case 6: return { 1, 3, 7, 11 };             // Tauren : guerrier, chasseur, chaman, métamorphe
            case 8: return { 4, 5, 7, 8, 6, 11 };       // Troll : voleur, prêtre, chaman, mage, nécromancien, métamorphe
            default: return {};
        }
    }


    // Compagnons (.bots groupe) : prêtre Sacré, guerrier Protection, mage Givre, paladin Vindicte, niveau 15,
    // équipés d'objets de niveau 15 minimum (vert / bleu obtenables), arme comprise, sans anneau, bijou ni artefact.
    // Choix fait par wow/compagnons/choix.py sur la base classicmangos.
    struct ObjetCompagnon { uint8 slot; uint32 item; };
    struct RoleCompagnon { uint8 cls; uint8 raceA; uint8 raceH; int32 premade; const char* nom; std::vector<ObjetCompagnon> objets; };
    static const uint32 COMPAGNONS_NIVEAU = 15;
    static const char* COMPAGNONS_COMPTE = "COMPAGNONS";
    static const std::vector<RoleCompagnon>& Compagnons()
    {
        static const std::vector<RoleCompagnon> v =
        {
            { 5, 4, 8, 1, "prêtre Sacré (soin)", { { EQUIPMENT_SLOT_HEAD, 994098 }, { EQUIPMENT_SLOT_BACK, 6378 }, { EQUIPMENT_SLOT_CHEST, 4782 }, { EQUIPMENT_SLOT_WRISTS, 14148 },
                { EQUIPMENT_SLOT_HANDS, 12977 }, { EQUIPMENT_SLOT_WAIST, 4786 }, { EQUIPMENT_SLOT_LEGS, 2982 }, { EQUIPMENT_SLOT_FEET, 4660 },
                { EQUIPMENT_SLOT_MAINHAND, 1300 }, { EQUIPMENT_SLOT_RANGED, 5243 } } },
            { 1, 3, 2, 2, "guerrier Protection (tank)", { { EQUIPMENT_SLOT_HEAD, 994097 }, { EQUIPMENT_SLOT_BACK, 14745 }, { EQUIPMENT_SLOT_CHEST, 3306 }, { EQUIPMENT_SLOT_WRISTS, 3211 },
                { EQUIPMENT_SLOT_HANDS, 1448 }, { EQUIPMENT_SLOT_WAIST, 12978 }, { EQUIPMENT_SLOT_LEGS, 14727 }, { EQUIPMENT_SLOT_FEET, 1446 },
                { EQUIPMENT_SLOT_MAINHAND, 12976 }, { EQUIPMENT_SLOT_OFFHAND, 5443 }, { EQUIPMENT_SLOT_RANGED, 3040 } } },
            { 8, 7, 5, 8, "mage Givre", { { EQUIPMENT_SLOT_HEAD, 994098 }, { EQUIPMENT_SLOT_BACK, 6378 }, { EQUIPMENT_SLOT_CHEST, 14150 }, { EQUIPMENT_SLOT_WRISTS, 14366 },
                { EQUIPMENT_SLOT_HANDS, 12977 }, { EQUIPMENT_SLOT_WAIST, 4786 }, { EQUIPMENT_SLOT_LEGS, 2970 }, { EQUIPMENT_SLOT_FEET, 4660 },
                { EQUIPMENT_SLOT_MAINHAND, 935 }, { EQUIPMENT_SLOT_OFFHAND, 5183 }, { EQUIPMENT_SLOT_RANGED, 5243 } } },
            { 2, 1, 5, 0, "paladin Vindicte", { { EQUIPMENT_SLOT_HEAD, 994097 }, { EQUIPMENT_SLOT_BACK, 14745 }, { EQUIPMENT_SLOT_CHEST, 3306 }, { EQUIPMENT_SLOT_WRISTS, 3211 },
                { EQUIPMENT_SLOT_HANDS, 2992 }, { EQUIPMENT_SLOT_WAIST, 12978 }, { EQUIPMENT_SLOT_LEGS, 14727 }, { EQUIPMENT_SLOT_FEET, 1446 },
                { EQUIPMENT_SLOT_MAINHAND, 12975 } } },
        };
        return v;
    }
    // point de téléportation « Stormwind » (game_tele 246)
    static const float SW_X = -8833.38f, SW_Y = 628.628f, SW_Z = 94.0066f, SW_O = 1.06535f;
    static const uint32 SW_ZONE = 1519;

    static const float XP_MULT[4] = { 0.6f, 1.0f, 1.3f, 1.6f };
    static const float REACT_MULT[4] = { 0.7f, 1.0f, 2.0f, 4.0f };
    static const char* NOM_RYTHME[4] = { "lent", "normal", "rapide", "très rapide" };
    static const char* NOM_QUALITE[4] = { "expert", "bon", "moyen", "débutant" };

    static uint8 Tirage(const uint32 poids[4])
    {
        uint32 total = poids[0] + poids[1] + poids[2] + poids[3];
        uint32 r = urand(0, total - 1);
        for (uint8 i = 0; i < 4; ++i)
        {
            if (r < poids[i])
                return i;
            r -= poids[i];
        }
        return 1;
    }

    VaguesModule::VaguesModule() : Module("Vagues", nullptr)
    {
    }

    void VaguesModule::OnInitialize()
    {
        CharacterDatabase.Execute(
            "CREATE TABLE IF NOT EXISTS `custom_bot_profile` ("
            " `guid` INT UNSIGNED NOT NULL,"
            " `vague` TINYINT UNSIGNED NOT NULL,"
            " `rythme` TINYINT UNSIGNED NOT NULL,"
            " `qualite` TINYINT UNSIGNED NOT NULL,"
            " `xp_mult` FLOAT NOT NULL,"
            " `react_mult` FLOAT NOT NULL,"
            " PRIMARY KEY (`guid`)) ENGINE=InnoDB DEFAULT CHARSET=utf8");
        CharacterDatabase.Execute("CREATE TABLE IF NOT EXISTS `custom_bot_arbre` (`guid` INT UNSIGNED NOT NULL, `arbre` TINYINT UNSIGNED NOT NULL,"
                                  " PRIMARY KEY (`guid`)) ENGINE=InnoDB DEFAULT CHARSET=utf8");
        CharacterDatabase.Execute("CREATE TABLE IF NOT EXISTS `custom_bot_wave_delete` (`vague` TINYINT UNSIGNED NOT NULL, PRIMARY KEY (`vague`)) ENGINE=InnoDB DEFAULT CHARSET=utf8");

        // Suppression des vagues demandees avec .bots supprimer (faite au demarrage, avant la connexion des bots)
        if (auto del = CharacterDatabase.Query("SELECT p.`guid`, c.`account` FROM `custom_bot_profile` p JOIN `characters` c ON c.`guid` = p.`guid` "
                                               "WHERE p.`vague` IN (SELECT `vague` FROM `custom_bot_wave_delete`)"))
        {
            uint32 n = 0;
            do
            {
                Field* f = del->Fetch();
                Player::DeleteFromDB(ObjectGuid(HIGHGUID_PLAYER, f[0].GetUInt32()), f[1].GetUInt32(), false, true);
                ++n;
            }
            while (del->NextRow());
            sLog.outString("Vagues : %u bot(s) supprime(s)", n);
        }
        CharacterDatabase.Execute("DELETE FROM `custom_bot_profile` WHERE `vague` IN (SELECT `vague` FROM `custom_bot_wave_delete`)");
        CharacterDatabase.Execute("DELETE FROM `custom_bot_wave_delete`");
        CharacterDatabase.Execute("DELETE FROM `ai_playerbot_random_bots` WHERE `bot` <> 0 AND `bot` NOT IN (SELECT `guid` FROM `characters`)");
        CharacterDatabase.Execute("DELETE FROM `custom_bot_profile` WHERE `guid` NOT IN (SELECT `guid` FROM `characters`)");
        CharacterDatabase.Execute("DELETE FROM `custom_bot_arbre` WHERE `guid` NOT IN (SELECT `guid` FROM `characters`)");

        if (auto result = CharacterDatabase.Query("SELECT `guid`, `vague`, `rythme`, `qualite`, `xp_mult`, `react_mult` FROM `custom_bot_profile`"))
        {
            do
            {
                Field* f = result->Fetch();
                ProfilBot& p = profils[f[0].GetUInt32()];
                p.vague = f[1].GetUInt32();
                p.rythme = uint8(f[2].GetUInt32());
                p.qualite = uint8(f[3].GetUInt32());
                p.xpMult = f[4].GetFloat();
                p.reactMult = f[5].GetFloat();
            }
            while (result->NextRow());
        }
        sLog.outString("Vagues : %u bot(s) de vague, %u vague(s)", uint32(profils.size()), NombreVagues());
    }

    uint32 VaguesModule::NombreVagues() const
    {
        uint32 n = 0;
        for (auto const& kv : profils)
            n = std::max(n, kv.second.vague);
        return n;
    }

    uint32 VaguesModule::VaguesPresentes() const
    {
        std::set<uint32> v;
        for (auto const& kv : profils)
            v.insert(kv.second.vague);
        return uint32(v.size());
    }

    void VaguesModule::Message(WorldSession* session, const std::string& text)
    {
        if (session)
            ChatHandler(session).SendSysMessage(text.c_str());
        sLog.outString("Vagues : %s", text.c_str());
    }

    std::vector<ModuleChatCommand>* VaguesModule::GetCommandTable()
    {
        static std::vector<ModuleChatCommand> commandTable =
        {
            { "vague", std::bind(&VaguesModule::HandleVague, this, std::placeholders::_1, std::placeholders::_2), SEC_GAMEMASTER },
            { "info", std::bind(&VaguesModule::HandleInfo, this, std::placeholders::_1, std::placeholders::_2), SEC_PLAYER },
            { "supprimer", std::bind(&VaguesModule::HandleSupprimer, this, std::placeholders::_1, std::placeholders::_2), SEC_GAMEMASTER },
            { "groupe", std::bind(&VaguesModule::HandleGroupe, this, std::placeholders::_1, std::placeholders::_2), SEC_GAMEMASTER },
        };
        return &commandTable;
    }

    bool VaguesModule::HandleVague(WorldSession* session, const std::string& args)
    {
        uint32 vague = NombreVagues() + 1;
        // niveau de départ facultatif : .bots vague 12
        uint32 niveau = args.empty() ? 1 : uint32(atoi(args.c_str()));
        if (niveau < 1 || niveau > 60)
        {
            Message(session, "Usage : .bots vague [niveau de 1 à 60]");
            return true;
        }
        if (VaguesPresentes() >= VAGUES_MAX)
        {
            Message(session, "Il y a déjà 5 vagues. Supprime-en une avec .bots supprimer <numéro>.");
            return true;
        }

        // Liste des bots a creer, race par race (voir SpesDeClasse et ClassesDeRace)
        struct Tache { uint8 race; uint8 cls; int32 premade; int32 arbre; };
        std::vector<Tache> taches;
        uint32 parFaction[2] = { 0, 0 };
        for (int faction = 0; faction < 2; ++faction)
        {
            for (uint8 race : (faction == 0 ? std::vector<uint8>(RACES_ALLIANCE, RACES_ALLIANCE + 4) : std::vector<uint8>(RACES_HORDE, RACES_HORDE + 4)))
                for (uint8 cls : ClassesDeRace(race))
                    for (Spe const& sp : SpesDeClasse(cls))
                        for (uint8 c = 0; c < (faction == 0 ? sp.nombreAlliance : sp.nombre); ++c)
                        {
                            taches.push_back({ race, cls, sp.premade, sp.arbre });
                            ++parFaction[faction];
                        }
        }

        Message(session, "Création de la vague " + std::to_string(vague) + " (" + std::to_string(taches.size()) + " bots niveau " + std::to_string(niveau) + " : "
            + std::to_string(parFaction[0]) + " Alliance, " + std::to_string(parFaction[1]) + " Horde)...");

        std::set<uint64> avant;
        for (auto const& kv : sObjectAccessor.GetPlayers())
            avant.insert(kv.first.GetRawValue());

        struct Cree { Player* player; Tache tache; };
        std::vector<Cree> crees;
        size_t prochain = 0;

        for (uint32 accountId : sPlayerbotAIConfig.randomBotAccounts)
        {
            if (prochain >= taches.size())
                break;
            uint32 count = sAccountMgr.GetCharactersCount(accountId);
            RandomPlayerbotFactory factory(accountId);
            while (count < 9 && prochain < taches.size())
            {
                const Tache& t = taches[prochain];
                if (!factory.CreateRandomBot(t.cls, t.race))
                {
                    ++prochain;     // nom indisponible ou erreur : on passe a la suivante
                    continue;
                }
                ++count;
                // retrouver le personnage qui vient d'etre cree
                for (auto const& kv : sObjectAccessor.GetPlayers())
                {
                    uint64 raw = kv.first.GetRawValue();
                    if (avant.count(raw))
                        continue;
                    avant.insert(raw);
                    Player* p = kv.second;
                    if (p && p->GetSession() && p->GetSession()->GetAccountId() == accountId)
                        crees.push_back({ p, t });
                }
                ++prochain;
            }
        }

        // Enregistrement en base puis fermeture des sessions temporaires (meme logique que la creation au demarrage)
        for (Cree& c : crees)
        {
            if (niveau > 1)
            {
                // équipement et sorts du niveau : donnés par les bots aléatoires à leur première connexion
                c.player->GiveLevel(niveau);
                c.player->InitTalentForLevel();
                c.player->SetUInt32Value(PLAYER_XP, 0);
            }
            c.player->SaveToDB();
        }

        std::ostringstream sql;
        uint32 rythmes[4] = { 0, 0, 0, 0 }, qualites[4] = { 0, 0, 0, 0 };
        static const uint32 POIDS_RYTHME[4] = { 20, 40, 25, 15 };
        static const uint32 POIDS_QUALITE[4] = { 15, 35, 30, 20 };
        for (Cree& c : crees)
        {
            uint32 guid = c.player->GetObjectGuid().GetCounter();
            ProfilBot p;
            p.vague = vague;
            p.rythme = Tirage(POIDS_RYTHME);
            p.qualite = Tirage(POIDS_QUALITE);
            p.xpMult = XP_MULT[p.rythme];
            p.reactMult = REACT_MULT[p.qualite];
            profils[guid] = p;
            ++rythmes[p.rythme];
            ++qualites[p.qualite];

            CharacterDatabase.PExecute("REPLACE INTO `custom_bot_profile` (`guid`, `vague`, `rythme`, `qualite`, `xp_mult`, `react_mult`) VALUES (%u, %u, %u, %u, %f, %f)",
                guid, vague, uint32(p.rythme), uint32(p.qualite), p.xpMult, p.reactMult);
            // specialisation imposee : spe pre-faite (valable 10 ans) ou arbre de talents gere par le module classes
            if (c.tache.premade >= 0)
                sRandomPlayerbotMgr.SetValue(guid, "specNo", uint32(c.tache.premade) + 1, "", 315360000);
            else
            {
                sRandomPlayerbotMgr.SetValue(guid, "specNo", 0, "", 315360000);
                CharacterDatabase.PExecute("REPLACE INTO `custom_bot_arbre` (`guid`, `arbre`) VALUES (%u, %u)", guid, uint32(c.tache.arbre));
            }
        }

        for (Cree& c : crees)
        {
            WorldSession* s = c.player->GetSession();
            s->LogoutPlayer();
            sObjectAccessor.RemoveObject(c.player);
            delete c.player;
            delete s;
        }

        std::ostringstream out;
        out << "Vague " << vague << " créée : " << crees.size() << " bots niveau " << niveau << " sur " << taches.size() << " prévus. Ils se connectent dans les prochaines minutes."
            << " Rythme : " << rythmes[0] << " lents, " << rythmes[1] << " normaux, " << rythmes[2] << " rapides, " << rythmes[3] << " très rapides."
            << " Jeu : " << qualites[0] << " experts, " << qualites[1] << " bons, " << qualites[2] << " moyens, " << qualites[3] << " débutants.";
        Message(session, out.str());
        if (crees.size() < taches.size())
            Message(session, "Attention : certains bots n'ont pas pu être créés (comptes pleins ou noms épuisés).");
        return true;
    }

    // .bots groupe [recreer] : crée (ou reconnecte) 4 compagnons sur le compte COMPAGNONS, au point de téléportation de Hurlevent,
    // dans le groupe du joueur qui lance la commande.
    bool VaguesModule::HandleGroupe(WorldSession* session, const std::string& args)
    {
        Player* maitre = session ? session->GetPlayer() : nullptr;
        if (!maitre || !maitre->GetPlayerbotMgr())
        {
            Message(session, "Cette commande se lance en jeu, depuis ton personnage.");
            return true;
        }
        if (!compagnons.empty())
        {
            Message(session, "Des compagnons sont déjà en route, patiente quelques secondes.");
            return true;
        }

        uint32 compte = sAccountMgr.GetId(COMPAGNONS_COMPTE);
        if (!compte)
        {
            sAccountMgr.CreateAccount(COMPAGNONS_COMPTE, "compagnons");
            compte = sAccountMgr.GetId(COMPAGNONS_COMPTE);
        }
        if (!compte)
        {
            Message(session, "Impossible de créer le compte COMPAGNONS.");
            return true;
        }

        bool recreer = args.find("recreer") != std::string::npos || args.find("recréer") != std::string::npos;
        std::vector<std::pair<uint32, uint8>> existants;     // guid, classe
        if (auto r = CharacterDatabase.PQuery("SELECT `guid`, `class` FROM `characters` WHERE `account` = %u", compte))
        {
            do
            {
                Field* f = r->Fetch();
                existants.push_back({ f[0].GetUInt32(), f[1].GetUInt8() });
            } while (r->NextRow());
        }

        if (recreer && !existants.empty())
        {
            for (auto const& e : existants)
            {
                if (Player* p = sObjectMgr.GetPlayer(ObjectGuid(HIGHGUID_PLAYER, e.first)))
                    maitre->GetPlayerbotMgr()->LogoutPlayerBot(p->GetGUIDLow());
                Player::DeleteFromDB(ObjectGuid(HIGHGUID_PLAYER, e.first), compte, true, true);
            }
            existants.clear();
        }

        auto const& roles = Compagnons();
        if (!existants.empty())
        {
            // reconnexion des compagnons déjà créés
            for (auto const& e : existants)
            {
                Compagnon c;
                c.guid = e.first;
                c.maitre = maitre->GetGUIDLow();
                for (uint8 i = 0; i < roles.size(); ++i)
                    if (roles[i].cls == e.second)
                        c.role = i;
                c.attente = 500;
                compagnons.push_back(c);
            }
            Message(session, "Tes " + std::to_string(existants.size()) + " compagnons arrivent (.bots groupe recreer pour en refaire des neufs).");
            return true;
        }

        bool horde = maitre->GetTeam() == HORDE;
        std::set<uint64> avant;
        for (auto const& kv : sObjectAccessor.GetPlayers())
            avant.insert(kv.first.GetRawValue());

        RandomPlayerbotFactory factory(compte);
        std::vector<std::pair<Player*, uint8>> crees;
        for (uint8 i = 0; i < roles.size(); ++i)
        {
            RoleCompagnon const& r = roles[i];
            if (!factory.CreateRandomBot(r.cls, horde ? r.raceH : r.raceA))
                continue;
            for (auto const& kv : sObjectAccessor.GetPlayers())
            {
                uint64 raw = kv.first.GetRawValue();
                if (avant.count(raw))
                    continue;
                avant.insert(raw);
                Player* p = kv.second;
                if (p && p->GetSession() && p->GetSession()->GetAccountId() == compte)
                    crees.push_back({ p, i });
            }
        }

        for (auto& c : crees)
        {
            Player* p = c.first;
            p->GiveLevel(COMPAGNONS_NIVEAU);
            p->InitTalentForLevel();
            p->SetUInt32Value(PLAYER_XP, 0);
            p->SetHomebindToLocation(WorldLocation(0, SW_X, SW_Y, SW_Z, SW_O), SW_ZONE);
            p->SaveToDB();
            // apparition au point de téléportation de Hurlevent
            CharacterDatabase.PExecute("UPDATE `characters` SET `map` = 0, `position_x` = %f, `position_y` = %f, `position_z` = %f, `orientation` = %f, `zone` = %u WHERE `guid` = %u",
                SW_X, SW_Y, SW_Z, SW_O, SW_ZONE, p->GetGUIDLow());

            Compagnon k;
            k.guid = p->GetGUIDLow();
            k.maitre = maitre->GetGUIDLow();
            k.role = c.second;
            k.nouveau = true;
            k.attente = 3000;       // laisser la sauvegarde partir avant la connexion
            compagnons.push_back(k);
            sRandomPlayerbotMgr.SetValue(k.guid, "specNo", uint32(roles[c.second].premade) + 1, "", 315360000);
        }
        for (auto& c : crees)
        {
            WorldSession* s = c.first->GetSession();
            s->LogoutPlayer();
            sObjectAccessor.RemoveObject(c.first);
            delete c.first;
            delete s;
        }

        if (crees.empty())
            Message(session, "Aucun compagnon n'a pu être créé.");
        else
            Message(session, "Création de " + std::to_string(crees.size()) + " compagnons niveau 15 au point de téléportation de Hurlevent, ils arrivent dans quelques secondes.");
        return true;
    }

    void VaguesModule::SuivreCompagnons(uint32 elapsed)
    {
        if (compagnons.empty())
            return;
        timerCompagnons += elapsed;
        if (timerCompagnons < 500)
            return;
        uint32 dt = timerCompagnons;
        timerCompagnons = 0;

        for (auto it = compagnons.begin(); it != compagnons.end();)
        {
            Compagnon& c = *it;
            Player* maitre = sObjectMgr.GetPlayer(ObjectGuid(HIGHGUID_PLAYER, c.maitre));
            if (!maitre || !maitre->IsInWorld() || !maitre->GetPlayerbotMgr())
            {
                it = compagnons.erase(it);
                continue;
            }
            if (c.attente > dt)
            {
                c.attente -= dt;
                ++it;
                continue;
            }
            c.attente = 0;
            Player* bot = sObjectMgr.GetPlayer(ObjectGuid(HIGHGUID_PLAYER, c.guid));
            if (!c.connecte)
            {
                c.connecte = true;
                if (!bot)
                {
                    // un bot d'un autre compte n'est accepté que s'il est dans la même guilde que le joueur
                    ObjectGuid og(HIGHGUID_PLAYER, c.guid);
                    if (uint32 gid = maitre->GetGuildId())
                        if (Player::GetGuildIdFromDB(og) != gid)
                            if (Guild* guilde = sGuildMgr.GetGuildById(gid))
                            {
                                if (uint32 ancienne = Player::GetGuildIdFromDB(og))
                                    if (Guild* a = sGuildMgr.GetGuildById(ancienne))
                                        a->DelMember(og);
                                guilde->AddMember(og, guilde->GetLowestRank());
                            }
                    maitre->GetPlayerbotMgr()->AddPlayerBot(c.guid, maitre->GetSession()->GetAccountId());
                }
                ++it;
                continue;
            }
            if (!bot || !bot->IsInWorld() || !bot->GetPlayerbotAI())
            {
                if (++c.essais > 120)       // une minute sans connexion : abandon
                {
                    ChatHandler(maitre->GetSession()).SendSysMessage("Un compagnon n'a pas pu se connecter.");
                    it = compagnons.erase(it);
                }
                else
                    ++it;
                continue;
            }
            PreparerCompagnon(bot, maitre, c);
            it = compagnons.erase(it);
        }
    }

    void VaguesModule::PreparerCompagnon(Player* bot, Player* maitre, Compagnon const& c)
    {
        auto const& roles = Compagnons();
        RoleCompagnon const& r = roles[c.role < roles.size() ? c.role : 0];
        if (c.nouveau)
        {
            bot->learnClassLevelSpells();
            PlayerbotFactory f(bot, COMPAGNONS_NIVEAU, ITEM_QUALITY_UNCOMMON);
            f.InitSkills();

            sRandomPlayerbotMgr.SetValue(bot->GetGUIDLow(), "specNo", uint32(r.premade) + 1, "", 315360000);
            std::ostringstream out;
            ai::ChangeTalentsAction::AutoSelectTalents(bot, &out);

            // on vide les emplacements visés (et la main gauche si arme à deux mains), puis on équipe
            bool deuxMains = false;
            for (ObjetCompagnon const& o : r.objets)
                if (o.slot == EQUIPMENT_SLOT_MAINHAND)
                    if (ItemPrototype const* proto = sObjectMgr.GetItemPrototype(o.item))
                        deuxMains = proto->InventoryType == INVTYPE_2HWEAPON;
            if (deuxMains && bot->GetItemByPos(INVENTORY_SLOT_BAG_0, EQUIPMENT_SLOT_OFFHAND))
                bot->DestroyItem(INVENTORY_SLOT_BAG_0, EQUIPMENT_SLOT_OFFHAND, true);
            uint32 equipes = 0;
            for (ObjetCompagnon const& o : r.objets)
            {
                if (!sObjectMgr.GetItemPrototype(o.item))
                    continue;
                if (bot->GetItemByPos(INVENTORY_SLOT_BAG_0, o.slot))
                    bot->DestroyItem(INVENTORY_SLOT_BAG_0, o.slot, true);
                uint16 dest;
                if (bot->CanEquipNewItem(o.slot, dest, o.item, false) == EQUIP_ERR_OK && bot->EquipNewItem(dest, o.item, true))
                    ++equipes;
                else
                    sLog.outError("Compagnons : %s ne peut pas équiper l'objet %u", bot->GetName(), o.item);
            }
            f.AddFood();
            sLog.outString("Compagnons : %s (%s) prêt, %u objets équipés", bot->GetName(), r.nom, equipes);
        }

        // au point de téléportation de Hurlevent s'il n'y est pas
        if (bot->GetMapId() != 0 || bot->GetDistance(SW_X, SW_Y, SW_Z) > 30.0f)
            bot->TeleportTo(0, SW_X, SW_Y, SW_Z, SW_O);

        // dans le groupe du joueur
        Group* g = maitre->GetGroup();
        if (!g)
        {
            g = new Group();
            if (g->Create(maitre->GetObjectGuid(), maitre->GetName()))
                sObjectMgr.AddGroup(g);
            else
            {
                delete g;
                g = nullptr;
            }
        }
        if (g && !g->IsMember(bot->GetObjectGuid()))
        {
            if (bot->GetGroup())
                bot->RemoveFromGroup();
            if (g->IsFull() || !g->AddMember(bot->GetObjectGuid(), bot->GetName()))
                ChatHandler(maitre->GetSession()).SendSysMessage((std::string(bot->GetName()) + " n'a pas pu rejoindre ton groupe (groupe plein ?).").c_str());
        }
        if (PlayerbotAI* ai = bot->GetPlayerbotAI())
            ai->ResetStrategies();
        bot->SaveToDB();
        ChatHandler(maitre->GetSession()).SendSysMessage((std::string(bot->GetName()) + ", " + r.nom + ", te rejoint.").c_str());
    }

    bool VaguesModule::HandleSupprimer(WorldSession* session, const std::string& args)
    {
        uint32 v = uint32(atoi(args.c_str()));
        bool existe = false;
        for (auto const& kv : profils)
            if (kv.second.vague == v)
                existe = true;
        if (!v || !existe)
        {
            Message(session, "Usage : .bots supprimer <numéro de vague> (voir .bots info).");
            return true;
        }
        CharacterDatabase.PExecute("REPLACE INTO `custom_bot_wave_delete` (`vague`) VALUES (%u)", v);
        Message(session, "La vague " + std::to_string(v) + " sera supprimée au prochain redémarrage du serveur (.server shutdown 0 puis relance).");
        return true;
    }

    bool VaguesModule::HandleInfo(WorldSession* session, const std::string& args)
    {
        std::map<uint32, uint32> parVague;
        uint32 rythmes[4] = { 0, 0, 0, 0 }, qualites[4] = { 0, 0, 0, 0 };
        for (auto const& kv : profils)
        {
            ++parVague[kv.second.vague];
            ++rythmes[kv.second.rythme & 3];
            ++qualites[kv.second.qualite & 3];
        }
        std::ostringstream out;
        out << "Vagues présentes : " << VaguesPresentes() << " / " << VAGUES_MAX << ". Bots bloqués relancés : " << deblocages
            << ", téléportés : " << teleportations << ". Bots :";
        for (auto const& kv : parVague)
            out << " vague " << kv.first << " = " << kv.second << ";";
        Message(session, out.str());

        std::ostringstream out2;
        out2 << "Rythme : " << rythmes[0] << " " << NOM_RYTHME[0] << ", " << rythmes[1] << " " << NOM_RYTHME[1] << ", "
             << rythmes[2] << " " << NOM_RYTHME[2] << ", " << rythmes[3] << " " << NOM_RYTHME[3] << ". Jeu : "
             << qualites[0] << " " << NOM_QUALITE[0] << ", " << qualites[1] << " " << NOM_QUALITE[1] << ", "
             << qualites[2] << " " << NOM_QUALITE[2] << ", " << qualites[3] << " " << NOM_QUALITE[3] << ".";
        Message(session, out2.str());

        // profil de la cible si c'est un bot de vague
        if (session && session->GetPlayer())
        {
            ObjectGuid sel = session->GetPlayer()->GetSelectionGuid();
            if (sel.IsPlayer())
            {
                auto it = profils.find(sel.GetCounter());
                if (it != profils.end())
                    Message(session, std::string("Cible : vague ") + std::to_string(it->second.vague) + ", rythme " + NOM_RYTHME[it->second.rythme & 3]
                        + ", jeu " + NOM_QUALITE[it->second.qualite & 3] + ".");
            }
        }
        return true;
    }

    void VaguesModule::OnUpdate(uint32 elapsed)
    {
        SuivreCompagnons(elapsed);
        timerReact += elapsed;
        if (timerReact < 5000)
            return;
        timerReact = 0;
        SurveillerBots();

        for (auto const& kv : profils)
        {
            if (kv.second.reactMult == 1.0f)
                continue;
            Player* p = sObjectMgr.GetPlayer(ObjectGuid(HIGHGUID_PLAYER, kv.first));
            if (!p)
                continue;
            if (PlayerbotAI* ai = p->GetPlayerbotAI())
            {
                if (ai->GetReactMult() != kv.second.reactMult)
                    ai->SetReactMult(kv.second.reactMult);
            }
        }
    }

    // toutes les 5 s : un bot qui « court » sans avancer depuis 15 s, ou qui tourne en rond depuis 1 min (beaucoup de chemin parcouru,
    // jamais à plus de 10 m de son point de départ), est relancé (IA remise à zéro) ; s'il recommence dans les 5 min, il est téléporté
    // vers une zone de son niveau.
    void VaguesModule::SurveillerBots()
    {
        time_t now = time(nullptr);
        std::vector<std::pair<Map*, std::pair<ObjectGuid, bool>>> todo;
        std::unordered_set<uint32> vus;
        {
            HashMapHolder<Player>::ReadGuard g(HashMapHolder<Player>::GetLock());
            for (auto const& kv : HashMapHolder<Player>::GetContainer())
            {
                Player* p = kv.second;
                if (!p || !p->IsInWorld() || p->IsBeingTeleported())
                    continue;
                PlayerbotAI* ai = p->GetPlayerbotAI();
                if (!ai || ai->HasRealPlayerMaster() || !p->IsAlive() || p->IsTaxiFlying() || p->IsInCombat())
                    continue;
                uint32 guid = p->GetGUIDLow();
                vus.insert(guid);
                Suivi& s = suivis[guid];
                float x = p->GetPositionX(), y = p->GetPositionY();
                if (s.map != p->GetMapId() || s.trace.empty())
                {
                    s.map = p->GetMapId();
                    s.x = x; s.y = y;
                    s.surPlace = 0;
                    s.trace.assign(1, { x, y });
                    continue;
                }
                float d = std::sqrt((x - s.x) * (x - s.x) + (y - s.y) * (y - s.y));
                bool bouge = p->IsMoving() || !p->movespline->Finalized();
                s.surPlace = (bouge && d < 0.5f) ? s.surPlace + 1 : 0;
                s.x = x; s.y = y;
                s.trace.push_back({ x, y });
                if (s.trace.size() > 13)
                    s.trace.erase(s.trace.begin());
                bool enRond = false;
                if (s.trace.size() == 13)
                {
                    float chemin = 0, loin = 0;
                    for (size_t i = 1; i < s.trace.size(); ++i)
                    {
                        float dx = s.trace[i].first - s.trace[i - 1].first, dy = s.trace[i].second - s.trace[i - 1].second;
                        chemin += std::sqrt(dx * dx + dy * dy);
                        float ex = s.trace[i].first - s.trace[0].first, ey = s.trace[i].second - s.trace[0].second;
                        loin = std::max(loin, std::sqrt(ex * ex + ey * ey));
                    }
                    enRond = chemin > 60.0f && loin < 10.0f;
                }
                if (s.surPlace >= 3 || enRond)
                {
                    bool teleporter = s.dernierDeblocage && now - s.dernierDeblocage < 300;
                    s.dernierDeblocage = now;
                    s.surPlace = 0;
                    s.trace.clear();
                    if (Map* map = p->GetMap())
                        todo.push_back({ map, { p->GetObjectGuid(), teleporter } });
                }
            }
        }
        for (auto it = suivis.begin(); it != suivis.end();)
            it = vus.count(it->first) ? std::next(it) : suivis.erase(it);
        for (auto const& t : todo)
        {
            ObjectGuid guid = t.second.first;
            bool teleporter = t.second.second;
            if (teleporter)
                ++teleportations;
            else
                ++deblocages;
            t.first->GetMessager().AddMessage([guid, teleporter](Map* map)
            {
                Player* p = map->GetPlayer(guid);
                if (!p || !p->IsInWorld() || !p->GetPlayerbotAI())
                    return;
                p->GetMotionMaster()->Clear(false);              // garde le mouvement de repos (pile jamais vide)
                p->StopMoving(true);
                if (teleporter)
                    sRandomPlayerbotMgr.RandomTeleportForLevel(p, false);
                else
                    p->GetPlayerbotAI()->Reset();
            });
        }
    }

    bool VaguesModule::OnPreGiveXP(Player* player, uint32& xp, Creature* victim)
    {
        if (!player || !xp)
            return false;
        float mult = 1.0f;
        auto it = profils.find(player->GetObjectGuid().GetCounter());
        if (it != profils.end())
            mult = it->second.xpMult;               // rythme du bot de vague
        if (player->GetPlayerbotAI())
            mult *= VAGUES_BONUS_XP_BOTS;           // tous les bots : expérience x1,25
        if (mult == 1.0f)
            return false;
        xp = std::max(1u, uint32(xp * mult + 0.5f));
        return false;
    }
}
