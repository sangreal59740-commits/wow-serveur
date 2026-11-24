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
#include "playerbot/AiFactory.h"
#include "playerbot/strategy/generic/PullStrategy.h"
#include "Grids/GridNotifiers.h"
#include "Grids/GridNotifiersImpl.h"
#include "Grids/CellImpl.h"
#include "Tools/Formulas.h"
#include <mutex>
#include "playerbot/strategy/actions/ChangeTalentsAction.h"

#include <cmath>
#include <cstdlib>
#include <unordered_set>
#include <functional>
#include <map>
#include <set>
#include <sstream>

// rôle imposé aux bots (défini dans playerbot, rempli par le module classes)
extern std::function<int(Player const*)> gRoleCustom;

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


    // Groupes de compagnons (.bots groupe 1 à 5) : niveau 20, équipement bleu (vert quand aucun bleu n'existe pour l'emplacement),
    // arme comprise, sans anneau, bijou ni artefact. Objets choisis par wow/compagnons/choix20.py sur la base classicmangos.
    struct ObjetCompagnon { uint8 slot; uint32 item; };
    static const ObjetCompagnon OBJ_GUERRIER_TANK[] = { { 1, 20442 }, { 2, 3231 }, { 4, 6642 }, { 5, 6460 }, { 6, 10410 }, { 7, 12982 }, { 8, 12999 }, { 9, 12994 }, { 14, 2059 }, { 15, 2194 }, { 16, 12997 }, { 17, 3021 } };
    static const ObjetCompagnon OBJ_GUERRIER_BERSERK[] = { { 1, 20442 }, { 2, 3231 }, { 4, 10399 }, { 5, 6460 }, { 6, 10410 }, { 7, 1121 }, { 8, 12999 }, { 9, 12994 }, { 14, 5193 }, { 15, 23171 }, { 17, 3021 } };
    static const ObjetCompagnon OBJ_PALADIN_SOLEIL[] = { { 1, 20442 }, { 2, 3231 }, { 4, 6642 }, { 5, 6460 }, { 6, 10410 }, { 7, 12982 }, { 8, 12999 }, { 9, 12994 }, { 14, 20427 }, { 15, 2194 }, { 16, 6630 } };
    static const ObjetCompagnon OBJ_VOLEUR_FANTOME[] = { { 1, 20442 }, { 2, 4709 }, { 4, 10399 }, { 5, 3429 }, { 6, 10410 }, { 7, 1121 }, { 8, 12999 }, { 9, 3058 }, { 14, 5193 }, { 15, 1935 }, { 16, 20441 }, { 17, 3021 } };
    static const ObjetCompagnon OBJ_PRETRE_SOIN[] = { { 1, 20442 }, { 2, 12998 }, { 4, 2292 }, { 5, 2911 }, { 6, 12987 }, { 7, 14374 }, { 8, 1974 }, { 9, 12977 }, { 14, 20427 }, { 15, 5201 }, { 17, 5198 } };
    static const ObjetCompagnon OBJ_NECRO[] = { { 1, 20442 }, { 2, 12998 }, { 4, 2292 }, { 5, 2911 }, { 6, 23173 }, { 7, 14374 }, { 8, 1974 }, { 9, 12977 }, { 14, 20427 }, { 15, 890 }, { 17, 5198 } };
    static const ObjetCompagnon OBJ_SNIPER[] = { { 1, 20442 }, { 2, 4709 }, { 4, 10399 }, { 5, 3429 }, { 6, 10410 }, { 7, 1121 }, { 8, 12999 }, { 9, 3058 }, { 14, 5193 }, { 15, 20425 }, { 17, 3021 } };
    static const ObjetCompagnon OBJ_META_SOIN[] = { { 1, 20442 }, { 2, 4709 }, { 4, 1489 }, { 5, 14559 }, { 6, 10410 }, { 7, 1121 }, { 8, 12999 }, { 9, 1945 }, { 14, 20427 }, { 15, 5201 } };
    static const ObjetCompagnon OBJ_META_TANK[] = { { 1, 20442 }, { 2, 4709 }, { 4, 10399 }, { 5, 3429 }, { 6, 10410 }, { 7, 1121 }, { 8, 12999 }, { 9, 3058 }, { 14, 2059 }, { 15, 20425 } };
    static const ObjetCompagnon OBJ_META_DPS[] = { { 1, 20442 }, { 2, 4709 }, { 4, 10399 }, { 5, 5975 }, { 6, 10410 }, { 7, 1121 }, { 8, 12999 }, { 9, 14572 }, { 14, 5193 }, { 15, 7230 } };
    static const ObjetCompagnon OBJ_CHAMAN_TANK[] = { { 1, 20442 }, { 2, 4709 }, { 4, 10399 }, { 5, 3429 }, { 6, 10410 }, { 7, 1121 }, { 8, 12999 }, { 9, 3058 }, { 14, 2059 }, { 15, 2194 }, { 16, 12997 } };
    static const ObjetCompagnon OBJ_MAGE_SOIN[] = { { 1, 20442 }, { 2, 12998 }, { 4, 2292 }, { 5, 2911 }, { 6, 12987 }, { 7, 14374 }, { 8, 1974 }, { 9, 12977 }, { 14, 20427 }, { 15, 5201 }, { 17, 5198 } };

    struct MembreGroupe
    {
        uint8 cls, raceA, raceH;
        int32 premade;      // spé pré-faite d'aiplayerbot.conf, ou -1
        int32 arbre;        // arbre de talents imposé (module classes), ou -1
        const char* nom;
        const ObjetCompagnon* objets;
        uint32 nObjets;
    };
    #define OBJS(x) OBJ_##x, uint32(sizeof(OBJ_##x) / sizeof(OBJ_##x[0]))
    static const uint32 COMPAGNONS_NIVEAU = 20;
    static const char* COMPAGNONS_COMPTE = "COMPAGNONS";
    static const std::vector<std::vector<MembreGroupe>>& GroupesCompagnons()
    {
        static const std::vector<std::vector<MembreGroupe>> v =
        {
            {   // 1
                { 1, 3, 2, 2, -1, "guerrier Protection (tank)", OBJS(GUERRIER_TANK) },
                { 11, 4, 6, -1, 0, "métamorphe Totémique (soin)", OBJS(META_SOIN) },
            },
            {   // 2
                { 11, 4, 6, -1, 2, "métamorphe Angélique (tank)", OBJS(META_TANK) },
                { 5, 1, 8, 1, -1, "prêtre Sacré (soin)", OBJS(PRETRE_SOIN) },
            },
            {   // 3
                { 5, 4, 8, 1, -1, "prêtre Sacré (soin)", OBJS(PRETRE_SOIN) },
                { 6, 1, 5, -1, 0, "nécromancien Invocateur", OBJS(NECRO) },
                { 10, 3, 2, -1, 2, "sniper Mécanisme", OBJS(SNIPER) },
                { 11, 7, 8, -1, 1, "métamorphe Druidique (DPS)", OBJS(META_DPS) },
            },
            {   // 4
                { 1, 1, 2, 2, -1, "guerrier Protection (tank)", OBJS(GUERRIER_TANK) },
                { 2, 1, 5, -1, 3, "paladin Soleil", OBJS(PALADIN_SOLEIL) },
                { 4, 7, 2, -1, 3, "voleur Fantôme", OBJS(VOLEUR_FANTOME) },
                { 5, 1, 5, -1, 3, "prêtre Corrompu (soin)", OBJS(PRETRE_SOIN) },
            },
            {   // 5
                { 7, 3, 6, -1, 3, "chaman Ruines (tank)", OBJS(CHAMAN_TANK) },
                { 8, 7, 8, -1, 3, "mage Nature (soin)", OBJS(MAGE_SOIN) },
                { 1, 3, 2, -1, 3, "guerrier Berserker", OBJS(GUERRIER_BERSERK) },
                { 6, 1, 5, -1, 2, "nécromancien Magicien", OBJS(NECRO) },
            },
        };
        return v;
    }
    #undef OBJS

    // compétence et sort de maniement d'un objet (pour que le compagnon puisse le porter)
    static void Proficience(ItemPrototype const* proto, uint32& skill, uint32& spell)
    {
        skill = 0; spell = 0;
        if (proto->Class == ITEM_CLASS_WEAPON)
        {
            static const uint32 sk[20] = { SKILL_AXES, SKILL_2H_AXES, SKILL_BOWS, SKILL_GUNS, SKILL_MACES, SKILL_2H_MACES, SKILL_POLEARMS, SKILL_SWORDS,
                SKILL_2H_SWORDS, 0, SKILL_STAVES, 0, 0, SKILL_UNARMED, 0, SKILL_DAGGERS, SKILL_THROWN, 0, SKILL_CROSSBOWS, SKILL_WANDS };
            static const uint32 sp[20] = { 196, 197, 264, 266, 198, 199, 200, 201, 202, 0, 227, 0, 0, 15590, 0, 1180, 2567, 0, 5011, 5009 };
            if (proto->SubClass < 20) { skill = sk[proto->SubClass]; spell = sp[proto->SubClass]; }
        }
        else if (proto->Class == ITEM_CLASS_ARMOR)
        {
            switch (proto->SubClass)
            {
                case 1: skill = SKILL_CLOTH; spell = 9078; break;
                case 2: skill = SKILL_LEATHER; spell = 9077; break;
                case 3: skill = SKILL_MAIL; spell = 8737; break;
                case 6: skill = SKILL_SHIELD; spell = 9116; break;
            }
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
            { "pull", std::bind(&VaguesModule::HandlePull, this, std::placeholders::_1, std::placeholders::_2), SEC_PLAYER },
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

    // .bots groupe <1 à 5> : remplace les compagnons actuels par le groupe choisi, niveau 20, sur le joueur et dans son groupe.
    bool VaguesModule::HandleGroupe(WorldSession* session, const std::string& args)
    {
        Player* maitre = session ? session->GetPlayer() : nullptr;
        if (!maitre || !maitre->GetPlayerbotMgr())
        {
            Message(session, "Cette commande se lance en jeu, depuis ton personnage.");
            return true;
        }
        auto const& groupes = GroupesCompagnons();
        int n = args.empty() ? 0 : atoi(args.c_str());
        if (n < 1 || n > int(groupes.size()))
        {
            Message(session, "Usage : .bots groupe <1 à 5>");
            Message(session, "1 : guerrier tank, métamorphe soin");
            Message(session, "2 : métamorphe tank, prêtre soin");
            Message(session, "3 : prêtre soin, nécromancien Invocateur, sniper Mécanisme, métamorphe DPS");
            Message(session, "4 : guerrier tank, paladin Soleil, voleur Fantôme, prêtre Corrompu");
            Message(session, "5 : chaman Ruines (tank), mage Nature (soin), guerrier Berserker, nécromancien Magicien");
            return true;
        }
        if (demandeGroupe || !compagnons.empty())
        {
            Message(session, "Des compagnons sont déjà en route, patiente quelques secondes.");
            return true;
        }
        demandeGroupe = uint32(n);
        demandeMaitre = maitre->GetGUIDLow();
        demandeAttente = 0;
        Message(session, "Groupe " + std::to_string(n) + " : je renvoie les anciens compagnons et je prépare les nouveaux.");
        return true;
    }

    // étape 1 : déconnecter les anciens compagnons ; étape 2 : les supprimer et créer le nouveau groupe
    void VaguesModule::RemplacerCompagnons(uint32 dt)
    {
        Player* maitre = sObjectMgr.GetPlayer(ObjectGuid(HIGHGUID_PLAYER, demandeMaitre));
        if (!maitre || !maitre->IsInWorld() || !maitre->GetPlayerbotMgr())
        {
            demandeGroupe = 0;
            return;
        }
        uint32 compte = sAccountMgr.GetId(COMPAGNONS_COMPTE);
        if (!compte)
        {
            sAccountMgr.CreateAccount(COMPAGNONS_COMPTE, "compagnons");
            compte = sAccountMgr.GetId(COMPAGNONS_COMPTE);
        }
        if (!compte)
        {
            Message(maitre->GetSession(), "Impossible de créer le compte COMPAGNONS.");
            demandeGroupe = 0;
            return;
        }

        std::vector<uint32> anciens;
        if (auto r = CharacterDatabase.PQuery("SELECT `guid` FROM `characters` WHERE `account` = %u", compte))
        {
            do anciens.push_back(r->Fetch()[0].GetUInt32()); while (r->NextRow());
        }
        bool enLigne = false;
        for (uint32 g : anciens)
            if (Player* p = sObjectMgr.GetPlayer(ObjectGuid(HIGHGUID_PLAYER, g)))
            {
                enLigne = true;
                if (p->GetPlayerbotAI() && p->GetPlayerbotAI()->GetMaster() && p->GetPlayerbotAI()->GetMaster()->GetPlayerbotMgr())
                    p->GetPlayerbotAI()->GetMaster()->GetPlayerbotMgr()->LogoutPlayerBot(p->GetGUIDLow());
                else
                    maitre->GetPlayerbotMgr()->LogoutPlayerBot(p->GetGUIDLow());
            }
        if (enLigne)
        {
            demandeAttente += dt;
            if (demandeAttente > 20000)
            {
                Message(maitre->GetSession(), "Les anciens compagnons ne se déconnectent pas, réessaie dans un moment.");
                demandeGroupe = 0;
            }
            return;         // on attend qu'ils soient partis
        }
        for (uint32 g : anciens)
        {
            Player::DeleteFromDB(ObjectGuid(HIGHGUID_PLAYER, g), compte, true, true);
            CharacterDatabase.PExecute("DELETE FROM `custom_bot_arbre` WHERE `guid` = %u", g);
        }

        auto const& membres = GroupesCompagnons()[demandeGroupe - 1];
        bool horde = maitre->GetTeam() == HORDE;
        std::set<uint64> avant;
        for (auto const& kv : sObjectAccessor.GetPlayers())
            avant.insert(kv.first.GetRawValue());

        RandomPlayerbotFactory factory(compte);
        std::vector<std::pair<Player*, uint8>> crees;
        for (uint8 i = 0; i < membres.size(); ++i)
        {
            MembreGroupe const& m = membres[i];
            if (!factory.CreateRandomBot(m.cls, horde ? m.raceH : m.raceA))
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

        float x = maitre->GetPositionX(), y = maitre->GetPositionY(), z = maitre->GetPositionZ(), o = maitre->GetOrientation();
        uint32 mapId = maitre->GetMapId(), zone = maitre->GetZoneId();
        for (auto& c : crees)
        {
            Player* p = c.first;
            MembreGroupe const& m = membres[c.second];
            p->GiveLevel(COMPAGNONS_NIVEAU);
            p->InitTalentForLevel();
            p->SetUInt32Value(PLAYER_XP, 0);
            p->SaveToDB();
            // apparition sur le joueur
            CharacterDatabase.PExecute("UPDATE `characters` SET `map` = %u, `position_x` = %f, `position_y` = %f, `position_z` = %f, `orientation` = %f, `zone` = %u WHERE `guid` = %u",
                mapId, x, y, z, o, zone, p->GetGUIDLow());

            Compagnon k;
            k.guid = p->GetGUIDLow();
            k.maitre = maitre->GetGUIDLow();
            k.groupe = uint8(demandeGroupe);
            k.role = c.second;
            k.nouveau = true;
            k.attente = 3000;       // laisser la sauvegarde partir avant la connexion
            compagnons.push_back(k);
            if (m.premade >= 0)
                sRandomPlayerbotMgr.SetValue(k.guid, "specNo", uint32(m.premade) + 1, "", 315360000);
            else
            {
                sRandomPlayerbotMgr.SetValue(k.guid, "specNo", 0, "", 315360000);
                CharacterDatabase.PExecute("REPLACE INTO `custom_bot_arbre` (`guid`, `arbre`) VALUES (%u, %u)", k.guid, uint32(m.arbre));
            }
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
            Message(maitre->GetSession(), "Aucun compagnon n'a pu être créé.");
        else
            Message(maitre->GetSession(), "Groupe " + std::to_string(demandeGroupe) + " : " + std::to_string(crees.size()) + " compagnons niveau 20 arrivent sur toi.");
        demandeGroupe = 0;
    }

    void VaguesModule::SuivreCompagnons(uint32 elapsed)
    {
        timerCompagnons += elapsed;
        if (timerCompagnons < 500)
            return;
        uint32 dt = timerCompagnons;
        timerCompagnons = 0;

        if (demandeGroupe)
        {
            RemplacerCompagnons(dt);
            return;
        }

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
        auto const& groupes = GroupesCompagnons();
        if (c.groupe < 1 || c.groupe > groupes.size() || c.role >= groupes[c.groupe - 1].size())
            return;
        MembreGroupe const& m = groupes[c.groupe - 1][c.role];
        if (c.nouveau)
        {
            bot->learnClassLevelSpells();
            PlayerbotFactory f(bot, COMPAGNONS_NIVEAU, ITEM_QUALITY_RARE);
            f.InitSkills();

            if (m.premade >= 0)
            {
                sRandomPlayerbotMgr.SetValue(bot->GetGUIDLow(), "specNo", uint32(m.premade) + 1, "", 315360000);
                std::ostringstream out;
                ai::ChangeTalentsAction::AutoSelectTalents(bot, &out);
            }
            // arbre imposé : rempli par le module classes (table custom_bot_arbre)

            // on vide les emplacements visés (et la main gauche si arme à deux mains), puis on équipe
            bool deuxMains = false;
            for (uint32 i = 0; i < m.nObjets; ++i)
                if (m.objets[i].slot == EQUIPMENT_SLOT_MAINHAND)
                    if (ItemPrototype const* proto = sObjectMgr.GetItemPrototype(m.objets[i].item))
                        deuxMains = proto->InventoryType == INVTYPE_2HWEAPON;
            if (deuxMains && bot->GetItemByPos(INVENTORY_SLOT_BAG_0, EQUIPMENT_SLOT_OFFHAND))
                bot->DestroyItem(INVENTORY_SLOT_BAG_0, EQUIPMENT_SLOT_OFFHAND, true);
            uint32 equipes = 0;
            for (uint32 i = 0; i < m.nObjets; ++i)
            {
                ObjetCompagnon const& o = m.objets[i];
                ItemPrototype const* proto = sObjectMgr.GetItemPrototype(o.item);
                if (!proto)
                    continue;
                // maniement de l'arme ou de l'armure si le personnage ne l'a pas encore
                uint32 skill, spell;
                Proficience(proto, skill, spell);
                if (skill && !bot->HasSkill(skill))
                {
                    if (spell)
                        bot->learnSpell(spell, false);
                    if (!bot->HasSkill(skill))
                        bot->SetSkill(skill, COMPAGNONS_NIVEAU * 5, COMPAGNONS_NIVEAU * 5);
                }
                if (bot->GetItemByPos(INVENTORY_SLOT_BAG_0, o.slot))
                    bot->DestroyItem(INVENTORY_SLOT_BAG_0, o.slot, true);
                uint16 dest;
                if (bot->CanEquipNewItem(o.slot, dest, o.item, false) == EQUIP_ERR_OK && bot->EquipNewItem(dest, o.item, true))
                    ++equipes;
                else
                    sLog.outError("Compagnons : %s ne peut pas équiper l'objet %u", bot->GetName(), o.item);
            }
            f.AddFood();
            f.AddPotions();
            f.AddReagents();
            f.InitAmmo();
            sLog.outString("Compagnons : %s (%s) prêt, %u objets équipés", bot->GetName(), m.nom, equipes);
        }

        // sur le joueur s'il n'y est pas déjà
        if (bot->GetMapId() != maitre->GetMapId() || bot->GetDistance(maitre) > 30.0f)
            bot->TeleportTo(maitre->GetMapId(), maitre->GetPositionX(), maitre->GetPositionY(), maitre->GetPositionZ(), maitre->GetOrientation());

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
        ChatHandler(maitre->GetSession()).SendSysMessage((std::string(bot->GetName()) + ", " + m.nom + ", te rejoint.").c_str());
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
        timerPilote += elapsed;
        timerZones += elapsed;
        if (timerPilote >= 1000)
        {
            timerPilote = 0;
            bool zones = timerZones >= 30000;
            if (zones)
                timerZones = 0;
            PiloterBots(zones);
        }
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

    // ------------------------------------------------------------------ pilotage des bots
    // Soigneurs : n'attaquent plus sous 60 % de mana (reprennent à 65 %).
    // Tanks : prennent l'initiative de pull quand le groupe est prêt (hors combat, vie et mana remontées).
    // Rôles : si la stratégie ne correspond plus au rôle (arbre imposé chargé après la connexion), l'IA est réinitialisée.
    // Zones : un bot de vague trop haut niveau pour sa zone (zone de départ comprise) part dans une zone de son niveau.
    static std::mutex piloteLock;
    static std::unordered_map<uint32, time_t> dernierPull, dernierReset, dernierDepart;
    static std::set<uint32> pullAutoOff;            // joueurs qui ont coupé le pull automatique de leur tank
    static std::unordered_map<uint32, uint32> niveauCompagnon;

    static uint32 PctMana(Player* p)
    {
        if (p->GetPowerType() != POWER_MANA || !p->GetMaxPower(POWER_MANA))
            return 100;
        return p->GetPower(POWER_MANA) * 100 / p->GetMaxPower(POWER_MANA);
    }

    // niveau au-delà duquel un bot n'a plus rien à faire dans la zone (zones de départ et zones du monde)
    static uint32 NiveauMaxZone(uint32 zone, uint32 area)
    {
        switch (area)
        {
            case 9: case 132: case 188: case 363: case 154: case 220:   // vallées de départ (niveaux 1 à 5)
                return 6;
        }
        switch (zone)
        {
            case 12: case 1: case 141: case 14: case 85: case 215: return 12;       // Elwynn, Dun Morogh, Teldrassil, Durotar, Tirisfal, Mulgore
            case 40: case 38: case 148: case 130: return 20;                        // Marche de l'Ouest, Loch Modan, Sombrivage, Forêt des Pins-Argentés
            case 17: case 44: case 406: return 25;                                  // Tarides, Les Carmines, Les Serres-Rocheuses
            case 10: case 11: case 331: return 30;                                  // Bois de la Pénombre, Les Paluns, Orneval
            case 267: return 32;                                                    // Contreforts de Hautebrande
            case 400: return 35;                                                    // Mille pointes
            case 45: case 36: case 405: return 40;                                  // Hautes-terres d'Arathi, Montagnes d'Alterac, Désolace
            case 15: case 33: case 3: case 8: return 45;                            // Marécage d'Âprefange, Strangleronce, Terres ingrates, Marais des Chagrins
            case 357: case 440: case 47: case 51: return 50;                        // Féralas, Tanaris, Hinterlands, Gorge des Vents brûlants
            case 16: case 361: case 490: case 4: return 55;                         // Azshara, Gangrebois, Cratère d'Un'Goro, Terres foudroyées
            case 46: return 58;                                                     // Steppes ardentes
        }
        return 0;
    }

    static bool GroupeAvecVraiJoueur(Player* p)
    {
        Group* g = p->GetGroup();
        if (!g)
            return false;
        for (GroupReference* ref = g->GetFirstMember(); ref; ref = ref->next())
            if (Player* m = ref->getSource())
                if (!m->GetPlayerbotAI())
                    return true;
        return false;
    }

    // cible de pull : monstre hostile le plus proche (30 m), pas gris, pas déjà engagé par d'autres
    static Creature* CibleDePull(Player* tank)
    {
        std::list<Unit*> liste;
        MaNGOS::AnyUnfriendlyUnitInObjectRangeCheck check(tank, 30.0f);
        MaNGOS::UnitListSearcher<MaNGOS::AnyUnfriendlyUnitInObjectRangeCheck> searcher(liste, check);
        Cell::VisitAllObjects(tank, searcher, 30.0f);
        uint32 gris = MaNGOS::XP::GetGrayLevel(tank->GetLevel());
        Creature* best = nullptr;
        float bestDist = 1000.0f;
        for (Unit* u : liste)
        {
            if (u->GetTypeId() != TYPEID_UNIT)
                continue;
            Creature* c = static_cast<Creature*>(u);
            if (!c->IsAlive() || c->IsCritter() || c->IsCivilian() || c->IsTotem() || c->IsPet() || c->IsInCombat())
                continue;
            if (c->GetLevel() <= gris || c->GetLevel() > tank->GetLevel() + 3)
                continue;
            if (!c->CanAttackOnSight(tank))         // seulement les monstres agressifs (les packs)
                continue;
            if (c->HasLootRecipient() && !c->IsTappedBy(tank))
                continue;
            if (std::fabs(c->GetPositionZ() - tank->GetPositionZ()) > 8.0f)
                continue;
            float d = tank->GetDistance(c);
            if (d < bestDist)
            {
                bestDist = d;
                best = c;
            }
        }
        return best;
    }

    // le tank va chercher la cible (stratégie « pull » si sa classe en a une, sinon il fonce dessus)
    static bool LancerPull(Player* tank, Unit* cible, Player* demandeur)
    {
        PlayerbotAI* ai = tank->GetPlayerbotAI();
        if (!ai || !cible)
            return false;
        ai::PullStrategy* ps = ai::PullStrategy::Get(ai);
        if (ps && ps->CanDoPullAction(cible))
            if (ai->DoSpecificAction("pull my target", Event("attack anything", cible->GetObjectGuid(), demandeur), true))
                return true;
        tank->SetSelectionGuid(cible->GetObjectGuid());
        tank->Attack(cible, true);
        tank->GetMotionMaster()->MoveChase(cible);
        return true;
    }

    static void PiloterUnBot(Player* p, bool zones, bool estCompagnon)
    {
        PlayerbotAI* ai = p->GetPlayerbotAI();
        if (!ai || !p->IsInWorld() || !p->IsAlive() || p->IsBeingTeleported())
            return;
        time_t now = time(nullptr);
        uint32 guid = p->GetGUIDLow();
        BotRoles role = AiFactory::GetPlayerRoles(p);
        bool tank = (role & BOT_ROLE_TANK) != 0;
        bool soin = !tank && (role & BOT_ROLE_HEALER) != 0;

        // rôle imposé (4e spé, classe custom) pas encore appliqué : on réinitialise l'IA (au plus une fois par minute)
        int custom = gRoleCustom ? gRoleCustom(p) : -1;
        bool aTank = ai->HasStrategy("tank assist", BotState::BOT_STATE_COMBAT);
        if (custom >= 0 && aTank != (custom == 0))
        {
            std::lock_guard<std::mutex> g(piloteLock);
            time_t& t = dernierReset[guid];
            if (now - t >= 60)
            {
                t = now;
                ai->ResetStrategies();
                return;
            }
        }

        // soigneur : pas d'attaque sous 60 % de mana
        if (soin)
        {
            uint32 mana = PctMana(p);
            bool dps = ai->HasStrategy("dps assist", BotState::BOT_STATE_COMBAT);
            if (mana < 60 && dps)
                ai->ChangeStrategy("-dps assist,-offdps", BotState::BOT_STATE_COMBAT);
            else if (mana >= 65 && !dps)
                ai->ChangeStrategy("+dps assist", BotState::BOT_STATE_COMBAT);
        }

        // tank : pull quand le groupe est prêt
        if (tank && p->GetGroup() && !p->IsInCombat() && !p->IsMounted() && !p->IsTaxiFlying() && p->GetHealthPercent() >= 80.0f)
        {
            Group* grp = p->GetGroup();
            Player* chef = sObjectMgr.GetPlayer(grp->GetLeaderGuid());
            bool pret = chef && chef->IsInWorld() && chef->GetMap() == p->GetMap() && chef->IsAlive() && !chef->IsMounted()
                && !chef->IsTaxiFlying() && !chef->HasFlag(PLAYER_FLAGS, PLAYER_FLAGS_RESTING) && p->GetDistance(chef) <= 25.0f;
            if (pret && !chef->GetPlayerbotAI())
            {
                std::lock_guard<std::mutex> g(piloteLock);
                pret = !pullAutoOff.count(chef->GetGUIDLow());
            }
            if (pret)
                for (GroupReference* ref = grp->GetFirstMember(); ref && pret; ref = ref->next())
                {
                    Player* m = ref->getSource();
                    if (!m || m == p)
                        continue;
                    if (!m->IsInWorld() || m->GetMap() != p->GetMap() || p->GetDistance(m) > 50.0f)
                        continue;
                    if (!m->IsAlive() || m->IsInCombat() || m->GetHealthPercent() < 70.0f)
                        pret = false;
                    else if (m->GetPlayerbotAI() && (AiFactory::GetPlayerRoles(m) & BOT_ROLE_HEALER) && PctMana(m) < 60)
                        pret = false;
                }
            if (pret)
            {
                bool go = false;
                {
                    std::lock_guard<std::mutex> g(piloteLock);
                    time_t& t = dernierPull[guid];
                    if (now - t >= 8)
                    {
                        t = now;
                        go = true;
                    }
                }
                if (go)
                    if (Creature* c = CibleDePull(p))
                        LancerPull(p, c, chef);
            }
        }

        // compagnons : meilleur équipement à chaque niveau gagné
        if (estCompagnon)
        {
            uint32 niveau = p->GetLevel();
            bool monte = false;
            {
                std::lock_guard<std::mutex> g(piloteLock);
                uint32& n = niveauCompagnon[guid];
                if (n && niveau > n)
                    monte = true;
                n = niveau;
            }
            if (monte && !p->IsInCombat())
            {
                PlayerbotFactory f(p, niveau, ITEM_QUALITY_UNCOMMON);
                f.UpgradeGear(false);
                f.AddFood();
                f.AddPotions();
                f.AddReagents();
            }
        }

        // bot de vague trop fort pour sa zone : direction une zone de son niveau (au plus toutes les 10 min)
        if (zones && !estCompagnon && !p->IsInCombat() && !GroupeAvecVraiJoueur(p) && !p->GetMap()->IsDungeon() && !p->InBattleGround())
        {
            uint32 zone, area;
            p->GetZoneAndAreaId(zone, area);
            uint32 max = NiveauMaxZone(zone, area);
            if (max && p->GetLevel() > max)
            {
                bool go = false;
                {
                    std::lock_guard<std::mutex> g(piloteLock);
                    time_t& t = dernierDepart[guid];
                    if (now - t >= 600)
                    {
                        t = now;
                        go = true;
                    }
                }
                if (go)
                {
                    p->GetMotionMaster()->Clear(false);
                    p->StopMoving(true);
                    sRandomPlayerbotMgr.RandomTeleportForLevel(p, false);
                }
            }
        }
    }

    void VaguesModule::PiloterBots(bool zones)
    {
        uint32 compte = 0;
        std::vector<std::pair<Map*, ObjectGuid>> todo;
        {
            HashMapHolder<Player>::ReadGuard g(HashMapHolder<Player>::GetLock());
            for (auto const& kv : HashMapHolder<Player>::GetContainer())
            {
                Player* p = kv.second;
                if (!p || !p->IsInWorld() || !p->GetPlayerbotAI() || !p->GetMap())
                    continue;
                todo.emplace_back(p->GetMap(), p->GetObjectGuid());
            }
        }
        static uint32 compteCompagnons = 0, essaiCompte = 0;
        if (!compteCompagnons && ++essaiCompte % 60 == 1)       // compte cherché au plus une fois par minute tant qu'il n'existe pas
            compteCompagnons = sAccountMgr.GetId(COMPAGNONS_COMPTE);
        compte = compteCompagnons;
        for (auto const& t : todo)
        {
            ObjectGuid guid = t.second;
            t.first->GetMessager().AddMessage([guid, zones, compte](Map* map)
            {
                if (Player* p = map->GetPlayer(guid))
                    PiloterUnBot(p, zones, compte && p->GetSession() && p->GetSession()->GetAccountId() == compte);
            });
        }
    }

    // .bots pull : le tank de ton groupe pull ta cible (ou le monstre le plus proche) ; .bots pull auto on|off
    bool VaguesModule::HandlePull(WorldSession* session, const std::string& args)
    {
        Player* joueur = session ? session->GetPlayer() : nullptr;
        if (!joueur)
            return true;
        if (args.find("auto") != std::string::npos)
        {
            bool off = args.find("off") != std::string::npos;
            {
                std::lock_guard<std::mutex> g(piloteLock);
                if (off)
                    pullAutoOff.insert(joueur->GetGUIDLow());
                else
                    pullAutoOff.erase(joueur->GetGUIDLow());
            }
            Message(session, off ? "Pull automatique du tank : coupé." : "Pull automatique du tank : activé.");
            return true;
        }
        Group* grp = joueur->GetGroup();
        Player* tank = nullptr;
        if (grp)
            for (GroupReference* ref = grp->GetFirstMember(); ref; ref = ref->next())
                if (Player* m = ref->getSource())
                    if (m->GetPlayerbotAI() && m->IsAlive() && m->GetMap() == joueur->GetMap() && (AiFactory::GetPlayerRoles(m) & BOT_ROLE_TANK))
                    {
                        tank = m;
                        break;
                    }
        if (!tank)
        {
            Message(session, "Aucun tank bot dans ton groupe.");
            return true;
        }
        ObjectGuid tankGuid = tank->GetObjectGuid(), joueurGuid = joueur->GetObjectGuid(), cible = joueur->GetSelectionGuid();
        tank->GetMap()->GetMessager().AddMessage([tankGuid, joueurGuid, cible](Map* map)
        {
            Player* t = map->GetPlayer(tankGuid);
            Player* j = map->GetPlayer(joueurGuid);
            if (!t || !j)
                return;
            Unit* u = cible ? map->GetUnit(cible) : nullptr;
            if (!u || !u->IsAlive() || !t->CanAttack(u))
                u = CibleDePull(t);
            if (u)
            {
                {
                    std::lock_guard<std::mutex> g(piloteLock);
                    dernierPull[t->GetGUIDLow()] = time(nullptr);
                }
                LancerPull(t, u, j);
            }
            else
                ChatHandler(j->GetSession()).SendSysMessage("Rien à puller à portée.");
        });
        return true;
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
