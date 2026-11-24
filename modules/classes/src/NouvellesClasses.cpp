// Nouvelles classes (23/11/2026) : Tisserand de vie (12), Fossoyeur (13), Martyr (14).
// Mécaniques que les données de sorts ne décrivent pas : Fils (alliés et ennemis), Trancher les fils, sauts du Fil de vie,
// fin de Toile protectrice, Lien de force, Don de trame, Fil d'Ariane, Fil du destin, Liens partagés, Fil conducteur,
// Fils mortels de la Moire (Serrer le nœud, Fil d'Atropos, Récolte, Contagion...), posture du Profanateur, sombredogue,
// fantômes du Passeur et pactes qui verrouillent les spés du Fossoyeur.
// Appelé par ClassesModule.cpp (crochets OnCast, OnHit, OnPeriodicTick, OnDealDamage, OnDealHeal, Upkeep), sous son verrou.

#include "ClassesModule.h"
#include "ClassesData.h"

#include "AI/BaseAI/UnitAI.h"
#include "Chat/Chat.h"
#include "Entities/Creature.h"
#include "Entities/Pet.h"
#include "Entities/Player.h"
#include "Entities/Unit.h"
#include "Groups/Group.h"
#include "Maps/Map.h"
#include "Server/WorldSession.h"
#include "Spells/Spell.h"
#include "Spells/SpellAuras.h"
#include "Spells/SpellMgr.h"
#include "Grids/GridNotifiers.h"
#include "Grids/GridNotifiersImpl.h"
#include "Grids/CellImpl.h"

#include <algorithm>
#include <cmath>

using namespace classes_data;

namespace cmangos_module
{
    static const uint8 C_TISSERAND = 12;
    static const uint8 C_FOSSOYEUR = 13;
    static const uint8 C_MARTYR = 14;

    static uint64 Raw(Unit const* u) { return u->GetObjectGuid().GetRawValue(); }

    static bool HasTalent(Player const* p, const uint32_t* arr, uint32 n)
    {
        for (uint32 i = 0; i < n; ++i)
            if (arr[i] && p->HasSpell(arr[i]))
                return true;
        return false;
    }

    static uint32 Rank(Player const* p, const uint32_t* arr, uint32 n)
    {
        uint32 r = 0;
        for (uint32 i = 0; i < n; ++i)
            if (arr[i] && p->HasSpell(arr[i]))
                r = i + 1;
        return r;
    }

    // valeur d'un sort qui grandit avec le niveau (même courbe que le générateur : 5 % au niveau 0, 100 % au niveau 60)
    static int32 AuNiveau(Unit const* u, float v60)
    {
        float L = float(std::min<uint32>(u->GetLevel(), 60));
        return std::max(1, int32(std::lround(v60 * (0.05f + 0.95f * std::pow(L / 60.0f, 1.4f)))));
    }

    static float Pct(Unit const* u)
    {
        return u->GetMaxHealth() ? float(u->GetHealth()) / float(u->GetMaxHealth()) : 1.0f;
    }

    static void Dire(Player* p, const char* text)
    {
        if (p->GetSession() && p->GetSession()->GetRemoteAddress() != "disconnected/bot")
            ChatHandler(p).SendSysMessage(text);
    }

    static uint32 Piles(Unit const* target, uint32 spellId, ObjectGuid caster)
    {
        if (SpellAuraHolder* h = target->GetSpellAuraHolder(spellId, caster))
            return h->GetStackAmount();
        return 0;
    }

    // membres du groupe vivants à moins de `range` mètres de `center` (le joueur seul s'il n'a pas de groupe)
    static void Groupe(Player* p, Unit* center, float range, std::vector<Unit*>& out)
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

    // ennemis du lanceur à moins de `range` mètres de `center` (le centre peut être un ennemi : sa cible, par exemple)
    static void Ennemis(Unit* center, Unit* caster, float range, std::vector<Unit*>& out)
    {
        std::list<Unit*> list;
        MaNGOS::AnyUnitInObjectRangeCheck check(center, range);
        MaNGOS::UnitListSearcher<MaNGOS::AnyUnitInObjectRangeCheck> searcher(list, check);
        Cell::VisitAllObjects(center, searcher, range);
        for (Unit* u : list)
            if (u && u != caster && u->IsAlive() && caster->CanAttack(u) &&
                !(u->GetTypeId() == TYPEID_UNIT && static_cast<Creature*>(u)->IsTotem()))
                out.push_back(u);
    }

    static bool Dans(const uint32_t* arr, uint32 n, uint32 id)
    {
        for (uint32 i = 0; i < n; ++i)
            if (arr[i] == id)
                return true;
        return false;
    }

    // aura cachée dont les valeurs sont recalculées : remplacée seulement si une valeur change, retirée si tout vaut 0
    static void Cachee(Unit* u, uint32 spellId, int32 b0, int32 b1 = 0, int32 b2 = 0, Unit* caster = nullptr)
    {
        SpellAuraHolder* h = u->GetSpellAuraHolder(spellId);
        if (!b0 && !b1 && !b2)
        {
            if (h)
                u->RemoveAurasDueToSpell(spellId);
            return;
        }
        if (h)
        {
            int32 want[3] = { b0, b1, b2 };
            bool same = true;
            for (int i = 0; i < 3; ++i)
                if (Aura* a = h->GetAuraByEffectIndex(SpellEffectIndex(i)))
                    if (a->GetModifier()->m_amount != want[i])
                        same = false;
            if (same)
                return;
        }
        u->RemoveAurasDueToSpell(spellId);
        (caster ? caster : u)->CastCustomSpell(u, spellId, &b0, &b1, &b2, TRIGGERED_OLD_TRIGGERED);
    }

    // coup critique de ce sort sur cette cible
    static bool Critique(Spell* spell, Unit* victim)
    {
        if (!spell)
            return false;
        for (auto const& t : spell->GetTargetList())
            if (t.targetGUID == victim->GetObjectGuid())
                return t.isCrit;
        return false;
    }

    // cible étourdie ou hébétée
    static bool Etourdi(Unit const* u)
    {
        if (u->IsStunned())
            return true;
        for (auto const& kv : u->GetSpellAuraHolderMap())
            if (kv.second && kv.second->GetSpellProto() && kv.second->GetSpellProto()->Mechanic == 27)
                return true;
        return false;
    }

    static bool Roll(float pct)
    {
        return pct > 0.0f && frand(0.0f, 100.0f) < pct;
    }

    // Martyr : une charge de Ferveur (5 au maximum)
    static void GagnerFerveur(Player* p, uint32 n = 1)
    {
        for (uint32 i = 0; i < n; ++i)
            p->CastSpell(p, MA_FERVEUR[0], TRIGGERED_OLD_TRIGGERED);
    }

    // multiplie la valeur d'une aura déjà posée (effet 1) en la reposant
    static void Renforcer(Player* p, Unit* target, uint32 spellId, float f, int32 plafond = 0)
    {
        SpellAuraHolder* h = target->GetSpellAuraHolder(spellId, p->GetObjectGuid());
        Aura* a = h ? h->GetAuraByEffectIndex(EFFECT_INDEX_0) : nullptr;
        if (!a || f <= 1.0f)
            return;
        int32 bp = int32(std::lround(a->GetModifier()->m_amount * f));
        if (plafond && std::abs(bp) > std::abs(plafond))
            bp = plafond;
        int32 dur = h->GetAuraDuration();
        target->RemoveAurasByCasterSpell(spellId, p->GetObjectGuid());
        p->CastCustomSpell(target, spellId, &bp, nullptr, nullptr, TRIGGERED_OLD_TRIGGERED);
        if (SpellAuraHolder* h2 = target->GetSpellAuraHolder(spellId, p->GetObjectGuid()))
        {
            h2->SetAuraDuration(dur);
            h2->UpdateAuraDuration();
        }
    }

    // multiplie la valeur d'un effet périodique déjà posé (pas d'effet de stat : on peut changer la valeur en place)
    static void Amplifier(Player* p, Unit* target, uint32 spellId, float f)
    {
        if (SpellAuraHolder* h = target->GetSpellAuraHolder(spellId, p->GetObjectGuid()))
            if (Aura* a = h->GetAuraByEffectIndex(EFFECT_INDEX_0))
                a->GetModifier()->m_amount = int32(std::lround(a->GetModifier()->m_amount * f));
    }

    static Unit* Cadavre(Unit* center, float range)
    {
        std::list<Unit*> list;
        MaNGOS::AnyDeadUnitCheck check(center);
        MaNGOS::UnitListSearcher<MaNGOS::AnyDeadUnitCheck> searcher(list, check);
        Cell::VisitAllObjects(center, searcher, range);
        for (Unit* u : list)
            if (u && u->GetTypeId() == TYPEID_UNIT && center->IsWithinDistInMap(u, range))
                return u;
        return nullptr;
    }

