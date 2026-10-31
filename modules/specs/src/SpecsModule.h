#ifndef CMANGOS_MODULE_SPECS_H
#define CMANGOS_MODULE_SPECS_H

#include "Module.h"
#include <map>
#include <mutex>
#include <set>
#include <unordered_map>
#include <vector>

// 3 specialisations par personnage (talents + barres d'action).
// 2e onglet debloque au niveau 20, 3e au niveau 30, chez le maitre de classe.
// Changement : .spe 1 / .spe 2 / .spe 3 (ou chez le maitre de classe), 5 secondes hors combat.

namespace cmangos_module
{
    #define SPECS_MAX           3
    #define SPECS_DELAY         5       // secondes
    #define SPECS_LEVEL_2       20
    #define SPECS_LEVEL_3       30

    struct SpecButton
    {
        uint8 button;
        uint32 action;
        uint8 type;
    };

    struct SpecStatus
    {
        uint8 count = 1;
        uint8 active = 0;
        bool pending = false;
    };

    class SpecsModule : public Module
    {
    public:
        SpecsModule();

        void OnInitialize() override;
        void OnGossipHello(Player* player, Creature* creature) override;
        bool OnGossipSelect(Player* player, Creature* creature, uint32 sender, uint32 action, const std::string& code, uint32 gossipListId) override;
        bool OnSaveActionButtons(Player* player, ActionButtonList& actionButtons) override;
        void OnDeleteFromDB(uint32 playerId) override;

        const char* GetChatCommandPrefix() const override { return "spe"; }
        std::vector<ModuleChatCommand>* GetCommandTable() override;

        void FinishSwitch(Player* player, uint8 spec);

    private:
        SpecStatus& GetStatus(uint32 guid);
        void SaveStatus(uint32 guid, const SpecStatus& st);
        bool RequestSwitch(Player* player, uint8 spec);
        bool HandleSpec(WorldSession* session, uint8 spec);
        bool HandleInfo(WorldSession* session, const std::string& args);
        static bool IsClassTrainerFor(Player* player, Creature* creature);
        void Message(Player* player, const std::string& text);

        std::recursive_mutex lock;
        std::unordered_map<uint32, SpecStatus> status;              // guid -> etat
        std::set<uint32> capture;                                   // guid dont on enregistre les barres a la sauvegarde
        std::unordered_map<uint32, std::vector<SpecButton>> captured;
    };
}
#endif
