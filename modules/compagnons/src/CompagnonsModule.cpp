#include "CompagnonsModule.h"
#include "CompagnonsData.h"

#include "Accounts/AccountMgr.h"
#include "Auth/SRP6.h"
#include "Chat/Chat.h"
#include "Database/DatabaseEnv.h"
#include "Entities/Creature.h"
#include "Entities/Item.h"
#include "Entities/ItemPrototype.h"
#include "Entities/Pet.h"
#include "Entities/Player.h"
#include "Globals/ObjectAccessor.h"
#include "Globals/ObjectMgr.h"
#include "Groups/Group.h"
#include "Log/Log.h"
#include "Loot/LootMgr.h"
#include "Mails/Mail.h"
#include "Maps/Map.h"
#include "Server/DBCStores.h"
#include "Server/WorldSession.h"
#include "Spells/Spell.h"
#include "Spells/SpellAuras.h"
#include "Spells/SpellMgr.h"
#include "Util/Util.h"

#include "playerbot/playerbot.h"
#include "playerbot/PlayerbotAI.h"
#include "playerbot/PlayerbotMgr.h"

#include <openssl/crypto.h>

#include <algorithm>
#include <cmath>
#include <ctime>
#include <functional>
#include <sstream>

using namespace compagnons_data;

// crochets du cœur (patches/07-compagnons.patch) et de playerbot (overlay AiFactory.cpp, LootRollAction.cpp)
extern bool (*gCpgEstCompagnon)(Player const*);
extern const char* (*gCpgNom)(uint32);
extern bool (*gCpgAutorise)(uint32);
extern std::function<int(Player const*)> gRoleCustom;     // overlay AiFactory.cpp (déjà rempli par le module classes)
extern std::function<int(Player const*)> gTabCustom;

namespace cmangos_module
{
    static CompagnonsModule* instance = nullptr;
    static thread_local int s_depth = 0;     // évite de se rappeler soi-même (dégâts lancés par le module), par fil d'exécution
    struct Profondeur { Profondeur() { ++s_depth; } ~Profondeur() { --s_depth; } };

    static const uint32 MAX_ACTIFS = 5;         // groupe de 6 : le joueur et 5 compagnons
    static const uint32 NIVEAU_MIN = 10;        // compagnons disponibles à partir de ce niveau
    static const uint32 CPG_OFFERT = 5;         // Rémy Deux-Fois, offert au niveau 10
    static const uint32 SORT_GROUPE_COMPLET = 46991;   // buff « Groupe complet » : 6 vrais joueurs dans le même donjon

    // ------------------------------------------------------------------ outils
    static Compagnon const* Def(uint32 id)
    {
        return id >= 1 && id <= COMPAGNONS_N ? &COMPAGNONS[id - 1] : nullptr;
    }

    static void Dire(Player* p, std::string const& s)
    {
        if (p && p->GetSession())
            ChatHandler(p).SendSysMessage(s.c_str());
    }

    static void Addon(Player* p, std::string const& s)
    {
        if (p && p->GetSession())
            ChatHandler(p).SendSysMessage(("##CPG " + s).c_str());
    }

    static bool EstBot(Player* p)
    {
        return p->GetSession() && p->GetSession()->GetRemoteAddress() == "disconnected/bot";
    }

    static std::string Nom(Compagnon const* d)
    {
        return d ? d->nom : "?";
    }

    // aura cachée d'un canal de statistiques : remplacée si sa valeur change
    static void SetSort(Unit* u, uint32 sp, int32 v)
    {
        int32 cur = INT32_MIN;
        if (Aura* a = u->GetAura(sp, EFFECT_INDEX_0))
            cur = a->GetModifier()->m_amount;
        if (v == 0)
        {
            if (cur != INT32_MIN)
                u->RemoveAurasDueToSpell(sp);
            return;
        }
        if (cur == v)
            return;
        u->RemoveAurasDueToSpell(sp);
        u->CastCustomSpell(u, sp, &v, nullptr, nullptr, TRIGGERED_OLD_TRIGGERED);
    }

    static bool EstSortDeClasse(uint32 spellId)
    {
        SkillLineAbilityMapBounds b = sSpellMgr.GetSkillLineAbilityMapBoundsBySpellId(spellId);
        for (auto it = b.first; it != b.second; ++it)
            if (SkillLineEntry const* sk = sSkillLineStore.LookupEntry(it->second->skillId))
                if (sk->categoryId == 7)
                    return true;
        return false;
    }

    // sorts de classe gardés en plus de la fiche : postures, tir automatique, familier, buffs de spé utilisés par l'IA
    static bool Implicite(uint8 cls, uint32 id)
    {
        static const uint32 GUERRIER[] = { 2457, 71, 2458 };
        static const uint32 CHASSEUR[] = { 75, 883, 2641, 982, 6991, 1515 };
        switch (cls)
        {
            case 1: return std::find(std::begin(GUERRIER), std::end(GUERRIER), id) != std::end(GUERRIER);
            case 3: return std::find(std::begin(CHASSEUR), std::end(CHASSEUR), id) != std::end(CHASSEUR);
            case 10: return id == 75;
        }
        for (uint32 i = 0; i < IMPLICITE_N; ++i)
            if (IMPLICITE[i].cls == cls && IMPLICITE[i].sort == id)
                return true;
        return false;
    }

    static uint8 Tranche(uint32 niveau)
    {
        return uint8(std::min<uint32>(11, (std::max<uint32>(1, niveau) - 1) / 5));
    }

