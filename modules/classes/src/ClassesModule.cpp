#include "ClassesModule.h"
#include "ClassesData.h"

#include "Chat/Chat.h"
#include "Entities/Creature.h"
#include "Entities/Pet.h"
#include "Entities/Player.h"
#include "Entities/Totem.h"
#include "Entities/Unit.h"
#include "Globals/ObjectAccessor.h"
#include "Groups/Group.h"
#include "Log/Log.h"
#include "Maps/Map.h"
#include "Server/WorldSession.h"
#include "Spells/Spell.h"
#include "Spells/SpellAuras.h"
#include "Spells/SpellMgr.h"
#include "World/World.h"

#include <algorithm>
#include <cmath>

using namespace classes_data;

namespace cmangos_module
{
    static const uint8 C_NECRO = 6;
    static const uint8 C_SNIPER = 10;
    static const uint8 C_META = 11;

    static ClassesModule* instance = nullptr;
    // profondeur d'appel : nos propres sorts déclenchés ne doivent pas relancer la logique (boucle infinie)
    static thread_local int s_depth = 0;
    struct DepthGuard { DepthGuard() { ++s_depth; } ~DepthGuard() { --s_depth; } };

    // ------------------------------------------------------------------ outils
    static bool In(const uint32_t* arr, uint32 n, uint32 id)
    {
        for (uint32 i = 0; i < n; ++i)
            if (arr[i] == id)
                return true;
        return false;
    }

    // rang le plus élevé connu (0 si aucun)
    static uint32 Best(Player* player, const uint32_t* arr, uint32 n)
    {
        for (int32 i = int32(n) - 1; i >= 0; --i)
            if (arr[i] && player->HasSpell(arr[i]))
                return arr[i];
        return 0;
    }

    // rang de talent appris (0 si aucun) ; les talents à plusieurs arbres sont rangés par blocs de `ranks`
    static uint32 TalentRank(Player* player, const uint32_t* arr, uint32 n, uint32 ranks)
    {
        uint32 best = 0;
        for (uint32 i = 0; i < n; ++i)
            if (arr[i] && player->HasSpell(arr[i]))
                best = std::max(best, (i % ranks) + 1);
        return best;
    }

    static bool IsBot(Player* player)
    {
        return player->GetSession() && player->GetSession()->GetRemoteAddress() == "disconnected/bot";
    }

    static int32 SpellValue(SpellEntry const* info, uint32 eff = 0)
    {
        return info ? info->CalculateSimpleValue(SpellEffectIndex(eff)) : 0;
    }

    static void Say(Player* player, const char* text)
    {
        if (!IsBot(player))
            ChatHandler(player).SendSysMessage(text);
    }

    ClassesModule::ClassesModule() : Module("Classes", nullptr)
    {
        instance = this;
    }

    void ClassesModule::OnInitialize()
    {
        sLog.outString("Classes custom : %u invocations du Nécromancien, IA des bots active", INVOCATIONS_N);
    }

    // ------------------------------------------------------------------ Nécromancien : armée
    uint32 ClassesModule::MaxPoints(Player* player) const
    {
        uint32 lvl = player->GetLevel();
        uint32 pts = 1 + (lvl >= 20 ? 1 : 0) + (lvl >= 40 ? 1 : 0) + (lvl >= 60 ? 1 : 0);
        if (T_HORDE[0] && player->HasSpell(T_HORDE[0])) ++pts;
        if (T_ARMEE[0] && player->HasSpell(T_ARMEE[0])) ++pts;
        if (T_LEGION[0] && player->HasSpell(T_LEGION[0])) ++pts;
        return pts;
    }

    void ClassesModule::CleanArmy(Player* player)
    {
        auto it = armies.find(player->GetObjectGuid().GetRawValue());
        if (it == armies.end())
            return;
        Map* map = player->GetMap();
        auto& dq = it->second;
        dq.erase(std::remove_if(dq.begin(), dq.end(), [&](const ArmyEntry& e)
        {
            Pet* pet = map ? map->GetPet(ObjectGuid(e.guid)) : nullptr;
            return !pet || !pet->IsAlive() || pet->GetOwnerGuid() != player->GetObjectGuid();
        }), dq.end());
    }