    // pactes du Fossoyeur : 0 aucun, 1 Requiem, 2 Charnier, 3 Passeur (le plus haut rang l'emporte si plusieurs)
    static bool PeutChien(Player const* p)
    {
        return HasTalent(p, TF_CHARNIER, TF_CHARNIER_N) && !HasTalent(p, TF_REQUIEM, TF_REQUIEM_N) && !HasTalent(p, TF_PASSEUR, TF_PASSEUR_N);
    }

    static bool PeutFantomes(Player const* p)
    {
        return HasTalent(p, TF_PASSEUR, TF_PASSEUR_N) && !HasTalent(p, TF_REQUIEM, TF_REQUIEM_N) && !HasTalent(p, TF_CHARNIER, TF_CHARNIER_N);
    }

    static bool EstFantome(uint32 id)
    {
        for (uint32 i = 0; i < F_AMES_N; ++i)
            if (F_AMES[i] == id)
                return true;
        return false;
    }

    // pose `n` Fils (ou Fils mortels) sur la cible
    static void Poser(Player* p, Unit* target, uint32 spellId, uint32 n)
    {
        for (uint32 i = 0; i < n && target->IsAlive(); ++i)
            p->CastSpell(target, spellId, TRIGGERED_OLD_TRIGGERED);
    }

    // ------------------------------------------------------------------ lancement (avant les effets)
    void ClassesModule::NouvCast(Player* p, uint32 id, Unit* /*victim*/, Spell* spell)
    {
        uint8 cls = p->getClass();
        if (cls == C_FOSSOYEUR)
        {
            // Tombeau ouvert : une faille reste ouverte à l'endroit visé
            if (id == F_TOMBEAU[0] && spell)
            {
                float x, y, z;
                spell->m_targets.getDestination(x, y, z);
                if (x != 0.0f || y != 0.0f)
                    p->CastSpell(x, y, z, F_H_FAILLE[0], TRIGGERED_OLD_TRIGGERED);
            }
            return;
        }
        if (cls == C_MARTYR)
        {
            if (!spell || spell->m_IsTriggeredSpell || !spell->m_spellInfo)
                return;
            SpellEntry const* e = spell->m_spellInfo;
            int32 k = -1;
            for (uint32 i = 0; i < MA_SANG_N; ++i)
                if (MA_SANG[i] == id)
                    k = int32(i);
            if (k >= 0)
            {
                // sort de sang : consomme la Ferveur (+20 % par charge), coûte un % des PV max sans pouvoir tuer
                uint32 n = 0;
                if (MA_SANG_CONSO[k])
                {
                    n = Piles(p, MA_FERVEUR[0], p->GetObjectGuid());
                    if (n)
                        p->RemoveAurasDueToSpell(MA_FERVEUR[0]);
                }
                ferveurConso[Raw(p)] = n;
                if (!p->HasAura(MA_FORTERESSE[0]) && !p->HasAura(MA_SAINT[0]))
                {
                    int32 cost = int32(p->GetMaxHealth()) * int32(MA_SANG_PCT[k]) / 100;
                    cost = std::min(cost, int32(p->GetHealth()) - 1);
                    if (cost > 0)
                        p->ModifyHealth(-cost);
                }
            }
            else if (e->SpellFamilyName == 16 && e->powerType == POWER_ENERGY && e->manaCost > 0)
                GagnerFerveur(p);                           // sort à énergie : 1 Ferveur
            return;
        }
        // Lame de trame : Trancher les fils sans recharge
        if (id == TW_TRANCHER[0] && p->HasAura(TW_LAME[0]))
            if (SpellEntry const* e = sSpellTemplate.LookupEntry<SpellEntry>(TW_TRANCHER[0]))
                p->RemoveSpellCooldown(*e, true);
        // Fil de vie lancé par le joueur : 3 sauts disponibles
        if (id == TW_VIE[0])
            vieSauts[Raw(p)] = 3;
    }

