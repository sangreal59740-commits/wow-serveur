#ifndef CMANGOS_MODULE_COMPAGNONS_H
#define CMANGOS_MODULE_COMPAGNONS_H

#include "Module.h"
#include <ctime>
#include <map>
#include <mutex>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

// Compagnons achetés en Gen (doc « Nouvelles classes et soutiens », 25/11/2026)
//  - un compagnon appartient à un seul personnage (base characters : custom_cpg) ; il est livré sous forme de pierre à son nom
//  - la pierre (ou .cpg invoquer) le fait apparaître à côté du joueur et l'ajoute à son groupe ; 4 compagnons au maximum
//  - c'est un bot (compte CPG<guid du joueur>) toujours au niveau de son propriétaire, avec les seuls sorts de sa fiche,
//    la puissance de sa rareté, un stuff de base fixe (stats par aura), ses talents à lui et son ultime
//  - le joueur change seulement cou, anneaux, bijoux, 2 artefacts et 2 orbes (couleurs différentes)
//  - les compagnons ne prennent pas de part d'XP ; le joueur gagne 10 % d'XP de plus par autre vrai joueur du groupe
//  - commandes .cpg (utilisées par l'addon Compagnons) : liste, fiche, invoquer, talent, reset, equiper, retirer, boutique, acheter

class Player;
class Unit;
class Item;
class Loot;

namespace cmangos_module
{
    struct CpgPossession
    {
        uint32 cpg = 0;              // identifiant du compagnon (1 à 32)
        uint32 bot = 0;              // guid du personnage bot (0 : pas encore créé)
        std::string talents;         // 11 chiffres : rangs des 10 talents puis l'ultime ; vide = répartition automatique
        uint32 orbes[2] = { 0, 0 };  // entrées des orbes posées
        uint32 artefacts[2] = { 0, 0 };
        bool actif = false;          // invoqué
    };

    struct CpgActif
    {
        uint32 proprio = 0;
        uint32 cpg = 0;
        uint32 bot = 0;
        uint32 attente = 0;          // ms avant la connexion
        bool connecte = false;       // connexion demandée
        bool pret = false;           // préparé une fois connecté
        bool groupe = false;         // a déjà été mis dans le groupe du joueur
        bool renvoi = false;         // sorti du groupe par le joueur : renvoyé
        uint32 essais = 0;
        uint32 entretien = 0;        // ms depuis le dernier entretien complet
        uint32 niveau = 0;           // niveau au dernier entretien
        uint32 mortDepuis = 0;       // ms passées mort hors combat
        uint32 combatDepuis = 0;     // ms en combat
        time_t ultime = 0;           // dernier ultime
        time_t buffFin = 0;          // fin du bonus de l'ultime géré par le module
        std::vector<uint32> sortsArtefacts;   // effets « Équipé » des artefacts posés sur le compagnon
    };

    class CompagnonsModule : public Module
    {
    public:
        CompagnonsModule();

        void OnInitialize() override;
        void OnUpdate(uint32 elapsed) override;
        bool OnUseItem(Player* player, Item* item) override;
        bool OnPreGiveXP(Player* player, uint32& xp, Creature* victim) override;
        void OnLogOut(Player* player) override;
        void OnDeleteFromDB(uint32 playerId) override;
        void OnDealDamage(Unit* unit, Unit* victim, uint32 health, uint32 damage) override;
        void OnHit(Spell* spell, Unit* caster, Unit* victim) override;
        bool OnFillLoot(Loot* loot, Player* owner) override;
        void OnGiveLevel(Player* player, uint32 level) override;
        bool OnPreInviteMember(Group* group, Player* player, Player* recipient) override;

        const char* GetChatCommandPrefix() const override { return "cpg"; }
        std::vector<ModuleChatCommand>* GetCommandTable() override;

        // pour les crochets du cœur et de playerbot
        bool EstCompagnon(uint32 botGuid) const;
        const char* NomAffiche(uint32 botGuid) const;
        int Role(uint32 botGuid) const;
        int Onglet(uint32 botGuid) const;

    private:
        bool HandleListe(WorldSession* session, const std::string& args);
        bool HandleFiche(WorldSession* session, const std::string& args);
        bool HandleInvoquer(WorldSession* session, const std::string& args);
        bool HandleRenvoyer(WorldSession* session, const std::string& args);
        bool HandleTalent(WorldSession* session, const std::string& args);
        bool HandleReset(WorldSession* session, const std::string& args);
        bool HandleEquiper(WorldSession* session, const std::string& args);
        bool HandleRetirer(WorldSession* session, const std::string& args);
        bool HandleBoutique(WorldSession* session, const std::string& args);
        bool HandleAcheter(WorldSession* session, const std::string& args);
        bool HandleDonner(WorldSession* session, const std::string& args);

        void Charger(uint32 proprio);
        void Sauver(uint32 proprio, CpgPossession const& p);
        CpgPossession* Possession(uint32 proprio, uint32 cpg);
        uint32 CompteBots(uint32 proprio);
        uint32 CreerBot(Player* proprio, uint32 cpg);
        void Invoquer(Player* proprio, uint32 cpg);
        void Renvoyer(uint32 proprio, uint32 cpg, bool message);
        void Livrer();
        void Offrir(Player* p);
        void Sixieme(uint32 dt);
        void GroupeComplet(Player* p);
        void Suivre(uint32 dt);
        void Preparer(Player* bot, Player* proprio, CpgActif& a, bool complet);
        void Sorts(Player* bot, uint32 cpg);
        void Equipement(Player* bot, uint32 cpg);
        void Auras(Player* bot, Player* proprio, CpgPossession const& p, CpgActif& a);
        void Groupe(Player* bot, Player* proprio, CpgActif& a);
        void Ultime(Player* bot, Player* proprio, CpgActif& a);
        std::vector<uint32> Rangs(CpgPossession const& p, uint32 niveau) const;
        void EnvoyerFiche(Player* proprio, uint32 cpg);
        void EnvoyerListe(Player* proprio);
        int32 Solde(uint32 compte);

        mutable std::recursive_mutex lock;
        std::unordered_map<uint32, std::vector<CpgPossession>> possessions;   // proprio -> compagnons possédés
        std::unordered_set<uint32> charges;                                     // proprios chargés depuis la base
        std::unordered_set<uint32> offerts;              // personnages déjà vérifiés pour le compagnon offert au niveau 10
        std::unordered_set<uint32> sixiemeAffiche;       // joueurs à qui l'addon affiche le 6e membre du groupe
        uint32 timerSixieme = 0;
        std::vector<CpgActif> actifs;
        std::unordered_map<uint32, uint32> botCpg;                              // bot -> compagnon
        std::unordered_map<uint32, uint32> botProprio;                          // bot -> proprio
        uint32 timer = 0, timerLivraison = 0;
        bool crochets = false;
    };
}
#endif
