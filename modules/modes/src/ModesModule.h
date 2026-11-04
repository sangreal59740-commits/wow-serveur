#ifndef CMANGOS_MODULE_MODES_H
#define CMANGOS_MODULE_MODES_H

#include "Module.h"
#include <mutex>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

// Modes de jeu, choisis auprès du Héraut des Épreuves (PNJ 990800-990805, au point de départ de chaque race), jusqu'au niveau 5 :
//   Normal : rien ne change
//   JcJ : JcJ activé en permanence, même au niveau 1
//   Hardcore : mort définitive (le personnage ne peut plus être ressuscité)
//   Terrifiant : JcJ permanent et mort définitive
// Prestige, auprès du Maître du Renouveau (PNJ 990810-990815, près des banques des capitales), au niveau 60 :
//   retour au niveau 1 au point de départ, objets gardés (l'équipement va dans les sacs, ou par courrier s'ils sont pleins),
//   sorts de classe au-dessus du niveau 1 oubliés, talents remis à zéro ; buff Prestige (sort 65505) : +30 % d'expérience et d'or
// Base characters : custom_mode (guid, mode, mort, prestige)

#define MODES_HERAUT_MIN        990800
#define MODES_HERAUT_MAX        990805
#define MODES_RENOUVEAU_MIN     990810
#define MODES_RENOUVEAU_MAX     990815
#define MODES_NIVEAU_CHOIX      5
#define MODES_SORT_PRESTIGE     65505
#define MODES_BONUS_PRESTIGE    1.30f

class Creature;
class Player;
class Unit;

namespace cmangos_module
{
    enum ModeJeu : uint8
    {
        MODE_NORMAL = 0,
        MODE_JCJ = 1,
        MODE_HARDCORE = 2,
        MODE_TERRIFIANT = 3,
    };

    struct EtatMode
    {
        uint8 mode = MODE_NORMAL;
        bool mort = false;
        uint32 prestige = 0;
    };

    class ModesModule : public Module
    {
    public:
        ModesModule();

        void OnInitialize() override;
        void OnUpdate(uint32 elapsed) override;
        void OnGossipHello(Player* player, Creature* creature) override;
        bool OnGossipSelect(Player* player, Creature* creature, uint32 sender, uint32 action, const std::string& code, uint32 gossipListId) override;
        void OnDeath(Player* player, Unit* killer) override;
        void OnDeath(Player* player, uint8 environmentalDamageType) override;
        bool OnPreResurrect(Player* player) override;
        bool OnPreGiveXP(Player* player, uint32& xp, Creature* victim) override;
        void OnDeleteFromDB(uint32 playerId) override;

        const char* GetChatCommandPrefix() const override { return "mode"; }
        std::vector<ModuleChatCommand>* GetCommandTable() override;

        uint32 BonusArgent(Player* player, uint32 money);
        void Entretien(Player* player);

    private:
        bool HandleInfo(WorldSession* session, const std::string& args);
        bool HandleRelever(WorldSession* session, const std::string& args);
        EtatMode Etat(uint32 guid);
        void Sauver(uint32 guid, EtatMode const& e);
        void MortDefinitive(Player* player);
        void Prestige(Player* player);
        static std::string NomMode(uint8 mode);
        static bool Permadeath(uint8 mode) { return mode == MODE_HARDCORE || mode == MODE_TERRIFIANT; }
        static bool JcJ(uint8 mode) { return mode == MODE_JCJ || mode == MODE_TERRIFIANT; }

        std::recursive_mutex lock;
        std::unordered_map<uint32, EtatMode> etats;
        std::unordered_set<uint32> releve;      // personnages que le MJ fait revenir (résurrection autorisée une fois)
        uint32 timer = 0;
    };
}
#endif
