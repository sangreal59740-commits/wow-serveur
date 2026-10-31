#include "VaguesModule.h"

#include "Accounts/AccountMgr.h"
#include "Chat/Chat.h"
#include "Database/DatabaseEnv.h"
#include "Entities/Player.h"
#include "Globals/ObjectAccessor.h"
#include "Globals/ObjectMgr.h"
#include "Log/Log.h"
#include "Server/WorldSession.h"
#include "Util/Util.h"

#include "playerbot/playerbot.h"
#include "playerbot/PlayerbotAI.h"
#include "playerbot/PlayerbotAIConfig.h"
#include "playerbot/RandomPlayerbotFactory.h"
#include "playerbot/RandomPlayerbotMgr.h"

#include <cstdlib>
#include <functional>
#include <map>
#include <set>
#include <sstream>

namespace cmangos_module
{
    struct Combinaison { uint8 race; uint8 cls; };

    // 19 combinaisons race / classe par faction (druide exclu : remplace par le Metamorphe, joueur uniquement)
    static const Combinaison ALLIANCE[] =
    {
        { 1, 1 }, { 1, 2 }, { 1, 4 }, { 1, 5 }, { 1, 8 }, { 1, 9 },     // Humain
        { 3, 1 }, { 3, 2 }, { 3, 3 }, { 3, 4 }, { 3, 5 },               // Nain
        { 4, 1 }, { 4, 3 }, { 4, 4 }, { 4, 5 },                         // Elfe de la nuit
        { 7, 1 }, { 7, 4 }, { 7, 8 }, { 7, 9 },                         // Gnome
    };
    static const Combinaison HORDE[] =
    {
        { 2, 1 }, { 2, 3 }, { 2, 4 }, { 2, 7 }, { 2, 9 },               // Orc
        { 5, 1 }, { 5, 4 }, { 5, 5 }, { 5, 8 }, { 5, 9 },               // Mort-vivant
        { 6, 1 }, { 6, 3 }, { 6, 7 },                                   // Tauren
        { 8, 1 }, { 8, 3 }, { 8, 4 }, { 8, 5 }, { 8, 7 }, { 8, 8 },     // Troll
    };

    // Specialisations pre-faites d'aiplayerbot.conf (PremadeSpecName.<classe>.<id>), une par arbre
    static void SpecsDeClasse(uint8 cls, uint32 out[3])
    {
        switch (cls)
        {
            case 1: out[0] = 0; out[1] = 1; out[2] = 2; break;     // armes, fureur, protection
            case 2: out[0] = 2; out[1] = 9; out[2] = 0; break;     // sacre, protection, vindicte
            case 3: out[0] = 3; out[1] = 4; out[2] = 5; break;     // betes, precision, survie
            case 4: out[0] = 2; out[1] = 0; out[2] = 9; break;     // assassinat, combat, finesse
            case 5: out[0] = 0; out[1] = 1; out[2] = 2; break;     // discipline, sacre, ombre
            case 7: out[0] = 0; out[1] = 8; out[2] = 3; break;     // elementaire, amelioration, restauration
            case 8: out[0] = 0; out[1] = 1; out[2] = 8; break;     // arcanes, feu, givre
            case 9: out[0] = 4; out[1] = 0; out[2] = 2; break;     // affliction, demonologie, destruction
            default: out[0] = 0; out[1] = 1; out[2] = 2; break;
        }
    }

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
        };
        return &commandTable;
    }

    bool VaguesModule::HandleVague(WorldSession* session, const std::string& args)
    {
        uint32 vague = NombreVagues() + 1;
        if (VaguesPresentes() >= VAGUES_MAX)
        {
            Message(session, "Il y a déjà 5 vagues. Supprime-en une avec .bots supprimer <numéro>.");
            return true;
        }

        // Liste des bots a creer : chaque combinaison race / classe / spe, VAGUES_COPIES fois, pour les deux factions
        struct Tache { uint8 race; uint8 cls; uint32 spec; };
        std::vector<Tache> taches;
        for (int faction = 0; faction < 2; ++faction)
        {
            const Combinaison* liste = faction == 0 ? ALLIANCE : HORDE;
            uint32 n = faction == 0 ? sizeof(ALLIANCE) / sizeof(ALLIANCE[0]) : sizeof(HORDE) / sizeof(HORDE[0]);
            for (uint32 i = 0; i < n; ++i)
            {
                uint32 specs[3];
                SpecsDeClasse(liste[i].cls, specs);
                for (uint32 s = 0; s < 3; ++s)
                    for (uint32 c = 0; c < VAGUES_COPIES; ++c)
                        taches.push_back({ liste[i].race, liste[i].cls, specs[s] });
            }
        }

        Message(session, "Création de la vague " + std::to_string(vague) + " (" + std::to_string(taches.size()) + " bots niveau 1)...");

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
            c.player->SaveToDB();

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
            // specialisation imposee (valable 10 ans)
            sRandomPlayerbotMgr.SetValue(guid, "specNo", c.tache.spec + 1, "", 315360000);
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
        out << "Vague " << vague << " créée : " << crees.size() << " bots niveau 1 sur " << taches.size() << " prévus. Ils se connectent dans les prochaines minutes."
            << " Rythme : " << rythmes[0] << " lents, " << rythmes[1] << " normaux, " << rythmes[2] << " rapides, " << rythmes[3] << " très rapides."
            << " Jeu : " << qualites[0] << " experts, " << qualites[1] << " bons, " << qualites[2] << " moyens, " << qualites[3] << " débutants.";
        Message(session, out.str());
        if (crees.size() < taches.size())
            Message(session, "Attention : certains bots n'ont pas pu être créés (comptes pleins ou noms épuisés).");
        return true;
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
        out << "Vagues présentes : " << VaguesPresentes() << " / " << VAGUES_MAX << ". Bots :";
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
        timerReact += elapsed;
        if (timerReact < 5000)
            return;
        timerReact = 0;

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

    bool VaguesModule::OnPreGiveXP(Player* player, uint32& xp, Creature* victim)
    {
        if (!player || !xp)
            return false;
        auto it = profils.find(player->GetObjectGuid().GetCounter());
        if (it == profils.end() || it->second.xpMult == 1.0f)
            return false;
        xp = std::max(1u, uint32(xp * it->second.xpMult + 0.5f));
        return false;
    }
}
