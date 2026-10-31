#ifndef CMANGOS_MODULE_METIERS_H
#define CMANGOS_MODULE_METIERS_H

#include "Module.h"
#include <unordered_map>

// Experience des metiers : chaque point gagne dans un metier de recolte ou de fabrication
// donne la moitie de l'experience d'un monstre normal du niveau du joueur.

namespace cmangos_module
{
    class MetiersModule : public Module
    {
    public:
        MetiersModule();

        void OnUpdateSkill(Player* player, uint16 skillId) override;
        void OnLogOut(Player* player) override;

    private:
        // guid du joueur -> (metier -> derniere valeur connue)
        std::unordered_map<uint32, std::unordered_map<uint16, uint16>> valeurs;
    };
}
#endif
