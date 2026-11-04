#ifndef CMANGOS_MODULE_FICHE_H
#define CMANGOS_MODULE_FICHE_H

#include "Module.h"
#include <vector>

// Statistiques que le client 1.12 ne connaît pas (dégâts et soins des sorts, critiques, toucher, esquive, parade, blocage, mana / 5 s),
// envoyées à l'addon FicheStats : la commande .fiche donnees répond par une ligne « ##FICHE ... » que l'addon lit et masque.

namespace cmangos_module
{
    class FicheModule : public Module
    {
    public:
        FicheModule() : Module("Fiche", nullptr) {}

        const char* GetChatCommandPrefix() const override { return "fiche"; }
        std::vector<ModuleChatCommand>* GetCommandTable() override;

    private:
        bool HandleDonnees(WorldSession* session, const std::string& args);
    };
}
#endif
