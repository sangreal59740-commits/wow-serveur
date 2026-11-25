// Boutique du portail : livre par courrier les achats faits sur le site ou dans le launcher.
// Le portail écrit dans custom_boutique_livraison (base des personnages), le serveur envoie et marque comme livré.
#include "ClassesModule.h"

#include "Database/DatabaseEnv.h"
#include "Entities/Item.h"
#include "Entities/ItemPrototype.h"
#include "Entities/Player.h"
#include "Globals/ObjectMgr.h"
#include "Mails/Mail.h"

#include <algorithm>
#include <vector>

namespace cmangos_module
{
    void BoutiqueLivrer()
    {
        static bool pret = false;
        if (!pret)
        {
            CharacterDatabase.DirectExecute(
                "CREATE TABLE IF NOT EXISTS `custom_boutique_livraison` ("
                "`id` INT UNSIGNED NOT NULL AUTO_INCREMENT, `guid` INT UNSIGNED NOT NULL, `type` TINYINT UNSIGNED NOT NULL DEFAULT 0,"
                "`item` INT UNSIGNED NOT NULL DEFAULT 0, `quantite` INT UNSIGNED NOT NULL DEFAULT 1, `titre` VARCHAR(100) NOT NULL DEFAULT '',"
                "`statut` TINYINT UNSIGNED NOT NULL DEFAULT 0, `date` DATETIME NOT NULL, PRIMARY KEY (`id`), KEY `statut` (`statut`))"
                " ENGINE=InnoDB DEFAULT CHARSET=utf8");
            pret = true;
        }
        // type 2 (compagnon) : livré par le module compagnons
        auto r = CharacterDatabase.Query("SELECT `id`, `guid`, `type`, `item`, `quantite`, `titre` FROM `custom_boutique_livraison` WHERE `statut` = 0 AND `type` <> 2 ORDER BY `id` LIMIT 20");
        if (!r)
            return;
        std::vector<std::pair<uint32, uint32>> faits;            // id, statut (1 livré, 2 erreur)
        do
        {
            Field* f = r->Fetch();
            uint32 id = f[0].GetUInt32(), guid = f[1].GetUInt32(), type = f[2].GetUInt32(), item = f[3].GetUInt32(), qte = f[4].GetUInt32();
            std::string titre = f[5].GetCppString();
            ObjectGuid og(HIGHGUID_PLAYER, guid);
            Player* pl = sObjectMgr.GetPlayer(og);
            MailSender expediteur(MAIL_NORMAL, uint32(0), MAIL_STATIONERY_GM);
            if (type == 1)
            {
                // changement de nom : proposé à la prochaine connexion
                if (pl)
                    pl->SetAtLoginFlag(AT_LOGIN_RENAME);
                else
                    CharacterDatabase.PExecute("UPDATE `characters` SET `at_login` = `at_login` | 1 WHERE `guid` = %u", guid);
                MailDraft("Boutique : changement de nom", "Ton changement de nom est prêt. Déconnecte-toi : il te sera proposé sur l'écran des personnages.")
                    .SendMailTo(MailReceiver(pl, og), expediteur);
                faits.emplace_back(id, 1);
                continue;
            }
            ItemPrototype const* proto = ObjectMgr::GetItemPrototype(item);
            if (!proto || !qte)
            {
                faits.emplace_back(id, 2);
                continue;
            }
            MailDraft draft("Boutique : " + titre, "Merci pour ton soutien ! Voici ton achat, bon jeu.");
            uint32 reste = std::min<uint32>(qte, 12 * std::max<uint32>(1, proto->GetMaxStackSize()));
            uint32 nb = 0;
            while (reste && nb < 12)
            {
                uint32 n = std::min<uint32>(reste, std::max<uint32>(1, proto->GetMaxStackSize()));
                if (Item* it = Item::CreateItem(item, n, pl))
                {
                    it->SaveToDB();
                    draft.AddItem(it);
                    ++nb;
                }
                reste -= n;
            }
            draft.SendMailTo(MailReceiver(pl, og), expediteur);
            faits.emplace_back(id, nb ? 1 : 2);
        }
        while (r->NextRow());
        for (auto const& fa : faits)
            CharacterDatabase.DirectPExecute("UPDATE `custom_boutique_livraison` SET `statut` = %u WHERE `id` = %u", fa.second, fa.first);
    }
}
