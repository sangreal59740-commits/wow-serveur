#include "FicheModule.h"

#include "Chat/Chat.h"
#include "Entities/Player.h"
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
        ChatHandler(session).SendSysMessage(buf);
        return true;
    }
}
