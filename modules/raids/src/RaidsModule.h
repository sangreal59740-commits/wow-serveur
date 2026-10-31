#ifndef CMANGOS_MODULE_RAIDS_H
#define CMANGOS_MODULE_RAIDS_H

#include "Module.h"
#include <mutex>
#include <unordered_map>
#include <unordered_set>

// Raids a 10 ou 20 joueurs : PNJ a l'entree (taille choisie par le chef avant le premier combat, 20 par defaut),
// PV et degats des ennemis ajustes a la taille, butin des boss selon la taille, boss legendaire 30 s apres
// le boss final, fragment donne a chaque joueur present (une fois par personnage).

namespace cmangos_module
{
    #define RAIDS_NPC_BASE      990150      // Gardien des raids : + index du raid (0 a 6)
    #define RAIDS_LEG_BASE      990450      // boss legendaire : + index du raid
    #define RAIDS_FRAG_BASE     999000      // fragment : + index du raid
    #define RAIDS_LEGLOOT10     998900
    #define RAIDS_LEGLOOT20     998920
    #define RAIDS_COUNT         7

    struct RaidInfo
    {
        uint32 index;
        uint32 mapId;
        uint32 origSize;
        uint32 finalBoss;
        const char* nom;
    };

    struct RaidBoss
    {
        uint32 raid;
        uint32 loot10;
        uint32 loot20;
        bool final;
    };

    struct RaidMode
    {
        uint32 size = 20;
        bool locked = false;
        bool legendarySpawned = false;
        std::unordered_map<uint64, uint32> applied;     // guid -> taille appliquee
    };

    class RaidsModule : public Module
    {
    public:
        RaidsModule();

        void OnInitialize() override;
        void OnAddToWorld(Creature* creature) override;
        void OnGossipHello(Player* player, Creature* creature) override;
        bool OnGossipSelect(Player* player, Creature* creature, uint32 sender, uint32 action, const std::string& code, uint32 gossipListId) override;
        void OnKill(Unit* unit, Unit* victim) override;
        bool OnFillLoot(Loot* loot, Player* owner) override;
        void OnStoreItem(Player* player, Item* item) override;
        void OnStoreItem(Player* player, Loot* loot, Item* item) override;

    private:
        const RaidInfo* GetRaid(uint32 mapId) const;
        bool IsScalable(Creature* creature) const;
        void Apply(Creature* creature, const RaidInfo& raid, RaidMode& mode);
        void ApplyToInstance(Map* map, const RaidInfo& raid, RaidMode& mode);
        void Save(uint32 instanceId, const RaidMode& mode);
        void Announce(Map* map, const std::string& text);
        void GiveFragment(Player* player, uint32 raid);

        std::recursive_mutex lock;
        std::unordered_map<uint32, RaidMode> instances;         // instanceId -> mode
        std::unordered_map<uint32, RaidBoss> bosses;            // entry -> boss
        std::unordered_set<uint64> fragments;                   // (guid << 8 | raid) deja obtenus
    };
}
#endif