    // ------------------------------------------------------------------ impact (après les effets)
    void ClassesModule::NouvHit(Player* p, uint32 id, Unit* victim, Spell* spell)
    {
        if (!victim)
            return;
        ObjectGuid pg = p->GetObjectGuid();
        uint8 cls = p->getClass();

        if (cls == C_TISSERAND)
        {
            // Fils sur un allié : Toucher vital (et tous les soins sous Tapisserie de vie)
            bool soin = id == TW_TOUCHER[0] || id == TW_RACCOM[0] || id == TW_NAVETTE[0] || id == TW_GRANDE[0] || id == TW_VIE[0];
            if (id == TW_TOUCHER[0] || (soin && p->HasAura(TW_TAPISSERIE[0])))
                Poser(p, victim, TW_FILS[0], 1);
            // Grande trame : 10 % de plus par Fil sur la cible
            if (id == TW_GRANDE[0])
            {
                uint32 n = 0;
                if (SpellAuraHolder* h = victim->GetSpellAuraHolder(TW_FILS[0]))
                    n = h->GetStackAmount();
                if (n)
                {
                    int32 bp = AuNiveau(p, 1900.0f) * int32(n) / 10;
                    p->CastCustomSpell(victim, TW_BONUS_SOIN[0], &bp, nullptr, nullptr, TRIGGERED_OLD_TRIGGERED);
                }
            }
            // Fils sur un ennemi : Trait de fil, Pelote (Bobine : 4 % par rang d'en poser 2 ; Lame de trame : 2)
            if (id == TW_TRAIT[0] || id == TW_PELOTE[0])
            {
                uint32 n = 1;
                if (p->HasAura(TW_LAME[0]))
                    n = 2;
                else if (uint32 r = Rank(p, TT_BOBINE, TT_BOBINE_N))
                    if (frand(0.0f, 100.0f) < 4.0f * r)
                        n = 2;
                Poser(p, victim, TW_FILS_E[0], n);
            }
            else if (p->HasAura(TW_LAME[0]) && (id == TW_EPINES[0] || id == TW_LACERATION[0] || id == TW_TEMPETE[0]))
                Poser(p, victim, TW_FILS_E[0], 2);
            // Trancher les fils : 400 + 150 par Fil, doublé sous 25 %
            if (id == TW_TRANCHER[0])
            {
                uint32 n = Piles(victim, TW_FILS_E[0], pg);
                int32 bp = AuNiveau(p, 400.0f) + AuNiveau(p, 150.0f) * int32(n);
                if (Pct(victim) < 0.25f)
                    bp *= 2;
                if (uint32 r = Rank(p, TT_TENSION, TT_TENSION_N))
                    if (n >= 3)
                        bp = bp * int32(100 + 2 * r) / 100;
                victim->RemoveAurasByCasterSpell(TW_FILS_E[0], pg);
                p->CastCustomSpell(victim, TW_TRANCHER_D[0], &bp, nullptr, nullptr, TRIGGERED_OLD_TRIGGERED);
            }
            // Toile protectrice : soin sur la durée quand la toile disparaît (suivi dans NouvUpkeep)
            if (id == TW_TOILE_P[0])
                toileCaster[Raw(victim)] = Raw(p);
            // Lien de force : un seul allié lié (deux avec Double lien)
            if (id == TW_LIEN_F[0])
            {
                auto& v = lienForce[Raw(p)];
                v.erase(std::remove(v.begin(), v.end(), Raw(victim)), v.end());
                v.push_back(Raw(victim));
                size_t max = HasTalent(p, TT_DOUBLE, TT_DOUBLE_N) ? 2 : 1;
                while (v.size() > max)
                {
                    if (Unit* old = p->GetMap()->GetUnit(ObjectGuid(v.front())))
                        old->RemoveAurasByCasterSpell(TW_LIEN_F[0], pg);
                    v.erase(v.begin());
                }
            }
            // Fil d'Ariane : le Tisserand rejoint l'allié
            if (id == TW_ARIANE[0] && victim != p)
            {
                float x, y, z;
                victim->GetClosePoint(x, y, z, p->GetObjectBoundingRadius(), 1.5f, victim->GetAngle(p));
                p->NearTeleportTo(x, y, z, p->GetAngle(victim), true);
            }
            // Don de trame : 15 % du mana (+3 % par rang de Don renforcé) en 5 s, au Tisserand et à l'allié
            if (id == TW_DON[0])
            {
                int32 bp = (15 + 3 * int32(Rank(p, TT_DON, TT_DON_N)) + 4) / 5;
                p->CastCustomSpell(victim, TW_DON_E[0], &bp, nullptr, nullptr, TRIGGERED_OLD_TRIGGERED);
                if (victim != p)
                    p->CastCustomSpell(p, TW_DON_E[0], &bp, nullptr, nullptr, TRIGGERED_OLD_TRIGGERED);
            }
            // Recousu : consomme le Fil de vie et soigne aussitôt de 12 s de ce soin
            if (id == TW_RECOUSU[0])
                if (Aura* a = victim->GetAura(TW_VIE[0], EFFECT_INDEX_0))
                {
                    Modifier* m = a->GetModifier();
                    uint32 per = m->periodictime ? m->periodictime : 3000;
                    int32 bp = m->m_amount * int32(12000 / per);
                    victim->RemoveAurasDueToSpell(TW_VIE[0]);
                    if (bp > 0)
                        p->CastCustomSpell(victim, TW_BONUS_SOIN[0], &bp, nullptr, nullptr, TRIGGERED_OLD_TRIGGERED);
                }

            // Moire : Fils mortels
            if (id == TW_FUSEAU[0] || id == TW_FIL_NOIR[0])
            {
                uint32 n = id == TW_FIL_NOIR[0] ? 2 : 1;
                if (id == TW_FUSEAU[0])
                    if (uint32 r = Rank(p, TT_MAILLE, TT_MAILLE_N))
                        if (frand(0.0f, 100.0f) < 4.0f * r)
                            n = 2;
                if (p->HasAura(TW_DERNIERE[0]))
                    n *= 2;
                Poser(p, victim, TW_MORTEL[0], n);
            }
            if (id == TW_FUNEBRE[0] && victim != p)
                Poser(p, victim, TW_MORTEL[0], p->HasAura(TW_DERNIERE[0]) ? 2 : 1);
            if (id == TW_NOEUD[0])
                p->CastSpell(victim, TW_NOEUD_M[0], TRIGGERED_OLD_TRIGGERED);
            if (id == TW_NOEUD_C[0] && Piles(victim, TW_MORTEL[0], pg) < 3)
            {
                victim->RemoveAurasByCasterSpell(TW_NOEUD_C[0], pg);
                Dire(p, "Nœud coulant : la cible doit porter au moins 3 Fils mortels.");
            }
            if (id == TW_RECOLTE[0])
            {
                uint32 n = Piles(victim, TW_MORTEL[0], pg);
                int32 pct = int32(n) * (5 + int32(Rank(p, TT_RECOLTE, TT_RECOLTE_N)));
                if (pct > 0)
                    p->ModifyHealth(int32(p->GetMaxHealth()) * pct / 100);
            }
            if (id == TW_ATROPOS[0])
            {
                float seuil = (25.0f + 5.0f * Rank(p, TT_ATROPOS, TT_ATROPOS_N)) / 100.0f;
                if (Pct(victim) < seuil)
                    p->CastSpell(victim, TW_ATROPOS_M[0], TRIGGERED_OLD_TRIGGERED);
                else
                    Dire(p, "Fil d'Atropos : la cible a encore trop de vie.");
            }
            if (id == TW_CONTAGION[0])
            {
                uint32 n = Piles(victim, TW_MORTEL[0], pg);
                if (!n)
                    return;
                std::vector<Unit*> ennemis;
                Ennemis(victim, p, 10.0f, ennemis);
                uint32 faits = 0;
                for (Unit* e : ennemis)
                {
                    if (e == victim || faits >= 2)
                        continue;
                    Poser(p, e, TW_MORTEL[0], n);
                    ++faits;
                }
            }
            return;
        }

        if (cls == C_MARTYR)
        {
            uint32 n = ferveurConso[Raw(p)];
            float f = 1.0f + 0.2f * float(n);
            int32 dmg = int32(spell ? spell->GetTotalTargetDamage() : 0);
            bool crit = Critique(spell, victim);
            bool ennemi = victim != p && p->CanAttack(victim);
            // Ferveur sanglante / bienveillante : un critique peut donner 1 Ferveur de plus
            if (crit && spell && !spell->m_IsTriggeredSpell)
            {
                if (ennemi)
                {
                    if (uint32 r = Rank(p, TM_FERVEUR_S, TM_FERVEUR_S_N))
                        if (Roll(15.0f * r))
                            GagnerFerveur(p);
                }
                else if (uint32 r = Rank(p, TM_FERVEUR_B, TM_FERVEUR_B_N))
                    if (Roll(33.0f * r))
                        GagnerFerveur(p);
            }
            // Seigneur du sang : drains +50 %, soins reçus par la cible -25 %
            if (Dans(MA_DRAINS, MA_DRAINS_N, id) && ennemi && p->HasAura(MA_SEIGNEUR[0]))
            {
                if (dmg > 0)
                {
                    int32 bp = dmg / 2;
                    p->CastCustomSpell(victim, MA_LEECH_X[0], &bp, nullptr, nullptr, TRIGGERED_OLD_TRIGGERED);
                }
                else
                    Amplifier(p, victim, id, 1.5f);
                p->CastSpell(victim, MA_SEIGNEUR_A[0], TRIGGERED_OLD_TRIGGERED);
            }
            if (id == MA_PLAIE[0] && ennemi)
            {
                uint32 k = Piles(p, MA_FERVEUR[0], pg);          // Plaie partagée : +20 % par Ferveur, sans la consommer
                if (k && dmg > 0)
                {
                    int32 bp = dmg * int32(20 * k) / 100;
                    p->CastCustomSpell(victim, MA_BONUS_D[0], &bp, nullptr, nullptr, TRIGGERED_OLD_TRIGGERED);
                }
                if (uint32 r = Rank(p, TM_PLAIE_S, TM_PLAIE_S_N))
                {
                    int32 bp = std::max(1, AuNiveau(p, 50.0f * r) / 3);
                    p->CastCustomSpell(victim, MA_PLAIE_D[0], &bp, nullptr, nullptr, TRIGGERED_OLD_TRIGGERED);
                }
                return;
            }
            if (id == MA_CAILLOT[0])
            {
                if (Aura* a = p->GetAura(MA_CAILLOT[0], EFFECT_INDEX_0))
                    a->GetModifier()->m_amount = int32(float(p->GetMaxHealth()) * 0.10f * f *
                                                       (1.0f + 0.1f * Rank(p, TM_CAILLOT_A, TM_CAILLOT_A_N)));
                return;
            }
            if (id == MA_COAGULATION[0] || id == MA_PACTE[0] || id == MA_FRENESIE_S[0])
            {
                Renforcer(p, p, id, f, id == MA_COAGULATION[0] ? -60 : 0);
                return;
            }
            if (id == MA_MUR[0])
            {
                Renforcer(p, p, id, f, 60);
                int32 bp = int32(float(p->GetMaxHealth()) * 0.30f * f);
                p->CastCustomSpell(p, MA_BONUS_S[0], &bp, nullptr, nullptr, TRIGGERED_OLD_TRIGGERED);
                return;
            }
            if (id == MA_ANEMIE[0] && ennemi)
            {
                Renforcer(p, victim, id, f, -90);
                return;
            }
            if ((id == MA_HACHOIR[0] || id == MA_FESTIN_S[0]) && ennemi && n && dmg > 0)
            {
                int32 bp = int32(dmg * (f - 1.0f));
                p->CastCustomSpell(victim, id == MA_HACHOIR[0] ? MA_BONUS_D[0] : MA_LEECH_X[0], &bp, nullptr, nullptr, TRIGGERED_OLD_TRIGGERED);
                return;
            }
            if ((id == MA_HEMORRAGIE[0] || id == MA_CAILLE[0]) && ennemi)
            {
                Amplifier(p, victim, id, f);
                return;
            }
            if (id == MA_GRAND_S[0] && n)
            {
                int32 bp = int32(AuNiveau(p, 2150.0f) * (f - 1.0f));
                p->CastCustomSpell(victim, MA_BONUS_S[0], &bp, nullptr, nullptr, TRIGGERED_OLD_TRIGGERED);
                return;
            }
            if (id == MA_DON_U[0])
            {
                int32 bp = int32(float(victim->GetMaxHealth()) * 0.30f * f);
                p->CastCustomSpell(victim, MA_BONUS_S[0], &bp, nullptr, nullptr, TRIGGERED_OLD_TRIGGERED);
                return;
            }
            if (id == MA_FONTAINE[0])
            {
                Fontaine& ft = fontaines[Raw(p)];
                p->GetPosition(ft.x, ft.y, ft.z);
                ft.secondes = 10 + 2 * Rank(p, TM_FONTAINE_A, TM_FONTAINE_A_N);
                ft.soin = int32(AuNiveau(p, 60.0f) * f);
                return;
            }
            if (id == MA_MARQUE[0] && ennemi)
            {
                marques[Raw(victim)] = std::make_pair(Raw(p), (20.0f + 5.0f * Rank(p, TM_MARQUE_P, TM_MARQUE_P_N)) * f);
                return;
            }
            if (id == MA_FUREUR[0])
            {
                if (SpellAuraHolder* h = p->GetSpellAuraHolder(MA_FUREUR[0]))
                    h->SetStackAmount(3, p);
                return;
            }
            if (id == MA_FESTIN_L[0])
            {
                festinCoups[Raw(p)] = HasTalent(p, TM_FESTIN_P, TM_FESTIN_P_N) ? 5 : 3;
                return;
            }
            if (id == MA_DESESPOIR[0] && ennemi && dmg > 0)
            {
                float seuil = (35.0f + 5.0f * Rank(p, TM_DESESPOIR, TM_DESESPOIR_N)) / 100.0f;
                if (Pct(p) < seuil)
                    p->CastCustomSpell(victim, MA_BONUS_D[0], &dmg, nullptr, nullptr, TRIGGERED_OLD_TRIGGERED);
                return;
            }
            if (id == MA_COMMUNION[0])
            {
                float rayon = 10.0f + 5.0f * Rank(p, TM_COMMUNION_E, TM_COMMUNION_E_N);
                std::vector<Unit*> autour, groupe;
                Ennemis(p, p, rayon, autour);
                int32 total = 0;
                for (Unit* e : autour)
                {
                    int32 bp = AuNiveau(p, 150.0f);
                    p->CastCustomSpell(e, MA_COMMUNION_D[0], &bp, nullptr, nullptr, TRIGGERED_OLD_TRIGGERED);
                    total += bp;
                }
                Groupe(p, p, 30.0f, groupe);
                if (total > 0 && !groupe.empty())
                {
                    int32 part = std::max(1, total / int32(groupe.size()));
                    for (Unit* m : groupe)
                        p->CastCustomSpell(m, MA_BONUS_S[0], &part, nullptr, nullptr, TRIGGERED_OLD_TRIGGERED);
                }
                return;
            }
            if (id == MA_SEIGNEUR[0])
            {
                p->CastSpell(p, MA_SEIGNEUR_ST[0], TRIGGERED_OLD_TRIGGERED);
                return;
            }
            return;
        }

        if (cls == C_FOSSOYEUR)
        {
            // malédictions d'arme : une seule active (deux avec Malédictions jumelles), la plus ancienne disparaît
            if (id == F_M_POURRITURE[0] || id == F_M_ENTRAVE[0] || id == F_M_EPUISE[0])
            {
                auto& v = malOrdre[Raw(p)];
                v.erase(std::remove(v.begin(), v.end(), id), v.end());
                v.push_back(id);
                v.erase(std::remove_if(v.begin(), v.end(), [p](uint32 m) { return !p->HasAura(m); }), v.end());
                size_t max = HasTalent(p, TF_JUMELLES, TF_JUMELLES_N) ? 2 : 1;
                while (v.size() > max)
                {
                    p->RemoveAurasDueToSpell(v.front());
                    v.erase(v.begin());
                }
                return;
            }
            // Fosse commune : la malédiction posée par l'arme se propage à un autre ennemi à 8 m
            if (Dans(F_MALS, F_MALS_N, id))
            {
                if (p->HasAura(F_FOSSE[0]))
                {
                    std::vector<Unit*> autour;
                    Ennemis(victim, p, 8.0f, autour);
                    for (Unit* e : autour)
                        if (e != victim)
                        {
                            p->CastSpell(e, id, TRIGGERED_OLD_TRIGGERED);
                            break;
                        }
                }
                return;
            }
            // Pelletée funèbre : un point de combo de plus
            if (id == F_PELLE[0] || id == F_SORTIE[0])
                if (uint32 r = Rank(p, TF_PELLETEE, TF_PELLETEE_N))
                    if (Roll(4.0f * r))
                        p->AddComboPoints(victim, 1);
            // sorts du Requiem : Gravats, Acharnement, Écrasement
            if (Dans(F_REQ, F_REQ_N, id) && victim != p)
            {
                int32 dmg = int32(spell ? spell->GetTotalTargetDamage() : 0);
                bool crit = Critique(spell, victim);
                if (dmg > 0)
                {
                    int32 extra = 0;
                    bool etourdi = Etourdi(victim);
                    if (etourdi)
                        if (uint32 r = Rank(p, TF_ACHARNEMENT, TF_ACHARNEMENT_N))
                            extra += dmg * int32(4 * r) / 100;
                    if (id == F_PIERRE[0] && !crit && etourdi && HasTalent(p, TF_ECRASEMENT, TF_ECRASEMENT_N) && Roll(15.0f))
                    {
                        extra += dmg / 2;                   // critique de sort : +50 %
                        crit = true;
                    }
                    if (extra > 0)
                        p->CastCustomSpell(victim, F_H_TERRE[0], &extra, nullptr, nullptr, TRIGGERED_OLD_TRIGGERED);
                    if (crit)
                        if (uint32 r = Rank(p, TF_GRAVATS, TF_GRAVATS_N))
                        {
                            int32 bp = std::max(1, dmg * int32(8 * r) / 100 / 2);     // 2 ticks en 4 s
                            p->CastCustomSpell(victim, F_H_GRAVATS[0], &bp, nullptr, nullptr, TRIGGERED_OLD_TRIGGERED);
                        }
                }
                return;
            }
            // Hurlement : les ennemis à 10 m du sombredogue fuient
            if (id == F_HURLEMENT[0])
            {
                Pet* pet = p->GetPet();
                if (!pet || !pet->IsAlive() || pet->GetEntry() != C_SOMBREDOGUE[0])
                {
                    Dire(p, "Hurlement : il vous faut votre sombredogue.");
                    return;
                }
                std::vector<Unit*> autour;
                Ennemis(pet, p, 10.0f, autour);
                for (Unit* e : autour)
                    p->CastSpell(e, F_H_HURLEMENT[0], TRIGGERED_OLD_TRIGGERED);
                return;
            }
            // Bouclier partagé : une part du bouclier protège aussi le Fossoyeur
            if (id == F_BOUCLIER[0] && victim != p)
                if (uint32 r = Rank(p, TF_BOUCLIER, TF_BOUCLIER_N))
                {
                    int32 bp = AuNiveau(p, 700.0f) * int32(20 * r) / 100;
                    p->CastCustomSpell(p, F_H_BOUCLIER_P[0], &bp, nullptr, nullptr, TRIGGERED_OLD_TRIGGERED);
                }
            // Passage amélioré : rend 10 % des points de vie
            if (id == F_PASSAGE[0] && HasTalent(p, TF_PASSAGE, TF_PASSAGE_N))
            {
                int32 bp = int32(victim->GetMaxHealth()) / 10;
                p->CastCustomSpell(victim, F_H_PASSAGE[0], &bp, nullptr, nullptr, TRIGGERED_OLD_TRIGGERED);
            }
            // fantômes du Passeur : pacte obligatoire, un fantôme par allié, 3 au maximum (4 avec Procession)
            if (EstFantome(id))
            {
                if (!PeutFantomes(p))
                {
                    victim->RemoveAurasByCasterSpell(id, pg);
                    Dire(p, "Sans le Pacte du passeur, les fantômes ne répondent pas.");
                    return;
                }
                auto& dq = fantomes[Raw(p)];
                for (auto it = dq.begin(); it != dq.end();)
                {
                    if (it->first == Raw(victim))
                    {
                        if (it->second != id)
                            victim->RemoveAurasByCasterSpell(it->second, pg);
                        it = dq.erase(it);
                    }
                    else
                        ++it;
                }
                dq.emplace_back(Raw(victim), id);
                size_t maxF = HasTalent(p, TF_PROCESSION, TF_PROCESSION_N) ? 4 : 3;
                while (dq.size() > maxF)
                {
                    if (Unit* old = p->GetMap()->GetUnit(ObjectGuid(dq.front().first)))
                        old->RemoveAurasByCasterSpell(dq.front().second, pg);
                    dq.pop_front();
                }
                return;
            }
            if (id == F_CORTEGE[0] || id == F_LIBERATION[0])
            {
                auto& dq = fantomes[Raw(p)];
                std::vector<Unit*> groupe;
                if (id == F_CORTEGE[0])
                    Groupe(p, p, 40.0f, groupe);
                for (auto const& f : dq)
                {
                    Unit* ally = p->GetMap()->GetUnit(ObjectGuid(f.first));
                    if (!ally || !ally->GetSpellAuraHolder(f.second, pg))
                        continue;
                    if (id == F_LIBERATION[0])
                    {
                        int32 bp = int32(ally->GetMaxHealth()) * (15 + 5 * int32(Rank(p, TF_LIBERATION, TF_LIBERATION_N))) / 100;
                        p->CastCustomSpell(ally, F_LIBERATION_H[0], &bp, nullptr, nullptr, TRIGGERED_OLD_TRIGGERED);
                        ally->RemoveAurasByCasterSpell(f.second, pg);
                        continue;
                    }
                    for (Unit* m : groupe)
                    {
                        if (m == ally || m->GetSpellAuraHolder(f.second, pg))
                            continue;
                        p->CastSpell(m, f.second, TRIGGERED_OLD_TRIGGERED);
                        if (SpellAuraHolder* h = m->GetSpellAuraHolder(f.second, pg))
                        {
                            int32 d = 15000 + 5000 * int32(Rank(p, TF_CORTEGE, TF_CORTEGE_N));
                            h->SetAuraMaxDuration(d);
                            h->SetAuraDuration(d);
                            h->UpdateAuraDuration();
                        }
                    }
                }
                if (id == F_LIBERATION[0])
                    dq.clear();
                return;
            }
            // Profanation : 30 % de plus par malédiction sur la cible
            if (id == F_PROFANATION[0])
            {
                // malédictions d'arme posées par le Fossoyeur : pourriture, entrave, épuisement (sorts cachés)
                uint32 k = 0;
                Unit::SpellAuraHolderMap const& auras = victim->GetSpellAuraHolderMap();
                std::vector<uint32> vus;
                for (auto const& kv : auras)
                {
                    SpellAuraHolder* h = kv.second;
                    if (!h || h->GetCasterGuid() != pg || !h->GetSpellProto())
                        continue;
                    uint32 sid = h->GetSpellProto()->Id;
                    if (std::find(vus.begin(), vus.end(), sid) != vus.end())
                        continue;
                    SpellEntry const* e = h->GetSpellProto();
                    if (e->SpellFamilyName == 15 && h->IsPositive() == false)
                    {
                        vus.push_back(sid);
                        ++k;
                    }
                }
                if (k)
                {
                    float mn = p->GetFloatValue(UNIT_FIELD_MINDAMAGE), mx = p->GetFloatValue(UNIT_FIELD_MAXDAMAGE);
                    int32 par = 30 + 5 * int32(Rank(p, TF_PROFANATION, TF_PROFANATION_N));
                    int32 bp = int32((mn + mx) / 2.0f + AuNiveau(p, 100.0f)) * par * int32(k) / 100;
                    if (bp > 0)
                        p->CastCustomSpell(victim, F_CUREE_D[0], &bp, nullptr, nullptr, TRIGGERED_OLD_TRIGGERED);
                }
                return;
            }
            // sorts du sombredogue
            Pet* pet = p->GetPet();
            bool chien = pet && pet->IsAlive() && pet->GetEntry() == C_SOMBREDOGUE[0];
            if (id == F_CUREE[0])
            {
                Unit* cible = chien ? pet->GetVictim() : nullptr;
                if (!cible)
                    cible = p->GetVictim();
                if (!chien || !cible || !cible->IsAlive())
                {
                    Dire(p, "Curée : votre sombredogue doit avoir une cible.");
                    return;
                }
                int32 bp = AuNiveau(p, 320.0f) * (100 + 10 * int32(Rank(p, TF_CUREE, TF_CUREE_N))) / 100;
                pet->CastCustomSpell(cible, F_CUREE_D[0], &bp, nullptr, nullptr, TRIGGERED_OLD_TRIGGERED);
                return;
            }
            if (id == F_FESTIN[0])
            {
                if (!chien)
                    return;
                if (!Cadavre(pet, 10.0f))
                {
                    Dire(p, "Festin de cadavre : aucun cadavre à moins de 10 m de votre sombredogue.");
                    return;
                }
                int32 heal = int32(pet->GetMaxHealth()) * 30 / 100;
                pet->ModifyHealth(heal);
                p->CastSpell(pet, F_FESTIN_PET[0], TRIGGERED_OLD_TRIGGERED);
                if (uint32 r = Rank(p, TF_FESTIN, TF_FESTIN_N))
                    if (SpellAuraHolder* h = pet->GetSpellAuraHolder(F_FESTIN_PET[0]))
                    {
                        int32 d = 15000 + 5000 * int32(r);
                        h->SetAuraMaxDuration(d);
                        h->SetAuraDuration(d);
                        h->UpdateAuraDuration();
                    }
                return;
            }
            if (chien && id == F_D_FORCE[0])
            {
                int32 bp = 20 + 5 * int32(Rank(p, TF_RAPPORT, TF_RAPPORT_N));
                p->CastCustomSpell(pet, F_FORCE_PET[0], &bp, nullptr, nullptr, TRIGGERED_OLD_TRIGGERED);
            }
            if (chien && id == F_D_CELERITE[0])
                p->CastSpell(pet, F_CELERITE_PET[0], TRIGGERED_OLD_TRIGGERED);
            if (chien && id == F_D_MOELLE[0])
                p->CastSpell(pet, F_MOELLE_PET[0], TRIGGERED_OLD_TRIGGERED);
            (void)spell;
        }
    }

