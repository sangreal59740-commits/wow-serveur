#include "FicheModule.h"

#include "Chat/Chat.h"
#include "Entities/Player.h"
#include "Maps/Map.h"
#include "Server/SQLStorages.h"
#include "Server/WorldSession.h"

#include <cstdio>

namespace cmangos_module
{
    std::vector<ModuleChatCommand>* FicheModule::GetCommandTable()
    {
        static std::vector<ModuleChatCommand> commandTable =
        {
            { "donnees", std::bind(&FicheModule::HandleDonnees, this, std::placeholders::_1, std::placeholders::_2), SEC_PLAYER },
        };
        return &commandTable;
    }

    bool FicheModule::HandleDonnees(WorldSession* session, const std::string& /*args*/)
    {
        Player* p = session ? session->GetPlayer() : nullptr;
        if (!p)
            return false;
        int32 sorts = 0;
        float critSorts = 0.0f;
        for (uint32 s = SPELL_SCHOOL_HOLY; s < MAX_SPELL_SCHOOL; ++s)        // meilleure école de magie
        {
            SpellSchoolMask mask = SpellSchoolMask(1 << s);
            sorts = std::max(sorts, p->SpellBaseDamageBonusDone(mask));
            critSorts = std::max(critSorts, p->GetCritChance(mask));
        }
        char buf[320];
        snprintf(buf, sizeof(buf), "##FICHE sd=%d;so=%d;cc=%.2f;cd=%.2f;cs=%.2f;tm=%.2f;td=%.2f;ts=%.2f;es=%.2f;pa=%.2f;bl=%.2f;mp=%d",
                 sorts, p->SpellBaseHealingBonusDone(SPELL_SCHOOL_MASK_ALL),
                 p->GetCritChance(BASE_ATTACK), p->GetCritChance(RANGED_ATTACK), critSorts,
                 p->GetHitChance(BASE_ATTACK), p->GetHitChance(RANGED_ATTACK), p->GetHitChance(SPELL_SCHOOL_MASK_MAGIC),
                 p->GetFloatValue(PLAYER_DODGE_PERCENTAGE), p->GetFloatValue(PLAYER_PARRY_PERCENTAGE), p->GetFloatValue(PLAYER_BLOCK_PERCENTAGE),
                 p->GetTotalAuraModifierByMiscValue(SPELL_AURA_MOD_POWER_REGEN, POWER_MANA));
        std::string ligne = buf;
        // régénération : mana toutes les 5 s (hors incantation / en incantation), vie par seconde (hors combat / en combat)
        snprintf(buf, sizeof(buf), ";rmc=%.1f;rmi=%.1f;rv=%.1f;rvc=%.1f", p->m_modManaRegen * 5.0f, p->m_modManaRegenInterrupt * 5.0f,
                 p->OCTRegenHPPerSpirit() + p->GetTotalAuraModifier(SPELL_AURA_MOD_HEALTH_REGEN_IN_COMBAT),
                 float(p->GetTotalAuraModifier(SPELL_AURA_MOD_HEALTH_REGEN_IN_COMBAT)));
        ligne += buf;
        // réduction des dégâts physiques par l'armure contre un attaquant de même niveau
        snprintf(buf, sizeof(buf), ";ra=%.1f", 100.0f - Unit::CalcArmorReducedDamage(p, p, 1000.0f) / 10.0f);
        ligne += buf;
        // cible hostile : réductions dans les deux sens et chances de la rater
        Unit* t = p->GetMap()->GetUnit(p->GetSelectionGuid());
        if (t && t != p && t->IsAlive() && p->CanAttack(t))
        {
            SpellEntry const* sort = sSpellTemplate.LookupEntry<SpellEntry>(133);      // Boule de feu, sort de référence
            snprintf(buf, sizeof(buf), ";cn=%u;ctr=%.1f;car=%.1f;crm=%.1f;crs=%.1f", t->GetLevel(),
                     100.0f - Unit::CalcArmorReducedDamage(p, t, 1000.0f) / 10.0f,
                     100.0f - Unit::CalcArmorReducedDamage(t, p, 1000.0f) / 10.0f,
                     p->CalculateEffectiveMissChance(t, BASE_ATTACK),
                     sort ? p->CalculateSpellMissChance(t, SPELL_SCHOOL_MASK_FIRE, sort) : 0.0f);
            ligne += buf;
        }
        else
            ligne += ";cn=0";
        ChatHandler(session).SendSysMessage(ligne.c_str());
        return true;
    }
}