    // compétence d'arme ou d'armure pour porter un objet
    static void Maniement(Player* bot, ItemPrototype const* proto)
    {
        uint32 skill = 0, spell = 0;
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
                case 4: skill = SKILL_PLATE_MAIL; spell = 750; break;
                case 6: skill = SKILL_SHIELD; spell = 9116; break;
            }
        }
        if (spell && !bot->HasSpell(spell))
            bot->learnSpell(spell, false);
        if (skill && !bot->HasSkill(skill))
            bot->SetSkill(skill, bot->GetLevel() * 5, bot->GetLevel() * 5);
    }

    // orbe : couleur et niveau d'une entrée
    static bool Orbe(uint32 entry, uint32& couleur, uint32& niveau)
    {
        if (entry < ORBE_PREMIER || entry > ORBE_DERNIER)
            return false;
        couleur = (entry - ORBE_PREMIER) / 51;
        niveau = 10 + (entry - ORBE_PREMIER) % 51;
        return true;
    }

    // statistiques d'une orbe (mêmes formules que le générateur)
    static void OrbeStats(uint32 couleur, uint32 L, int32* vals)
    {
        float f = L / 60.0f;
        int32 pct = L >= 15 ? std::max(1, int32(std::lround(2 * f))) : 1;
        auto r = [&](float v) { return int32(std::lround(v * f)); };
        switch (couleur)
        {
            case 0: vals[CA_STAT_ENDU] += r(40); vals[CA_DEFENSE] += r(20); vals[CA_TOUCHER] += pct; vals[CA_RESIST] += r(20); break;
            case 1: vals[CA_STAT_INT] += r(30); vals[CA_STAT_ENDU] += r(16); vals[CA_CRIT_SORTS] += pct; vals[CA_PS] += r(40); break;
            case 2: vals[CA_STAT_AGI] += r(30); vals[CA_STAT_ENDU] += r(16); vals[CA_TOUCHER] += pct; vals[CA_PA] += r(60); vals[CA_PA_DIST] += r(60); break;
            case 3: vals[CA_STAT_FOR] += r(30); vals[CA_STAT_ENDU] += r(16); vals[CA_TOUCHER] += pct; vals[CA_PA] += r(60); break;
            default: vals[CA_STAT_INT] += r(30); vals[CA_STAT_ENDU] += r(16); vals[CA_CRIT_SORTS] += pct; vals[CA_SOIN_BONUS] += r(70); break;
        }
    }

    // équilibrage (27/11) : dégâts et soins réduits selon la rareté, les tanks tapent encore moins (menace compensée)
    static const int32 MALUS[5] = { 45, 30, 20, 10, 0 };
    static const int32 MALUS_TANK[5] = { 65, 50, 40, 30, 20 };
    static int32 PuissanceDegats(Compagnon const* d)
    {
        return PUISSANCE[d->rarete] * (100 - (d->role == 0 ? MALUS_TANK : MALUS)[d->rarete]) / 100;
    }
    static int32 PuissanceSoins(Compagnon const* d)
    {
        return PUISSANCE[d->rarete] * (100 - MALUS[d->rarete]) / 100;
    }

    // stuff de base : bleu 60 (avec le +50 % des objets du serveur) x ratio de la rareté x niveau
    static void Stuff(Compagnon const* d, uint32 L, bool bouclier, int32* vals)
    {
        float f = (L / 60.0f) * (STUFF[d->rarete] / 100.0f);
        auto r = [&](float v) { return int32(std::lround(v * f)); };
        static const uint32 STATS[4] = { CA_STAT_FOR, CA_STAT_AGI, 0, CA_STAT_INT };
        vals[CA_STAT_ENDU] += r(216);
        vals[STATS[d->stat]] += r(216);
        switch (d->bonus)
        {
            case 0: vals[CA_PA] += r(225); vals[CA_PA_DIST] += r(225); break;
            case 1: vals[CA_PS] += r(171); break;
            case 2: vals[CA_SOIN_BONUS] += r(314); break;
            default: vals[CA_DEFENSE] += r(80); break;
        }
        int32 pct = int32(std::lround(4.0f * f));
        bool sorts = d->stat == 3;
        vals[sorts ? CA_CRIT_SORTS : CA_CRIT] += pct;
        vals[sorts ? CA_TOUCHER_SORTS : CA_TOUCHER] += pct;
        static const float ARMURE[4] = { 600.0f, 1300.0f, 2700.0f, 4800.0f };
        vals[CA_ARMURE] += r(ARMURE[d->armure] + (bouclier ? 2000.0f : 0.0f));
    }

    // ------------------------------------------------------------------ module
    CompagnonsModule::CompagnonsModule() : Module("Compagnons", nullptr)
    {
        instance = this;
    }

    void CompagnonsModule::OnInitialize()
    {
        CharacterDatabase.Execute(
            "CREATE TABLE IF NOT EXISTS `custom_cpg` (`proprio` INT UNSIGNED NOT NULL, `cpg` TINYINT UNSIGNED NOT NULL, `bot` INT UNSIGNED NOT NULL DEFAULT 0,"
            " `talents` VARCHAR(16) NOT NULL DEFAULT '', `orbe1` INT UNSIGNED NOT NULL DEFAULT 0, `orbe2` INT UNSIGNED NOT NULL DEFAULT 0,"
            " `artefact1` INT UNSIGNED NOT NULL DEFAULT 0, `artefact2` INT UNSIGNED NOT NULL DEFAULT 0, `actif` TINYINT UNSIGNED NOT NULL DEFAULT 0,"
            " `date` DATETIME NOT NULL, PRIMARY KEY (`proprio`, `cpg`), KEY `bot` (`bot`)) ENGINE=InnoDB DEFAULT CHARSET=utf8");
        CharacterDatabase.Execute("CREATE TABLE IF NOT EXISTS `custom_bot_arbre` (`guid` INT UNSIGNED NOT NULL, `arbre` TINYINT UNSIGNED NOT NULL,"
                                  " PRIMARY KEY (`guid`)) ENGINE=InnoDB DEFAULT CHARSET=utf8");
        CharacterDatabase.Execute("DELETE FROM `custom_cpg` WHERE `proprio` NOT IN (SELECT `guid` FROM `characters`)");
        CharacterDatabase.Execute("UPDATE `custom_cpg` SET `bot` = 0 WHERE `bot` <> 0 AND `bot` NOT IN (SELECT `guid` FROM `characters`)");
        // tous les bots de compagnons sont connus dès le démarrage (nom affiché, XP, autorisation de connexion)
        if (auto r = CharacterDatabase.Query("SELECT `bot`, `cpg`, `proprio` FROM `custom_cpg` WHERE `bot` <> 0"))
        {
            do
            {
                Field* f = r->Fetch();
                botCpg[f[0].GetUInt32()] = f[1].GetUInt32();
                botProprio[f[0].GetUInt32()] = f[2].GetUInt32();
            }
            while (r->NextRow());
        }
        gCpgEstCompagnon = [](Player const* p) { return instance && p && instance->EstCompagnon(p->GetGUIDLow()); };
        gCpgNom = [](uint32 g) { return instance ? instance->NomAffiche(g) : nullptr; };
        gCpgAutorise = [](uint32 g) { return instance && instance->EstCompagnon(g); };
        sLog.outString("Compagnons : %u compagnons, %u bots connus", COMPAGNONS_N, uint32(botCpg.size()));
    }

    bool CompagnonsModule::EstCompagnon(uint32 g) const
    {
        std::lock_guard<std::recursive_mutex> l(lock);
        return botCpg.count(g) != 0;
    }

    const char* CompagnonsModule::NomAffiche(uint32 g) const
    {
        std::lock_guard<std::recursive_mutex> l(lock);
        auto it = botCpg.find(g);
        if (it == botCpg.end())
            return nullptr;
        Compagnon const* d = Def(it->second);
        return d ? d->nom : nullptr;
    }

    // rôle imposé à playerbot : 0 tank, 1 soin, 2 DPS cac, 3 DPS distance (soutien : distance)
    int CompagnonsModule::Role(uint32 g) const
    {
        std::lock_guard<std::recursive_mutex> l(lock);
        auto it = botCpg.find(g);
        if (it == botCpg.end())
            return -1;
        Compagnon const* d = Def(it->second);
        return d ? (d->role == 4 ? 3 : d->role) : -1;
    }

    int CompagnonsModule::Onglet(uint32 g) const
    {
        std::lock_guard<std::recursive_mutex> l(lock);
        auto it = botCpg.find(g);
        if (it == botCpg.end())
            return -1;
        Compagnon const* d = Def(it->second);
        return d ? d->tab : -1;
    }

    std::vector<ModuleChatCommand>* CompagnonsModule::GetCommandTable()
    {
        static std::vector<ModuleChatCommand> t =
        {
            { "liste", std::bind(&CompagnonsModule::HandleListe, this, std::placeholders::_1, std::placeholders::_2), SEC_PLAYER },
            { "fiche", std::bind(&CompagnonsModule::HandleFiche, this, std::placeholders::_1, std::placeholders::_2), SEC_PLAYER },
            { "invoquer", std::bind(&CompagnonsModule::HandleInvoquer, this, std::placeholders::_1, std::placeholders::_2), SEC_PLAYER },
            { "renvoyer", std::bind(&CompagnonsModule::HandleRenvoyer, this, std::placeholders::_1, std::placeholders::_2), SEC_PLAYER },
            { "talent", std::bind(&CompagnonsModule::HandleTalent, this, std::placeholders::_1, std::placeholders::_2), SEC_PLAYER },
            { "reset", std::bind(&CompagnonsModule::HandleReset, this, std::placeholders::_1, std::placeholders::_2), SEC_PLAYER },
            { "equiper", std::bind(&CompagnonsModule::HandleEquiper, this, std::placeholders::_1, std::placeholders::_2), SEC_PLAYER },
            { "retirer", std::bind(&CompagnonsModule::HandleRetirer, this, std::placeholders::_1, std::placeholders::_2), SEC_PLAYER },
            { "boutique", std::bind(&CompagnonsModule::HandleBoutique, this, std::placeholders::_1, std::placeholders::_2), SEC_PLAYER },
            { "acheter", std::bind(&CompagnonsModule::HandleAcheter, this, std::placeholders::_1, std::placeholders::_2), SEC_PLAYER },
            { "donner", std::bind(&CompagnonsModule::HandleDonner, this, std::placeholders::_1, std::placeholders::_2), SEC_GAMEMASTER },
        };
        return &t;
    }

    // ------------------------------------------------------------------ possessions
    void CompagnonsModule::Charger(uint32 proprio)
    {
        if (charges.count(proprio))
            return;
        charges.insert(proprio);
        auto& v = possessions[proprio];
        v.clear();
        if (auto r = CharacterDatabase.PQuery("SELECT `cpg`, `bot`, `talents`, `orbe1`, `orbe2`, `artefact1`, `artefact2`, `actif` FROM `custom_cpg` WHERE `proprio` = %u", proprio))
        {
            do
            {
                Field* f = r->Fetch();
                CpgPossession p;
                p.cpg = f[0].GetUInt32();
                p.bot = f[1].GetUInt32();
                p.talents = f[2].GetCppString();
                p.orbes[0] = f[3].GetUInt32(); p.orbes[1] = f[4].GetUInt32();
                p.artefacts[0] = f[5].GetUInt32(); p.artefacts[1] = f[6].GetUInt32();
                p.actif = f[7].GetUInt32() != 0;
                if (Def(p.cpg))
                    v.push_back(p);
            }
            while (r->NextRow());
        }
    }

    void CompagnonsModule::Sauver(uint32 proprio, CpgPossession const& p)
    {
        std::string t = p.talents;
        CharacterDatabase.escape_string(t);
        CharacterDatabase.PExecute("UPDATE `custom_cpg` SET `bot` = %u, `talents` = '%s', `orbe1` = %u, `orbe2` = %u, `artefact1` = %u, `artefact2` = %u, `actif` = %u "
                                   "WHERE `proprio` = %u AND `cpg` = %u", p.bot, t.c_str(), p.orbes[0], p.orbes[1], p.artefacts[0], p.artefacts[1],
                                   p.actif ? 1 : 0, proprio, p.cpg);
    }

    CpgPossession* CompagnonsModule::Possession(uint32 proprio, uint32 cpg)
    {
        Charger(proprio);
        for (auto& p : possessions[proprio])
            if (p.cpg == cpg)
                return &p;
        return nullptr;
    }

    uint32 CompagnonsModule::CompteBots(uint32 proprio)
    {
        std::string nom = "CPG" + std::to_string(proprio);
        uint32 id = sAccountMgr.GetId(nom);
        if (!id)
        {
            // création immédiate : AccountMgr::CreateAccount passe par une requête différée, le compte n'existerait pas encore ici
            std::string mdp = std::to_string(urand(100000, 999999)) + std::to_string(urand(100000, 999999));
            AccountMgr::normalizeString(nom);
            AccountMgr::normalizeString(mdp);
            SRP6 srp;
            srp.CalculateVerifier(sAccountMgr.CalculateShaPassHash(nom, mdp));
            const char* s_hex = srp.GetSalt().AsHexStr();
            const char* v_hex = srp.GetVerifier().AsHexStr();
            LoginDatabase.DirectPExecute("INSERT INTO account (username, v, s, joindate) VALUES ('%s', '%s', '%s', NOW())", nom.c_str(), v_hex, s_hex);
            OPENSSL_free((void*)s_hex);
            OPENSSL_free((void*)v_hex);
            LoginDatabase.DirectExecute("INSERT INTO realmcharacters (realmid, acctid, numchars) SELECT realmlist.id, account.id, 0 FROM realmlist, account "
                                        "LEFT JOIN realmcharacters ON acctid = account.id WHERE acctid IS NULL");
            id = sAccountMgr.GetId(nom);
            if (!id)
                sLog.outError("Compagnons : impossible de créer le compte %s", nom.c_str());
        }
        return id;
    }

    // rangs des talents (10 talents + l'ultime) ; répartition automatique tant que le joueur n'a rien choisi
    std::vector<uint32> CompagnonsModule::Rangs(CpgPossession const& p, uint32 niveau) const
    {
        std::vector<uint32> r(11, 0);
        uint32 points = niveau > 20 ? niveau - 20 : 0;
        if (!p.talents.empty())
        {
            uint32 total = 0;
            for (size_t i = 0; i < 11 && i < p.talents.size(); ++i)
            {
                r[i] = uint32(p.talents[i] - '0');
                total += r[i];
            }
            if (total <= points)
                return r;
            std::fill(r.begin(), r.end(), 0);       // plus assez de points (niveau perdu ?) : répartition automatique
        }
        // 1er talent de chaque palier jusqu'au 4e, l'ultime, le 1er du 5e, puis les seconds talents
        const uint32 ordre[] = { 0, 2, 4, 6, 10, 8, 1, 3, 5, 7, 9 };
        for (uint32 i : ordre)
        {
            uint32 max = i == 10 ? 1 : 5;
            uint32 n = std::min(max, points);
            r[i] = n;
            points -= n;
            if (!points)
                break;
        }
        return r;
    }

    // ------------------------------------------------------------------ création du bot
    uint32 CompagnonsModule::CreerBot(Player* proprio, uint32 cpg)
    {
        Compagnon const* d = Def(cpg);
        uint32 compte = CompteBots(proprio->GetGUIDLow());
        if (!d || !compte)
            return 0;
        uint8 race = proprio->GetTeam() == ALLIANCE ? d->raceA : d->raceH;
        uint8 genre = d->genre;
        // apparence : la première de la race et du sexe
        uint8 peau = 0, visage = 0, coiffure = 0, couleur = 0, pilosite = 0;
        for (auto const& kv : sCharSectionMap)
        {
            CharSectionsEntry const* e = kv.second;
            if (e->Race != race || e->Gender != genre)
                continue;
            if (e->BaseSection == SECTION_TYPE_FACE && !visage) { visage = e->VariationIndex; peau = e->ColorIndex; }
            if (e->BaseSection == SECTION_TYPE_HAIR && !coiffure) { coiffure = e->VariationIndex; couleur = e->ColorIndex; }
        }
        // nom interne unique (lettres seulement) ; le nom affiché est celui de la fiche
        std::string base;
        for (const char* c = d->cle; *c; ++c)
            if ((*c >= 'a' && *c <= 'z') || (*c >= 'A' && *c <= 'Z'))
                base += *c;
        base = base.substr(0, 7);
        base[0] = char(toupper(base[0]));
        std::string nom;
        uint32 n = proprio->GetGUIDLow();
        for (uint32 essai = 0; essai < 50; ++essai)
        {
            std::string suf;
            uint32 v = n + essai * 7919;
            for (int k = 0; k < 4; ++k) { suf += char('a' + v % 26); v /= 26; }
            nom = base + suf;
            if (sObjectMgr.GetPlayerGuidByName(nom).IsEmpty())
                break;
        }
        WorldSession* session = new WorldSession(compte, nullptr, SEC_PLAYER, 0, LOCALE_enUS, "", 0);
        session->SetNoAnticheat();
        Player* bot = new Player(session);
        if (!bot->Create(sObjectMgr.GeneratePlayerLowGuid(), nom, race, d->cls, genre, peau, visage, coiffure, couleur, pilosite, 0))
        {
            sLog.outError("Compagnons : création impossible de %s (race %u, classe %u)", nom.c_str(), race, d->cls);
            delete bot;
            delete session;
            return 0;
        }
        bot->setCinematic(2);
        bot->SetAtLoginFlag(AT_LOGIN_NONE);
        sObjectAccessor.AddObject(bot);
        if (proprio->GetLevel() > 1)
            bot->GiveLevel(proprio->GetLevel());
        bot->SetUInt32Value(PLAYER_XP, 0);
        bot->SaveToDB();
        uint32 guid = bot->GetGUIDLow();
        session->LogoutPlayer();
        sObjectAccessor.RemoveObject(bot);
        delete bot;
        delete session;
        CharacterDatabase.PExecute("REPLACE INTO `custom_bot_arbre` (`guid`, `arbre`) VALUES (%u, %u)", guid, uint32(d->tab));
        // vide l'équipement de départ (le module équipe le compagnon à sa connexion)
        CharacterDatabase.PExecute("DELETE FROM `item_instance` WHERE `guid` IN (SELECT `item` FROM `character_inventory` WHERE `guid` = %u)", guid);
        CharacterDatabase.PExecute("DELETE FROM `character_inventory` WHERE `guid` = %u", guid);
        botCpg[guid] = cpg;
        botProprio[guid] = proprio->GetGUIDLow();
        sLog.outString("Compagnons : %s (%s) créé pour %s", nom.c_str(), d->nom, proprio->GetName());
        return guid;
    }

    // ------------------------------------------------------------------ invocation
    void CompagnonsModule::Invoquer(Player* proprio, uint32 cpg)
    {
        std::lock_guard<std::recursive_mutex> l(lock);
        Compagnon const* d = Def(cpg);
        CpgPossession* p = Possession(proprio->GetGUIDLow(), cpg);
        if (!d || !p)
        {
            Dire(proprio, "Tu ne possèdes pas ce compagnon.");
            return;
        }
        for (auto const& a : actifs)
            if (a.proprio == proprio->GetGUIDLow() && a.cpg == cpg)
            {
                Renvoyer(proprio->GetGUIDLow(), cpg, true);
                return;
            }
        if (proprio->GetLevel() < NIVEAU_MIN)
        {
            Dire(proprio, "Les compagnons sont disponibles à partir du niveau 10.");
            return;
        }
        uint32 n = 0;
        for (auto const& a : actifs)
            if (a.proprio == proprio->GetGUIDLow())
                ++n;
        if (n >= MAX_ACTIFS)
        {
            Dire(proprio, "Tu as déjà 5 compagnons avec toi. Renvoie-en un avant d'en appeler un autre.");
            return;
        }
        if (!proprio->GetPlayerbotMgr())
        {
            Dire(proprio, "Les compagnons ne sont pas disponibles pour ce personnage.");
            return;
        }
        if (Group* g = proprio->GetGroup())
            if (g->IsFull())
            {
                Dire(proprio, "Ton groupe est plein.");
                return;
            }
        bool nouveau = false;
        if (!p->bot || sObjectMgr.GetPlayerAccountIdByGUID(ObjectGuid(HIGHGUID_PLAYER, p->bot)) == 0)
        {
            p->bot = CreerBot(proprio, cpg);
            if (!p->bot)
            {
                Dire(proprio, "Le compagnon n'a pas pu être créé.");
                return;
            }
            nouveau = true;
        }
        botCpg[p->bot] = cpg;
        botProprio[p->bot] = proprio->GetGUIDLow();
        p->actif = true;
        Sauver(proprio->GetGUIDLow(), *p);
        // connexion directement à côté du joueur
        CharacterDatabase.PExecute("UPDATE `characters` SET `map` = %u, `position_x` = %f, `position_y` = %f, `position_z` = %f, `orientation` = %f, `zone` = %u WHERE `guid` = %u",
                                   proprio->GetMapId(), proprio->GetPositionX(), proprio->GetPositionY(), proprio->GetPositionZ(), proprio->GetOrientation(),
                                   proprio->GetZoneId(), p->bot);
        CpgActif a;
        a.proprio = proprio->GetGUIDLow();
        a.cpg = cpg;
        a.bot = p->bot;
        a.attente = nouveau ? 3000 : 300;
        actifs.push_back(a);
        Dire(proprio, d->nom + std::string(" arrive."));
    }

    void CompagnonsModule::Renvoyer(uint32 proprio, uint32 cpg, bool message)
    {
        std::lock_guard<std::recursive_mutex> l(lock);
        Player* maitre = sObjectMgr.GetPlayer(ObjectGuid(HIGHGUID_PLAYER, proprio));
        for (auto it = actifs.begin(); it != actifs.end(); ++it)
        {
            if (it->proprio != proprio || it->cpg != cpg)
                continue;
            if (Player* bot = sObjectMgr.GetPlayer(ObjectGuid(HIGHGUID_PLAYER, it->bot)))
            {
                if (bot->GetGroup())
                    bot->RemoveFromGroup();
                if (maitre && maitre->GetPlayerbotMgr())
                    maitre->GetPlayerbotMgr()->LogoutPlayerBot(it->bot);
                else if (bot->GetPlayerbotAI() && bot->GetPlayerbotAI()->GetMaster() && bot->GetPlayerbotAI()->GetMaster()->GetPlayerbotMgr())
                    bot->GetPlayerbotAI()->GetMaster()->GetPlayerbotMgr()->LogoutPlayerBot(it->bot);
            }
            actifs.erase(it);
            break;
        }
        if (CpgPossession* p = Possession(proprio, cpg))
        {
            p->actif = false;
            Sauver(proprio, *p);
        }
        if (message && maitre)
            Dire(maitre, Nom(Def(cpg)) + " rentre chez lui.");
    }

    bool CompagnonsModule::OnUseItem(Player* player, Item* item)
    {
        if (!player || !item)
            return false;
        uint32 e = item->GetEntry();
        if (e < PIERRE_PREMIERE || e > PIERRE_DERNIERE)
            return false;
        for (uint32 i = 0; i < COMPAGNONS_N; ++i)
            if (COMPAGNONS[i].pierre == e)
            {
                if (player->IsInCombat())
                    Dire(player, "Impossible en combat.");
                else
                    Invoquer(player, COMPAGNONS[i].id);
                return true;
            }
        return false;
    }

    void CompagnonsModule::OnLogOut(Player* player)
    {
        std::lock_guard<std::recursive_mutex> l(lock);
        uint32 g = player->GetGUIDLow();
        // le joueur part : ses compagnons aussi (playerbot les déconnecte) ; ils reviendront à sa prochaine connexion
        actifs.erase(std::remove_if(actifs.begin(), actifs.end(), [&](CpgActif const& a) { return a.proprio == g; }), actifs.end());
        charges.erase(g);
        possessions.erase(g);
        offerts.erase(g);
        sixiemeAffiche.erase(g);
    }

    void CompagnonsModule::OnDeleteFromDB(uint32 playerId)
    {
        std::lock_guard<std::recursive_mutex> l(lock);
        CharacterDatabase.PExecute("DELETE FROM `custom_cpg` WHERE `proprio` = %u", playerId);
        CharacterDatabase.PExecute("UPDATE `custom_cpg` SET `bot` = 0 WHERE `bot` = %u", playerId);
        botCpg.erase(playerId);
        botProprio.erase(playerId);
    }

    // ------------------------------------------------------------------ XP
    bool CompagnonsModule::OnPreGiveXP(Player* player, uint32& xp, Creature* victim)
    {
        if (!player || !xp)
            return false;
        if (EstCompagnon(player->GetGUIDLow()))
        {
            xp = 0;
            return true;                    // toujours au niveau de son propriétaire
        }
        // +10 % par autre vrai joueur du groupe
        if (Group* g = player->GetGroup())
        {
            uint32 n = 0;
            for (GroupReference* ref = g->GetFirstMember(); ref; ref = ref->next())
                if (Player* m = ref->getSource())
                    if (m != player && !EstBot(m) && m->IsInMap(player))
                        ++n;
            if (n)
                xp = uint32(xp * (1.0f + 0.1f * n) + 0.5f);
        }
        // Groupe complet (6 vrais joueurs dans le même donjon) : +50 % sur les monstres du donjon
        if (victim && player->HasAura(SORT_GROUPE_COMPLET) && player->GetMap() && player->GetMap()->IsDungeon() && !player->GetMap()->IsRaid())
            xp = uint32(xp * 1.5f + 0.5f);
        return false;
    }

    // ------------------------------------------------------------------ niveau 10 : compagnon offert
    void CompagnonsModule::OnGiveLevel(Player* player, uint32 level)
    {
        if (level < NIVEAU_MIN)
            return;
        std::lock_guard<std::recursive_mutex> l(lock);
        Offrir(player);
    }

    void CompagnonsModule::Offrir(Player* p)
    {
        if (!p || !p->GetSession() || EstBot(p) || p->GetLevel() < NIVEAU_MIN)
            return;
        uint32 g = p->GetGUIDLow();
        if (offerts.count(g))
            return;
        offerts.insert(g);
        Compagnon const* d = Def(CPG_OFFERT);
        if (!d || Possession(g, CPG_OFFERT))
            return;
        CharacterDatabase.PExecute("INSERT IGNORE INTO `custom_cpg` (`proprio`, `cpg`, `date`) VALUES (%u, %u, NOW())", g, CPG_OFFERT);
        CpgPossession po;
        po.cpg = CPG_OFFERT;
        possessions[g].push_back(po);
        MailDraft draft(std::string("Cadeau : ") + d->nom, std::string("Bravo pour ton niveau 10 ! ") + d->nom +
                        " te rejoint gratuitement. Utilise sa pierre pour l'appeler à tes côtés (ou ouvre l'onglet Compagnons).");
        if (Item* it = Item::CreateItem(d->pierre, 1, p))
        {
            it->SaveToDB();
            draft.AddItem(it);
        }
        draft.SendMailTo(MailReceiver(p, p->GetObjectGuid()), MailSender(MAIL_NORMAL, uint32(0), MAIL_STATIONERY_GM));
        Dire(p, std::string("|cff00ff00Niveau 10 : ") + d->nom + " te rejoint gratuitement ! Sa pierre t'attend dans ta boîte aux lettres.|r");
        EnvoyerListe(p);
    }

    // ------------------------------------------------------------------ groupe de 6
    // invitation d'un vrai joueur dans un groupe plein : un compagnon cède sa place
    bool CompagnonsModule::OnPreInviteMember(Group* group, Player* player, Player* recipient)
    {
        if (!group || !player || !recipient || EstBot(recipient) || !group->IsFull() || group->IsRaidGroup())
            return false;
        std::lock_guard<std::recursive_mutex> l(lock);
        for (auto it = actifs.rbegin(); it != actifs.rend(); ++it)
        {
            Player* bot = sObjectMgr.GetPlayer(ObjectGuid(HIGHGUID_PLAYER, it->bot));
            if (!bot || bot->GetGroup() != group)
                continue;
            uint32 proprio = it->proprio, cpg = it->cpg;
            Renvoyer(proprio, cpg, true);
            break;
        }
        return false;
    }

    // 6e membre : le jeu ne l'affiche pas, l'addon le montre (H nom|nom affiché|PV|PV max|puissance|max|type|classe|état)
    void CompagnonsModule::Sixieme(uint32 dt)
    {
        timerSixieme += dt;
        if (timerSixieme < 1000)
            return;
        timerSixieme = 0;
        std::vector<Player*> joueurs;
        {
            HashMapHolder<Player>::ReadGuard g(HashMapHolder<Player>::GetLock());
            for (auto const& kv : HashMapHolder<Player>::GetContainer())
                if (Player* p = kv.second)
                    if (p->IsInWorld() && p->GetSession() && !EstBot(p))
                        joueurs.push_back(p);
        }
        for (Player* p : joueurs)
        {
            GroupeComplet(p);
            Group* g = p->GetGroup();
            ObjectGuid cache = g ? g->GetHiddenMemberFor(p->GetObjectGuid()) : ObjectGuid();
            if (!cache)
            {
                if (sixiemeAffiche.erase(p->GetGUIDLow()))
                    Addon(p, "H");
                continue;
            }
            sixiemeAffiche.insert(p->GetGUIDLow());
            std::ostringstream out;
            Player* m = sObjectMgr.GetPlayer(cache);
            std::string nom, affiche;
            for (auto citr = g->GetMemberSlots().begin(); citr != g->GetMemberSlots().end(); ++citr)
                if (citr->guid == cache)
                    nom = citr->name;
            affiche = nom;
            if (const char* n = NomAffiche(cache.GetCounter()))
                affiche = n;
            if (!m)
            {
                out << "H " << nom << "|" << affiche << "|0|1|0|1|0|0|2";
                Addon(p, out.str());
                continue;
            }
            uint32 etatM = m->IsDead() ? 1 : (!m->IsInMap(p) ? 3 : 0);
            Powers pt = m->GetPowerType();
            out << "H " << nom << "|" << affiche << "|" << m->GetHealth() << "|" << m->GetMaxHealth() << "|" << m->GetPower(pt) << "|"
                << m->GetMaxPower(pt) << "|" << uint32(pt) << "|" << uint32(m->getClass()) << "|" << etatM;
            Addon(p, out.str());
        }
    }

    // buff « Groupe complet » : 6 vrais joueurs (aucun bot) dans le même donjon
    void CompagnonsModule::GroupeComplet(Player* p)
    {
        bool ok = false;
        Map* map = p->GetMap();
        Group* g = p->GetGroup();
        if (g && !g->IsRaidGroup() && g->GetMembersCount() >= 6 && map && map->IsDungeon() && !map->IsRaid())
        {
            ok = true;
            for (auto citr = g->GetMemberSlots().begin(); citr != g->GetMemberSlots().end() && ok; ++citr)
            {
                Player* m = sObjectMgr.GetPlayer(citr->guid);
                if (!m || !m->IsInWorld() || EstBot(m) || m->GetMap() != map)
                    ok = false;
            }
        }
        if (ok && !p->HasAura(SORT_GROUPE_COMPLET))
            p->CastSpell(p, SORT_GROUPE_COMPLET, TRIGGERED_OLD_TRIGGERED);
        else if (!ok && p->HasAura(SORT_GROUPE_COMPLET))
            p->RemoveAurasDueToSpell(SORT_GROUPE_COMPLET);
    }

    // ------------------------------------------------------------------ boucle
    void CompagnonsModule::OnUpdate(uint32 elapsed)
    {
        // rôle et onglet imposés à playerbot : branchés au premier passage, après l'initialisation de tous les modules
        // (le module classes remplit gRoleCustom pour ses bots ; les compagnons passent avant)
        if (!crochets)
        {
            crochets = true;
            std::function<int(Player const*)> avant = gRoleCustom;
            gRoleCustom = [avant](Player const* p) -> int
            {
                int r = instance && p ? instance->Role(p->GetGUIDLow()) : -1;
                return r >= 0 ? r : (avant ? avant(p) : -1);
            };
            std::function<int(Player const*)> avantTab = gTabCustom;
            gTabCustom = [avantTab](Player const* p) -> int
            {
                int t = instance && p ? instance->Onglet(p->GetGUIDLow()) : -1;
                return t >= 0 ? t : (avantTab ? avantTab(p) : -1);
            };
        }
        timer += elapsed;
        timerLivraison += elapsed;
        if (timerLivraison >= 10000)
        {
            timerLivraison = 0;
            std::lock_guard<std::recursive_mutex> l(lock);
            Livrer();
        }
        if (timer < 500)
            return;
        uint32 dt = timer;
        timer = 0;
        std::lock_guard<std::recursive_mutex> l(lock);
        Suivre(dt);
        Sixieme(dt);
    }

    void CompagnonsModule::Suivre(uint32 dt)
    {
        // compagnons restés actifs à la déconnexion : ils reviennent quand le joueur se reconnecte
        static uint32 rappel = 0;
        rappel += dt;
        if (rappel >= 5000)
        {
            rappel = 0;
            std::vector<std::pair<uint32, uint32>> aRappeler;
            std::vector<uint32> aOffrir;
            {
                HashMapHolder<Player>::ReadGuard g(HashMapHolder<Player>::GetLock());
                for (auto const& kv : HashMapHolder<Player>::GetContainer())
                {
                    Player* p = kv.second;
                    if (!p || !p->IsInWorld() || EstBot(p) || p->IsBeingTeleported() || p->IsInCombat())
                        continue;
                    uint32 g2 = p->GetGUIDLow();
                    if (p->GetLevel() >= NIVEAU_MIN && !offerts.count(g2))
                        aOffrir.push_back(g2);
                    if (!charges.count(g2))
                    {
                        // chargement paresseux : un compte est fait une fois par connexion
                        Charger(g2);
                        for (auto const& po : possessions[g2])
                            if (po.actif)
                                aRappeler.emplace_back(g2, po.cpg);
                    }
                }
            }
            for (uint32 g2 : aOffrir)
                if (Player* p = sObjectMgr.GetPlayer(ObjectGuid(HIGHGUID_PLAYER, g2)))
                    Offrir(p);
            for (auto const& r : aRappeler)
            {
                bool deja = false;
                for (auto const& a : actifs)
                    if (a.proprio == r.first && a.cpg == r.second)
                        deja = true;
                if (!deja)
                    if (Player* p = sObjectMgr.GetPlayer(ObjectGuid(HIGHGUID_PLAYER, r.first)))
                        Invoquer(p, r.second);
            }
        }

        std::vector<std::pair<uint32, uint32>> renvois;
        for (auto it = actifs.begin(); it != actifs.end();)
        {
            CpgActif& a = *it;
            if (a.renvoi)
            {
                renvois.emplace_back(a.proprio, a.cpg);
                ++it;
                continue;
            }
            Player* maitre = sObjectMgr.GetPlayer(ObjectGuid(HIGHGUID_PLAYER, a.proprio));
            if (!maitre || !maitre->IsInWorld() || !maitre->GetPlayerbotMgr())
            {
                it = actifs.erase(it);
                continue;
            }
            if (a.attente > dt)
            {
                a.attente -= dt;
                ++it;
                continue;
            }
            a.attente = 0;
            Player* bot = sObjectMgr.GetPlayer(ObjectGuid(HIGHGUID_PLAYER, a.bot));
            if (!a.connecte)
            {
                a.connecte = true;
                if (!bot)
                    maitre->GetPlayerbotMgr()->AddPlayerBot(a.bot, maitre->GetSession()->GetAccountId());
                ++it;
                continue;
            }
            if (!bot && a.pret)
            {
                // déconnecté par autre chose que le module (playerbot, téléportation ratée...) : reconnecté
                a.pret = false;
                a.connecte = false;
                a.essais = 0;
                a.attente = 3000;
                ++it;
                continue;
            }
            if (!bot || !bot->IsInWorld() || !bot->GetPlayerbotAI())
            {
                if (++a.essais > 120)
                {
                    Dire(maitre, Nom(Def(a.cpg)) + " n'a pas pu se connecter.");
                    it = actifs.erase(it);
                }
                else
                    ++it;
                continue;
            }
            if (bot->IsBeingTeleported() || maitre->IsBeingTeleported())
            {
                ++it;
                continue;
            }
            a.entretien += dt;
            bool complet = !a.pret || a.entretien >= 5000 || bot->GetLevel() != maitre->GetLevel();
            if (complet)
                a.entretien = 0;
            Preparer(bot, maitre, a, complet);
            a.pret = true;
            ++it;
        }
        for (auto const& r : renvois)
            Renvoyer(r.first, r.second, true);
    }

    // ------------------------------------------------------------------ entretien du compagnon
    void CompagnonsModule::Preparer(Player* bot, Player* maitre, CpgActif& a, bool complet)
    {
        Compagnon const* d = Def(a.cpg);
        CpgPossession* p = Possession(a.proprio, a.cpg);
        if (!d || !p)
            return;
        Profondeur prof;
        // niveau du propriétaire
        if (bot->GetLevel() != maitre->GetLevel())
        {
            bot->GiveLevel(maitre->GetLevel());
            bot->SetUInt32Value(PLAYER_XP, 0);
        }
        if (complet)
        {
            Sorts(bot, a.cpg);
            Equipement(bot, a.cpg);
            bot->UpdateSkillsForLevel(true);     // armes et défense toujours au maximum du niveau
            if (!a.pret)
            {
                if (PlayerbotAI* ai = bot->GetPlayerbotAI())
                {
                    ai->ResetStrategies();
                    ai->ChangeStrategy("-loot,-gather,-rpg,-travel,-grind,-maintenance", BotState::BOT_STATE_NON_COMBAT);
                }
                bot->SetHealth(bot->GetMaxHealth());
                if (bot->GetPowerType() == POWER_MANA)
                    bot->SetPower(POWER_MANA, bot->GetMaxPower(POWER_MANA));
                Dire(maitre, d->nom + std::string(" te rejoint."));
                EnvoyerListe(maitre);
            }
        }
        // apparence et faction
        time_t now = time(nullptr);
        bool demon = d->ultBuff == 7 && a.buffFin > now;
        uint32 disp = demon ? 7970 : d->display;
        if (disp && bot->GetDisplayId() != disp)
            bot->SetDisplayId(disp);
        if (d->display && std::fabs(bot->GetObjectScale() - d->scale) > 0.01f)
            bot->SetObjectScale(d->scale);
        if (bot->GetTeam() != maitre->GetTeam() && bot->GetUInt32Value(UNIT_FIELD_FACTIONTEMPLATE) != maitre->GetUInt32Value(UNIT_FIELD_FACTIONTEMPLATE))
            bot->setFaction(maitre->GetUInt32Value(UNIT_FIELD_FACTIONTEMPLATE));
        Auras(bot, maitre, *p, a);
        Groupe(bot, maitre, a);
        // loin du joueur (autre carte, plus de 80 m) : téléporté à côté de lui
        if (bot->IsAlive() && (bot->GetMapId() != maitre->GetMapId() || (!bot->IsInCombat() && bot->GetDistance(maitre) > 80.0f)))
            bot->TeleportTo(maitre->GetMapId(), maitre->GetPositionX(), maitre->GetPositionY(), maitre->GetPositionZ(), maitre->GetOrientation());
        // mort hors combat : relevé à côté du joueur au bout de 15 s
        if (!bot->IsAlive())
        {
            a.mortDepuis = maitre->IsInCombat() ? 0 : a.mortDepuis + 1000;
            if (a.mortDepuis >= 15000 && maitre->IsAlive())
            {
                a.mortDepuis = 0;
                bot->ResurrectPlayer(0.5f);
                bot->SpawnCorpseBones();
                bot->TeleportTo(maitre->GetMapId(), maitre->GetPositionX(), maitre->GetPositionY(), maitre->GetPositionZ(), maitre->GetOrientation());
            }
        }
        else
            a.mortDepuis = 0;
        a.combatDepuis = bot->IsInCombat() ? a.combatDepuis + 1000 : 0;
        if (bot->IsAlive() && bot->IsInCombat())
            Ultime(bot, maitre, a);
    }

    // sorts : seuls ceux de la fiche (tous les rangs jusqu'au niveau), les postures et quelques sorts de service ;
    // talents de la vraie classe : seulement les talents clés de la spé ; aucun point de talent libre
    void CompagnonsModule::Sorts(Player* bot, uint32 cpg)
    {
        Compagnon const* d = Def(cpg);
        uint32 L = bot->GetLevel();
        std::unordered_set<uint32> ok;
        for (uint32 i = 0; i < d->nSorts; ++i)
        {
            ok.insert(d->sorts[i].id);
            if (d->sorts[i].niveau <= L && !bot->HasSpell(d->sorts[i].id))
                bot->learnSpell(d->sorts[i].id, false);
        }
        // talents clés (avec, pour Vol'jin, les rangs gagnés par ses propres talents)
        std::vector<uint32> cles(d->cles, d->cles + d->nCles);
        if (CpgPossession* p = Possession(botProprio[bot->GetGUIDLow()], cpg))
        {
            std::vector<uint32> rangs = Rangs(*p, L);
            for (uint32 t = 0; t < 10; ++t)
                for (uint32 e = 0; e < d->talents[t].n; ++e)
                    if (d->talents[t].effets[e].genre == 3 && d->talents[t].effets[e].a == SP_PACTE && rangs[t] && !cles.empty() && cles[0])
                        if (TalentSpellPos const* pos = GetTalentSpellPos(cles[0]))
                            if (TalentEntry const* te = sTalentStore.LookupEntry(pos->talent_id))
                            {
                                uint32 rk = std::min<uint32>(4, pos->rank + rangs[t]);
                                while (rk > 0 && !te->RankID[rk])
                                    --rk;
                                cles[0] = te->RankID[rk];
                            }
        }
        for (uint32 c : cles)
            if (c && !bot->HasSpell(c))
                bot->learnSpell(c, false, true);
        std::vector<uint32> retirer;
        for (auto const& kv : bot->GetSpellMap())
        {
            if (kv.second.state == PLAYERSPELL_REMOVED || kv.second.disabled)
                continue;
            uint32 id = kv.first;
            if (ok.count(id) || std::find(cles.begin(), cles.end(), id) != cles.end() || Implicite(d->cls, id))
                continue;
            if (GetTalentSpellPos(id))
            {
                // un sort appris par un talent clé (ex. Lames spectrales) reste
                bool garde = false;
                for (uint32 c : cles)
                    if (c == id)
                        garde = true;
                if (!garde)
                    retirer.push_back(id);
                continue;
            }
            if (EstSortDeClasse(id))
                retirer.push_back(id);
        }
        for (uint32 id : retirer)
            bot->removeSpell(id, false, false);
        if (bot->GetFreeTalentPoints())
            bot->SetFreeTalentPoints(0);
    }

    // équipement : armes de la tranche de niveau, tenue thématique, rien d'autre que ce que le joueur a posé (cou, anneaux, bijoux)
    void CompagnonsModule::Equipement(Player* bot, uint32 cpg)
    {
        Compagnon const* d = Def(cpg);
        uint8 tr = Tranche(bot->GetLevel());
        // emplacements des armes : 1re arme en main droite, bouclier ou 2e arme en main gauche, fusil et arc à distance
        std::vector<std::pair<uint8, uint32>> voulu;
        bool main = false;
        for (uint32 i = 0; i < d->nArmes; ++i)
        {
            uint8 g = d->armesGenre[i];
            uint32 entry = d->armes[i * 12 + tr];
            uint8 slot;
            if (g == 9 || g == 10)
                slot = EQUIPMENT_SLOT_RANGED;
            else if (g == 11)
                slot = EQUIPMENT_SLOT_OFFHAND;
            else if (!main)
            {
                slot = EQUIPMENT_SLOT_MAINHAND;
                main = true;
            }
            else
                slot = EQUIPMENT_SLOT_OFFHAND;
            voulu.emplace_back(slot, entry);
        }
        // tenue : chaque pièce va à l'emplacement de son type
        for (uint32 i = 0; i < d->nTenue; ++i)
            if (ItemPrototype const* tp = d->tenue[i] ? sObjectMgr.GetItemPrototype(d->tenue[i]) : nullptr)
            {
                uint8 slot = 0xFF;
                switch (tp->InventoryType)
                {
                    case INVTYPE_HEAD: slot = EQUIPMENT_SLOT_HEAD; break;
                    case INVTYPE_SHOULDERS: slot = EQUIPMENT_SLOT_SHOULDERS; break;
                    case INVTYPE_CHEST: case INVTYPE_ROBE: slot = EQUIPMENT_SLOT_CHEST; break;
                    case INVTYPE_WRISTS: slot = EQUIPMENT_SLOT_WRISTS; break;
                    case INVTYPE_HANDS: slot = EQUIPMENT_SLOT_HANDS; break;
                    case INVTYPE_WAIST: slot = EQUIPMENT_SLOT_WAIST; break;
                    case INVTYPE_LEGS: slot = EQUIPMENT_SLOT_LEGS; break;
                    case INVTYPE_FEET: slot = EQUIPMENT_SLOT_FEET; break;
                    default: break;
                }
                if (slot != 0xFF)
                    voulu.emplace_back(slot, d->tenue[i]);
            }
        // deux armes à une main : ambidextrie
        bool deuxArmes = false;
        for (uint32 i = 0; i < d->nArmes; ++i)
            if (i > 0 && d->armesGenre[i] <= 3 && d->armesGenre[0] <= 3)
                deuxArmes = true;
        if (deuxArmes && !bot->HasSpell(674))
            bot->learnSpell(674, false);
        // emplacements que seul le module remplit : vidés s'ils contiennent autre chose
        static const uint8 GERES[] = { EQUIPMENT_SLOT_HEAD, EQUIPMENT_SLOT_SHOULDERS, EQUIPMENT_SLOT_BODY, EQUIPMENT_SLOT_CHEST, EQUIPMENT_SLOT_WAIST,
                                       EQUIPMENT_SLOT_LEGS, EQUIPMENT_SLOT_FEET, EQUIPMENT_SLOT_WRISTS, EQUIPMENT_SLOT_HANDS, EQUIPMENT_SLOT_BACK,
                                       EQUIPMENT_SLOT_MAINHAND, EQUIPMENT_SLOT_OFFHAND, EQUIPMENT_SLOT_RANGED, EQUIPMENT_SLOT_TABARD };
        for (uint8 s : GERES)
        {
            uint32 entry = 0;
            for (auto const& v : voulu)
                if (v.first == s)
                    entry = v.second;
            Item* it = bot->GetItemByPos(INVENTORY_SLOT_BAG_0, s);
            if (it && it->GetEntry() == entry)
                continue;
            if (it)
                bot->DestroyItem(INVENTORY_SLOT_BAG_0, s, true);
            if (!entry)
                continue;
            ItemPrototype const* proto = sObjectMgr.GetItemPrototype(entry);
            if (!proto)
                continue;
            Maniement(bot, proto);
            uint16 dest;
            if (bot->CanEquipNewItem(s, dest, entry, false) == EQUIP_ERR_OK)
                bot->EquipNewItem(dest, entry, true);
        }
        // munitions : arc ou fusil, toujours de quoi tirer
        if (Item* tir = bot->GetItemByPos(INVENTORY_SLOT_BAG_0, EQUIPMENT_SLOT_RANGED))
        {
            uint32 sub = tir->GetProto()->SubClass;
            if (sub == ITEM_SUBCLASS_WEAPON_BOW || sub == ITEM_SUBCLASS_WEAPON_GUN || sub == ITEM_SUBCLASS_WEAPON_CROSSBOW)
            {
                static const uint32 FLECHES[5][2] = { { 51, 19316 }, { 40, 11285 }, { 25, 3030 }, { 10, 2515 }, { 1, 2512 } };
                static const uint32 BALLES[5][2] = { { 51, 19317 }, { 40, 11284 }, { 25, 3033 }, { 10, 2519 }, { 1, 2516 } };
                auto const& t = sub == ITEM_SUBCLASS_WEAPON_GUN ? BALLES : FLECHES;
                uint32 mun = 0;
                for (auto const& m : t)
                    if (bot->GetLevel() >= m[0])
                    {
                        mun = m[1];
                        break;
                    }
                if (mun && bot->GetItemCount(mun) < 200)
                {
                    ItemPosCountVec dest;
                    if (bot->CanStoreNewItem(NULL_BAG, NULL_SLOT, dest, mun, 400) == EQUIP_ERR_OK)
                        bot->StoreNewItem(dest, mun, true);
                }
                if (mun && bot->GetUInt32Value(PLAYER_AMMO_ID) != mun)
                    bot->SetAmmo(mun);
            }
        }
    }

    // auras : puissance de la rareté, stuff de base, orbes, talents ; bonus des invocations et du familier
    void CompagnonsModule::Auras(Player* bot, Player* maitre, CpgPossession const& p, CpgActif& a)
    {
        Compagnon const* d = Def(p.cpg);
        uint32 L = bot->GetLevel();
        int32 vals[CANAUX_N] = {};
        int32 pets[CANAUX_N] = {};
        vals[CA_DEGATS] += PuissanceDegats(d) - 100;
        vals[CA_SOINS] += PuissanceSoins(d) - 100;
        if (d->role == 0 && PuissanceDegats(d) > 0)     // tank : même menace qu'avant la baisse de ses dégâts
            vals[CA_MENACE] += int32(std::lround(100.0f * PUISSANCE[d->rarete] / PuissanceDegats(d))) - 100;
        bool bouclier = false;
        for (uint32 i = 0; i < d->nArmes; ++i)
            if (d->armesGenre[i] == 11)
                bouclier = true;
        Stuff(d, L, bouclier, vals);
        for (uint32 o : p.orbes)
        {
            uint32 c, n;
            if (Orbe(o, c, n))
                OrbeStats(c, std::min(n, L + 5), vals);
        }
        // artefacts : statistiques de l'objet (sans les améliorations de la machine, liées au personnage du joueur)
        std::vector<uint32> equipes;
        for (uint32 e : p.artefacts)
            if (ItemPrototype const* ap = e ? sObjectMgr.GetItemPrototype(e) : nullptr)
            {
                for (uint32 i = 0; i < MAX_ITEM_PROTO_STATS; ++i)
                    switch (ap->ItemStat[i].ItemStatType)
                    {
                        case ITEM_MOD_STAMINA: vals[CA_STAT_ENDU] += ap->ItemStat[i].ItemStatValue; break;
                        case ITEM_MOD_STRENGTH: vals[CA_STAT_FOR] += ap->ItemStat[i].ItemStatValue; break;
                        case ITEM_MOD_AGILITY: vals[CA_STAT_AGI] += ap->ItemStat[i].ItemStatValue; break;
                        case ITEM_MOD_INTELLECT: vals[CA_STAT_INT] += ap->ItemStat[i].ItemStatValue; break;
                        default: break;
                    }
                vals[CA_ARMURE] += int32(ap->Armor);
                for (uint32 i = 0; i < MAX_ITEM_PROTO_SPELLS; ++i)
                    if (ap->Spells[i].SpellId && ap->Spells[i].SpellTrigger == ITEM_SPELLTRIGGER_ON_EQUIP)
                        equipes.push_back(ap->Spells[i].SpellId);
            }
        for (uint32 sp : a.sortsArtefacts)
            if (std::find(equipes.begin(), equipes.end(), sp) == equipes.end())
                bot->RemoveAurasDueToSpell(sp);
        for (uint32 sp : equipes)
            if (!bot->HasAura(sp))
                bot->CastSpell(bot, sp, TRIGGERED_OLD_TRIGGERED);
        a.sortsArtefacts = equipes;
        std::vector<uint32> rangs = Rangs(p, L);
        std::vector<std::pair<uint32, int32>> mods;
        for (uint32 t = 0; t < 10; ++t)
        {
            uint32 r = rangs[t];
            Talent const& ta = d->talents[t];
            for (uint32 e = 0; e < ta.n; ++e)
            {
                EffetTalent const& ef = ta.effets[e];
                if (ef.genre == 1 && ef.a < CANAUX_N)
                    (ef.pet ? pets : vals)[ef.a] += r * ef.valeur;
                else if (ef.genre == 2)
                    mods.emplace_back(ef.a, int32(r) * ef.valeur);
            }
        }
        // bonus de l'ultime géré par le module
        time_t now = time(nullptr);
        if (a.buffFin > now)
        {
            if (d->ultBuff == 1 || d->ultBuff == 2)
                pets[CA_DEGATS] += d->ultBuffVal;
            else if (d->ultBuff == 4)
                pets[CA_SUBIS] += d->ultBuffVal;
        }
        for (uint32 k = 0; k < CANAUX_N; ++k)
            SetSort(bot, CANAL_SORT[k], vals[k]);
        for (auto const& m : mods)
            SetSort(bot, m.first, m.second);
        // familier et invocations
        std::vector<Unit*> unites;
        bot->CallForAllControlledUnits([&](Unit* u) { if (u && u->IsAlive()) unites.push_back(u); }, CONTROLLED_PET | CONTROLLED_GUARDIANS);
        for (Unit* u : unites)
            for (uint32 k = 0; k < CANAUX_N; ++k)
                if (k == CA_DEGATS || k == CA_CRIT || k == CA_PV || k == CA_ARMURE_PCT || k == CA_HATE || k == CA_SUBIS || k == CA_MENACE ||
                    k == CA_ESQUIVE || k == CA_PARADE)
                    SetSort(u, CANAL_SORT[k], pets[k] + (k == CA_DEGATS ? PuissanceDegats(d) - 100 : 0));
    }

    void CompagnonsModule::Groupe(Player* bot, Player* maitre, CpgActif& a)
    {
        Group* g = maitre->GetGroup();
        if (g && g->IsMember(bot->GetObjectGuid()))
        {
            a.groupe = true;
            return;
        }
        if (a.groupe)
        {
            // le joueur l'a exclu du groupe (ou a quitté le groupe) : il rentre chez lui
            a.renvoi = true;
            return;
        }
        if (!g)
        {
            g = new Group();
            if (g->Create(maitre->GetObjectGuid(), maitre->GetName()))
                sObjectMgr.AddGroup(g);
            else
            {
                delete g;
                return;
            }
        }
        if (bot->GetGroup())
            bot->RemoveFromGroup();
        if (g->IsFull())
            return;
        if (g->AddMember(bot->GetObjectGuid(), NomAffiche(bot->GetGUIDLow())))
            a.groupe = true;
    }

    // ultime : lancé par le module selon le rôle (recharge 3 min)
    void CompagnonsModule::Ultime(Player* bot, Player* maitre, CpgActif& a)
    {
        Compagnon const* d = Def(a.cpg);
        CpgPossession* p = Possession(a.proprio, a.cpg);
        if (!d || !p || !d->ultime)
            return;
        std::vector<uint32> rangs = Rangs(*p, bot->GetLevel());
        if (!rangs[10])
            return;
        time_t now = time(nullptr);
        if (now - a.ultime < 180 || a.combatDepuis < 4000 || bot->IsNonMeleeSpellCasted(false))
            return;
        Unit* cible = bot->GetVictim();
        if (!cible)
            cible = maitre->GetVictim();
        if (!cible)
            for (Unit* att : bot->getAttackers())
                if (att && att->IsAlive())
                {
                    cible = att;
                    break;
                }
        if (!cible || !cible->IsAlive() || !bot->IsWithinDistInMap(cible, 35.0f))
            return;
        // conditions selon le rôle
        uint32 ennemis = 0;
        float minPv = 100.0f;
        if (Group* g = maitre->GetGroup())
            for (GroupReference* ref = g->GetFirstMember(); ref; ref = ref->next())
                if (Player* m = ref->getSource())
                    if (m->IsInMap(bot) && m->IsAlive())
                    {
                        ennemis += uint32(m->getAttackers().size());
                        minPv = std::min(minPv, m->GetHealthPercent());
                    }
        bool elite = cible->GetTypeId() == TYPEID_UNIT && static_cast<Creature*>(cible)->IsElite();
        bool lancer = false;
        switch (d->role)
        {
            case 0: lancer = ennemis >= 3 || bot->GetHealthPercent() < 60.0f || elite; break;
            case 1: lancer = minPv < 45.0f; break;
            default: lancer = ennemis >= 3 || elite || cible->GetHealthPercent() > 60.0f; break;
        }
        if (!lancer)
            return;
        Unit* lanceur = bot;
        if (d->ultGeant)
            bot->CallForAllControlledUnits([&](Unit* u) { if (u && u->IsAlive() && u->GetEntry() == 990545) lanceur = u; }, CONTROLLED_GUARDIANS);
        a.ultime = now;
        lanceur->CastSpell(cible, d->ultime, TRIGGERED_OLD_TRIGGERED, nullptr, nullptr, bot->GetObjectGuid());
        for (uint32 i = 0; i < d->nUltExtra; ++i)
        {
            uint32 sp = d->ultExtra[i];
            if (!sp)
                continue;
            if (d->ultBuff == 8)
            {
                int32 v = int32(bot->GetMaxHealth() * 15 / 100);
                bot->CastCustomSpell(bot, sp, &v, nullptr, nullptr, TRIGGERED_OLD_TRIGGERED);
            }
            else
                lanceur->CastSpell(lanceur, sp, TRIGGERED_OLD_TRIGGERED, nullptr, nullptr, bot->GetObjectGuid());
        }
        if (d->ultSoin)
            bot->CastSpell(bot, d->ultSoin, TRIGGERED_OLD_TRIGGERED);
        for (uint32 i = 0; i < d->ultFils && cible->IsAlive(); ++i)
            bot->CastSpell(cible, 40301, TRIGGERED_OLD_TRIGGERED);
        if (d->ultBuff)
            a.buffFin = now + d->ultBuffDur / 1000;
    }

    // ------------------------------------------------------------------ effets spéciaux des talents

    void CompagnonsModule::OnDealDamage(Unit* unit, Unit* victim, uint32 health, uint32 damage)
    {
        if (!unit || !victim || !damage || s_depth > 0)
            return;
        // tri rapide sans verrou (appelé à chaque coup sur tout le serveur) : la table n'est modifiée que par le fil du monde,
        // jamais pendant la mise à jour des cartes
        Unit* maitreUnite = unit->GetTypeId() == TYPEID_PLAYER ? unit : unit->GetOwner();
        bool frappe = maitreUnite && maitreUnite->GetTypeId() == TYPEID_PLAYER && botCpg.count(maitreUnite->GetGUIDLow());
        bool frappeSur = victim->GetTypeId() == TYPEID_PLAYER && botCpg.count(victim->GetGUIDLow());
        if (!frappe && !frappeSur)
            return;
        Profondeur prof;
        std::lock_guard<std::recursive_mutex> l(lock);
        // le compagnon (ou son familier) frappe
        Player* bot = nullptr;
        bool parFamilier = false;
        if (unit->GetTypeId() == TYPEID_PLAYER)
            bot = static_cast<Player*>(unit);
        else if (Unit* owner = unit->GetOwner())
            if (owner->GetTypeId() == TYPEID_PLAYER)
            {
                bot = static_cast<Player*>(owner);
                parFamilier = true;
            }
        auto valeur = [&](Player* b, uint32 code) -> int32
        {
            auto it = botCpg.find(b->GetGUIDLow());
            if (it == botCpg.end())
                return 0;
            Compagnon const* d = Def(it->second);
            CpgPossession* p = Possession(botProprio[b->GetGUIDLow()], it->second);
            if (!d || !p)
                return 0;
            std::vector<uint32> rangs = Rangs(*p, b->GetLevel());
            int32 v = 0;
            for (uint32 t = 0; t < 10; ++t)
                for (uint32 e = 0; e < d->talents[t].n; ++e)
                    if (d->talents[t].effets[e].genre == 3 && d->talents[t].effets[e].a == code)
                        v += int32(rangs[t]) * d->talents[t].effets[e].valeur;
            return v;
        };
        if (bot && botCpg.count(bot->GetGUIDLow()) && victim != bot)
        {
            Compagnon const* d = Def(botCpg[bot->GetGUIDLow()]);
            uint32 dmg = std::min(damage, health);
            if (!parFamilier)
            {
                // vol de vie (talent ou ultime)
                int32 vv = valeur(bot, SP_VOLVIE);
                for (auto const& a : actifs)
                    if (a.bot == bot->GetGUIDLow() && d && d->ultBuff == 5 && a.buffFin > time(nullptr))
                        vv += d->ultBuffVal;
                if (vv > 0 && bot->IsAlive())
                    bot->SetHealth(std::min(bot->GetMaxHealth(), bot->GetHealth() + dmg * uint32(vv) / 100));
                // dégâts en plus selon l'état de la cible
                int32 bonus = 0;
                if (victim->HasAuraType(SPELL_AURA_MOD_STUN))
                    bonus += valeur(bot, SP_CIBLE_ETOURDIE);
                if (victim->GetHealthPercent() < 30.0f)
                    bonus += valeur(bot, SP_CIBLE_BASSE);
                if (victim->GetTypeId() == TYPEID_UNIT && static_cast<Creature*>(victim)->IsElite())
                    bonus += valeur(bot, SP_ELITE);
                if (int32 mq = valeur(bot, SP_MARQUEE))
                {
                    bool marquee = false;
                    for (auto const& h : victim->GetSpellAuraHolderMap())
                        if (h.second->GetCasterGuid() == bot->GetObjectGuid())
                            marquee = true;
                    if (marquee)
                        bonus += mq;
                }
                if (bonus > 0 && victim->IsAlive())
                {
                    int32 bp = std::max<int32>(1, int32(dmg) * bonus / 100);
                    bot->CastCustomSpell(victim, EXTRA_SORT[0], &bp, nullptr, nullptr, TRIGGERED_OLD_TRIGGERED);
                }
                // poisons
                int32 chance = (d && d->poison ? 20 : 0) + valeur(bot, SP_POISON);
                if (chance > 0 && victim->IsAlive() && roll_chance_i(chance))
                {
                    static const uint32 POISON[6][2] = { { 60, 11337 }, { 52, 11336 }, { 44, 11335 }, { 36, 8689 }, { 28, 8685 }, { 20, 8680 } };
                    for (auto const& pz : POISON)
                        if (bot->GetLevel() >= pz[0])
                        {
                            bot->CastSpell(victim, pz[1], TRIGGERED_OLD_TRIGGERED);
                            break;
                        }
                }
            }
            else if (int32 bs = valeur(bot, SP_BETE_SOIN))
            {
                if (roll_chance_i(20) && bot->IsAlive())
                    bot->SetHealth(std::min(bot->GetMaxHealth(), bot->GetHealth() + bot->GetMaxHealth() * uint32(bs) / 100));
            }
        }
        // le compagnon est frappé
        if (victim->GetTypeId() == TYPEID_PLAYER && botCpg.count(victim->GetGUIDLow()))
        {
            Player* b = static_cast<Player*>(victim);
            Compagnon const* d = Def(botCpg[b->GetGUIDLow()]);
            if (int32 mc = valeur(b, SP_MANA_COUP))
                if (b->GetPowerType() == POWER_MANA)
                    b->ModifyPower(POWER_MANA, int32(b->GetMaxPower(POWER_MANA)) * mc / 100);
            if (int32 fv = valeur(b, SP_FERVEUR))
                if (roll_chance_i(fv))
                    b->CastSpell(b, 42300, TRIGGERED_OLD_TRIGGERED);
            for (auto const& a : actifs)
                if (a.bot == b->GetGUIDLow() && d && d->ultBuff == 6 && a.buffFin > time(nullptr))
                {
                    b->ModifyPower(POWER_ENERGY, d->ultBuffVal);
                    b->CastSpell(b, 42300, TRIGGERED_OLD_TRIGGERED);
                }
        }
    }

    // points de combo en plus, Fils en plus
    void CompagnonsModule::OnHit(Spell* spell, Unit* caster, Unit* victim)
    {
        if (!spell || !caster || !victim || s_depth > 0 || caster->GetTypeId() != TYPEID_PLAYER || !spell->m_spellInfo)
            return;
        if (!botCpg.count(caster->GetGUIDLow()))          // tri rapide sans verrou (voir OnDealDamage)
            return;
        Profondeur prof;
        std::lock_guard<std::recursive_mutex> l(lock);
        auto it = botCpg.find(caster->GetGUIDLow());
        if (it == botCpg.end())
            return;
        Player* bot = static_cast<Player*>(caster);
        Compagnon const* d = Def(it->second);
        CpgPossession* p = Possession(botProprio[bot->GetGUIDLow()], it->second);
        if (!d || !p)
            return;
        std::vector<uint32> rangs = Rangs(*p, bot->GetLevel());
        int32 combo = 0, fils = 0;
        for (uint32 t = 0; t < 10; ++t)
            for (uint32 e = 0; e < d->talents[t].n; ++e)
            {
                EffetTalent const& ef = d->talents[t].effets[e];
                if (ef.genre != 3)
                    continue;
                if (ef.a == SP_COMBO) combo += int32(rangs[t]) * ef.valeur;
                if (ef.a == SP_FILS2) fils += int32(rangs[t]) * ef.valeur;
            }
        SpellEntry const* info = spell->m_spellInfo;
        bool donneCombo = false;
        for (int i = 0; i < 3; ++i)
            if (info->Effect[i] == SPELL_EFFECT_ADD_COMBO_POINTS)
                donneCombo = true;
        if (combo > 0 && donneCombo && roll_chance_i(combo))
            bot->AddComboPoints(victim, 1);
        if (fils > 0 && d->nPremiers && info->Id == d->premiers[0] && victim->IsAlive() && roll_chance_i(fils))
            bot->CastSpell(victim, 40301, TRIGGERED_OLD_TRIGGERED);
    }

    // ------------------------------------------------------------------ orbes du compagnon : butin des élites rares et des boss finaux de donjon
    // une orbe au niveau de la créature (couleur au hasard) : élite rare 20 %, boss final 30 % ; jets de groupe normaux (les compagnons n'y ont pas droit)
    static const uint32 BOSS_FINAUX[] = { 11520, 639, 3654, 4275, 1716, 4829, 7800, 4421, 4543, 6487, 3975, 3977, 7358, 2748, 7267, 12201, 5709, 9019,
                                          9568, 11492, 11486, 11501, 10813, 10440 };

    bool CompagnonsModule::OnFillLoot(Loot* loot, Player* owner)
    {
        if (!loot || !owner || loot->GetLootType() != LOOT_CORPSE || !loot->GetLootTarget() || loot->GetLootTarget()->GetTypeId() != TYPEID_UNIT)
            return false;
        Creature const* c = static_cast<Creature const*>(loot->GetLootTarget());
        Map* map = c->GetMap();
        if (!map || !map->IsDungeon())
            return false;
        uint32 entry = c->GetEntry();
        CreatureInfo const* info = c->GetCreatureInfo();
        bool rare = (entry >= 990400 && entry <= 990412) || (info && (info->Rank == CREATURE_ELITE_RAREELITE || info->Rank == CREATURE_ELITE_RARE));
        bool final = std::find(std::begin(BOSS_FINAUX), std::end(BOSS_FINAUX), entry) != std::end(BOSS_FINAUX);
        if (!(final ? roll_chance_i(30) : rare && roll_chance_i(20)))
            return false;
        uint32 niveau = std::max<uint32>(10, std::min<uint32>(60, c->GetLevel()));
        loot->AddItem(ORBE_PREMIER + urand(0, 4) * 51 + (niveau - 10), 1, 0, 0);
        return false;                       // le butin normal est généré quand même
    }

    // ------------------------------------------------------------------ livraison des achats (type 2 : compagnon)
    void CompagnonsModule::Livrer()
    {
        auto r = CharacterDatabase.Query("SELECT `id`, `guid`, `item` FROM `custom_boutique_livraison` WHERE `statut` = 0 AND `type` = 2 ORDER BY `id` LIMIT 20");
        if (!r)
            return;
        std::vector<std::pair<uint32, uint32>> faits;
        do
        {
            Field* f = r->Fetch();
            uint32 id = f[0].GetUInt32(), guid = f[1].GetUInt32(), cpg = f[2].GetUInt32();
            Compagnon const* d = Def(cpg);
            if (!d)
            {
                faits.emplace_back(id, 2);
                continue;
            }
            CharacterDatabase.PExecute("INSERT IGNORE INTO `custom_cpg` (`proprio`, `cpg`, `date`) VALUES (%u, %u, NOW())", guid, cpg);
            if (charges.count(guid))
            {
                bool deja = false;
                for (auto const& p : possessions[guid])
                    if (p.cpg == cpg)
                        deja = true;
                if (!deja)
                {
                    CpgPossession p;
                    p.cpg = cpg;
                    possessions[guid].push_back(p);
                }
            }
            ObjectGuid og(HIGHGUID_PLAYER, guid);
            Player* pl = sObjectMgr.GetPlayer(og);
            MailDraft draft(std::string("Boutique : ") + d->nom, std::string("Merci pour ton soutien ! Voici la pierre de ") + d->nom +
                            ". Utilise-la pour l'appeler à tes côtés (ou ouvre l'onglet Compagnons).");
            if (Item* it = Item::CreateItem(d->pierre, 1, pl))
            {
                it->SaveToDB();
                draft.AddItem(it);
            }
            draft.SendMailTo(MailReceiver(pl, og), MailSender(MAIL_NORMAL, uint32(0), MAIL_STATIONERY_GM));
            if (pl)
                EnvoyerListe(pl);
            faits.emplace_back(id, 1);
        }
        while (r->NextRow());
        for (auto const& fa : faits)
            CharacterDatabase.DirectPExecute("UPDATE `custom_boutique_livraison` SET `statut` = %u WHERE `id` = %u", fa.second, fa.first);
    }

    int32 CompagnonsModule::Solde(uint32 compte)
    {
        if (auto r = LoginDatabase.PQuery("SELECT `solde` FROM `portail_gen` WHERE `compte` = %u", compte))
            return r->Fetch()[0].GetInt32();
        return 0;
    }

    // ------------------------------------------------------------------ addon : liste et fiche
    void CompagnonsModule::EnvoyerListe(Player* p)
    {
        Charger(p->GetGUIDLow());
        std::ostringstream out;
        out << "L " << Solde(p->GetSession()->GetAccountId()) << " ";
        bool premier = true;
        for (auto const& po : possessions[p->GetGUIDLow()])
        {
            bool actif = false;
            for (auto const& a : actifs)
                if (a.proprio == p->GetGUIDLow() && a.cpg == po.cpg)
                    actif = true;
            out << (premier ? "" : ";") << po.cpg << ":" << (actif ? 1 : 0);
            premier = false;
        }
        Addon(p, out.str());
    }

    bool CompagnonsModule::HandleListe(WorldSession* session, const std::string& /*args*/)
    {
        std::lock_guard<std::recursive_mutex> l(lock);
        if (Player* p = session->GetPlayer())
            EnvoyerListe(p);
        return true;
    }

    void CompagnonsModule::EnvoyerFiche(Player* p, uint32 cpg)
    {
        Compagnon const* d = Def(cpg);
        CpgPossession* po = Possession(p->GetGUIDLow(), cpg);
        if (!d || !po)
            return;
        uint32 L = p->GetLevel();
        std::vector<uint32> rangs = Rangs(*po, L);
        int32 vals[CANAUX_N] = {};
        bool bouclier = false;
        for (uint32 i = 0; i < d->nArmes; ++i)
            if (d->armesGenre[i] == 11)
                bouclier = true;
        Stuff(d, L, bouclier, vals);
        for (uint32 o : po->orbes)
        {
            uint32 c, n;
            if (Orbe(o, c, n))
                OrbeStats(c, std::min(n, L + 5), vals);
        }
        Player* bot = po->bot ? sObjectMgr.GetPlayer(ObjectGuid(HIGHGUID_PLAYER, po->bot)) : nullptr;
        std::ostringstream out;
        out << "F " << cpg << "|" << L << "|" << (L > 20 ? L - 20 : 0) << "|";
        for (uint32 r : rangs)
            out << r;
        out << (po->talents.empty() ? "A" : "M") << "|";
        // statistiques : celles du compagnon s'il est là, sinon celles de son stuff
        if (bot && bot->IsInWorld())
            out << "pv=" << bot->GetMaxHealth() << ",endu=" << int32(bot->GetStat(STAT_STAMINA)) << ",for=" << int32(bot->GetStat(STAT_STRENGTH))
                << ",agi=" << int32(bot->GetStat(STAT_AGILITY)) << ",int=" << int32(bot->GetStat(STAT_INTELLECT))
                << ",armure=" << bot->GetArmor() << ",pa=" << bot->GetTotalAttackPowerValue(BASE_ATTACK)
                << ",ps=" << bot->SpellBaseDamageBonusDone(SPELL_SCHOOL_MASK_ALL) << ",soins=" << bot->SpellBaseHealingBonusDone(SPELL_SCHOOL_MASK_ALL);
        else
            out << "endu=" << vals[CA_STAT_ENDU] << ",for=" << vals[CA_STAT_FOR] << ",agi=" << vals[CA_STAT_AGI] << ",int=" << vals[CA_STAT_INT]
                << ",armure=" << vals[CA_ARMURE] << ",pa=" << vals[CA_PA] << ",ps=" << vals[CA_PS] << ",soins=" << vals[CA_SOIN_BONUS];
        out << ",crit=" << (vals[CA_CRIT] + vals[CA_CRIT_SORTS]) << ",toucher=" << (vals[CA_TOUCHER] + vals[CA_TOUCHER_SORTS])
            << ",def=" << vals[CA_DEFENSE] << ",puissance=" << PUISSANCE[d->rarete] << ",stuff=" << STUFF[d->rarete];
        Addon(p, out.str());
        // 2e message : ce que le joueur a posé sur le compagnon
        out.str("");
        out << "G " << cpg << "|";
        // emplacements que le joueur peut changer : cou, anneaux, bijoux (sur le compagnon), orbes, artefacts
        static const uint8 SLOTS[5] = { EQUIPMENT_SLOT_NECK, EQUIPMENT_SLOT_FINGER1, EQUIPMENT_SLOT_FINGER2, EQUIPMENT_SLOT_TRINKET1, EQUIPMENT_SLOT_TRINKET2 };
        uint32 equip[5] = { 0, 0, 0, 0, 0 };
        if (bot && bot->IsInWorld())
        {
            for (int i = 0; i < 5; ++i)
                if (Item* it = bot->GetItemByPos(INVENTORY_SLOT_BAG_0, SLOTS[i]))
                    equip[i] = it->GetEntry();
        }
        else if (po->bot)
        {
            if (auto r = CharacterDatabase.PQuery("SELECT `slot`, `item_template` FROM `character_inventory` WHERE `guid` = %u AND `bag` = 0 AND `slot` IN (1, 10, 11, 12, 13)", po->bot))
                do
                {
                    Field* f = r->Fetch();
                    for (int i = 0; i < 5; ++i)
                        if (SLOTS[i] == f[0].GetUInt8())
                            equip[i] = f[1].GetUInt32();
                }
                while (r->NextRow());
        }
        for (int i = 0; i < 5; ++i)
            out << (i ? "," : "") << equip[i];
        out << "|" << po->orbes[0] << "," << po->orbes[1] << "|" << po->artefacts[0] << "," << po->artefacts[1] << "|";
        bool actif = false;
        for (auto const& a : actifs)
            if (a.proprio == p->GetGUIDLow() && a.cpg == cpg)
                actif = true;
        out << (actif ? 1 : 0);
        Addon(p, out.str());
    }

    bool CompagnonsModule::HandleFiche(WorldSession* session, const std::string& args)
    {
        std::lock_guard<std::recursive_mutex> l(lock);
        if (Player* p = session->GetPlayer())
            EnvoyerFiche(p, uint32(atoi(args.c_str())));
        return true;
    }

    bool CompagnonsModule::HandleInvoquer(WorldSession* session, const std::string& args)
    {
        Player* p = session->GetPlayer();
        if (!p)
            return true;
        if (p->IsInCombat())
        {
            Dire(p, "Impossible en combat.");
            return true;
        }
        Invoquer(p, uint32(atoi(args.c_str())));
        return true;
    }

    // .cpg renvoyer : tous les compagnons présents ; .cpg renvoyer <n> : celui-là
    bool CompagnonsModule::HandleRenvoyer(WorldSession* session, const std::string& args)
    {
        std::lock_guard<std::recursive_mutex> l(lock);
        Player* p = session->GetPlayer();
        if (!p)
            return true;
        uint32 voulu = uint32(atoi(args.c_str()));
        std::vector<uint32> liste;
        for (auto const& a : actifs)
            if (a.proprio == p->GetGUIDLow() && (!voulu || a.cpg == voulu))
                liste.push_back(a.cpg);
        if (liste.empty())
        {
            Dire(p, voulu ? "Ce compagnon n'est pas avec toi." : "Aucun compagnon avec toi.");
            return true;
        }
        for (uint32 c : liste)
            Renvoyer(p->GetGUIDLow(), c, true);
        return true;
    }

    // ------------------------------------------------------------------ addon : talents
    bool CompagnonsModule::HandleTalent(WorldSession* session, const std::string& args)
    {
        std::lock_guard<std::recursive_mutex> l(lock);
        Player* p = session->GetPlayer();
        if (!p)
            return true;
        std::istringstream in(args);
        uint32 cpg = 0, idx = 99;
        in >> cpg >> idx;
        Compagnon const* d = Def(cpg);
        CpgPossession* po = Possession(p->GetGUIDLow(), cpg);
        if (!d || !po || idx > 10)
            return true;
        uint32 points = p->GetLevel() > 20 ? p->GetLevel() - 20 : 0;
        std::vector<uint32> r(11, 0);
        if (!po->talents.empty())
            for (size_t i = 0; i < 11 && i < po->talents.size(); ++i)
                r[i] = uint32(po->talents[i] - '0');
        uint32 total = 0;
        for (uint32 v : r)
            total += v;
        uint32 palier = idx == 10 ? 5 : d->talents[idx].palier;
        uint32 avant = 0;                                  // points dans les paliers inférieurs
        for (uint32 t = 0; t < 10; ++t)
            if (d->talents[t].palier < palier)
                avant += r[t];
        uint32 max = idx == 10 ? 1 : 5;
        if (total >= points)
            Dire(p, "Plus de point de talent à dépenser.");
        else if (avant < 5 * (palier - 1))
            Dire(p, "Il faut " + std::to_string(5 * (palier - 1)) + " points dans les paliers précédents.");
        else if (r[idx] >= max)
            Dire(p, "Ce talent est déjà au maximum.");
        else
        {
            ++r[idx];
            po->talents.clear();
            for (uint32 v : r)
                po->talents += char('0' + v);
            Sauver(p->GetGUIDLow(), *po);
        }
        EnvoyerFiche(p, cpg);
        return true;
    }

    bool CompagnonsModule::HandleReset(WorldSession* session, const std::string& args)
    {
        std::lock_guard<std::recursive_mutex> l(lock);
        Player* p = session->GetPlayer();
        if (!p)
            return true;
        uint32 cpg = uint32(atoi(args.c_str()));
        if (CpgPossession* po = Possession(p->GetGUIDLow(), cpg))
        {
            po->talents = "00000000000";
            Sauver(p->GetGUIDLow(), *po);
            EnvoyerFiche(p, cpg);
        }
        return true;
    }

    // ------------------------------------------------------------------ addon : équipement modifiable
    // emplacements : 1 cou, 2 anneau 1, 3 anneau 2, 4 bijou 1, 5 bijou 2, 6 orbe 1, 7 orbe 2, 8 artefact 1, 9 artefact 2
    static bool Rendre(Player* p, uint32 entry)
    {
        ItemPosCountVec dest;
        if (p->CanStoreNewItem(NULL_BAG, NULL_SLOT, dest, entry, 1) != EQUIP_ERR_OK)
            return false;
        return p->StoreNewItem(dest, entry, true) != nullptr;
    }

    static InventoryResult PeutRanger(Player* p, ItemPosCountVec& dest, Item* it)
    {
        uint8 bagSlot = 0;
        return p->CanStoreItem(NULL_BAG, NULL_SLOT, dest, it, bagSlot, false);
    }

    static uint32 ArtefactCouleur(uint32 entry)
    {
        if (auto r = WorldDatabase.PQuery("SELECT `type` FROM `custom_relique_objet` WHERE `entry` = %u", entry))
            return r->Fetch()[0].GetUInt32();
        return 0;
    }

    bool CompagnonsModule::HandleEquiper(WorldSession* session, const std::string& args)
    {
        std::lock_guard<std::recursive_mutex> l(lock);
        Player* p = session->GetPlayer();
        if (!p)
            return true;
        std::istringstream in(args);
        uint32 cpg = 0, sac = 99, place = 0, empl = 0;
        in >> cpg >> sac >> place >> empl;
        Compagnon const* d = Def(cpg);
        CpgPossession* po = Possession(p->GetGUIDLow(), cpg);
        if (!d || !po || empl < 1 || empl > 9 || sac > 4)
            return true;
        if (p->IsInCombat())
        {
            Dire(p, "Impossible en combat.");
            return true;
        }
        uint8 bag = sac == 0 ? INVENTORY_SLOT_BAG_0 : uint8(INVENTORY_SLOT_BAG_START + sac - 1);
        uint8 slot = sac == 0 ? uint8(INVENTORY_SLOT_ITEM_START + place - 1) : uint8(place - 1);
        Item* item = p->GetItemByPos(bag, slot);
        if (!item)
        {
            Dire(p, "Aucun objet à cet endroit.");
            return true;
        }
        ItemPrototype const* proto = item->GetProto();
        uint32 entry = item->GetEntry();
        if (empl >= 6 && empl <= 7)
        {
            uint32 c, n;
            if (!Orbe(entry, c, n))
            {
                Dire(p, "Cet objet n'est pas une orbe du compagnon.");
                return true;
            }
            uint32 autre = po->orbes[empl == 6 ? 1 : 0], c2, n2;
            if (autre && Orbe(autre, c2, n2) && c2 == c)
            {
                Dire(p, "Ton compagnon porte déjà une orbe de cette couleur.");
                return true;
            }
            uint32& cur = po->orbes[empl - 6];
            uint32 un = 1;
            p->DestroyItemCount(*item, un, true);
            if (cur && !Rendre(p, cur))
            {
                Rendre(p, entry);
                Dire(p, "Fais de la place dans tes sacs.");
                return true;
            }
            cur = entry;
            Sauver(p->GetGUIDLow(), *po);
            EnvoyerFiche(p, cpg);
            return true;
        }
        if (empl >= 8)
        {
            uint32 coul = ArtefactCouleur(entry);
            if (!coul || coul > 4)
            {
                Dire(p, "Cet objet n'est pas un artefact.");
                return true;
            }
            uint32 autre = po->artefacts[empl == 8 ? 1 : 0];
            if (autre && ArtefactCouleur(autre) == coul)
            {
                Dire(p, "Ton compagnon porte déjà un artefact de cette couleur.");
                return true;
            }
            uint32& cur = po->artefacts[empl - 8];
            uint32 un = 1;
            p->DestroyItemCount(*item, un, true);
            if (cur && !Rendre(p, cur))
            {
                Rendre(p, entry);
                Dire(p, "Fais de la place dans tes sacs.");
                return true;
            }
            cur = entry;
            Sauver(p->GetGUIDLow(), *po);
            EnvoyerFiche(p, cpg);
            return true;
        }
        // cou, anneaux, bijoux : l'objet passe sur le compagnon (il doit être invoqué)
        Player* bot = po->bot ? sObjectMgr.GetPlayer(ObjectGuid(HIGHGUID_PLAYER, po->bot)) : nullptr;
        if (!bot || !bot->IsInWorld())
        {
            Dire(p, "Invoque ton compagnon pour changer son équipement.");
            return true;
        }
        static const uint8 SLOTS[6] = { 0, EQUIPMENT_SLOT_NECK, EQUIPMENT_SLOT_FINGER1, EQUIPMENT_SLOT_FINGER2, EQUIPMENT_SLOT_TRINKET1, EQUIPMENT_SLOT_TRINKET2 };
        static const uint32 TYPES[6] = { 0, INVTYPE_NECK, INVTYPE_FINGER, INVTYPE_FINGER, INVTYPE_TRINKET, INVTYPE_TRINKET };
        if (proto->InventoryType != TYPES[empl])
        {
            Dire(p, "Cet objet ne va pas à cet emplacement.");
            return true;
        }
        if (proto->RequiredLevel > bot->GetLevel())
        {
            Dire(p, "Niveau trop élevé pour ton compagnon.");
            return true;
        }
        uint8 s = SLOTS[empl];
        // l'ancien objet revient au joueur
        if (Item* ancien = bot->GetItemByPos(INVENTORY_SLOT_BAG_0, s))
        {
            ItemPosCountVec dest;
            if (PeutRanger(p, dest, ancien) != EQUIP_ERR_OK)
            {
                Dire(p, "Fais de la place dans tes sacs.");
                return true;
            }
            bot->MoveItemFromInventory(INVENTORY_SLOT_BAG_0, s, true);
            p->MoveItemToInventory(dest, ancien, true, true);
        }
        p->MoveItemFromInventory(bag, slot, true);
        item->SetOwnerGuid(bot->GetObjectGuid());
        uint16 dest;
        if (bot->CanEquipItem(s, dest, item, false) == EQUIP_ERR_OK)
        {
            bot->EquipItem(dest, item, true);
            item->SetState(ITEM_CHANGED, bot);
        }
        else
        {
            ItemPosCountVec back;
            if (PeutRanger(p, back, item) == EQUIP_ERR_OK)
                p->MoveItemToInventory(back, item, true, true);
            Dire(p, "Ton compagnon ne peut pas porter cet objet.");
        }
        p->SaveInventoryAndGoldToDB();
        bot->SaveInventoryAndGoldToDB();
        EnvoyerFiche(p, cpg);
        return true;
    }

    bool CompagnonsModule::HandleRetirer(WorldSession* session, const std::string& args)
    {
        std::lock_guard<std::recursive_mutex> l(lock);
        Player* p = session->GetPlayer();
        if (!p)
            return true;
        std::istringstream in(args);
        uint32 cpg = 0, empl = 0;
        in >> cpg >> empl;
        CpgPossession* po = Possession(p->GetGUIDLow(), cpg);
        if (!po || empl < 1 || empl > 9)
            return true;
        if (empl >= 6)
        {
            uint32& cur = empl <= 7 ? po->orbes[empl - 6] : po->artefacts[empl - 8];
            if (!cur)
                return true;
            if (!Rendre(p, cur))
            {
                Dire(p, "Fais de la place dans tes sacs.");
                return true;
            }
            cur = 0;
            Sauver(p->GetGUIDLow(), *po);
            EnvoyerFiche(p, cpg);
            return true;
        }
        Player* bot = po->bot ? sObjectMgr.GetPlayer(ObjectGuid(HIGHGUID_PLAYER, po->bot)) : nullptr;
        if (!bot || !bot->IsInWorld())
        {
            Dire(p, "Invoque ton compagnon pour changer son équipement.");
            return true;
        }
        static const uint8 SLOTS[6] = { 0, EQUIPMENT_SLOT_NECK, EQUIPMENT_SLOT_FINGER1, EQUIPMENT_SLOT_FINGER2, EQUIPMENT_SLOT_TRINKET1, EQUIPMENT_SLOT_TRINKET2 };
        Item* it = bot->GetItemByPos(INVENTORY_SLOT_BAG_0, SLOTS[empl]);
        if (!it)
            return true;
        ItemPosCountVec dest;
        if (PeutRanger(p, dest, it) != EQUIP_ERR_OK)
        {
            Dire(p, "Fais de la place dans tes sacs.");
            return true;
        }
        bot->MoveItemFromInventory(INVENTORY_SLOT_BAG_0, SLOTS[empl], true);
        p->MoveItemToInventory(dest, it, true, true);
        p->SaveInventoryAndGoldToDB();
        bot->SaveInventoryAndGoldToDB();
        EnvoyerFiche(p, cpg);
        return true;
    }

    // ------------------------------------------------------------------ addon : boutique en jeu (même catalogue et même solde que le portail)
    bool CompagnonsModule::HandleBoutique(WorldSession* session, const std::string& /*args*/)
    {
        Player* p = session->GetPlayer();
        if (!p)
            return true;
        Addon(p, "S " + std::to_string(Solde(session->GetAccountId())));
        if (auto r = LoginDatabase.Query("SELECT `id`, `categorie`, `nom`, `description`, `prix`, `qualite`, `type`, `item` FROM `portail_catalogue` ORDER BY `ordre`"))
            do
            {
                Field* f = r->Fetch();
                // description raccourcie (lignes de discussion courtes), coupée entre deux caractères UTF-8
                std::string desc = f[3].GetCppString();
                if (desc.size() > 110)
                {
                    size_t n = 110;
                    while (n > 0 && (uint8(desc[n]) & 0xC0) == 0x80)
                        --n;
                    desc = desc.substr(0, n) + "...";
                }
                std::ostringstream out;
                out << "A " << f[0].GetCppString() << "|" << f[1].GetCppString() << "|" << f[2].GetCppString() << "|" << f[4].GetUInt32() << "|"
                    << f[5].GetCppString() << "|" << f[6].GetUInt32() << "|" << f[7].GetUInt32() << "|" << desc;
                Addon(p, out.str());
            }
            while (r->NextRow());
        Addon(p, "B");
        return true;
    }

    bool CompagnonsModule::HandleAcheter(WorldSession* session, const std::string& args)
    {
        std::lock_guard<std::recursive_mutex> l(lock);
        Player* p = session->GetPlayer();
        if (!p)
            return true;
        std::string id = args;
        id.erase(std::remove_if(id.begin(), id.end(), [](char c) { return !(isalnum((unsigned char)c) || c == '_'); }), id.end());
        LoginDatabase.escape_string(id);
        auto r = LoginDatabase.PQuery("SELECT `nom`, `prix`, `type`, `item`, `quantite` FROM `portail_catalogue` WHERE `id` = '%s' AND `prix` > 0", id.c_str());
        if (!r)
        {
            Dire(p, "Article introuvable.");
            return true;
        }
        Field* f = r->Fetch();
        std::string nom = f[0].GetCppString();
        uint32 prix = f[1].GetUInt32(), type = f[2].GetUInt32(), item = f[3].GetUInt32(), qte = std::max<uint32>(1, f[4].GetUInt32());
        if (type == 2 && (Possession(p->GetGUIDLow(), item) ||
                          CharacterDatabase.PQuery("SELECT 1 FROM `custom_boutique_livraison` WHERE `guid` = %u AND `type` = 2 AND `item` = %u AND `statut` = 0", p->GetGUIDLow(), item)))
        {
            Dire(p, "Tu possèdes déjà ce compagnon.");
            return true;
        }
        uint32 compte = session->GetAccountId();
        int32 avant = Solde(compte);
        if (avant < int32(prix))
        {
            Dire(p, "Solde de Gen insuffisant.");
            Addon(p, "S " + std::to_string(avant));
            return true;
        }
        LoginDatabase.DirectPExecute("UPDATE `portail_gen` SET `solde` = `solde` - %u WHERE `compte` = %u AND `solde` >= %u", prix, compte, prix);
        int32 apres = Solde(compte);
        if (avant - apres != int32(prix))
        {
            Dire(p, "L'achat n'a pas pu être fait, réessaie.");
            return true;
        }
        std::string n2 = nom;
        CharacterDatabase.escape_string(n2);
        std::string n3 = nom;
        LoginDatabase.escape_string(n3);
        LoginDatabase.DirectPExecute("INSERT INTO `portail_operation` (`compte`, `type`, `gen`, `euros`, `reference`, `detail`, `date`) VALUES (%u, 'achat', %d, 0, '%s', 'en jeu : %s', NOW())",
                                     compte, -int32(prix), id.c_str(), n3.c_str());
        CharacterDatabase.DirectPExecute("INSERT INTO `custom_boutique_livraison` (`guid`, `type`, `item`, `quantite`, `titre`, `statut`, `date`) VALUES (%u, %u, %u, %u, '%s', 0, NOW())",
                                         p->GetGUIDLow(), type, item, qte, n2.c_str());
        Dire(p, "Achat validé : " + nom + ". Il arrive par courrier dans quelques secondes.");
        Addon(p, "S " + std::to_string(apres));
        return true;
    }

    // commande MJ : .cpg donner <id> (donne un compagnon au personnage ciblé ou à soi)
    bool CompagnonsModule::HandleDonner(WorldSession* session, const std::string& args)
    {
        Player* p = session->GetPlayer();
        if (!p)
            return true;
        uint32 cpg = uint32(atoi(args.c_str()));
        Compagnon const* d = Def(cpg);
        if (!d)
        {
            Dire(p, "Usage : .cpg donner <1 à 32>");
            return true;
        }
        Player* cible = p;
        if (Player* sel = sObjectMgr.GetPlayer(p->GetSelectionGuid()))
            cible = sel;
        CharacterDatabase.DirectPExecute("INSERT INTO `custom_boutique_livraison` (`guid`, `type`, `item`, `quantite`, `titre`, `statut`, `date`) VALUES (%u, 2, %u, 1, 'Compagnon', 0, NOW())",
                                         cible->GetGUIDLow(), cpg);
        Dire(p, std::string(d->nom) + " sera livré par courrier à " + cible->GetName() + ".");
        return true;
    }
}