    // ------------------------------------------------------------------ ticks des effets sur la durée (true = tick ignoré)
    bool ClassesModule::NouvTick(Aura* aura)
    {
        Unit* caster = aura->GetCaster();
        Unit* target = aura->GetTarget();
        if (!caster || !target || caster->GetTypeId() != TYPEID_PLAYER || !target->IsAlive())
            return false;
        Player* p = static_cast<Player*>(caster);
        uint8 cls = p->getClass();
        uint32 id = aura->GetSpellProto()->Id;
        ObjectGuid pg = p->GetObjectGuid();

        if (cls == C_TISSERAND)
        {
            // Fil de vie : saute sur l'allié le plus blessé quand la cible n'a plus de blessure
            if (id == TW_VIE[0] && target->GetHealth() >= target->GetMaxHealth())
            {
                uint32& sauts = vieSauts[Raw(p)];
                if (!sauts)
                    return false;
                std::vector<Unit*> allies;
                Groupe(p, target, 30.0f, allies);
                Unit* best = nullptr;
                for (Unit* a : allies)
                    if (a != target && Pct(a) < 1.0f && !a->GetSpellAuraHolder(TW_VIE[0], pg) && (!best || Pct(a) < Pct(best)))
                        best = a;
                if (!best)
                    return false;
                --sauts;
                int32 reste = aura->GetAuraDuration();
                // l'aura en cours de tick n'est pas retirée ici : elle expire à la prochaine mise à jour
                if (SpellAuraHolder* cur = aura->GetHolder())
                {
                    cur->SetAuraDuration(1);
                    cur->UpdateAuraDuration();
                }
                p->CastSpell(best, TW_VIE[0], TRIGGERED_OLD_TRIGGERED);
                if (SpellAuraHolder* h = best->GetSpellAuraHolder(TW_VIE[0], pg))
                    if (reste > 0)
                    {
                        h->SetAuraDuration(reste);
                        h->UpdateAuraDuration();
                    }
                return true;
            }
            // Garrot : pose 1 Fil à chaque tick
            if (id == TW_GARROT[0])
                Poser(p, target, TW_FILS_E[0], 1);
            // Fils mortels : talents et effets de la Moire
            if (id == TW_MORTEL[0])
            {
                int32 amount = aura->GetModifier()->m_amount;
                int32 bonus = 3 * int32(Rank(p, TT_EMPOISONNE, TT_EMPOISONNE_N));
                if (p->HasAura(TW_DERNIERE[0]))
                    bonus += 20;
                if (target->GetSpellAuraHolder(TW_ATROPOS_M[0], pg))
                    bonus += 100;
                int32 extra = amount * bonus / 100;
                // Serrer le nœud : un tick de plus, et la durée raccourcit d'autant (même total)
                if (target->GetSpellAuraHolder(TW_NOEUD_M[0], pg))
                {
                    extra += amount;
                    if (SpellAuraHolder* h = aura->GetHolder())
                    {
                        int32 d = h->GetAuraDuration() - int32(aura->GetModifier()->periodictime);
                        if (d > 0)
                        {
                            h->SetAuraDuration(d);
                            h->UpdateAuraDuration();
                        }
                    }
                }
                if (extra > 0)
                    p->CastCustomSpell(target, TW_MORTEL_X[0], &extra, nullptr, nullptr, TRIGGERED_OLD_TRIGGERED);
                if (uint32 r = Rank(p, TT_VAMPIRIQUE, TT_VAMPIRIQUE_N))
                    p->ModifyHealth((amount + extra) * int32(10 * r) / 100);
            }
            return false;
        }

        if (cls == C_FOSSOYEUR)
        {
            // Drain de chair : le sombredogue est soigné du double
            if (id == F_DRAIN[0])
                if (Pet* pet = p->GetPet())
                    if (pet->IsAlive() && pet->GetEntry() == C_SOMBREDOGUE[0])
                    {
                        int32 bp = aura->GetModifier()->m_amount * 2;
                        p->CastCustomSpell(pet, F_DRAIN_PET[0], &bp, nullptr, nullptr, TRIGGERED_OLD_TRIGGERED);
                    }
            // Âme vengeresse : le fantôme frappe la cible de l'allié
            if (id == F_A_VENGERESSE[0])
            {
                Unit* v = target->GetVictim();
                if (v && v->IsAlive() && p->CanAttack(v) && target->IsWithinDistInMap(v, 30.0f))
                {
                    int32 bp = AuNiveau(p, 80.0f) * (100 + 15 * int32(Rank(p, TF_VENGERESSE, TF_VENGERESSE_N))) / 100;
                    p->CastCustomSpell(v, F_VENGERESSE_D[0], &bp, nullptr, nullptr, TRIGGERED_OLD_TRIGGERED);
                }
                return true;
            }
            // faille de Tombeau ouvert : hébète
            if (id == F_H_FAILLE[0] && p->CanAttack(target))
                p->CastSpell(target, F_H_DAZE_F[0], TRIGGERED_OLD_TRIGGERED);
        }
        return false;
    }