    template<typename F> void ClassesModule::ForArmy(Player* player, bool withPet, F f)
    {
        std::vector<Unit*> units;
        player->CallForAllControlledUnits([&](Unit* u) { if (u && u->IsAlive()) units.push_back(u); },
                                          CONTROLLED_GUARDIANS | (withPet ? CONTROLLED_PET : 0));
        for (Unit* u : units)
            f(u);
    }

    void ClassesModule::Summon(Player* player, uint32 index)
    {
        const Invocation& inv = INVOCATIONS[index];
        CleanArmy(player);
        auto& dq = armies[player->GetObjectGuid().GetRawValue()];
        uint32 maxPts = MaxPoints(player);
        if (inv.cost > maxPts)
        {
            Say(player, "Pas assez de points d'invocation pour cette créature.");
            return;
        }
        uint32 used = 0;
        for (auto const& e : dq)
            used += e.cost;
        Map* map = player->GetMap();
        while (!dq.empty() && used + inv.cost > maxPts)
        {
            ArmyEntry old = dq.front();
            dq.pop_front();
            used -= old.cost;
            if (Pet* pet = map->GetPet(ObjectGuid(old.guid)))
                pet->Unsummon(PET_SAVE_AS_DELETED, player);
        }

        // invocations déjà présentes, pour retrouver la nouvelle
        std::vector<uint64> before;
        ForArmy(player, false, [&](Unit* u) { before.push_back(u->GetObjectGuid().GetRawValue()); });
        player->CastSpell(player, inv.hidden, TRIGGERED_OLD_TRIGGERED);
        ForArmy(player, false, [&](Unit* u)
        {
            uint64 g = u->GetObjectGuid().GetRawValue();
            if (u->GetEntry() == inv.entry && std::find(before.begin(), before.end(), g) == before.end())
                dq.push_back({ g, inv.cost });
        });
    }

