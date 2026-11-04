#include "RoutesModule.h"
#include "../../classes/src/ClassesData.h"

#include "Chat/Chat.h"
#include "Entities/Player.h"
#include "Globals/ObjectAccessor.h"
#include "Log/Log.h"
#include "Maps/Map.h"
#include "Server/WorldSession.h"
#include "World/World.h"

#include <cmath>
#include <cstdio>

namespace cmangos_module
{
    static RoutesModule* instance = nullptr;
    static const float TUILE = 533.33333f;
    static const uint32 ZONES_CAPITALES[] = { 1519, 1537, 1657, 1637, 1638, 1497 };   // Hurlevent, Forgefer, Darnassus, Orgrimmar, Pitons, Fossoyeuse

    std::vector<ModuleChatCommand>* RoutesModule::GetCommandTable()
    {
        static std::vector<ModuleChatCommand> commandTable =
        {
            { "", std::bind(&RoutesModule::HandleRoute, this, std::placeholders::_1, std::placeholders::_2), SEC_GAMEMASTER },
        };
        return &commandTable;
    }

    void RoutesModule::OnInitialize()
    {
        instance = this;
        std::string chemins[] = { sWorld.GetDataPath() + "routes.bin", "routes.bin" };
        for (auto const& c : chemins)
            if (Charger(c))
                return;
        sLog.outError("Routes : routes.bin introuvable (a placer dans %s), pas de bonus de vitesse sur les routes", sWorld.GetDataPath().c_str());
    }

    bool RoutesModule::Charger(const std::string& chemin)
    {
        FILE* f = fopen(chemin.c_str(), "rb");
        if (!f)
            return false;
        uint32 entete[3];
        if (fread(entete, 4, 3, f) != 3 || entete[0] != 0x54554F52)
        {
            fclose(f);
            return false;
        }
        for (uint32 i = 0; i < entete[2]; ++i)
        {
            uint8 e[4];
            std::vector<uint8> bits(256 * 256 / 8);
            if (fread(e, 1, 4, f) != 4 || fread(bits.data(), 1, bits.size(), f) != bits.size())
                break;
            tuiles[(uint32(e[0]) << 16) | (uint32(e[1]) << 8) | e[2]] = std::move(bits);
        }
        fclose(f);
        sLog.outString("Routes : %u tuiles chargees depuis %s", uint32(tuiles.size()), chemin.c_str());
        return true;
    }

    bool RoutesModule::SurRoute(uint32 map, float x, float y) const
    {
        if (map > 1 || tuiles.empty())
            return false;
        // lignes le long de x, colonnes le long de y (comme les fichiers de l'ADT : carte_<tx>_<ty>, tx selon y, ty selon x)
        float fr = (32.0f - x / TUILE) * 256.0f, fc = (32.0f - y / TUILE) * 256.0f;
        if (fr < 0 || fc < 0 || fr >= 64 * 256 || fc >= 64 * 256)
            return false;
        uint32 r = uint32(fr), c = uint32(fc);
        auto it = tuiles.find((map << 16) | ((c / 256) << 8) | (r / 256));
        if (it == tuiles.end())
            return false;
        uint32 bit = (r % 256) * 256 + (c % 256);
        return (it->second[bit >> 3] >> (bit & 7)) & 1;
    }

    void RoutesModule::Appliquer(Player* p)
    {
        bool route = p->IsAlive() && !p->IsTaxiFlying() && SurRoute(p->GetMapId(), p->GetPositionX(), p->GetPositionY());
        if (route)
        {
            uint32 zone = p->GetZoneId();
            for (uint32 z : ZONES_CAPITALES)
                if (zone == z)
                    route = false;
        }
        bool a = p->HasAura(classes_data::ROUTE_SPELL);
        if (route && !a)
            p->CastSpell(p, classes_data::ROUTE_SPELL, TRIGGERED_OLD_TRIGGERED);
        else if (!route && a)
            p->RemoveAurasDueToSpell(classes_data::ROUTE_SPELL);
    }

    void RoutesModule::OnUpdate(uint32 elapsed)
    {
        timer += elapsed;
        if (timer < 250 || tuiles.empty())
            return;
        timer = 0;
        std::vector<std::pair<Map*, ObjectGuid>> todo;
        {
            HashMapHolder<Player>::ReadGuard g(HashMapHolder<Player>::GetLock());
            for (auto const& kv : HashMapHolder<Player>::GetContainer())
            {
                Player* p = kv.second;
                if (!p || !p->IsInWorld() || p->GetMapId() > 1)
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
                    if (instance && p->IsInWorld())
                        instance->Appliquer(p);
            });
        }
    }

    bool RoutesModule::OnPreGiveXP(Player* player, uint32& xp, Creature* /*victim*/)
    {
        if (!player || !xp)
            return false;
        for (uint32 i = 0; i < classes_data::BIEN_NOURRI_N; ++i)
            if (player->HasAura(classes_data::BIEN_NOURRI[i]))
            {
                xp = uint32(std::lround(xp * 1.05));
                break;
            }
        return false;
    }

    bool RoutesModule::HandleRoute(WorldSession* session, const std::string& /*args*/)
    {
        Player* p = session ? session->GetPlayer() : nullptr;
        if (!p)
            return false;
        float fr = (32.0f - p->GetPositionX() / TUILE) * 256.0f, fc = (32.0f - p->GetPositionY() / TUILE) * 256.0f;
        char buf[256];
        snprintf(buf, sizeof(buf), "Route : %s (carte %u, tuile %d_%d, case %d %d, %u tuiles chargees, bonus %s)",
                 SurRoute(p->GetMapId(), p->GetPositionX(), p->GetPositionY()) ? "oui" : "non", p->GetMapId(),
                 int(fc / 256), int(fr / 256), int(fr) % 256, int(fc) % 256, uint32(tuiles.size()),
                 p->HasAura(classes_data::ROUTE_SPELL) ? "actif" : "inactif");
        ChatHandler(session).SendSysMessage(buf);
        return true;
    }
}