    // ------------------------------------------------------------------ dégâts reçus
    void ClassesModule::NouvDamage(Unit* unit, Unit* victim, uint32 health, uint32 damage)
    {
        if (!victim || !damage)
            return;
        // mort évitée (Fil du destin, Refus du trépas) : effets après coup
        if (victim->GetTypeId() == TYPEID_PLAYER)
        {
            auto it = mortEvitee.find(Raw(victim));
            if (it != mortEvitee.end())
            {
                uint8 kind = it->second;
                mortEvitee.erase(it);
                Player* pv = static_cast<Player*>(victim);
                if (kind == 3)
                {
                    // Dernier sacrifice : le groupe est soigné de 15 % (25 % avec Vie offerte)
                    int32 pct = HasTalent(pv, TM_VIE_OFFERTE, TM_VIE_OFFERTE_N) ? 25 : 15;
                    std::vector<Unit*> groupe;
                    Groupe(pv, pv, 40.0f, groupe);
                    for (Unit* m : groupe)
                    {
                        int32 bp = int32(m->GetMaxHealth()) * pct / 100;
                        pv->CastCustomSpell(m, MA_BONUS_S[0], &bp, nullptr, nullptr, TRIGGERED_OLD_TRIGGERED);
                    }
                    Dire(pv, "Dernier sacrifice !");
                    return;
                }
                if (kind == 1)
                {
                    victim->RemoveAurasDueToSpell(TW_DESTIN[0]);
                    int32 bp = int32(victim->GetMaxHealth()) * 20 / 100;
                    victim->CastCustomSpell(victim, TW_DESTIN_R[0], &bp, nullptr, nullptr, TRIGGERED_OLD_TRIGGERED);
                }
                else
                    pv->CastSpell(pv, TW_TREPAS[0], TRIGGERED_OLD_TRIGGERED);
                return;
            }
        }
        // Fossoyeur : rats zombies, Molosse d'os, Charogne (unités du joueur)
        if (unit && unit->GetTypeId() == TYPEID_UNIT && unit != victim)
            if (Unit* owner = unit->GetOwner())
                if (owner->GetTypeId() == TYPEID_PLAYER && static_cast<Player*>(owner)->getClass() == C_FOSSOYEUR && owner->IsAlive())
                {
                    Player* po = static_cast<Player*>(owner);
                    if (unit->GetEntry() == C_CHAROGNARD[0] && victim->IsAlive() && damage < health)
                        po->CastSpell(victim, F_H_RAT[0], TRIGGERED_OLD_TRIGGERED);
                    if (unit->GetEntry() == C_SOMBREDOGUE[0])
                    {
                        if (damage >= health)
                        {
                            if (uint32 r = Rank(po, TF_CHAROGNE, TF_CHAROGNE_N))
                                po->ModifyPower(POWER_MANA, int32(po->GetMaxPower(POWER_MANA)) * int32(2 * r) / 100);
                        }
                        if (unit->HasAura(F_ALPHA[0]))
                        {
                            std::vector<Unit*> autour;
                            Ennemis(victim, po, 8.0f, autour);
                            int32 bp = int32(damage);
                            for (Unit* e : autour)
                                if (e != victim)
                                    unit->CastCustomSpell(e, F_H_ALPHA_D[0], &bp, nullptr, nullptr, TRIGGERED_OLD_TRIGGERED);
                        }
                    }
                }
        // Martyr : Festin de lames (ses coups le soignent)
        if (unit && unit != victim && unit->GetTypeId() == TYPEID_PLAYER && static_cast<Player*>(unit)->getClass() == C_MARTYR)
        {
            auto it = festinCoups.find(Raw(unit));
            if (it != festinCoups.end() && it->second && unit->HasAura(MA_FESTIN_L[0]))
            {
                int32 bp = int32(std::min(damage, health)) * 30 / 100;
                if (bp > 0)
                    unit->CastCustomSpell(unit, MA_BONUS_S[0], &bp, nullptr, nullptr, TRIGGERED_OLD_TRIGGERED);
                if (--it->second == 0)
                    unit->RemoveAurasDueToSpell(MA_FESTIN_L[0]);
            }
        }
        // Marque du sang : une part des dégâts subis par la cible soigne le Martyr
        if (unit != victim)
        {
            auto it = marques.find(Raw(victim));
            if (it != marques.end())
            {
                Unit* m = victim->GetMap()->GetUnit(ObjectGuid(it->second.first));
                if (m && m->IsAlive() && victim->GetSpellAuraHolder(MA_MARQUE[0], m->GetObjectGuid()))
                {
                    int32 bp = int32(float(std::min(damage, health)) * it->second.second / 100.0f);
                    if (bp > 0)
                        m->CastCustomSpell(m, MA_BONUS_S[0], &bp, nullptr, nullptr, TRIGGERED_OLD_TRIGGERED);
                }
                else
                    marques.erase(it);
            }
        }
        // Martyr frappé : Rempart vivant, Forteresse de sang, Ferveur du gardien, Caillot réflexe
        if (victim->GetTypeId() == TYPEID_PLAYER && static_cast<Player*>(victim)->getClass() == C_MARTYR && unit && unit != victim &&
            victim->IsAlive() && damage < health)
        {
            Player* pm = static_cast<Player*>(victim);
            if (pm->HasAura(MA_REMPART[0]))
                pm->ModifyPower(POWER_ENERGY, 5);
            if (pm->HasAura(MA_FORTERESSE[0]))
                GagnerFerveur(pm);
            else if (uint32 r = Rank(pm, TM_GARDIEN, TM_GARDIEN_N))
                if (Roll(10.0f * r))
                    GagnerFerveur(pm);
            if (HasTalent(pm, TM_REFLEXE, TM_REFLEXE_N) && (health - damage) * 4 < pm->GetMaxHealth())
            {
                time_t now = time(nullptr);
                time_t& last = reflexeTime[Raw(pm)];
                if (now - last >= 60)
                {
                    last = now;
                    int32 bp = int32(pm->GetMaxHealth()) / 10;
                    pm->CastCustomSpell(pm, MA_CAILLOT_H[0], &bp, nullptr, nullptr, TRIGGERED_OLD_TRIGGERED);
                }
            }
        }
        // Sacrifice : 50 % des dégâts subis par l'allié vont au Martyr (moins 10 % par rang de Sacrifice renforcé)
        if (victim->GetTypeId() == TYPEID_PLAYER && unit != victim && victim->IsAlive() && damage < health)
            if (SpellAuraHolder* h = victim->GetSpellAuraHolder(MA_SACRIFICE[0]))
                if (Unit* mu = victim->GetMap()->GetUnit(h->GetCasterGuid()))
                    if (mu != victim && mu->IsAlive() && mu->GetTypeId() == TYPEID_PLAYER)
                    {
                        Player* pm = static_cast<Player*>(mu);
                        uint32 part = damage / 2;
                        uint32 pris = part * (100 - 10 * Rank(pm, TM_SACRIFICE_R, TM_SACRIFICE_R_N)) / 100;
                        uint32 hm = pm->GetHealth();
                        pris = std::min(pris, hm > 1 ? hm - 1 : 0);
                        victim->ModifyHealth(int32(part));
                        if (pris)
                            pm->ModifyHealth(-int32(pris));
                    }
        if (!victim->IsAlive() || damage >= health || unit == victim)
            return;
        // Liens partagés : les dégâts sont répartis entre les membres reliés à 30 m
        if (victim->GetTypeId() == TYPEID_PLAYER && victim->HasAura(TW_PARTAGES[0]))
        {
            Player* pv = static_cast<Player*>(victim);
            std::vector<Unit*> groupe, lies;
            Groupe(pv, pv, 30.0f, groupe);
            for (Unit* m : groupe)
                if (m != victim && m->HasAura(TW_PARTAGES[0]))
                    lies.push_back(m);
            if (!lies.empty())
            {
                uint32 part = damage / uint32(lies.size() + 1);
                victim->ModifyHealth(int32(damage - part));
                for (Unit* m : lies)
                {
                    uint32 h = m->GetHealth();
                    m->ModifyHealth(-int32(std::min(part, h > 1 ? h - 1 : 0)));
                }
            }
        }
        // Partage des chairs : 30 % des dégâts vont au sombredogue
        if (victim->GetTypeId() == TYPEID_PLAYER && static_cast<Player*>(victim)->getClass() == C_FOSSOYEUR && victim->HasAura(F_PARTAGE[0]))
            if (Pet* pet = static_cast<Player*>(victim)->GetPet())
                if (pet->IsAlive())
                {
                    uint32 part = damage * 30 / 100;
                    uint32 h = pet->GetHealth();
                    part = std::min(part, h > 1 ? h - 1 : 0);
                    if (part)
                    {
                        victim->ModifyHealth(int32(part));
                        pet->ModifyHealth(-int32(part));
                    }
                }
    }

