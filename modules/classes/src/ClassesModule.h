#ifndef CMANGOS_MODULE_CLASSES_H
#define CMANGOS_MODULE_CLASSES_H

#include "Module.h"
#include <deque>
#include <mutex>
#include <unordered_map>
#include <unordered_set>
#include <vector>
#include <ctime>

// Classes custom : mécaniques qui ne peuvent pas être décrites par les seules données de sorts.
//  - Nécromancien : points d'invocation, armée (Explosion de peste, Berserk, Rénovation, Sang enflammé, Annihilation...),
//    Trait de la mort, Maléfice, talents (Horde grandissante, Récolte d'âme, Maîtrise de l'invocation)
//  - Sniper : Recul, Appel animal, Ordre, Balle magique
//  - Métamorphe : Appel / Renvoi totémique, Jugement selon la spé, Esprit guérisseur, Force de l'esprit
//  - Bots des classes custom : rotation simple (invocations, buffs, DoT, sorts de dégâts, soins)

class Player;
class Unit;

namespace cmangos_module
{
    struct ArmyEntry
    {
        uint64 guid;
        uint32 cost;
    };

    class ClassesModule : public Module
    {
    public:
        ClassesModule();

        void OnInitialize() override;
        void OnCast(Spell* spell, Unit* caster, Unit* victim) override;
        void OnHit(Spell* spell, Unit* caster, Unit* victim) override;
        bool OnPeriodicTick(Aura* aura) override;
        void OnKill(Unit* unit, Unit* victim) override;
        void OnLearnTalent(Player* player, uint32 spellId) override;
        void OnLogOut(Player* player) override;
        void OnUpdate(uint32 elapsed) override;

        void BotThink(Player* bot);
        void Upkeep(Player* player);
        void OnDealDamage(Unit* unit, Unit* victim, uint32 health, uint32 damage) override;

    private:
        // Nécromancien
        uint32 MaxPoints(Player* player) const;
        void Summon(Player* player, uint32 index);
        void CleanArmy(Player* player);
        template<typename F> void ForArmy(Player* player, bool withPet, F f);
        void NecroCast(Player* player, uint32 spellId, Unit* victim, Spell* spell);
        // Sniper
        void SniperCast(Player* player, uint32 spellId, Unit* victim);
        // Métamorphe
        void MetaCast(Player* player, uint32 spellId, Unit* victim);
        void MetaPassives(Player* player);
        // 4e spé des classes vanilla
        void Spe4Cast(Player* player, uint32 spellId, Unit* victim);
        void Spe4Upkeep(Player* player);
        // bots
        bool TryCast(Player* bot, Unit* target, uint32 spellId);

        std::recursive_mutex lock;
        std::unordered_map<uint64, std::deque<ArmyEntry>> armies;   // joueur -> invocations permanentes (ordre d'arrivée)
        std::unordered_map<uint64, int32> forceValue;               // joueur -> Force donnée par Force de l'esprit
        std::unordered_map<uint64, time_t> egideTime;               // joueur -> dernier déclenchement d'Égide angélique
        std::unordered_set<uint64> runique;                          // Chamans sous Appel runique (soin à la fin)
        uint32 botTimer = 0;
    };
}
#endif