    void ClassesModule::NecroCast(Player* player, uint32 id, Unit* victim, Spell* spell)
    {
        // invocations
        for (uint32 i = 0; i < INVOCATIONS_N; ++i)
        {
            if (INVOCATIONS[i].front == id)
            {
                Summon(player, i);
                return;
            }
        }

        SpellEntry const* info = spell->m_spellInfo;
        if (In(N_PESTE_EXPLO, N_PESTE_EXPLO_N, id))
        {
            int32 bp = SpellValue(info) + int32(player->SpellBaseDamageBonusDone(SPELL_SCHOOL_MASK_NATURE) * 0.15f);
            ForArmy(player, false, [&](Unit* u) { u->CastCustomSpell(u, N_H_PESTE, &bp, nullptr, nullptr, TRIGGERED_OLD_TRIGGERED); });
        }
        else if (In(N_BERSERK, N_BERSERK_N, id))
            ForArmy(player, true, [&](Unit* u) { player->CastSpell(u, N_H_BERSERK, TRIGGERED_OLD_TRIGGERED); });
        else if (In(N_MORTEXPLO, N_MORTEXPLO_N, id))
        {
            ForArmy(player, false, [&](Unit* u)
            {
                int32 bp = int32(u->GetMaxHealth() / 10);
                u->CastCustomSpell(u, N_H_MORTEXPLO, &bp, nullptr, nullptr, TRIGGERED_OLD_TRIGGERED);
                if (u->GetHealth() > uint32(bp))
                    u->SetHealth(u->GetHealth() - bp);
            });
        }
        else if (In(N_RENOVATION, N_RENOVATION_N, id))
        {
            int32 tick = std::max(1, (SpellValue(info) + int32(player->SpellBaseHealingBonusDone(SPELL_SCHOOL_MASK_NATURE) * 0.67f)) / 10);
            ForArmy(player, true, [&](Unit* u) { player->CastCustomSpell(u, N_H_RENOV, &tick, nullptr, nullptr, TRIGGERED_OLD_TRIGGERED); });
        }
        else if (In(N_SANG, N_SANG_N, id))
        {
            int32 bp0 = SpellValue(info) + int32(player->SpellBaseDamageBonusDone(SPELL_SCHOOL_MASK_FIRE) * 0.15f);
            int32 bp1 = std::max(1, bp0 * 2 / 5);
            ForArmy(player, false, [&](Unit* u) { u->CastCustomSpell(u, N_H_SANG, &bp0, &bp1, nullptr, TRIGGERED_OLD_TRIGGERED); });
        }
        else if (In(N_CHEVALIER_RENF, N_CHEVALIER_RENF_N, id))
        {
            Unit* knight = nullptr;
            ForArmy(player, false, [&](Unit* u) { if (u->GetEntry() == INVOCATIONS[5].entry) knight = u; });
            if (!knight)
            {
                Say(player, "Il vous faut un Chevalier de la mort.");
                return;
            }
            player->CastSpell(knight, N_H_BULLE, TRIGGERED_OLD_TRIGGERED);
            if (Group* group = player->GetGroup())
            {
                for (GroupReference* ref = group->GetFirstMember(); ref; ref = ref->next())
                    if (Player* m = ref->getSource())
                        if (m->IsAlive() && m->IsWithinDistInMap(player, 40.0f))
                            player->CastSpell(m, N_H_ABSORBE, TRIGGERED_OLD_TRIGGERED);
            }
            else
                player->CastSpell(player, N_H_ABSORBE, TRIGGERED_OLD_TRIGGERED);
        }
        else if (In(N_ANNIHILATION, N_ANNIHILATION_N, id))
        {
            std::vector<uint64> before;
            ForArmy(player, false, [&](Unit* u) { before.push_back(u->GetObjectGuid().GetRawValue()); });
            for (uint32 i = 0; i < INVOCATIONS_N; ++i)
                if (player->HasSpell(INVOCATIONS[i].front))
                    player->CastSpell(player, INVOCATIONS[i].anni, TRIGGERED_OLD_TRIGGERED);
            ForArmy(player, false, [&](Unit* u)
            {
                if (std::find(before.begin(), before.end(), u->GetObjectGuid().GetRawValue()) == before.end())
                {
                    u->CastSpell(u, N_H_AFFAIBLI, TRIGGERED_OLD_TRIGGERED);
                    u->SetHealth(u->GetMaxHealth() / 2);
                }
            });
        }
        else if (In(N_MORT, N_MORT_N, id))
        {
            if (!victim || !victim->IsAlive())
                return;
            const uint32_t* lists[] = { N_DOT_MOT, N_DOT_CORRUPTION, N_DOT_VOL, N_DOT_MALEDICTION, N_DOT_PESTE, N_DOT_MAUDIT };
            const uint32 sizes[] = { N_DOT_MOT_N, N_DOT_CORRUPTION_N, N_DOT_VOL_N, N_DOT_MALEDICTION_N, N_DOT_PESTE_N, N_DOT_MAUDIT_N };
            for (uint32 i = 0; i < 6; ++i)
                if (uint32 r = Best(player, lists[i], sizes[i]))
                    player->CastSpell(victim, r, TRIGGERED_OLD_TRIGGERED);
        }
        else if (In(N_CAMOUFLAGE, N_CAMOUFLAGE_N, id))
            ForArmy(player, true, [&](Unit* u) { player->CastSpell(u, N_H_CAMOU, TRIGGERED_OLD_TRIGGERED); });
    }

    // ------------------------------------------------------------------ Sniper
    void ClassesModule::SniperCast(Player* player, uint32 id, Unit* /*victim*/)
    {
        if (In(S_RECUL, S_RECUL_N, id))
            player->KnockBackWithAngle(player->GetOrientation() + 3.14159265f, 9.0f, 4.0f);
        else if (In(S_APPEL, S_APPEL_N, id))
        {
            std::vector<uint64> before;
            ForArmy(player, false, [&](Unit* u) { before.push_back(u->GetObjectGuid().GetRawValue()); });
            for (uint32 i = 0; i < S_BEASTS_N && i < S_BEAST_HIDDEN_N; ++i)
                if (player->HasSpell(S_BEASTS[i]))
                    player->CastSpell(player, S_BEAST_HIDDEN[i], TRIGGERED_OLD_TRIGGERED);
            ForArmy(player, false, [&](Unit* u)
            {
                if (std::find(before.begin(), before.end(), u->GetObjectGuid().GetRawValue()) == before.end())
                    u->CastSpell(u, S_H_AFFAIBLI, TRIGGERED_OLD_TRIGGERED);
            });
        }
        else if (In(S_ORDRE, S_ORDRE_N, id))
            ForArmy(player, true, [&](Unit* u) { player->CastSpell(u, S_H_ENRAGE, TRIGGERED_OLD_TRIGGERED); });
    }