    // ------------------------------------------------------------------ soins
    void ClassesModule::NouvHeal(Unit* unit, Unit* victim, uint32 addHealth)
    {
        if (!unit || !victim || !addHealth || unit->GetTypeId() != TYPEID_PLAYER || victim->GetTypeId() != TYPEID_PLAYER)
            return;
        Player* pv = static_cast<Player*>(victim);
        // Sang béni : les soins reçus par l'allié soignent aussi le Martyr
        if (SpellAuraHolder* h = victim->GetSpellAuraHolder(MA_BENI[0]))
            if (Unit* mu = victim->GetMap()->GetUnit(h->GetCasterGuid()))
                if (mu != victim && mu->IsAlive() && mu->GetTypeId() == TYPEID_PLAYER)
                {
                    int32 bp = int32(addHealth) * (20 + 5 * int32(Rank(static_cast<Player*>(mu), TM_BENI_A, TM_BENI_A_N))) / 100;
                    if (bp > 0)
                        mu->CastCustomSpell(mu, MA_BONUS_S[0], &bp, nullptr, nullptr, TRIGGERED_OLD_TRIGGERED);
                }
        // Saint martyr : chaque soin du Martyr soigne aussi tout le groupe
        Player* pu = static_cast<Player*>(unit);
        if (pu->getClass() == C_MARTYR && pu->HasAura(MA_SAINT[0]))
        {
            std::vector<Unit*> groupe;
            Groupe(pu, pu, 40.0f, groupe);
            int32 bp = int32(addHealth) * (20 + 5 * int32(Rank(pu, TM_SAINT_P, TM_SAINT_P_N))) / 100;
            if (bp > 0)
                for (Unit* m : groupe)
                    if (m != victim)
                        pu->CastCustomSpell(m, MA_BONUS_S[0], &bp, nullptr, nullptr, TRIGGERED_OLD_TRIGGERED);
        }
        // Fil conducteur : la cible reçoit 20 % des soins faits sur les autres membres du groupe
        Group* g = pv->GetGroup();
        if (!g)
            return;
        for (GroupReference* ref = g->GetFirstMember(); ref; ref = ref->next())
        {
            Player* m = ref->getSource();
            if (!m || m == victim || !m->IsInWorld() || !m->IsAlive() || m->GetMap() != victim->GetMap())
                continue;
            if (!m->HasAura(TW_CONDUCTEUR[0]) || !m->IsWithinDistInMap(victim, 40.0f))
                continue;
            int32 bp = int32(addHealth) * 20 / 100;
            if (bp > 0)
                unit->CastCustomSpell(m, TW_BONUS_SOIN[0], &bp, nullptr, nullptr, TRIGGERED_OLD_TRIGGERED);
        }
    }

