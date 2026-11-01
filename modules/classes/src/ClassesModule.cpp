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
#include "Maps/GridDefines.h"
#include "Grids/GridNotifiers.h"
#include "Grids/GridNotifiersImpl.h"
#include "Grids/CellImpl.h"

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

    static uint32 TRank(Player* player, const uint32_t* arr, uint32 n)
    {
        return TalentRank(player, arr, n, n ? n : 1);
    }

    static bool Roll(float pct)
    {
        return pct > 0.0f && frand(0.0f, 100.0f) < pct;
    }

    // remplace l'aura cachée si sa valeur a changé (bp0 sur l'effet 1, bp1 sur l'effet 2)
    static void SetHiddenAura(Unit* u, uint32 spellId, int32 bp0, int32 bp1, Unit* source = nullptr)
    {
        int32 current = INT32_MIN;
        if (Aura* a = u->GetAura(spellId, EFFECT_INDEX_0))
            current = a->GetModifier()->m_amount;
        if (bp0 == 0 && bp1 == 0)
        {
            if (current != INT32_MIN)
                u->RemoveAurasDueToSpell(spellId);
            return;
        }
        if (current == bp0)
            return;
        u->RemoveAurasDueToSpell(spellId);
        u->CastCustomSpell(u, spellId, &bp0, &bp1, nullptr, TRIGGERED_OLD_TRIGGERED, nullptr, nullptr,
                           source ? source->GetObjectGuid() : ObjectGuid());
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

    // membres du groupe (ou le joueur seul) à moins de `range` mètres de `center`
    static void GroupAround(Player* p, Unit* center, float range, std::vector<Unit*>& out)
    {
        if (Group* g = p->GetGroup())
        {
            for (GroupReference* ref = g->GetFirstMember(); ref; ref = ref->next())
                if (Player* m = ref->getSource())
                    if (m->IsInWorld() && m->IsAlive() && m->GetMap() == p->GetMap() && center->IsWithinDistInMap(m, range))
                        out.push_back(m);
        }
        else if (p->IsAlive() && center->IsWithinDistInMap(p, range))
            out.push_back(p);
    }

    static float HpPct(Unit* u)
    {
        return u->GetMaxHealth() ? float(u->GetHealth()) / float(u->GetMaxHealth()) : 1.0f;
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
        // seules les invocations encore dans la liste des gardiens du joueur comptent
        // (un gardien renvoyé quitte cette liste tout de suite, même s'il reste un instant sur la carte)
        std::vector<uint64> alive;
        player->CallForAllControlledUnits([&](Unit* u) { if (u && u->IsAlive()) alive.push_back(u->GetObjectGuid().GetRawValue()); },
                                          CONTROLLED_GUARDIANS);
        auto& dq = it->second;
        dq.erase(std::remove_if(dq.begin(), dq.end(), [&](const ArmyEntry& e)
        {
            return std::find(alive.begin(), alive.end(), e.guid) == alive.end();
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
            ForArmy(player, true, [&](Unit* u) { u->CastSpell(u, N_H_BERSERK, TRIGGERED_OLD_TRIGGERED, nullptr, nullptr, player->GetObjectGuid()); });
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
            ForArmy(player, true, [&](Unit* u) { u->CastCustomSpell(u, N_H_RENOV, &tick, nullptr, nullptr, TRIGGERED_OLD_TRIGGERED, nullptr, nullptr, player->GetObjectGuid()); });
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
            knight->CastSpell(knight, N_H_BULLE, TRIGGERED_OLD_TRIGGERED, nullptr, nullptr, player->GetObjectGuid());
            if (Group* group = player->GetGroup())
            {
                for (GroupReference* ref = group->GetFirstMember(); ref; ref = ref->next())
                    if (Player* m = ref->getSource())
                        if (m->IsAlive() && m->IsWithinDistInMap(player, 40.0f))
                            m->CastSpell(m, N_H_ABSORBE, TRIGGERED_OLD_TRIGGERED, nullptr, nullptr, player->GetObjectGuid());
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
            const uint32_t* dups[] = { N_DUP_MOT, N_DUP_CORRUPTION, N_DUP_VOL, N_DUP_MALEDICTION, N_DUP_PESTE, N_DUP_MAUDIT };
            const uint32 dsizes[] = { N_DUP_MOT_N, N_DUP_CORRUPTION_N, N_DUP_VOL_N, N_DUP_MALEDICTION_N, N_DUP_PESTE_N, N_DUP_MAUDIT_N };
            bool doubled = T_DOUBLE[0] && player->HasSpell(T_DOUBLE[0]);
            for (uint32 i = 0; i < 6; ++i)
            {
                uint32 r = Best(player, lists[i], sizes[i]);
                if (!r)
                    continue;
                // Fléau double : la copie (autre identifiant) se cumule avec la DoT d'origine
                if (doubled)
                    for (uint32 j = 0; j < sizes[i] && j < dsizes[i]; ++j)
                        if (lists[i][j] == r)
                            r = dups[i][j];
                player->CastSpell(victim, r, TRIGGERED_OLD_TRIGGERED);
            }
        }
        else if (In(N_CAMOUFLAGE, N_CAMOUFLAGE_N, id))
            ForArmy(player, true, [&](Unit* u) { u->CastSpell(u, N_H_CAMOU, TRIGGERED_OLD_TRIGGERED, nullptr, nullptr, player->GetObjectGuid()); });
    }

    // ------------------------------------------------------------------ Sniper
    void ClassesModule::SniperCast(Player* player, uint32 id, Unit* /*victim*/)
    {
        // balles maîtrisées : recharge propre, hors recharge partagée
        struct Maitrise { const uint32_t* ranks; uint32 n; const uint32_t* talent; uint32 cd; };
        const Maitrise maitrises[] = { { S_BALLE2_FEU, S_BALLE2_FEU_N, T_B_FEU, 20000 }, { S_BALLE2_EAU, S_BALLE2_EAU_N, T_B_EAU, 15000 },
                                       { S_BALLE2_GIVRE, S_BALLE2_GIVRE_N, T_B_GIVRE, 15000 } };
        for (auto const& m : maitrises)
        {
            if (In(m.ranks, m.n, id) && m.talent[0] && player->HasSpell(m.talent[0]))
            {
                player->RemoveSpellCategoryCooldown(BULLET_CAT, true);
                if (SpellEntry const* info = sSpellTemplate.LookupEntry<SpellEntry>(id))
                    player->AddCooldown(*info, nullptr, false, m.cd, true);
                return;
            }
        }
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
            ForArmy(player, true, [&](Unit* u) { u->CastSpell(u, S_H_ENRAGE, TRIGGERED_OLD_TRIGGERED, nullptr, nullptr, player->GetObjectGuid()); });
    }

    // ------------------------------------------------------------------ Métamorphe
    void ClassesModule::MetaCast(Player* player, uint32 id, Unit* victim)
    {
        // Massacre : 2e frappe à 150 %, avec l'arme en main gauche ou, avec un bouclier, l'arme principale
        if (In(M_MASSACRE, M_MASSACRE_N, id))
        {
            if (victim && victim->IsAlive())
            {
                if (player->GetWeaponForAttack(OFF_ATTACK, true, true))
                    player->CastSpell(victim, M_H2_MASSACRE_G, TRIGGERED_OLD_TRIGGERED);
                else
                    player->CastSpell(victim, M_H2_MASSACRE_B, TRIGGERED_OLD_TRIGGERED);
            }
            return;
        }
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
        bool talent = T_ESPRIT[0] && player->HasSpell(T_ESPRIT[0]);
        bool combat = (M_RENFO[0] && player->HasAura(M_RENFO[0])) || (M_MASSIVE[0] && player->HasAura(M_MASSIVE[0]));
        bool has = player->HasAura(M_H_ESPRIT);
        if (talent && !combat && !has)
            player->CastSpell(player, M_H_ESPRIT, TRIGGERED_OLD_TRIGGERED);
        else if ((!talent || combat) && has)
            player->RemoveAurasDueToSpell(M_H_ESPRIT);
        // Force de l'esprit : une partie de l'Intelligence convertie en Force
        uint32 rank = TalentRank(player, T_FORCE, T_FORCE_N, 3);
        int32 value = rank ? int32(player->GetStat(STAT_INTELLECT) * (rank >= 3 ? 1.0f : 0.33f * rank)) : 0;
        int32 current = -1;
        if (Aura* a = player->GetAura(M_H_FORCE, EFFECT_INDEX_0))
            current = a->GetModifier()->m_amount;
        if (value <= 0)
        {
            if (current >= 0)
                player->RemoveAurasDueToSpell(M_H_FORCE);
        }
        else if (value != current)
        {
            player->RemoveAurasDueToSpell(M_H_FORCE);
            player->CastCustomSpell(player, M_H_FORCE, &value, nullptr, nullptr, TRIGGERED_OLD_TRIGGERED);
        }
    }

    // ------------------------------------------------------------------ 4e spé des classes vanilla
    void ClassesModule::Spe4Cast(Player* player, uint32 id, Unit* victim)
    {
        uint8 cls = player->getClass();
        if (cls == CLASS_PALADIN)
        {
            // Sceau du soleil : le Jugement ne le consomme pas (on le remet après le retrait fait par le script du Jugement)
            if (In(P4_JUG_SOLEIL, P4_JUG_SOLEIL_N, id))
                player->CastSpell(player, P4_SCEAU[0], TRIGGERED_OLD_TRIGGERED);
            // Appel du Soleil : puissance des sorts du Sacré +25 %
            else if (In(P4_APPEL, P4_APPEL_N, id) && !player->HasAura(P4_APPEL_SP[0]))
            {
                int32 bp = player->SpellBaseDamageBonusDone(SPELL_SCHOOL_MASK_HOLY) / 4;
                if (bp > 0)
                    player->CastCustomSpell(player, P4_APPEL_SP[0], &bp, nullptr, nullptr, TRIGGERED_OLD_TRIGGERED);
            }
        }
        else if (cls == CLASS_WARLOCK)
        {
            // Double armure : 2e couche d'Armure démoniaque du même rang
            for (uint32 i = 0; i < K4_DA_N; ++i)
                if (id == K4_DA[i] && T4_DOUBLE[0] && player->HasSpell(T4_DOUBLE[0]))
                {
                    player->RemoveAurasDueToSpell(K4_DA2[i]);
                    player->CastSpell(player, K4_DA2[i], TRIGGERED_OLD_TRIGGERED);
                }
            // Absorption démoniaque : dégâts +25 %, dégâts subis -10 %
            if (In(K4_ABSORB, K4_ABSORB_N, id))
                player->CastSpell(player, K4_ABSORB2[0], TRIGGERED_OLD_TRIGGERED);
        }
        else if (cls == CLASS_HUNTER)
        {
            // Rafale : 3 Tirs multiples d'un coup sur tout le monde à 20 m (soins en Posture infirmier, dégâts sinon)
            if (In(I4_RAFALE, I4_RAFALE_N, id))
            {
                int32 bp = int32((float(player->CalculateDamage(RANGED_ATTACK, false)) + 150.0f) * (player->GetShapeshiftForm() == ShapeshiftForm(I4_FORM[0]) ? 1.2f : 1.0f));
                if (player->GetShapeshiftForm() == ShapeshiftForm(I4_FORM[0]))
                {
                    std::vector<Unit*> allies;
                    GroupAround(player, player, 20.0f, allies);
                    for (Unit* a : allies)
                        for (int k = 0; k < 3; ++k)
                            player->CastCustomSpell(a, I4_SOIN[0], &bp, nullptr, nullptr, TRIGGERED_OLD_TRIGGERED);
                }
                else
                {
                    UnitList enemies;
                    MaNGOS::AnyUnfriendlyUnitInObjectRangeCheck check(player, 20.0f);
                    MaNGOS::UnitListSearcher<MaNGOS::AnyUnfriendlyUnitInObjectRangeCheck> searcher(enemies, check);
                    Cell::VisitAllObjects(player, searcher, 20.0f);
                    for (Unit* e : enemies)
                        if (e->IsAlive() && player->CanAttack(e))
                            for (int k = 0; k < 3; ++k)
                                player->CastCustomSpell(e, I4_DEGATS[0], &bp, nullptr, nullptr, TRIGGERED_OLD_TRIGGERED);
                }
            }
        }
        else if (cls == CLASS_ROGUE)
        {
            // Forme spectrale : recharge de Spectre remise à zéro
            if (In(R4_FORME, R4_FORME_N, id))
                player->RemoveSpellCooldown(*sSpellTemplate.LookupEntry<SpellEntry>(R4_SPECTRE[0]), true);
        }
        else if (cls == CLASS_MAGE)
        {
            // Lien de vie : un seul allié lié à la fois
            if (In(A4_LIEN, A4_LIEN_N, id) && victim)
            {
                uint64 key = player->GetObjectGuid().GetRawValue();
                ObjectGuid old(lienTarget[key]);
                if (!old.IsEmpty() && old != victim->GetObjectGuid())
                    if (Unit* prev = player->GetMap()->GetUnit(old))
                        prev->RemoveAurasByCasterSpell(A4_LIEN[0], player->GetObjectGuid());
                lienTarget[key] = victim->GetObjectGuid().GetRawValue();
            }
        }
        else if (cls == CLASS_SHAMAN)
        {
            // Bouclier de terre et Bouclier de foudre s'excluent, sauf avec Bouclier double
            bool dbl = T4_DOUBLE_B[0] && player->HasSpell(T4_DOUBLE_B[0]);
            if (!dbl && In(H4_TERRE, H4_TERRE_N, id))
                for (uint32 i = 0; i < H4_FOUDRE_N; ++i)
                    player->RemoveAurasDueToSpell(H4_FOUDRE[i]);
            else if (!dbl && In(H4_FOUDRE, H4_FOUDRE_N, id))
                player->RemoveAurasDueToSpell(H4_TERRE[0]);
        }
        else if (cls == CLASS_WARRIOR)
        {
            // Soif de carnage : un coup critique rend 1 % des PV max par rang
            if (In(W4_SOIF, W4_SOIF_N, id))
                if (uint32 r = TRank(player, T4_SOIF, T4_SOIF_N))
                    player->DealHeal(player, player->GetMaxHealth() * r / 100, sSpellTemplate.LookupEntry<SpellEntry>(W4_SOIF[0]));
        }
    }

    void ClassesModule::Spe4Upkeep(Player* player)
    {
        uint8 cls = player->getClass();
        if (cls == CLASS_PALADIN)
        {
            if (!player->HasAura(P4_APPEL[0]) && player->HasAura(P4_APPEL_SP[0]))
                player->RemoveAurasDueToSpell(P4_APPEL_SP[0]);
        }
        else if (cls == CLASS_WARLOCK)
        {
            uint32 rA = TRank(player, T4_ARMURE, T4_ARMURE_N);
            // Armure démoniaque renforcée : maille, bouclier et blocage (retirés après un reset de talents)
            static const uint32 gear[] = { 8737, 9116, 107 };
            for (uint32 g : gear)
            {
                if (rA && !player->HasSpell(g))
                    player->learnSpell(g, false);
                else if (!rA && player->HasSpell(g))
                    player->removeSpell(g);
            }
            bool armor = false;
            for (uint32 i = 0; i < K4_DA_N; ++i)
                if (player->HasAura(K4_DA[i]))
                    armor = true;
            // menace +5 % par rang tant qu'Armure démoniaque est active
            SetHiddenAura(player, K4_MENACE[0], armor ? int32(5 * rA) : 0, 0);
            // Double armure : la 2e couche disparaît avec l'armure ou le talent
            bool dbl = T4_DOUBLE[0] && player->HasSpell(T4_DOUBLE[0]);
            if (!armor || !dbl)
                for (uint32 i = 0; i < K4_DA_N; ++i)
                    if (player->HasAura(K4_DA2[i]))
                        player->RemoveAurasDueToSpell(K4_DA2[i]);
            // Incantation démoniaque : dégâts d'Immolation et Corruption -25 % (le reste est sur le talent)
            bool incant = T4_INCANT[0] && player->HasSpell(T4_INCANT[0]);
            if (incant && !player->HasAura(K4_INCANT[0]))
                player->CastSpell(player, K4_INCANT[0], TRIGGERED_OLD_TRIGGERED);
            else if (!incant && player->HasAura(K4_INCANT[0]))
                player->RemoveAurasDueToSpell(K4_INCANT[0]);
        }
        else if (cls == CLASS_HUNTER)
        {
            // Postures de campagne : un tir de soin pour chaque rang de tir connu
            bool postures = T4_POSTURES[0] && player->HasSpell(T4_POSTURES[0]);
            for (uint32 j = 0; j < I4_SHOT_N; ++j)
            {
                if (!I4_SRC[j])
                    continue;
                if (postures && player->HasSpell(I4_SRC[j]) && !player->HasSpell(I4_SHOT[j]))
                    player->learnSpell(I4_SHOT[j], false);
                else if (!postures && player->HasSpell(I4_SHOT[j]))
                    player->removeSpell(I4_SHOT[j], false, false);
            }
            // Familier infirmier : le familier soigne l'allié le plus blessé toutes les 6 s
            if (T4_FAMILIER[0] && player->HasSpell(T4_FAMILIER[0]))
            {
                uint32& tick = petHealTick[player->GetObjectGuid().GetRawValue()];
                if (++tick >= 6)
                {
                    tick = 0;
                    if (Pet* pet = player->GetPet())
                        if (pet->IsAlive() && pet->IsInWorld())
                        {
                            std::vector<Unit*> allies;
                            GroupAround(player, pet, 30.0f, allies);
                            Unit* best = nullptr;
                            for (Unit* a : allies)
                                if (HpPct(a) < 0.9f && (!best || HpPct(a) < HpPct(best)))
                                    best = a;
                            if (best)
                            {
                                int32 bp = int32(100.0f + player->GetTotalAttackPowerValue(RANGED_ATTACK) * 0.15f);
                                pet->CastCustomSpell(best, I4_SOIN[0], &bp, nullptr, nullptr, TRIGGERED_OLD_TRIGGERED);
                            }
                        }
                }
            }
        }
        else if (cls == CLASS_ROGUE)
        {
            // Pénombre : critique contre une cible qui ne vous attaque pas
            int32 crit = 0;
            if (uint32 r = TRank(player, T4_PENOMBRE, T4_PENOMBRE_N))
                if (Unit* v = player->GetVictim())
                    if (v->GetVictim() != player)
                        crit = int32(r);
            SetHiddenAura(player, R4_CRIT[0], crit, 0);
        }
        else if (cls == CLASS_MAGE)
        {
            // Cœur de la nature : sorts de Feu <-> soins de Nature (en deux temps : retirer un rang retire aussi les suivants)
            bool coeur = T4_COEUR[0] && player->HasSpell(T4_COEUR[0]);
            std::vector<std::pair<uint32, uint32>> swaps;
            if (coeur)
            {
                std::vector<uint32> remove;
                for (uint32 i = 0; i < A4_FIRE_N; ++i)
                    if (player->HasSpell(A4_FIRE[i]))
                    {
                        if (!player->HasSpell(A4_HEAL[i]))
                            player->learnSpell(A4_HEAL[i], false);
                        swaps.emplace_back(A4_FIRE[i], A4_HEAL[i]);
                        if (!In(A4_KEEP, A4_KEEP_N, A4_FIRE[i]))
                            remove.push_back(A4_FIRE[i]);
                    }
                for (uint32 f : remove)
                    if (player->HasSpell(f))
                        player->removeSpell(f, false, false);
            }
            else
            {
                std::vector<uint32> remove;
                for (uint32 i = 0; i < A4_FIRE_N; ++i)
                    if (player->HasSpell(A4_HEAL[i]))
                    {
                        if (!player->HasSpell(A4_FIRE[i]))
                            player->learnSpell(A4_FIRE[i], false);
                        swaps.emplace_back(A4_HEAL[i], A4_FIRE[i]);
                        remove.push_back(A4_HEAL[i]);
                    }
                for (uint32 h : remove)
                    if (player->HasSpell(h))
                        player->removeSpell(h, false, false);
            }
            // barre d'action : les boutons suivent le changement de sort
            auto it = actionLists.find(player->GetObjectGuid().GetRawValue());
            if (!swaps.empty() && it != actionLists.end() && it->second)
            {
                bool sent = false;
                ActionButtonList copy = *it->second;
                for (auto const& b : copy)
                    if (b.second.GetType() == ACTION_BUTTON_SPELL && b.second.uState != ACTIONBUTTON_DELETED)
                        for (auto const& sw : swaps)
                            if (b.second.GetAction() == sw.first)
                            {
                                player->addActionButton(b.first, sw.second, ACTION_BUTTON_SPELL);
                                sent = true;
                            }
                if (sent)
                    player->SendInitialActionButtons();
            }
            // Armure de nature : puissance des soins +20 %
            int32 sp = 0;
            if (player->HasAura(A4_ARMURE[0]))
            {
                int32 cur = 0;
                if (Aura* a = player->GetAura(A4_ARMURE_SP[0], EFFECT_INDEX_0))
                    cur = a->GetModifier()->m_amount;
                sp = (player->SpellBaseHealingBonusDone(SPELL_SCHOOL_MASK_ALL) - cur) / 5;
            }
            SetHiddenAura(player, A4_ARMURE_SP[0], std::max(0, sp), 0);
            // Intelligence sylvestre : Intelligence des arcanes +20 % et autant d'Esprit, sur le Mage seulement
            int32 ai = 0;
            if (T4_SYLV[0] && player->HasSpell(T4_SYLV[0]))
                for (uint32 i = 0; i < A4_INT_N; ++i)
                    if (Aura* a = player->GetAura(A4_INT[i], EFFECT_INDEX_0))
                        ai = std::max(ai, a->GetModifier()->m_amount);
            SetHiddenAura(player, A4_AI[0], ai / 5, ai * 6 / 5);
        }
        else if (cls == CLASS_SHAMAN)
        {
            // Appel runique : soin sur la durée quand le bouclier se termine
            uint64 key = player->GetObjectGuid().GetRawValue();
            if (player->HasAura(H4_RUNIQUE[0]))
                runique.insert(key);
            else if (runique.erase(key))
                player->CastSpell(player, H4_HOT[0], TRIGGERED_OLD_TRIGGERED);
        }
        else if (cls == CLASS_WARRIOR)
        {
            bool instinct = T4_INSTINCT[0] && player->HasSpell(T4_INSTINCT[0]);
            // Instinct du berserker : Posture berserker dès le niveau 10 (gardée après un reset de talents)
            if (instinct && !player->HasSpell(2458))
                player->learnSpell(2458, false);
            bool low = player->GetHealth() * 2 < player->GetMaxHealth();
            // critique : +3 % en Posture berserker avec Instinct, Fureur aveugle sous 50 % de vie
            int32 crit = 0;
            if (instinct && player->GetShapeshiftForm() == FORM_BERSERKERSTANCE)
                crit += 3;
            if (low)
                crit += 2 * int32(TRank(player, T4_FUREUR_AV, T4_FUREUR_AV_N));
            SetHiddenAura(player, W4_CRIT[0], crit, 0);
            // Endurci : dégâts subis réduits sous 50 % de vie
            int32 red = low ? -2 * int32(TRank(player, T4_ENDURCI, T4_ENDURCI_N)) : 0;
            SetHiddenAura(player, W4_ENDURCI[0], red, 0);
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
        {
            if (s_depth == 0)
            {
                std::lock_guard<std::recursive_mutex> guard(lock);
                DepthGuard depth;
                Spe4Cast(player, spell->m_spellInfo->Id, victim);
            }
            return;
        }
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
        if (player->getClass() == CLASS_HUNTER)
        {
            // tirs de soin de l'Infirmier : le module calcule le soin (arme, base du sort, puissance d'attaque à distance)
            for (uint32 j = 0; j < I4_SHOT_N; ++j)
                if (I4_SHOT[j] == id && I4_KIND[j] != 9)
                {
                    float amount = 0.0f;
                    int32 base = SpellValue(info, 0);
                    if (base <= 1)
                        base = 0;
                    if (I4_W[j])
                        amount += float(player->CalculateDamage(RANGED_ATTACK, false));
                    amount = (amount + float(base)) * float(I4_MULT[j]) / 100.0f;
                    amount += player->GetTotalAttackPowerValue(RANGED_ATTACK) * float(I4_APC[j]) / 100.0f;
                    uint32 rT = TRank(player, T4_TRIAGE, T4_TRIAGE_N);
                    std::vector<Unit*> targets;
                    if (I4_KIND[j] == 2)
                    {
                        // la cible + les 2 alliés les plus blessés à 10 m d'elle
                        std::vector<Unit*> near;
                        GroupAround(player, victim, 10.0f, near);
                        near.erase(std::remove(near.begin(), near.end(), victim), near.end());
                        std::sort(near.begin(), near.end(), [](Unit* a, Unit* b) { return HpPct(a) < HpPct(b); });
                        targets.push_back(victim);
                        for (uint32 k = 0; k < near.size() && k < 2; ++k)
                            targets.push_back(near[k]);
                    }
                    else if (I4_KIND[j] == 3)
                    {
                        GroupAround(player, victim, 8.0f, targets);
                        if (std::find(targets.begin(), targets.end(), victim) == targets.end())
                            targets.push_back(victim);
                    }
                    else
                        targets.push_back(victim);
                    for (Unit* t : targets)
                    {
                        float a = amount;
                        if (rT && HpPct(t) < 0.5f)
                            a *= 1.0f + 0.05f * rT;
                        if (I4_KIND[j] == 1)
                        {
                            int32 bp = int32(a / 5.0f);
                            if (bp > 0)
                                player->CastCustomSpell(t, I4_HOT[0], &bp, nullptr, nullptr, TRIGGERED_OLD_TRIGGERED);
                        }
                        else
                        {
                            int32 bp = int32(a);
                            if (bp > 0)
                                player->CastCustomSpell(t, I4_SOIN[0], &bp, nullptr, nullptr, TRIGGERED_OLD_TRIGGERED);
                        }
                    }
                    break;
                }
            return;
        }
        if (player->getClass() == CLASS_MAGE)
        {
            // Bouclier de nature : Âme affaiblie comme Mot de pouvoir : Bouclier
            if (In(A4_BOUCLIER, A4_BOUCLIER_N, id) && victim->IsAlive())
                player->CastSpell(victim, 6788, TRIGGERED_OLD_TRIGGERED);
            return;
        }
        if (player->getClass() == C_NECRO && victim->IsAlive())
        {
            if ((In(N_DOT_PESTE, N_DOT_PESTE_N, id) || In(N_DUP_PESTE, N_DUP_PESTE_N, id)) && T_FLEAU[0] && player->HasSpell(T_FLEAU[0]))
                player->CastSpell(victim, N_H_FLEAU, TRIGGERED_OLD_TRIGGERED);
            if (In(N_ECLAIR, N_ECLAIR_N, id))
                if (uint32 r = TRank(player, T_MORSURE, T_MORSURE_N))
                {
                    int32 bp = -int32(20 + 4 * r);
                    player->CastCustomSpell(victim, N_H_MORSURE, &bp, nullptr, nullptr, TRIGGERED_OLD_TRIGGERED);
                }
            if (In(N_JAVELOT, N_JAVELOT_N, id))
                if (uint32 r = TRank(player, T_SYNERGIE, T_SYNERGIE_N))
                {
                    int32 bp = int32(15 * r);
                    player->CastCustomSpell(player, N_H_SYNERGIE, &bp, nullptr, nullptr, TRIGGERED_OLD_TRIGGERED);
                }
            return;
        }
        if (player->getClass() == C_SNIPER && victim->IsAlive())
        {
            if (In(S_CRI, S_CRI_N, id))
                if (uint32 r = TRank(player, T_CRI, T_CRI_N))
                {
                    int32 bp = -int32(3 * r);
                    player->CastCustomSpell(victim, S_H2_CRI, &bp, nullptr, nullptr, TRIGGERED_OLD_TRIGGERED);
                }
            if (In(S_BOMBE, S_BOMBE_N, id) || In(S_DYNAMITE, S_DYNAMITE_N, id))
                if (uint32 r = TRank(player, T_PIEGE, T_PIEGE_N))
                    if (Roll(5.0f * r))
                        player->CastSpell(victim, S_H2_PIEGE, TRIGGERED_OLD_TRIGGERED);
        }
        if (player->getClass() == C_META)
        {
            // Voie de la guérison : chaque Récupération renforce les suivantes sur la même cible
            if (In(M_RECUP, M_RECUP_N, id))
                if (uint32 r = TRank(player, T_VOIE, T_VOIE_N))
                {
                    uint32 stacks = 0;
                    if (SpellAuraHolder* hold = victim->GetSpellAuraHolder(M_H2_VOIE, player->GetObjectGuid()))
                        stacks = hold->GetStackAmount();
                    int32 extra = int32(SpellValue(info) * 0.06f * r * stacks);
                    if (extra > 0)
                        player->CastCustomSpell(victim, M_H2_VOIE_SOIN, &extra, nullptr, nullptr, TRIGGERED_OLD_TRIGGERED);
                    player->CastSpell(victim, M_H2_VOIE, TRIGGERED_OLD_TRIGGERED);
                }
            // Éclair lunaire : hâte cumulable (5 %, +1 % par rang de Fougue lunaire)
            if (In(M_LUNAIRE, M_LUNAIRE_N, id))
            {
                int32 bp = 5 + int32(TRank(player, T_FOUGUE, T_FOUGUE_N));
                player->CastCustomSpell(player, M_H2_LUNAIRE, &bp, nullptr, nullptr, TRIGGERED_OLD_TRIGGERED);
            }
        }
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
            {
                // soin sur la durée : 30 par seconde au niveau 60, +25 % par rang de Jugement du gardien
                float lvl = std::min(60.0f, float(player->GetLevel()));
                int32 bp = std::max(1, int32(30.0f * (0.05f + 0.95f * lvl / 60.0f) * (1.0f + 0.25f * TRank(player, T_JUG_GARDIEN, T_JUG_GARDIEN_N))));
                player->CastCustomSpell(player, M_H_JUG_ANG, &bp, nullptr, nullptr, TRIGGERED_OLD_TRIGGERED);
            }
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
        uint32 id = aura->GetSpellProto()->Id;
        Player* pc = static_cast<Player*>(caster);
        if (pc->getClass() == C_NECRO)
        {
            if (In(N_DOT_MOT, N_DOT_MOT_N, id) || In(N_DOT_CORRUPTION, N_DOT_CORRUPTION_N, id) ||
                In(N_DUP_MOT, N_DUP_MOT_N, id) || In(N_DUP_CORRUPTION, N_DUP_CORRUPTION_N, id))
                if (uint32 r = TRank(pc, T_CREPUSCULE, T_CREPUSCULE_N))
                    if (Roll(2.0f * r))
                    {
                        DepthGuard depth;
                        caster->CastSpell(caster, N_H_CREPUSCULE, TRIGGERED_OLD_TRIGGERED);
                    }
            if (In(N_METEORITE, N_METEORITE_N, id))
                if (uint32 r = TRank(pc, T_PYRO, T_PYRO_N))
                    if (Roll(13.0f * r))
                    {
                        DepthGuard depth;
                        caster->CastSpell(target, N_H_PYRO, TRIGGERED_OLD_TRIGGERED);
                    }
        }
        if (!caster->HasAura(N_MALEFICE[0]))
            return false;
        if (In(N_DOT_MOT, N_DOT_MOT_N, id) || In(N_DOT_CORRUPTION, N_DOT_CORRUPTION_N, id) || In(N_DOT_VOL, N_DOT_VOL_N, id) ||
            In(N_DOT_MALEDICTION, N_DOT_MALEDICTION_N, id) || In(N_DOT_PESTE, N_DOT_PESTE_N, id) || In(N_DOT_MAUDIT, N_DOT_MAUDIT_N, id) ||
            In(N_DUP_MOT, N_DUP_MOT_N, id) || In(N_DUP_CORRUPTION, N_DUP_CORRUPTION_N, id) || In(N_DUP_VOL, N_DUP_VOL_N, id) ||
            In(N_DUP_MALEDICTION, N_DUP_MALEDICTION_N, id) || In(N_DUP_PESTE, N_DUP_PESTE_N, id) || In(N_DUP_MAUDIT, N_DUP_MAUDIT_N, id))
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
        const uint32_t* lists[] = { N_DOT_MOT, N_DOT_CORRUPTION, N_DOT_VOL, N_DOT_MALEDICTION, N_DOT_PESTE, N_DOT_MAUDIT,
                                    N_DUP_MOT, N_DUP_CORRUPTION, N_DUP_VOL, N_DUP_MALEDICTION, N_DUP_PESTE, N_DUP_MAUDIT };
        const uint32 sizes[] = { N_DOT_MOT_N, N_DOT_CORRUPTION_N, N_DOT_VOL_N, N_DOT_MALEDICTION_N, N_DOT_PESTE_N, N_DOT_MAUDIT_N,
                                 N_DUP_MOT_N, N_DUP_CORRUPTION_N, N_DUP_VOL_N, N_DUP_MALEDICTION_N, N_DUP_PESTE_N, N_DUP_MAUDIT_N };
        std::vector<uint32> dots;
        for (uint32 i = 0; i < 12; ++i)
            for (uint32 j = 0; j < sizes[i]; ++j)
                if (victim->GetSpellAuraHolder(lists[i][j], player->GetObjectGuid()))
                    dots.push_back(lists[i][j]);
        if (dots.empty())
            return;
        std::lock_guard<std::recursive_mutex> guard(lock);
        DepthGuard depth;
        // Récolte d'âme : mana
        if (uint32 rank = TalentRank(player, T_RECOLTE, T_RECOLTE_N, 2))
            player->ModifyPower(POWER_MANA, int32(player->GetMaxPower(POWER_MANA) * 5 * rank / 100));
        // Contagion : les DoT passent à un ennemi proche
        if (uint32 r = TRank(player, T_CONTAGION, T_CONTAGION_N))
            if (Roll(25.0f * r))
                if (Unit* next = player->SelectRandomUnfriendlyTarget(victim, 20.0f))
                    if (next->IsAlive() && next != victim)
                        for (uint32 d : dots)
                            player->CastSpell(next, d, TRIGGERED_OLD_TRIGGERED);
    }

    void ClassesModule::OnDealDamage(Unit* unit, Unit* victim, uint32 health, uint32 damage)
    {
        // Chaman Ruines : Bouclier de terre, chaque coup reçu est absorbé à 10 % et consomme une charge
        if (victim && damage && damage < health && s_depth == 0 && victim->GetTypeId() == TYPEID_PLAYER && victim != unit &&
            static_cast<Player*>(victim)->getClass() == CLASS_SHAMAN && victim->IsAlive())
            if (SpellAuraHolder* hold = victim->GetSpellAuraHolder(H4_TERRE[0]))
            {
                if (uint32 back = damage / 10)
                    victim->ModifyHealth(int32(back));
                if (hold->DropAuraCharge() || hold->GetAuraCharges() == 0)
                    victim->RemoveAurasDueToSpell(H4_TERRE[0]);
            }
        // Démoniste Transfuge : Lien gangrené, les dégâts du démon soignent le Démoniste
        if (unit && victim && damage && s_depth == 0 && unit->GetTypeId() == TYPEID_UNIT && static_cast<Creature*>(unit)->IsPet())
            if (Unit* owner = unit->GetOwner())
                if (owner->GetTypeId() == TYPEID_PLAYER && owner != victim && owner->IsAlive() &&
                    static_cast<Player*>(owner)->getClass() == CLASS_WARLOCK && T4_LIEN[0] && static_cast<Player*>(owner)->HasSpell(T4_LIEN[0]))
                {
                    uint32 pct = 10 + 5 * TRank(static_cast<Player*>(owner), T4_LIEN_AM, T4_LIEN_AM_N);
                    if (uint32 h = std::min(damage, health) * pct / 100)
                        owner->ModifyHealth(int32(h));
                }
        // Guerrier Berserker : Carnage (vol de vie) et Fou de rage (rage +10 %)
        if (unit && victim && unit != victim && damage && s_depth == 0 && unit->GetTypeId() == TYPEID_PLAYER &&
            static_cast<Player*>(unit)->getClass() == CLASS_WARRIOR && unit->IsAlive())
        {
            Player* war = static_cast<Player*>(unit);
            uint32 dealt = std::min(damage, health);
            if (uint32 r = TRank(war, T4_CARNAGE, T4_CARNAGE_N))
                if (uint32 h = dealt * r / 100)
                    war->ModifyHealth(int32(h));
            if (W4_FOU[0] && war->HasAura(W4_FOU[0]))
            {
                float L = float(war->GetLevel());
                float conv = 0.0091107836f * L * L + 3.225598133f * L + 4.2652911f;
                int32 add = int32(float(dealt) / conv * 7.5f);     // 10 % de la rage d'un coup (rage interne x10)
                if (add > 0)
                    war->ModifyPower(POWER_RAGE, add);
            }
        }
        if (!victim || victim->GetTypeId() != TYPEID_PLAYER || !victim->IsAlive() || damage >= health)
            return;
        Player* player = static_cast<Player*>(victim);
        if (player->getClass() != C_META || s_depth > 0)
            return;
        uint32 r = TRank(player, T_EGIDE, T_EGIDE_N);
        if (!r)
            return;
        uint32 seuil = player->GetMaxHealth() * 35 / 100;
        if (health - damage >= seuil || health < seuil)
            return;
        std::lock_guard<std::recursive_mutex> guard(lock);
        time_t now = time(nullptr);
        time_t& last = egideTime[player->GetObjectGuid().GetRawValue()];
        if (now - last < 60)
            return;
        last = now;
        static const int32 pct[] = { 3, 6, 10 };
        int32 bp = int32(player->GetMaxHealth()) * pct[std::min<uint32>(r, 3) - 1] / 100;
        DepthGuard depth;
        player->CastCustomSpell(player, M_H2_EGIDE, &bp, nullptr, nullptr, TRIGGERED_OLD_TRIGGERED);
    }

    void ClassesModule::OnDealHeal(Unit* unit, Unit* victim, int32 /*gain*/, uint32 addHealth)
    {
        if (!unit || !victim || !addHealth || s_depth > 0 || unit->GetTypeId() != TYPEID_PLAYER)
            return;
        Player* mage = static_cast<Player*>(unit);
        if (mage->getClass() != CLASS_MAGE)
            return;
        std::lock_guard<std::recursive_mutex> guard(lock);
        DepthGuard depth;
        // Écorce protectrice : armure de la cible +10 % pendant 5 s
        if (T4_ECORCE[0] && mage->HasSpell(T4_ECORCE[0]) && victim->IsAlive())
            mage->CastSpell(victim, A4_ECORCE[0], TRIGGERED_OLD_TRIGGERED);
        // Lien de vie : l'allié lié reçoit 10 % (20 % avec le talent) des soins faits sur les autres
        auto it = lienTarget.find(mage->GetObjectGuid().GetRawValue());
        if (it == lienTarget.end() || !it->second)
            return;
        ObjectGuid tg(it->second);
        if (tg == victim->GetObjectGuid())
            return;
        Unit* linked = mage->GetMap()->GetUnit(tg);
        if (!linked || !linked->IsAlive() || !linked->GetSpellAuraHolder(A4_LIEN[0], mage->GetObjectGuid()) ||
            !mage->IsWithinDistInMap(linked, 40.0f))
            return;
        int32 bp = int32(addHealth * (10 + 5 * TRank(mage, T4_LIEN_VAM, T4_LIEN_VAM_N)) / 100);
        if (bp > 0)
            mage->CastCustomSpell(linked, A4_LIEN_SOIN[0], &bp, nullptr, nullptr, TRIGGERED_OLD_TRIGGERED);
    }

    bool ClassesModule::OnLoadActionButtons(Player* player, ActionButtonList& actionButtons)
    {
        std::lock_guard<std::recursive_mutex> guard(lock);
        actionLists[player->GetObjectGuid().GetRawValue()] = &actionButtons;
        return false;
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
        runique.erase(player->GetObjectGuid().GetRawValue());
        lienTarget.erase(player->GetObjectGuid().GetRawValue());
        petHealTick.erase(player->GetObjectGuid().GetRawValue());
        actionLists.erase(player->GetObjectGuid().GetRawValue());
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
                // classes vanilla : seulement les vrais joueurs (4e spé) ; les bots ne la prennent pas
                if (cls != C_NECRO && cls != C_SNIPER && cls != C_META && IsBot(p))
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
                if (Player* p = map->GetPlayer(guid))
                    if (instance && p->IsInWorld() && p->IsAlive())
                    {
                        instance->Upkeep(p);
                        if (IsBot(p))
                            instance->BotThink(p);
                    }
            });
        }
    }

    // effets permanents qui dépendent de l'armée, du familier ou des talents (toutes les secondes)
    void ClassesModule::Upkeep(Player* player)
    {
        std::lock_guard<std::recursive_mutex> guard(lock);
        DepthGuard depth;
        uint8 cls = player->getClass();
        if (cls != C_NECRO && cls != C_SNIPER && cls != C_META)
        {
            Spe4Upkeep(player);
            return;
        }
        if (cls == C_NECRO)
        {
            CleanArmy(player);
            auto& dq = armies[player->GetObjectGuid().GetRawValue()];
            Map* map = player->GetMap();
            std::vector<Unit*> army;
            for (auto const& e : dq)
                if (Pet* pet = map->GetPet(ObjectGuid(e.guid)))
                    army.push_back(pet);
            // Étreinte de la tombe + Chair putride : endurance et dégâts des invocations
            uint32 rE = TRank(player, T_ETREINTE, T_ETREINTE_N), rC = TRank(player, T_CHAIR, T_CHAIR_N);
            int32 sta = int32(2 * rE + 3 * rC), dmg = int32(rE * 3 / 2);
            for (Unit* u : army)
                if (!u->HasAura(N_H_TOMBE) && (sta || dmg))
                    u->CastCustomSpell(u, N_H_TOMBE, &sta, &dmg, nullptr, TRIGGERED_OLD_TRIGGERED);
            // Maître nécromancien : par type d'invocation différent
            uint32 rM = TRank(player, T_MAITRE, T_MAITRE_N);
            std::vector<uint32> types;
            for (Unit* u : army)
                if (std::find(types.begin(), types.end(), u->GetEntry()) == types.end())
                    types.push_back(u->GetEntry());
            int32 pct = int32(types.size() * 0.3f * rM + 0.5f);
            SetHiddenAura(player, N_H_MAITRE, pct, -pct);
            for (Unit* u : army)
                SetHiddenAura(u, N_H_MAITRE, pct, -pct);
            // Lien des morts : 20 % des dégâts subis vont à l'invocation principale
            bool lien = T_LIEN[0] && player->HasSpell(T_LIEN[0]) && !army.empty();
            SpellAuraHolder* held = player->GetSpellAuraHolder(N_H_LIEN);
            if (!lien && held)
                player->RemoveAurasDueToSpell(N_H_LIEN);
            else if (lien && (!held || held->GetCasterGuid() != army.front()->GetObjectGuid()))
            {
                player->RemoveAurasDueToSpell(N_H_LIEN);
                army.front()->CastSpell(player, N_H_LIEN, TRIGGERED_OLD_TRIGGERED);
            }
        }
        else if (cls == C_SNIPER)
        {
            Pet* pet = player->GetPet();
            bool petOk = pet && pet->IsAlive();
            // Meute / Grande meute : compagnons tant que le familier est là
            uint32 wanted = petOk ? ((T_MEUTE[0] && player->HasSpell(T_MEUTE[0])) ? 1 : 0) + ((T_GRANDE_MEUTE[0] && player->HasSpell(T_GRANDE_MEUTE[0])) ? 1 : 0) : 0;
            std::vector<Pet*> pack, robots;
            ForArmy(player, false, [&](Unit* u)
            {
                if (u->GetEntry() == C_MEUTE) pack.push_back(static_cast<Pet*>(u));
                if (u->GetEntry() == C_ROBOT) robots.push_back(static_cast<Pet*>(u));
            });
            while (pack.size() > wanted)
            {
                pack.back()->Unsummon(PET_SAVE_AS_DELETED, player);
                pack.pop_back();
            }
            for (size_t i = pack.size(); i < wanted; ++i)
                player->CastSpell(player, S_H2_MEUTE, TRIGGERED_OLD_TRIGGERED);
            // Tireur solitaire : sans familier permanent
            uint32 rS = TRank(player, T_SOLITAIRE, T_SOLITAIRE_N);
            SetHiddenAura(player, S_H2_SOLITAIRE, (rS && !petOk) ? int32(4 * rS) : 0, 0);
            // Robots améliorés
            if (uint32 rR = TRank(player, T_ROBOTS, T_ROBOTS_N))
            {
                int32 v = int32(5 * rR);
                for (Pet* r : robots)
                    if (!r->HasAura(S_H2_ROBOT))
                        r->CastCustomSpell(r, S_H2_ROBOT, &v, &v, nullptr, TRIGGERED_OLD_TRIGGERED);
            }
            // Familier blindé
            if (petOk)
            {
                uint32 rB = TRank(player, T_BLINDE, T_BLINDE_N);
                SetHiddenAura(pet, S_H2_BLINDE, int32(10 * rB), int32(10 * rB));
            }
        }
        else if (cls == C_META)
            MetaPassives(player);
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
