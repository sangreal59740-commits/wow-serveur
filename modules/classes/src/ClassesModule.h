#ifndef CMANGOS_MODULE_CLASSES_H
#define CMANGOS_MODULE_CLASSES_H

#include "Module.h"
#include "Entities/Player.h"
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
    void BoutiqueLivrer();                                  // Boutique.cpp : achats du portail envoyés par courrier

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
        void OnLoadFromDB(Player* player) override;
        void OnUpdate(uint32 elapsed) override;

        void BotThink(Player* bot);
        void Upkeep(Player* player);
        void OnDealDamage(Unit* unit, Unit* victim, uint32 health, uint32 damage) override;
        void OnDealHeal(Unit* unit, Unit* victim, int32 gain, uint32 addHealth) override;
        bool OnLoadActionButtons(Player* player, ActionButtonList& actionButtons) override;
        bool OnCalculateEffectiveCritChance(const Unit* unit, const Unit* victim, uint8 attType, const SpellEntry* ability, float& outChance) override;

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
        void SwapSpells(Player* player, const uint32_t* from, const uint32_t* to, uint32 n, bool active);
        // nouvelles classes (23/11) : Tisserand de vie, Fossoyeur, Martyr (NouvellesClasses.cpp)
    public:
        void NouvCast(Player* player, uint32 spellId, Unit* victim, Spell* spell);
        void NouvHit(Player* player, uint32 spellId, Unit* victim, Spell* spell);
        bool NouvTick(Aura* aura);
        void NouvDamage(Unit* unit, Unit* victim, uint32 health, uint32 damage);
        void NouvHeal(Unit* unit, Unit* victim, uint32 addHealth);
        void NouvUpkeep(Player* player);
        void NouvLogOut(Player* player);
        bool NouvEviteMort(Player const* player);
    private:
        std::unordered_map<uint64, std::vector<uint64>> lienForce;                   // Tisserand -> alliés liés (Lien de force)
        std::unordered_map<uint64, uint64> toileCaster;                              // cible de Toile protectrice -> Tisserand
        std::unordered_map<uint64, uint32> vieSauts;                                 // Tisserand -> sauts restants du Fil de vie
        std::unordered_map<uint64, std::deque<std::pair<uint64, uint32>>> fantomes;  // Passeur -> (allié, sort du fantôme)
        std::unordered_map<uint64, time_t> trepasTime;                               // Tisserand -> dernier Refus du trépas
        std::unordered_map<uint64, uint8> mortEvitee;                                // joueur -> 1 Fil du destin, 2 Refus du trépas, 3 Dernier sacrifice
        std::unordered_map<uint64, std::vector<uint32>> malOrdre;                    // Fossoyeur -> malédictions d'arme (ordre de pose)
        std::unordered_set<uint64> legion;                                           // Passeurs sous Légion des trépassés
        std::unordered_map<uint64, uint32> ferveurConso;                             // Martyr -> Ferveur consommée par le dernier sort de sang
        struct Fontaine { float x = 0, y = 0, z = 0; int32 secondes = 0; int32 soin = 0; };
        std::unordered_map<uint64, Fontaine> fontaines;                              // Martyr -> Fontaine de sang
        std::unordered_map<uint64, uint32> festinCoups;                              // Martyr -> coups restants de Festin de lames
        std::unordered_map<uint64, std::pair<uint64, float>> marques;               // cible -> (Martyr, % des dégâts rendus)
        std::unordered_map<uint64, time_t> dernierTime;                              // Martyr -> dernier Dernier sacrifice
        std::unordered_map<uint64, time_t> reflexeTime;                              // Martyr -> dernier Caillot réflexe
        void MartyrUpkeep(Player* player);
        // bots
        bool TryCast(Player* bot, Unit* target, uint32 spellId);
        bool TryCastAt(Player* bot, Unit* where, uint32 spellId);
        void BotTalents(Player* bot);
        bool ShamanTank(Player* bot, Unit* victim, bool combat);
        void Bot4Think(Player* bot);

        std::recursive_mutex lock;
        std::unordered_map<uint64, std::deque<ArmyEntry>> armies;   // joueur -> invocations permanentes (ordre d'arrivée)
        std::unordered_map<uint64, int32> forceValue;               // joueur -> Force donnée par Force de l'esprit
        std::unordered_map<uint64, uint32> formation;              // invocation -> place dans la formation (0 = à replacer)
        std::unordered_map<uint64, time_t> egideTime;               // joueur -> dernier déclenchement d'Égide angélique
        std::unordered_set<uint64> runique;                          // Chamans sous Appel runique (soin à la fin)
        std::unordered_map<uint64, uint64> lienTarget;              // Mage -> allié sous Lien de vie
        std::unordered_map<uint64, uint32> petHealTick;             // Chasseur -> secondes depuis le dernier soin du familier
        std::unordered_map<uint64, uint32> botTalentTick;           // bot -> secondes depuis la dernière vérification des talents
        std::unordered_map<uint64, ActionButtonList*> actionLists;  // joueur -> sa barre d'action (pour suivre les changements de sorts)
        uint32 botTimer = 0;
        uint32 arbreTimer = 0;
        uint32 boutiqueTimer = 0;
    };
}
#endif