    // ------------------------------------------------------------------ chaque seconde
    void ClassesModule::NouvUpkeep(Player* p)
    {
        uint8 cls = p->getClass();
        ObjectGuid pg = p->GetObjectGuid();
        if (cls == C_TISSERAND)
        {
            // fin de Toile protectrice : 400 points de vie en 10 s (+10 % par rang de Fil réparateur)
            for (auto it = toileCaster.begin(); it != toileCaster.end();)
            {
                if (it->second != Raw(p))
                {
                    ++it;
                    continue;
                }
                Unit* t = p->GetMap()->GetUnit(ObjectGuid(it->first));
                if (!t || !t->IsAlive())
                {
                    it = toileCaster.erase(it);
                    continue;
                }
                if (t->GetSpellAuraHolder(TW_TOILE_P[0], pg))
                {
                    ++it;
                    continue;
                }
                int32 bp = AuNiveau(p, 80.0f) * int32(100 + 10 * Rank(p, TT_REPARATEUR, TT_REPARATEUR_N)) / 100;
                p->CastCustomSpell(t, TW_TOILE_HOT[0], &bp, nullptr, nullptr, TRIGGERED_OLD_TRIGGERED);
                it = toileCaster.erase(it);
            }
            return;
        }
        if (cls == C_MARTYR)
        {
            MartyrUpkeep(p);
            return;
        }
        if (cls != C_FOSSOYEUR)
            return;
        // Posture du profanateur : énergie tant que la posture est active, mana sinon
        bool posture = p->HasAura(F_POSTURE[0]);
        if (posture && p->GetPowerType() != POWER_ENERGY)
        {
            if (!p->GetMaxPower(POWER_ENERGY))
                p->SetMaxPower(POWER_ENERGY, 100);
            p->SetPowerType(POWER_ENERGY);
        }
        else if (!posture && p->GetPowerType() == POWER_ENERGY)
            p->SetPowerType(POWER_MANA);
        // sombredogue : Pacte du charnier obligatoire ; ses dégâts et sa vie augmentent de 4 % par rang
        if (Pet* pet = p->GetPet())
            if (pet->GetEntry() == C_SOMBREDOGUE[0])
            {
                if (!PeutChien(p))
                {
                    pet->Unsummon(PET_SAVE_AS_DELETED, p);
                    Dire(p, "Sans le Pacte du charnier, le sombredogue retourne à la terre.");
                }
                else if (pet->IsAlive())
                {
                    // Pacte (dégâts et vie +4 %), Dressage macabre (dégâts +5 %), Os renforcés (vie +5 %, critique +1 %),
                    // Peau de goule (armure +10 %), Lien de la meute (vitesse d'attaque +3 %), Crocs d'os (critique +2 %)
                    int32 pacte = 4 * int32(Rank(p, TF_CHARNIER, TF_CHARNIER_N));
                    int32 os = int32(Rank(p, TF_OS, TF_OS_N));
                    Cachee(pet, F_PACTE_PET[0], pacte + 5 * int32(Rank(p, TF_DRESSAGE, TF_DRESSAGE_N)), pacte + 5 * os,
                           10 * int32(Rank(p, TF_PEAU, TF_PEAU_N)));
                    Cachee(pet, F_PACTE_PET2[0], 3 * int32(Rank(p, TF_LIEN, TF_LIEN_N)), 2 * int32(Rank(p, TF_CROCS, TF_CROCS_N)) + os);
                }
            }
        // Maîtrise de la pelle : critique avec une autre arme à deux mains (l'arme d'hast est gérée par le talent)
        {
            int32 crit = 0;
            if (uint32 r = Rank(p, TF_MAITRISE, TF_MAITRISE_N))
                if (Item* w = p->GetWeaponForAttack(BASE_ATTACK, true, true))
                {
                    uint32 sc = w->GetProto()->SubClass;
                    if (sc == ITEM_SUBCLASS_WEAPON_AXE2 || sc == ITEM_SUBCLASS_WEAPON_MACE2 || sc == ITEM_SUBCLASS_WEAPON_SWORD2 ||
                        sc == ITEM_SUBCLASS_WEAPON_STAFF)
                        crit = int32(r) / 2;
                }
            Cachee(p, F_H_MAITRISE[0], crit);
        }
        // Légion des trépassés : les fantômes frappent la cible de leur allié, puis explosent à la fin
        {
            bool active = p->HasAura(F_LEGION[0]);
            auto& dq = fantomes[Raw(p)];
            if (active)
            {
                legion.insert(Raw(p));
                for (auto const& fa : dq)
                {
                    Unit* ally = p->GetMap()->GetUnit(ObjectGuid(fa.first));
                    Unit* v = ally ? ally->GetVictim() : nullptr;
                    if (v && v->IsAlive() && p->CanAttack(v) && ally->IsWithinDistInMap(v, 30.0f))
                    {
                        p->CastSpell(v, F_H_LEGION_D[0], TRIGGERED_OLD_TRIGGERED);
                        p->ModifyPower(POWER_MANA, int32(p->GetMaxPower(POWER_MANA)) / 100);
                    }
                }
            }
            else if (legion.erase(Raw(p)))
            {
                for (auto const& fa : dq)
                {
                    Unit* ally = p->GetMap()->GetUnit(ObjectGuid(fa.first));
                    Unit* v = ally ? ally->GetVictim() : nullptr;
                    if (!v || !v->IsAlive())
                        continue;
                    std::vector<Unit*> autour;
                    Ennemis(v, p, 8.0f, autour);
                    if (p->CanAttack(v) && std::find(autour.begin(), autour.end(), v) == autour.end())
                        autour.push_back(v);
                    for (Unit* e : autour)
                    {
                        p->CastSpell(e, F_H_LEGION_X[0], TRIGGERED_OLD_TRIGGERED);
                        p->CastSpell(e, F_H_AME_MAUDITE[0], TRIGGERED_OLD_TRIGGERED);
                    }
                }
            }
        }
        // fantômes : liste nettoyée des auras disparues
        auto fit = fantomes.find(Raw(p));
        if (fit != fantomes.end())
        {
            auto& dq = fit->second;
            for (auto it = dq.begin(); it != dq.end();)
            {
                Unit* a = p->GetMap()->GetUnit(ObjectGuid(it->first));
                if (!a || !a->GetSpellAuraHolder(it->second, pg))
                    it = dq.erase(it);
                else
                    ++it;
            }
            if (!PeutFantomes(p))
            {
                for (auto const& f : dq)
                    if (Unit* a = p->GetMap()->GetUnit(ObjectGuid(f.first)))
                        a->RemoveAurasByCasterSpell(f.second, pg);
                dq.clear();
            }
        }
    }

