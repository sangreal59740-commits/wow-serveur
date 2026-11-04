#ifndef CMANGOS_MODULE_MAISONS_H
#define CMANGOS_MODULE_MAISONS_H

#include "Module.h"
#include <string>
#include <unordered_map>
#include <vector>

// Logement, étape 1 : repérage des maisons en jeu (commandes .maison, MJ uniquement)
// Tables de la base world : custom_maison (maisons candidates) et custom_maison_pnj (PNJ à sortir des maisons)
//   .maison suivante [zone]  : téléporte à la prochaine maison à vérifier
//   .maison ok [note] / .maison non [note] : valide ou rejette la maison actuelle (ou la plus proche, à 40 m)
//   .maison ajout [note]     : ajoute une maison à l'endroit où l'on se tient
//   .maison pnj [note]       : marque le PNJ ciblé comme « à sortir »
//   .maison dehors           : place le dernier PNJ marqué à l'endroit où l'on se tient
//   .maison bilan            : où en est le repérage

namespace cmangos_module
{
    class MaisonsModule : public Module
    {
    public:
        MaisonsModule();

        void OnInitialize() override;

        const char* GetChatCommandPrefix() const override { return "maison"; }
        std::vector<ModuleChatCommand>* GetCommandTable() override;

    private:
        bool HandleSuivante(WorldSession* session, const std::string& args);
        bool HandleOk(WorldSession* session, const std::string& args);
        bool HandleNon(WorldSession* session, const std::string& args);
        bool HandleAjout(WorldSession* session, const std::string& args);
        bool HandlePnj(WorldSession* session, const std::string& args);
        bool HandleDehors(WorldSession* session, const std::string& args);
        bool HandleBilan(WorldSession* session, const std::string& args);

        bool Statut(WorldSession* session, const std::string& args, uint32 statut);
        uint32 MaisonActuelle(Player* player);
        void Message(WorldSession* session, const std::string& text);
        static std::string Echappe(const std::string& s);
        static std::string NomZone(Player* player);

        std::unordered_map<uint32, uint32> actuelle;     // joueur -> maison sur laquelle il a été téléporté
        std::unordered_map<uint32, uint32> dernierPnj;   // joueur -> guid (base) du dernier PNJ marqué
    };
}
#endif