    // ------------------------------------------------------------------ Métamorphe
    void ClassesModule::MetaCast(Player* player, uint32 id, Unit* /*victim*/)
    {
        if (In(M_APPEL_TOT, M_APPEL_TOT_N, id))
        {
            const uint32_t* lists[] = { M_TOTEM_FEU, M_TOTEM_EAU, M_TOTEM_ROCHE, M_TOTEM_GIVRE };
            const uint32 sizes[] = { M_TOTEM_FEU_N, M_TOTEM_EAU_N, M_TOTEM_ROCHE_N, M_TOTEM_GIVRE_N };
            for (uint32 i = 0; i < 4; ++i)
                if (uint32 r = Best(player, lists[i], sizes[i]))
                    player->CastSpell(player, r, TRIGGERED_OLD_TRIGGERED);
        }
        else if (In(M_RENVOI_TOT, M_RENVOI_TOT_N, id))
        {
            int32 refund = 0;
            for (int i = 0; i < MAX_TOTEM_SLOT; ++i)
            {
                if (Totem* totem = player->GetTotem(TotemSlot(i)))
                {
                    if (SpellEntry const* s = sSpellTemplate.LookupEntry<SpellEntry>(totem->GetUInt32Value(UNIT_CREATED_BY_SPELL)))
                        refund += int32(s->manaCost) * 3 / 4;
                    totem->UnSummon();
                }
            }
            if (refund)
                player->ModifyPower(POWER_MANA, refund);
        }
        MetaPassives(player);
    }

    void ClassesModule::MetaPassives(Player* player)
    {
        // Esprit guérisseur : soins x2,5 et recharges -50 % sans buff de spé DPS ou tank
        if (T_ESPRIT[0] && player->HasSpell(T_ESPRIT[0]))
        {
            bool combat = (M_RENFO[0] && player->HasAura(M_RENFO[0])) || (M_MASSIVE[0] && player->HasAura(M_MASSIVE[0]));
            bool has = player->HasAura(M_H_ESPRIT);
            if (!combat && !has)
                player->CastSpell(player, M_H_ESPRIT, TRIGGERED_OLD_TRIGGERED);
            else if (combat && has)
                player->RemoveAurasDueToSpell(M_H_ESPRIT);
        }
        // Force de l'esprit : une partie de l'Intelligence convertie en Force
        uint32 rank = TalentRank(player, T_FORCE, T_FORCE_N, 3);
        int32 value = rank ? int32(player->GetStat(STAT_INTELLECT) * (rank >= 3 ? 1.0f : 0.33f * rank)) : 0;
        int32& last = forceValue[player->GetObjectGuid().GetRawValue()];
        if (value != last)
        {
            player->RemoveAurasDueToSpell(M_H_FORCE);
            if (value > 0)
                player->CastCustomSpell(player, M_H_FORCE, &value, nullptr, nullptr, TRIGGERED_OLD_TRIGGERED);
            last = value;
        }
    }

    // ------------------------------------------------------------------ crochets
    void ClassesModule::OnCast(Spell* spell, Unit* caster, Unit* victim)
    {
        if (!spell || !caster || caster->GetTypeId() != TYPEID_PLAYER || !spell->m_spellInfo)
            return;
        Player* player = static_cast<Player*>(caster);
        uint8 cls = player->getClass();
        if (cls != C_NECRO && cls != C_SNIPER && cls != C_META)
            return;
        if (s_depth > 0)
            return;
        std::lock_guard<std::recursive_mutex> guard(lock);
        DepthGuard depth;
        uint32 id = spell->m_spellInfo->Id;
        if (cls == C_NECRO)
            NecroCast(player, id, victim, spell);
        else if (cls == C_SNIPER)
            SniperCast(player, id, victim);
        else
            MetaCast(player, id, victim);
    }