    // Martyr, chaque seconde : énergie, Soif de sang, Instinct de survie, Prédateur, Seigneur du sang, Fontaine de sang
    void ClassesModule::MartyrUpkeep(Player* p)
    {
        if (p->GetPowerType() != POWER_ENERGY)
            p->SetPowerType(POWER_ENERGY);
        float pct = Pct(p);
        // Soif de sang : +1 % de dégâts par tranche de 2 % de PV manquants (25 %, +2 % par rang de Soif accrue)
        int32 soif = 0;
        if (p->HasSpell(MA_SOIF[0]))
            soif = std::min(25 + 2 * int32(Rank(p, TM_SOIF_A, TM_SOIF_A_N)), int32((1.0f - pct) * 100.0f) / 2);
        Cachee(p, MA_H_SOIF[0], soif);
        int32 instinct = 0;
        if (pct < 0.35f)
            instinct = -2 * int32(Rank(p, TM_INSTINCT, TM_INSTINCT_N));
        Cachee(p, MA_H_INSTINCT[0], instinct);
        int32 pred = 0;
        if (Unit* v = p->GetVictim())
            if (v->IsAlive() && Pct(v) < 0.5f)
                pred = 2 * int32(Rank(p, TM_PREDATEUR, TM_PREDATEUR_N));
        Cachee(p, MA_H_PREDATEUR[0], pred);
        // Seigneur du sang : camouflage entretenu tant qu'il dure, critique +10 % par rang de Seigneur prolongé
        if (SpellAuraHolder* h = p->GetSpellAuraHolder(MA_SEIGNEUR[0]))
        {
            Cachee(p, MA_H_CRIT[0], 10 * int32(Rank(p, TM_SEIGNEUR_P, TM_SEIGNEUR_P_N)));
            if (!p->HasAura(MA_SEIGNEUR_ST[0]))
            {
                p->CastSpell(p, MA_SEIGNEUR_ST[0], TRIGGERED_OLD_TRIGGERED);
                if (SpellAuraHolder* st = p->GetSpellAuraHolder(MA_SEIGNEUR_ST[0]))
                {
                    st->SetAuraDuration(h->GetAuraDuration());
                    st->UpdateAuraDuration();
                }
            }
        }
        else
        {
            Cachee(p, MA_H_CRIT[0], 0);
            if (p->HasAura(MA_SEIGNEUR_ST[0]))
                p->RemoveAurasDueToSpell(MA_SEIGNEUR_ST[0]);
        }
        // Fontaine de sang : soigne les alliés à 20 m de la fontaine
        auto it = fontaines.find(Raw(p));
        if (it != fontaines.end())
        {
            Fontaine& ft = it->second;
            if (ft.secondes <= 0 || !p->IsAlive())
            {
                fontaines.erase(it);
                return;
            }
            --ft.secondes;
            std::vector<Unit*> groupe;
            Groupe(p, p, 100.0f, groupe);
            for (Unit* m : groupe)
                if (m->GetDistance(ft.x, ft.y, ft.z) <= 20.0f)
                {
                    int32 bp = ft.soin;
                    p->CastCustomSpell(m, MA_BONUS_S[0], &bp, nullptr, nullptr, TRIGGERED_OLD_TRIGGERED);
                }
        }
    }

    // Fureur du sang : les prochains coups du Martyr sont critiques (une charge par coup)
    bool ClassesModule::OnCalculateEffectiveCritChance(const Unit* unit, const Unit* /*victim*/, uint8 /*attType*/, const SpellEntry* ability, float& outChance)
    {
        if (!unit || unit->GetTypeId() != TYPEID_PLAYER || static_cast<Player const*>(unit)->getClass() != C_MARTYR || !MA_FUREUR[0])
            return false;
        if (ability && IsPositiveSpell(ability))
            return false;
        Unit* u = const_cast<Unit*>(unit);
        SpellAuraHolder* h = u->GetSpellAuraHolder(MA_FUREUR[0]);
        if (!h)
            return false;
        if (h->GetStackAmount() > 1)
            h->SetStackAmount(h->GetStackAmount() - 1, u);
        else
            u->RemoveAurasDueToSpell(MA_FUREUR[0]);
        outChance = 100.0f;
        return true;
    }

    void ClassesModule::NouvLogOut(Player* p)
    {
        uint64 g = Raw(p);
        malOrdre.erase(g);
        legion.erase(g);
        ferveurConso.erase(g);
        fontaines.erase(g);
        festinCoups.erase(g);
        marques.erase(g);
        lienForce.erase(g);
        vieSauts.erase(g);
        fantomes.erase(g);
        trepasTime.erase(g);
        mortEvitee.erase(g);
        for (auto it = toileCaster.begin(); it != toileCaster.end();)
            it = (it->second == g || it->first == g) ? toileCaster.erase(it) : std::next(it);
    }

    // appelé par le coeur quand un coup va tuer un joueur : true = il reste à 1 point de vie
    bool ClassesModule::NouvEviteMort(Player const* p)
    {
        std::lock_guard<std::recursive_mutex> guard(lock);
        uint64 g = p->GetObjectGuid().GetRawValue();
        if (p->HasAura(TW_DESTIN[0]))
        {
            mortEvitee[g] = 1;
            return true;
        }
        if (p->getClass() == C_MARTYR && p->HasSpell(MA_DERNIER[0]))
        {
            time_t now = time(nullptr);
            time_t& last = dernierTime[g];
            time_t cd = HasTalent(p, TM_VIE_OFFERTE, TM_VIE_OFFERTE_N) ? 300 : 600;
            if (now - last >= cd)
            {
                last = now;
                mortEvitee[g] = 3;
                return true;
            }
        }
        if (p->getClass() == C_TISSERAND && HasTalent(p, TT_TREPAS, TT_TREPAS_N))
        {
            time_t now = time(nullptr);
            time_t& last = trepasTime[g];
            if (now - last >= 300)
            {
                last = now;
                mortEvitee[g] = 2;
                return true;
            }
        }
        return false;
    }
}
