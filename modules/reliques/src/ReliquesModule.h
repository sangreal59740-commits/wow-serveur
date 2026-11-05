#ifndef CMANGOS_MODULE_RELIQUES_H
#define CMANGOS_MODULE_RELIQUES_H

#include "Module.h"
#include <array>
#include <mutex>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

// Emplacements en plus de l'équipement : 4 Artefacts et 1 Mascotte, dessinés sur la fiche du personnage par l'addon Reliques.
// Le client 1.12 n'a que 19 emplacements : l'objet placé dans une case est retiré des sacs et gardé par le serveur
// (base characters : custom_relique), qui applique ses statistiques et ses effets « Équipé » comme s'il était porté.
// Objets autorisés (base world : custom_relique_objet) : type 1 à 4 = artefact bleu (Endurance), rouge (Force ou Intelligence),
// vert (critique ou toucher), jaune (défense, puissance des sorts ou d'attaque), chacun dans sa case ; type 5 = mascotte.
// Mascottes : les compagnons du jeu (custom_relique_mascotte : deux statistiques), au budget d'un casque bleu du niveau du joueur,
// effets par sorts passifs 65690-65699 ; le compagnon suit le joueur tant que la mascotte est dans sa case.
// Commandes (utilisées par l'addon) : .relique liste / equiper <sac> <case du sac> <emplacement 1-5> / retirer <emplacement 1-5>

#define RELIQUES_CASES      5           // 1 à 4 : artefacts bleu, rouge, vert, jaune ; 5 : mascotte
#define RELIQUES_MACHINE    991000      // machine à artefacts (près des hôtels des ventes), recettes : custom_relique_recette
#define RELIQUES_PALIERS    7           // 10, 20, 30, 40, 50, 60, 60 épique

class GameObject;
class Player;
struct ItemPrototype;

namespace cmangos_module
{
    class ReliquesModule : public Module
    {
    public:
        ReliquesModule() : Module("Reliques", nullptr) {}

        void OnInitialize() override;
        void OnUpdate(uint32 elapsed) override;
        void OnLogOut(Player* player) override;
        void OnDeleteFromDB(uint32 playerId) override;
        void OnGossipHello(Player* player, GameObject* gameObject) override;
        bool OnGossipSelect(Player* player, GameObject* gameObject, uint32 sender, uint32 action, const std::string& code, uint32 gossipListId) override;

        const char* GetChatCommandPrefix() const override { return "relique"; }
        std::vector<ModuleChatCommand>* GetCommandTable() override;

        void Initialiser(Player* player);
        void Entretien(Player* player);

    private:
        bool HandleListe(WorldSession* session, const std::string& args);
        bool HandleEquiper(WorldSession* session, const std::string& args);
        bool HandleRetirer(WorldSession* session, const std::string& args);
        void Bonus(Player* player, uint32 entry, bool apply);
        void Liste(Player* player);
        void Mascotte(Player* player, uint32 entry, bool apply);
        void Fabriquer(Player* player, uint32 couleur, uint32 palier);
        void MenuPaliers(Player* player, GameObject* go, uint32 couleur);
        std::array<uint32, RELIQUES_CASES>& Cases(uint32 guid);

        std::recursive_mutex lock;
        std::unordered_map<uint32, uint8> types;                                    // objet -> type
        std::unordered_map<uint32, std::array<uint32, RELIQUES_CASES>> cases;      // personnage -> objets en place
        std::unordered_set<uint32> appliques;                                       // personnages dont les bonus sont appliqués
        std::unordered_map<uint32, std::pair<std::string, std::string>> mascottes;  // mascotte -> ses deux statistiques
        std::unordered_map<uint32, uint32> niveauMascotte;                          // personnage -> niveau des statistiques de sa mascotte
        struct Recette { uint32 objet[4] = { 0, 0, 0, 0 }; uint32 nombre[4] = { 0, 0, 0, 0 }; uint32 argent = 0; };
        std::unordered_map<uint32, Recette> recettes;                               // couleur * 10 + palier -> composants
        std::unordered_map<uint32, std::vector<uint32>> artefacts;                  // couleur * 10 + palier -> artefacts possibles
        uint32 timerEntretien = 0;
        uint32 timer = 0;
    };
}
#endif
