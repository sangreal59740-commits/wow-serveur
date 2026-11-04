#ifndef CMANGOS_MODULE_MAISONS_H
#define CMANGOS_MODULE_MAISONS_H

#include "Module.h"
#include "Entities/ObjectGuid.h"
#include <map>
#include <mutex>
#include <string>
#include <unordered_map>
#include <vector>

// Logement
// Repérage (MJ) : .maison suivante [zone] / ok / non / ajout / pnj / dehors / bilan / panneau
// Maisons (base world : custom_maison_lieu) : panneau « Maison à vendre » (objet 990590, guid 9906000 + id) pour acheter ou vendre.
// Plusieurs joueurs peuvent posséder la même maison : chacun y voit ses meubles, les autres voient ceux de la maison
// la mieux classée (le plus de meubles), grâce au correctif du cœur 03-maisons-visibilite.patch.
// Meubles (objets 990600+, catalogue custom_maison_catalogue) : .maison meubles / poser <numéro> / retirer
// Base characters : custom_maison_proprio (une maison par personnage), custom_maison_meuble

#define MAISONS_PANNEAU         990590
#define MAISONS_PANNEAU_GUID    9906000
#define MAISONS_MEUBLE_MIN      990600
#define MAISONS_MEUBLE_MAX      990999
#define MAISONS_MEUBLES_MAX     100         // meubles par maison et par propriétaire

class GameObject;
class Map;
class Player;

namespace cmangos_module
{
    struct MaisonLieu
    {
        uint32 id = 0;
        std::string ville;
        uint32 map = 0;
        float x = 0, y = 0, z = 0;
        float b[6] = { 0, 0, 0, 0, 0, 0 };      // boîte intérieure x0 y0 z0 x1 y1 z1
        std::string taille;
        uint32 prix = 0;                        // en pièces de cuivre
    };

    struct MaisonMeuble
    {
        uint32 id = 0;
        uint32 owner = 0;
        uint32 maison = 0;
        uint32 entry = 0;
        float x = 0, y = 0, z = 0, o = 0;
        ObjectGuid go;                          // objet en jeu (vide tant que la zone n'est pas chargée)
        bool retirer = false;
    };

    class MaisonsModule : public Module
    {
    public:
        MaisonsModule();

        void OnInitialize() override;
        void OnUpdate(uint32 elapsed) override;
        void OnGossipHello(Player* player, GameObject* gameObject) override;
        bool OnGossipSelect(Player* player, GameObject* gameObject, uint32 sender, uint32 action, const std::string& code, uint32 gossipListId) override;

        const char* GetChatCommandPrefix() const override { return "maison"; }
        std::vector<ModuleChatCommand>* GetCommandTable() override;

        bool Visible(GameObject const* go, Player const* viewer);
        void Entretien(Map* map);

    private:
        // repérage
        bool HandleSuivante(WorldSession* session, const std::string& args);
        bool HandleOk(WorldSession* session, const std::string& args);
        bool HandleNon(WorldSession* session, const std::string& args);
        bool HandleAjout(WorldSession* session, const std::string& args);
        bool HandlePnj(WorldSession* session, const std::string& args);
        bool HandleDehors(WorldSession* session, const std::string& args);
        bool HandleBilan(WorldSession* session, const std::string& args);
        bool HandlePanneau(WorldSession* session, const std::string& args);
        bool Statut(WorldSession* session, const std::string& args, uint32 statut);
        uint32 MaisonActuelle(Player* player);
        // maisons et meubles
        bool HandleMeubles(WorldSession* session, const std::string& args);
        bool HandlePoser(WorldSession* session, const std::string& args);
        bool HandleRetirer(WorldSession* session, const std::string& args);
        void ChargerMaisons();
        void CalculerVitrine(uint32 maison);
        void Rafraichir(uint32 maison);
        uint32 NombreMeubles(uint32 maison, uint32 owner) const;
        bool Dedans(MaisonLieu const& l, float x, float y, float z, float marge) const;

        void Message(WorldSession* session, const std::string& text);
        static std::string Echappe(const std::string& s);
        static std::string NomZone(Player* player);
        static std::string Or(uint32 cuivre);

        std::recursive_mutex lock;
        std::unordered_map<uint32, uint32> actuelle;            // joueur -> maison de repérage où il a été téléporté
        std::unordered_map<uint32, uint32> dernierPnj;          // joueur -> guid (base) du dernier PNJ marqué
        std::map<uint32, MaisonLieu> lieux;                     // id -> maison
        std::unordered_map<uint32, uint32> proprio;             // personnage -> maison possédée
        std::map<uint32, MaisonMeuble> meubles;                 // id -> meuble
        std::unordered_map<uint64, uint32> goMeuble;            // guid de l'objet en jeu -> meuble
        std::unordered_map<uint32, uint32> vitrine;             // maison -> propriétaire affiché aux autres
        std::map<uint32, std::string> catalogue;                // entrée d'objet -> nom (numéro = entrée - 990599)
        uint32 prochainMeuble = 1;
        uint32 timer = 0;
    };
}
#endif