    void ClassesModule::OnHit(Spell* spell, Unit* caster, Unit* victim)
    {
        if (!spell || !caster || !victim || caster->GetTypeId() != TYPEID_PLAYER || !spell->m_spellInfo)
            return;
        if (s_depth > 0)
            return;
        DepthGuard depth;
        Player* player = static_cast<Player*>(caster);
        SpellEntry const* info = spell->m_spellInfo;
        uint32 id = info->Id;
        if (player->getClass() == C_SNIPER)
        {
            // Balle magique : chaque tir applique les 4 balles
            if (info->DmgClass == SPELL_DAMAGE_CLASS_RANGED && S_MAGIQUE[0] && player->HasAura(S_MAGIQUE[0]) && victim->IsAlive())
            {
                const uint32_t* lists[] = { S_BALLE_FEU, S_BALLE_EAU, S_BALLE_GIVRE, S_BALLE_ROCHE };
                const uint32 sizes[] = { S_BALLE_FEU_N, S_BALLE_EAU_N, S_BALLE_GIVRE_N, S_BALLE_ROCHE_N };
                for (uint32 i = 0; i < 4; ++i)
                {
                    uint32 r = Best(player, lists[i], sizes[i]);
                    SpellEntry const* b = r ? sSpellTemplate.LookupEntry<SpellEntry>(r) : nullptr;
                    if (b && b->EffectTriggerSpell[1])
                        player->CastSpell(victim, b->EffectTriggerSpell[1], TRIGGERED_OLD_TRIGGERED);
                }
            }
        }
        else if (player->getClass() == C_META && In(M_JUGEMENT, M_JUGEMENT_N, id))
        {
            if (M_BEAU[0] && player->HasAura(M_BEAU[0]))
            {
                player->ModifyPower(POWER_MANA, int32(info->manaCost));
                player->CastSpell(player, M_H_JUG_EAU, TRIGGERED_OLD_TRIGGERED);
            }
            else if (M_RENFO[0] && player->HasAura(M_RENFO[0]))
                player->CastSpell(victim, M_H_JUG_FEU, TRIGGERED_OLD_TRIGGERED);
            else if (M_MASSIVE[0] && player->HasAura(M_MASSIVE[0]))
                player->CastSpell(player, M_H_JUG_ANG, TRIGGERED_OLD_TRIGGERED);
        }
    }

    bool ClassesModule::OnPeriodicTick(Aura* aura)
    {
        // Maléfice : les DoT du Nécromancien infligent un tick supplémentaire (dégâts doublés)
        if (!aura || !N_MALEFICE[0] || s_depth > 0)
            return false;
        Unit* caster = aura->GetCaster();
        Unit* target = aura->GetTarget();
        if (!caster || !target || caster->GetTypeId() != TYPEID_PLAYER || !target->IsAlive())
            return false;
        if (!caster->HasAura(N_MALEFICE[0]))
            return false;
        uint32 id = aura->GetSpellProto()->Id;
        if (In(N_DOT_MOT, N_DOT_MOT_N, id) || In(N_DOT_CORRUPTION, N_DOT_CORRUPTION_N, id) || In(N_DOT_VOL, N_DOT_VOL_N, id) ||
            In(N_DOT_MALEDICTION, N_DOT_MALEDICTION_N, id) || In(N_DOT_PESTE, N_DOT_PESTE_N, id) || In(N_DOT_MAUDIT, N_DOT_MAUDIT_N, id))
        {
            int32 amount = std::max(1, aura->GetModifier()->m_amount);
            DepthGuard depth;
            caster->CastCustomSpell(target, N_H_MALEFICE_TICK, &amount, nullptr, nullptr, TRIGGERED_OLD_TRIGGERED);
        }
        return false;
    }

    void ClassesModule::OnKill(Unit* unit, Unit* victim)
    {
        // Récolte d'âme : tuer une cible affectée par une DoT du Nécromancien rend du mana
        if (!unit || !victim || unit->GetTypeId() != TYPEID_PLAYER)
            return;
        Player* player = static_cast<Player*>(unit);
        if (player->getClass() != C_NECRO)
            return;
        uint32 rank = TalentRank(player, T_RECOLTE, T_RECOLTE_N, 2);
        if (!rank)
            return;
        const uint32_t* lists[] = { N_DOT_MOT, N_DOT_CORRUPTION, N_DOT_VOL, N_DOT_MALEDICTION, N_DOT_PESTE, N_DOT_MAUDIT };
        const uint32 sizes[] = { N_DOT_MOT_N, N_DOT_CORRUPTION_N, N_DOT_VOL_N, N_DOT_MALEDICTION_N, N_DOT_PESTE_N, N_DOT_MAUDIT_N };
        for (uint32 i = 0; i < 6; ++i)
            for (uint32 j = 0; j < sizes[i]; ++j)
                if (victim->HasAura(lists[i][j]))
                {
                    player->ModifyPower(POWER_MANA, int32(player->GetMaxPower(POWER_MANA) * 5 * rank / 100));
                    return;
                }
    }

