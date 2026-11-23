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

    static void Ennemis(Unit* center, Unit* caster, float range, std::vector<Unit*>& out)
    {
        std::list<Unit*> list;
        MaNGOS::AnyUnfriendlyUnitInObjectRangeCheck check(center, range);
        MaNGOS::UnitListSearcher<MaNGOS::AnyUnfriendlyUnitInObjectRangeCheck> searcher(list, check);
        Cell::VisitAllObjects(center, searcher, range);
        for (Unit* u : list)
            if (u && u->IsAlive() && caster->CanAttack(u))
                out.push_back(u);
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
    void ClassesModule::NouvCast(Player* p, uint32 id, Unit* /*victim*/, Spell* /*spell*/)
    {
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

        if (cls == C_FOSSOYEUR)
        {
            // fantômes du Passeur : pacte obligatoire, un fantôme par allié, 3 au maximum
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
                while (dq.size() > 3)
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
                        int32 bp = int32(ally->GetMaxHealth()) * 15 / 100;
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
                            h->SetAuraMaxDuration(15000);
                            h->SetAuraDuration(15000);
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
                    int32 bp = int32((mn + mx) / 2.0f + AuNiveau(p, 100.0f)) * int32(30 * k) / 100;
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
                int32 bp = AuNiveau(p, 320.0f);
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
                return;
            }
            if (chien && id == F_D_FORCE[0])
                p->CastSpell(pet, F_FORCE_PET[0], TRIGGERED_OLD_TRIGGERED);
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
                target->RemoveAurasByCasterSpell(TW_VIE[0], pg);
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
                    p->CastSpell(v, F_VENGERESSE_D[0], TRIGGERED_OLD_TRIGGERED);
                return true;
            }
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
        // Fil conducteur : la cible reçoit 20 % des soins faits sur les autres membres du groupe
        Player* pv = static_cast<Player*>(victim);
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
                    int32 bp = 4 * int32(Rank(p, TF_CHARNIER, TF_CHARNIER_N));
                    int32 cur = INT32_MIN;
                    if (Aura* a = pet->GetAura(F_PACTE_PET[0], EFFECT_INDEX_0))
                        cur = a->GetModifier()->m_amount;
                    if (cur != bp)
                    {
                        pet->RemoveAurasDueToSpell(F_PACTE_PET[0]);
                        pet->CastCustomSpell(pet, F_PACTE_PET[0], &bp, &bp, nullptr, TRIGGERED_OLD_TRIGGERED);
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

    void ClassesModule::NouvLogOut(Player* p)
    {
        uint64 g = Raw(p);
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
