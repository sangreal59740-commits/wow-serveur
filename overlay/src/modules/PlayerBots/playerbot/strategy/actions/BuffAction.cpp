
#include "playerbot/playerbot.h"
#include "BuffAction.h"
#include "Spells/SpellMgr.h"
#include <set>
#include <map>
#include <vector>

#include "playerbot/strategy/values/ItemCountValue.h"

using namespace ai;

class FindBuffVisitor : public IterateItemsVisitor {
public:
    FindBuffVisitor(Player* bot) : IterateItemsVisitor(), bot(bot)
    {
    }

    virtual bool Visit(Item* item)
    {
        if (bot->CanUseItem(item->GetProto()) != EQUIP_ERR_OK)
            return true;

        const ItemPrototype* proto = item->GetProto();

        if (proto->Class != ITEM_CLASS_CONSUMABLE)
            return true;

        if (proto->SubClass != ITEM_SUBCLASS_ELIXIR && 
            proto->SubClass != ITEM_SUBCLASS_FLASK &&
            proto->SubClass != ITEM_SUBCLASS_SCROLL && 
            proto->SubClass != ITEM_SUBCLASS_FOOD &&
            proto->SubClass != ITEM_SUBCLASS_CONSUMABLE_OTHER &&
            proto->SubClass != ITEM_SUBCLASS_ITEM_ENHANCEMENT)
            return true;

        for (int i=0; i<MAX_ITEM_PROTO_SPELLS; i++)
        {
            uint32 spellId = proto->Spells[i].SpellId;
            if (!spellId)
                continue;

            if (bot->HasAura(spellId))
                return true;

            Item* itemForSpell = *bot->GetPlayerbotAI()->GetAiObjectContext()->GetValue<Item*>("item for spell", spellId);
            if (itemForSpell && itemForSpell->GetEnchantmentId(TEMP_ENCHANTMENT_SLOT))
                return true;
        
            if (items.find(proto->SubClass) == items.end())
                items[proto->SubClass] = std::list<Item*>();

            items[proto->SubClass].push_back(item);
            break;
        }

        return true;
    }

public:
    std::map<uint32, std::list<Item*> > items;

private:
    Player* bot;
};

void BuffAction::TellHeader(uint32 subClass, Player* requester)
{
    switch (subClass)
    {
    case ITEM_SUBCLASS_ELIXIR:
        ai->TellPlayer(requester, "--- Elixir ---");
        return;
    case ITEM_SUBCLASS_FLASK:
        ai->TellPlayer(requester, "--- Flask ---");
        return;
    case ITEM_SUBCLASS_SCROLL:
        ai->TellPlayer(requester, "--- Scroll ---");
        return;
    case ITEM_SUBCLASS_FOOD:
        ai->TellPlayer(requester, "--- Food ---");
        return;
    case ITEM_SUBCLASS_ITEM_ENHANCEMENT:
        ai->TellPlayer(requester, "--- Enchant ---");
        return;
    }
}

// Serveur d'Alexis : « buff » = le bot met ses buffs de classe (sorts amicaux d'au moins 5 min) sur le joueur qui le demande.
// Une seule bénédiction par paladin (Rois, sinon Sagesse pour les classes à mana, Puissance sinon).
static uint32 PremierRang(uint32 spellId)
{
    uint32 first = sSpellMgr.GetFirstSpellInChain(spellId);
    return first ? first : spellId;
}

static bool BuffsDeClasse(Player* bot, PlayerbotAI* ai, Player* target)
{
    if (!target || !target->IsAlive() || bot->IsInCombat() || !bot->IsWithinDistInMap(target, 30.0f))
        return false;
    static const std::set<uint32> BENEDICTIONS = { 19740, 19742, 20217, 1038, 19977, 20911, 25782, 25894, 25898, 25895, 25890, 25899 };
    std::vector<uint32> buffs;
    std::map<uint32, uint32> benedictions;      // premier rang -> rang le plus haut connu
    for (auto const& kv : bot->GetSpellMap())
    {
        if (kv.second.state == PLAYERSPELL_REMOVED || kv.second.disabled || !kv.second.active)
            continue;
        uint32 id = kv.first;
        SpellEntry const* info = sSpellTemplate.LookupEntry<SpellEntry>(id);
        if (!info || (info->Attributes & SPELL_ATTR_PASSIVE))
            continue;
        uint32 next = sSpellMgr.GetNextSpellInChain(id);
        if (next && bot->HasSpell(next))
            continue;
        bool aura = false, ami = true;
        for (int i = 0; i < MAX_EFFECT_INDEX; ++i)
        {
            if (!info->Effect[i])
                continue;
            if (info->Effect[i] == SPELL_EFFECT_APPLY_AURA)
                aura = true;
            if (info->EffectImplicitTargetA[i] != TARGET_UNIT_FRIEND)
                ami = false;
        }
        int32 duree = GetSpellDuration(info);
        if (!aura || !ami || duree < 5 * MINUTE * IN_MILLISECONDS || !IsPositiveSpell(info))
            continue;
        uint32 first = PremierRang(id);
        if (BENEDICTIONS.count(first))
            benedictions[first] = id;
        else
            buffs.push_back(id);
    }
    if (!benedictions.empty())
    {
        bool mana = target->GetPowerType() == POWER_MANA;
        uint32 choix = 0;
        for (uint32 pref : { 20217u, mana ? 19742u : 19740u, mana ? 19740u : 19742u, 19977u, 20911u })
            if (benedictions.count(pref)) { choix = benedictions[pref]; break; }
        if (!choix)
            choix = benedictions.begin()->second;
        buffs.push_back(choix);
    }
    bool fait = false;
    for (uint32 id : buffs)
    {
        if (target->HasAura(id))
            continue;
        if (bot->CastSpell(target, id, TRIGGERED_OLD_TRIGGERED) == SPELL_CAST_OK)
            fait = true;
    }
    return fait;
}

bool BuffAction::Execute(Event& event)
{
    std::string text = event.getParam();
    Player* requester = event.getOwner() ? event.getOwner() : GetMaster();

    if (text.empty())
    {
        if (BuffsDeClasse(bot, ai, requester))
            ai->TellPlayer(requester, "Et voilà, c'est fait !");
        return true;
    }

    FindBuffVisitor visitor(bot);
    ai->InventoryIterateItems(&visitor, IterateItemsMask::ITERATE_ITEMS_IN_BAGS);

    uint32 oldSubClass = -1;
    for (std::map<uint32, std::list<Item*> >::iterator i = visitor.items.begin(); i != visitor.items.end(); ++i)
    {
        std::list<Item*> items = i->second;

        uint32 subClass = i->first;
        if (oldSubClass != subClass)
        {
            if (!items.empty())
            {
                TellHeader(subClass, requester);
            }

            oldSubClass = subClass;
        }
        for (std::list<Item*>::iterator j = items.begin(); j != items.end(); ++j)
        {
            Item* item = *j;
            std::ostringstream out;
            out << chat->formatItem(item, item->GetCount());
            ai->TellPlayer(requester, out);
        }
    }
    
    return true;
}
