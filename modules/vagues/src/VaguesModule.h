#ifndef CMANGOS_MODULE_VAGUES_H
#define CMANGOS_MODULE_VAGUES_H

#include "Module.h"
#include <unordered_map>
#include <vector>

// Vagues de bots (niveau 1 par défaut), lancées à la main avec la commande .bots vague [niveau]
// Une vague = 275 bots (137 Alliance, 138 Horde), spe imposee par bot : voir SpesDeClasse / ClassesDeRace.
// Chaque bot recoit un rythme de progression (multiplicateur d'experience) et une qualite de jeu
// (multiplicateur du temps de reaction de l'IA), tires au hasard.

namespace cmangos_module
{
    #define VAGUES_MAX              5
    #define VAGUES_BONUS_XP_BOTS    1.25f   // les bots gagnent 25 % d'expérience de plus que les joueurs

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
        bool HandleSupprimer(WorldSession* session, const std::string& args);
        bool HandleGroupe(WorldSession* session, const std::string& args);
        bool HandlePull(WorldSession* session, const std::string& args);

        // pilotage de tous les bots (chaque seconde) : soigneurs économes, tanks qui pullent, rôles, sortie des zones trop basses
        uint32 timerPilote = 0, timerZones = 0;
        void PiloterBots(bool zones);

        // compagnons (.bots groupe 1 à 5) : groupes de personnages niveau 20 équipés qui suivent le joueur
        struct Compagnon
        {
            uint32 guid = 0;
            uint32 maitre = 0;          // guid du joueur
            uint8 groupe = 0;           // 1 à 5
            uint8 role = 0;             // membre du groupe
            bool nouveau = false;       // à préparer (sorts, talents, équipement) à la connexion
            uint32 attente = 0;         // ms avant de lancer la connexion
            bool connecte = false;      // connexion demandée
            uint32 essais = 0;
        };
        std::vector<Compagnon> compagnons;
        uint32 timerCompagnons = 0;
        void SuivreCompagnons(uint32 elapsed);
        void RemplacerCompagnons(uint32 dt);
        uint32 demandeGroupe = 0, demandeMaitre = 0, demandeAttente = 0;
        void PreparerCompagnon(Player* bot, Player* maitre, Compagnon const& c);
        uint32 VaguesPresentes() const;
        void Message(WorldSession* session, const std::string& text);
        uint32 NombreVagues() const;

        std::unordered_map<uint32, ProfilBot> profils;     // guid -> profil
        uint32 timerReact = 0;

        // bots bloqués (courent sur place ou tournent en rond) : relancés, puis téléportés si ça recommence
        struct Suivi
        {
            uint32 map = 0;
            float x = 0, y = 0;
            uint32 surPlace = 0;                            // relevés consécutifs « en mouvement mais immobile »
            std::vector<std::pair<float, float>> trace;     // positions des 60 dernières secondes
            time_t dernierDeblocage = 0;
        };
        std::unordered_map<uint32, Suivi> suivis;
        uint32 deblocages = 0, teleportations = 0;
        void SurveillerBots();
    };
}
#endif
