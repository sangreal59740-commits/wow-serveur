#ifndef CMANGOS_MODULE_VAGUES_H
#define CMANGOS_MODULE_VAGUES_H

#include "Module.h"
#include <unordered_map>
#include <vector>

// Vagues de bots niveau 1, lancees a la main avec la commande .bots vague
// Une vague = chaque combinaison race / classe / specialisation x2, pour chaque faction (114 + 114 = 228 bots).
// Chaque bot recoit un rythme de progression (multiplicateur d'experience) et une qualite de jeu
// (multiplicateur du temps de reaction de l'IA), tires au hasard.

namespace cmangos_module
{
    #define VAGUES_MAX              5
    #define VAGUES_COPIES           2   // nombre de bots par combinaison race / classe / spe et par vague

    struct ProfilBot
    {
        uint32 vague = 0;
        uint8 rythme = 1;           // 0 lent, 1 normal, 2 rapide, 3 tres rapide
        uint8 qualite = 1;          // 0 expert, 1 bon, 2 moyen, 3 debutant
        float xpMult = 1.0f;
        float reactMult = 1.0f;
    };

    class VaguesModule : public Module
    {
    public:
        VaguesModule();

        void OnInitialize() override;
        void OnUpdate(uint32 elapsed) override;
        bool OnPreGiveXP(Player* player, uint32& xp, Creature* victim) override;

        const char* GetChatCommandPrefix() const override { return "bots"; }
        std::vector<ModuleChatCommand>* GetCommandTable() override;

    private:
        bool HandleVague(WorldSession* session, const std::string& args);
        bool HandleInfo(WorldSession* session, const std::string& args);
        void Message(WorldSession* session, const std::string& text);
        uint32 NombreVagues() const;

        std::unordered_map<uint32, ProfilBot> profils;     // guid -> profil
        uint32 timerReact = 0;
    };
}
#endif
