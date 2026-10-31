#include "MetiersModule.h"

#include "Entities/Player.h"
#include "Tools/Formulas.h"
#include "World/World.h"

namespace cmangos_module
{
    static bool EstMetier(uint16 skillId)
    {
        switch (skillId)
        {
            case 164:   // forge
            case 165:   // travail du cuir
            case 171:   // alchimie
            case 182:   // herboristerie
            case 186:   // minage
            case 197:   // couture
            case 202:   // ingenierie
            case 333:   // enchantement
            case 393:   // depecage
            case 185:   // cuisine
            case 129:   // secourisme
            case 356:   // peche
                return true;
            default:
                return false;
        }
    }

    MetiersModule::MetiersModule() : Module("Metiers", nullptr)
    {
    }

    void MetiersModule::OnUpdateSkill(Player* player, uint16 skillId)
    {
        if (!player || !EstMetier(skillId))
            return;

        const uint16 valeur = player->GetSkillValuePure(skillId);
        auto& connues = valeurs[player->GetGUIDLow()];
        auto it = connues.find(skillId);
        if (it == connues.end())
        {
            // premiere fois qu'on voit ce metier pendant la session : on note la valeur
            connues[skillId] = valeur;
            return;
        }

        const uint16 avant = it->second;
        it->second = valeur;

        // gain normal de 1 a 3 points (pas un apprentissage ni une commande MJ)
        if (valeur <= avant || valeur - avant > 3)
            return;

        if (player->GetLevel() >= sWorld.getConfig(CONFIG_UINT32_MAX_PLAYER_LEVEL))
            return;

        const uint32 niveau = player->GetLevel();
        float xp = MaNGOS::XP::BaseGain(niveau, niveau) * 0.5f * (valeur - avant) * sWorld.getConfig(CONFIG_FLOAT_RATE_XP_KILL);
        if (xp >= 1.0f)
            player->GiveXP(uint32(xp), nullptr);
    }

    void MetiersModule::OnLogOut(Player* player)
    {
        if (player)
            valeurs.erase(player->GetGUIDLow());
    }
}
