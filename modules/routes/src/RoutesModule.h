#ifndef CMANGOS_MODULE_ROUTES_H
#define CMANGOS_MODULE_ROUTES_H

#include "Module.h"
#include <mutex>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

// Vitesse sur les routes : +20 % à pied et en monture (sort 65506) tant que le joueur est sur une route ou un chemin, hors capitales.
// Les routes viennent de routes.bin (dossier des données du serveur, à côté de dbc et maps), produit par routes_extract.exe
// à partir des textures du sol du client : cases de 2 m, Azeroth et Kalimdor.
// Bien nourri : +5 % d'expérience tant qu'un buff de nourriture est actif.
// Commande MJ : .route (dit si la position actuelle est une route)

class Player;
class Creature;

namespace cmangos_module
{
    class RoutesModule : public Module
    {
    public:
        RoutesModule() : Module("Routes", nullptr) {}

        void OnInitialize() override;
        void OnUpdate(uint32 elapsed) override;
        bool OnPreGiveXP(Player* player, uint32& xp, Creature* victim) override;

        const char* GetChatCommandPrefix() const override { return "route"; }
        std::vector<ModuleChatCommand>* GetCommandTable() override;

        bool SurRoute(uint32 map, float x, float y) const;
        void Appliquer(Player* player);

    private:
        bool HandleRoute(WorldSession* session, const std::string& args);
        bool Charger(const std::string& chemin);

        std::unordered_map<uint32, std::vector<uint8>> tuiles;      // (carte << 16 | tx << 8 | ty) -> 256 x 256 bits
        uint32 timer = 0;
    };
}
#endif