    void ClassesModule::OnLearnTalent(Player* player, uint32 spellId)
    {
        // Maîtrise de l'invocation : toutes les armes
        if (player && T_MAITRISE_INV[0] && spellId == T_MAITRISE_INV[0])
        {
            static const uint32 weapons[] = { 196, 197, 198, 199, 200, 201, 202, 227, 264, 266, 1180, 5011, 15590 };
            for (uint32 w : weapons)
                if (!player->HasSpell(w))
                    player->learnSpell(w, false);
        }
    }

    void ClassesModule::OnLogOut(Player* player)
    {
        std::lock_guard<std::recursive_mutex> guard(lock);
        armies.erase(player->GetObjectGuid().GetRawValue());
        forceValue.erase(player->GetObjectGuid().GetRawValue());
    }

    // ------------------------------------------------------------------ IA des bots
    void ClassesModule::OnUpdate(uint32 elapsed)
    {
        botTimer += elapsed;
        if (botTimer < 1000)
            return;
        botTimer = 0;

        std::vector<std::pair<Map*, ObjectGuid>> todo;
        {
            HashMapHolder<Player>::ReadGuard g(HashMapHolder<Player>::GetLock());
            for (auto const& kv : HashMapHolder<Player>::GetContainer())
            {
                Player* p = kv.second;
                if (!p || !p->IsInWorld() || !p->IsAlive())
                    continue;
                uint8 cls = p->getClass();
                if ((cls != C_NECRO && cls != C_SNIPER && cls != C_META) || !IsBot(p))
                    continue;
                if (Map* map = p->GetMap())
                    todo.emplace_back(map, p->GetObjectGuid());
            }
        }
        for (auto const& t : todo)
        {
            ObjectGuid guid = t.second;
            t.first->GetMessager().AddMessage([guid](Map* map)
            {
                if (Player* bot = map->GetPlayer(guid))
                    if (instance)
                        instance->BotThink(bot);
            });
        }
    }

    bool ClassesModule::TryCast(Player* bot, Unit* target, uint32 spellId)
    {
        if (!spellId || !target)
            return false;
        SpellEntry const* info = sSpellTemplate.LookupEntry<SpellEntry>(spellId);
        if (!info || !bot->IsSpellReady(*info))
            return false;
        if (info->manaCost && bot->GetPower(POWER_MANA) < info->manaCost)
            return false;
        return bot->CastSpell(target, info, TRIGGERED_NONE) == SPELL_CAST_OK;
    }

