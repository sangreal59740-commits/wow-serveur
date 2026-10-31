#ifndef CMANGOS_MODULE_DONJONS_H
#define CMANGOS_MODULE_DONJONS_H

#include "Module.h"
#include <mutex>
#include <unordered_map>
#include <unordered_set>
#include <vector>

// Modes de donjon niveau 40 / 50 pour les 13 donjons de moins de 40.
// Un PNJ a l'entree propose Normal / Niveau 40 / Niveau 50. Les monstres sont remontes au niveau
// choisi (stats, degats des sorts, experience, or). Le choix est verrouille des le premier monstre tue.
// Mode mythique M0 a M+10 (tous les donjons) : monstres niveau 60, PV et degats x1,2 a x5, clones en plus,
// butin mythique des boss. Finir un niveau (boss final) debloque le suivant.

namespace cmangos_module
{
    #define DONJONS_NPC_BASE        990100      // Gardien des epreuves : 990100 + index du donjon (0 a 12)
    #define DONJONS_NPC_LAST        990124
    #define DONJONS_MODES_4050      13          // modes 40 / 50 : donjons 0 a 12 seulement
    #define DONJONS_MYTHIC          100         // niveau de mode 100 + M = mythique M+M
    #define DONJONS_MYTHIC_MAX      10
    #define DONJONS_MYTHIC_LOOT     997000      // butin des boss : 997000 + M (2 objets), boss final 997100 + M (3 objets)
    #define DONJONS_CREDIT_BASE     990200      // + index*2 + (mode 50 ? 1 : 0)
    #define DONJONS_RARE_BASE       990400      // boss rare : 990400 + index du donjon ; butin +20 (mode 40), +40 (mode 50)
    #define DONJONS_RARE_LAST       990412

    struct DonjonInfo
    {
        uint32 index;
        uint32 mapId;
        float x, y, z;          // entree de l'instance
        uint32 refLevel;        // niveau du boss final
        uint32 finalBoss;       // entry du boss final
        const char* nom;
    };

    struct InstanceMode
    {
        uint32 mapId = 0;
        int32 dungeon = -1;     // index dans la table, -1 si inconnu
        uint32 level = 0;       // 0 = normal, 40 ou 50, 100 + M = mythique
        bool locked = false;
        std::unordered_map<uint64, uint32> origLevels;   // guid -> niveau d'origine
        std::unordered_map<uint64, float> appliedMult;   // guid -> multiplicateur PV / degats applique
    };

    class DonjonsModule : public Module
    {
    public:
        DonjonsModule();

        void OnInitialize() override;
        void OnAddToWorld(Creature* creature) override;
        void OnGossipHello(Player* player, Creature* creature) override;
        bool OnGossipSelect(Player* player, Creature* creature, uint32 sender, uint32 action, const std::string& code, uint32 gossipListId) override;
        void OnKill(Unit* unit, Unit* victim) override;
        bool OnGenerateMoneyLoot(Loot* loot, uint32& outMoney) override;
        bool OnFillLoot(Loot* loot, Player* owner) override;

    private:
        const DonjonInfo* FindDonjon(uint32 mapId, float x, float y, float z) const;
        const DonjonInfo* GetDonjon(const InstanceMode& mode) const;
        bool IsScalable(Creature* creature) const;
        void ApplyToCreature(Creature* creature, InstanceMode& mode);
        void ApplyToInstance(Map* map, InstanceMode& mode);
        void SaveMode(uint32 instanceId, const InstanceMode& mode);
        void Announce(Map* map, const std::string& text);
        static float DamageRatio(uint32 from, uint32 to);
        bool CanClone(Creature* creature) const;
        void QueueClones(Creature* creature, uint32 mythic);
        int32 GetBest(Player* player, int32 dungeon) const;
        void SetBest(Player* player, int32 dungeon, int32 best);
        bool IsBoss(uint32 entry) const { return bossEntries.find(entry) != bossEntries.end(); }

        std::recursive_mutex lock;
        std::unordered_set<uint32> bossEntries;                 // boss de donjon (butin mythique)
        std::unordered_map<uint64, int32> bestLevels;           // (guid << 8 | donjon) -> meilleur niveau mythique

        std::unordered_map<uint32, InstanceMode> instances;     // instanceId -> mode
    };
}
#endif