    void ClassesModule::BotThink(Player* bot)
    {
        if (!bot->IsAlive() || bot->IsNonMeleeSpellCasted(false) || bot->IsMounted())
            return;
        std::lock_guard<std::recursive_mutex> guard(lock);
        uint8 cls = bot->getClass();
        if (cls == C_META)
        {
            DepthGuard depth;
            MetaPassives(bot);
        }
        Unit* victim = bot->GetVictim();
        if (victim && (!victim->IsAlive() || !bot->CanAttack(victim)))
            victim = nullptr;
        bool combat = bot->IsInCombat() && victim;

        auto selfBuff = [&](const uint32_t* arr, uint32 n) -> bool
        {
            uint32 r = Best(bot, arr, n);
            return r && !bot->HasAura(r) && TryCast(bot, bot, r);
        };
        auto dot = [&](const uint32_t* arr, uint32 n) -> bool
        {
            uint32 r = Best(bot, arr, n);
            return r && victim && !victim->HasAura(r) && TryCast(bot, victim, r);
        };
        auto nuke = [&](const uint32_t* arr, uint32 n) -> bool
        {
            uint32 r = Best(bot, arr, n);
            return r && victim && TryCast(bot, victim, r);
        };

        if (cls == C_NECRO)
        {
            if (selfBuff(BN_ARMURE, BN_ARMURE_N))
                return;
            // armée : invoquer si des points sont libres (hors combat de préférence)
            CleanArmy(bot);
            uint32 used = 0;
            for (auto const& e : armies[bot->GetObjectGuid().GetRawValue()])
                used += e.cost;
            if (!combat && used < MaxPoints(bot))
            {
                for (int32 i = int32(INVOCATIONS_N) - 1; i >= 0; --i)
                    if (bot->HasSpell(INVOCATIONS[i].front) && used + INVOCATIONS[i].cost <= MaxPoints(bot) &&
                        TryCast(bot, bot, INVOCATIONS[i].front))
                        return;
            }
            if (!combat)
                return;
            if (dot(BN_MOT, BN_MOT_N) || dot(BN_CORRUPTION, BN_CORRUPTION_N) || dot(BN_MALEDICTION, BN_MALEDICTION_N) ||
                dot(BN_PESTE, BN_PESTE_N) || dot(BN_MAUDIT, BN_MAUDIT_N) || dot(BN_VOL, BN_VOL_N))
                return;
            if (nuke(BN_BOULE, BN_BOULE_N) || nuke(BN_TIROMBRE, BN_TIROMBRE_N) || nuke(BN_ECLAIR, BN_ECLAIR_N) ||
                nuke(BN_JAVELOT, BN_JAVELOT_N) || nuke(BN_TRAIT, BN_TRAIT_N))
                return;
        }
        else if (cls == C_SNIPER)
        {
            uint32 fauve = Best(bot, BS_FAUVE, BS_FAUVE_N);
            if (fauve && !bot->HasAura(fauve) && TryCast(bot, bot, fauve))
                return;
            if (!combat)
                return;
            if (bot->GetDistance(victim) > 8.0f && !bot->IsNonMeleeSpellCasted(false, false, true) && bot->HasSpell(75))
                bot->CastSpell(victim, 75, TRIGGERED_NONE);
            uint32 feu = Best(bot, S_BALLE_FEU, S_BALLE_FEU_N);
            if (feu && !bot->HasAura(feu) && TryCast(bot, bot, feu))
                return;
            if (dot(BS_MARQUE, BS_MARQUE_N) || dot(BS_SAIGNANT, BS_SAIGNANT_N))
                return;
            if (nuke(BS_EXPLOSIF, BS_EXPLOSIF_N) || nuke(BS_PRECISION, BS_PRECISION_N) || nuke(BS_MULTIPLE, BS_MULTIPLE_N) ||
                nuke(BS_BESTIAL, BS_BESTIAL_N) || nuke(BS_ARCANES, BS_ARCANES_N))
                return;
        }
        else if (cls == C_META)
        {
            if (selfBuff(BM_LIEN, BM_LIEN_N))
                return;
            // soins d'abord : membre du groupe sous 50 %
            Unit* hurt = nullptr;
            if (Group* group = bot->GetGroup())
            {
                for (GroupReference* ref = group->GetFirstMember(); ref; ref = ref->next())
                    if (Player* m = ref->getSource())
                        if (m->IsAlive() && m->IsInMap(bot) && m->IsWithinDistInMap(bot, 40.0f) && m->GetHealthPercent() < 50.0f)
                            if (!hurt || m->GetHealthPercent() < hurt->GetHealthPercent())
                                hurt = m;
            }
            else if (bot->GetHealthPercent() < 50.0f)
                hurt = bot;
            if (hurt)
            {
                uint32 remous = Best(bot, BM_REMOUS, BM_REMOUS_N);
                if (remous && !hurt->HasAura(remous) && TryCast(bot, hurt, remous))
                    return;
                if (TryCast(bot, hurt, Best(bot, BM_RECUP, BM_RECUP_N)) || TryCast(bot, hurt, Best(bot, BM_SALVE, BM_SALVE_N)))
                    return;
            }
            if (!combat)
                return;
            if (dot(BM_TONNERRE, BM_TONNERRE_N))
                return;
            if (nuke(BM_MASSACRE, BM_MASSACRE_N) || nuke(BM_STELLAIRE, BM_STELLAIRE_N) || nuke(BM_COLERE, BM_COLERE_N) ||
                nuke(BM_HFEU, BM_HFEU_N) || nuke(BM_TERRE, BM_TERRE_N) || nuke(BM_LUNAIRE, BM_LUNAIRE_N))
                return;
        }
    }
}
