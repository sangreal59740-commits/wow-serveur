// Boutique : monnaie Gen (achetée par PayPal), catalogue, achats livrés par courrier dans le jeu.
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using MySqlConnector;

namespace Portail
{
    class Pack { public string id; public decimal euros; public int gen; public string badge = ""; }
    class Article
    {
        public string id; public string nom; public string categorie; public int prix; public string desc = "";
        public int item; public int quantite = 1; public int type;      // type 0 objet, 1 changement de nom, 2 compagnon (item = identifiant du compagnon)
        public string qualite = "epique"; public bool bientot;
    }
    class Catalogue
    {
        public List<string> categories = new List<string>();
        public List<Pack> packs = new List<Pack>();
        public List<Article> articles = new List<Article>();
    }

    static partial class Program
    {
        static Catalogue Boutique = new Catalogue();
        static readonly HttpClient Http = new HttpClient();

        static void PreparerBoutique()
        {
            using (var c = new MySqlConnection(ConnStr(C.bddRealmd)))
            {
                c.Open();
                foreach (var q in new[] {
                    "CREATE TABLE IF NOT EXISTS portail_gen (compte INT UNSIGNED NOT NULL, solde INT NOT NULL DEFAULT 0, PRIMARY KEY (compte)) ENGINE=InnoDB",
                    "CREATE TABLE IF NOT EXISTS portail_operation (id INT UNSIGNED NOT NULL AUTO_INCREMENT, compte INT UNSIGNED NOT NULL, type VARCHAR(16) NOT NULL, gen INT NOT NULL, euros DECIMAL(8,2) NOT NULL DEFAULT 0, reference VARCHAR(64) NOT NULL DEFAULT '', detail VARCHAR(200) NOT NULL DEFAULT '', date DATETIME NOT NULL, PRIMARY KEY (id), KEY compte (compte)) ENGINE=InnoDB",
                    "CREATE TABLE IF NOT EXISTS portail_commande (id VARCHAR(64) NOT NULL, compte INT UNSIGNED NOT NULL, pack VARCHAR(32) NOT NULL, euros DECIMAL(8,2) NOT NULL, gen INT NOT NULL, statut VARCHAR(16) NOT NULL, date DATETIME NOT NULL, PRIMARY KEY (id)) ENGINE=InnoDB",
                    "CREATE TABLE IF NOT EXISTS portail_session (jeton CHAR(64) NOT NULL, compte INT UNSIGNED NOT NULL, expire DATETIME NOT NULL, PRIMARY KEY (jeton)) ENGINE=InnoDB",
                    // copie du catalogue pour la boutique en jeu (module compagnons, addon Compagnons)
                    "CREATE TABLE IF NOT EXISTS portail_catalogue (id VARCHAR(64) NOT NULL, categorie VARCHAR(32) NOT NULL, nom VARCHAR(100) NOT NULL, description VARCHAR(255) NOT NULL DEFAULT '', prix INT UNSIGNED NOT NULL, qualite VARCHAR(16) NOT NULL DEFAULT '', type TINYINT UNSIGNED NOT NULL DEFAULT 0, item INT UNSIGNED NOT NULL DEFAULT 0, quantite INT UNSIGNED NOT NULL DEFAULT 1, ordre INT UNSIGNED NOT NULL DEFAULT 0, PRIMARY KEY (id)) ENGINE=InnoDB DEFAULT CHARSET=utf8" })
                    new MySqlCommand(q, c).ExecuteNonQuery();
            }
            using (var c = new MySqlConnection(ConnStr(C.bddPersos)))
            {
                c.Open();
                new MySqlCommand("CREATE TABLE IF NOT EXISTS custom_boutique_livraison (id INT UNSIGNED NOT NULL AUTO_INCREMENT, guid INT UNSIGNED NOT NULL, type TINYINT UNSIGNED NOT NULL DEFAULT 0, item INT UNSIGNED NOT NULL DEFAULT 0, quantite INT UNSIGNED NOT NULL DEFAULT 1, titre VARCHAR(100) NOT NULL DEFAULT '', statut TINYINT UNSIGNED NOT NULL DEFAULT 0, date DATETIME NOT NULL, PRIMARY KEY (id), KEY statut (statut)) ENGINE=InnoDB DEFAULT CHARSET=utf8", c).ExecuteNonQuery();
            }
        }

        static void ChargerBoutique()
        {
            var f = Path.Combine(Racine, "boutique.json");
            try
            {
                if (File.Exists(f)) Boutique = Json.Deserialize<Catalogue>(File.ReadAllText(f, Encoding.UTF8)) ?? new Catalogue();
                PublierCatalogue();
                Log("Boutique : " + Boutique.articles.Count + " articles, " + Boutique.packs.Count + " packs de Gen" + (string.IsNullOrEmpty(C.paypalClientId) ? " (PayPal pas encore configuré)" : " (PayPal " + C.paypalMode + ")"));
            }
            catch (Exception e) { Log("boutique.json illisible : " + e.Message); }
        }

        // le jeu lit le même catalogue (boutique en jeu) : recopié à chaque chargement de boutique.json
        static void PublierCatalogue()
        {
            try
            {
                using (var c = new MySqlConnection(ConnStr(C.bddRealmd)))
                {
                    c.Open();
                    using (var t = c.BeginTransaction())
                    {
                        new MySqlCommand("DELETE FROM portail_catalogue", c, t).ExecuteNonQuery();
                        int ordre = 0;
                        foreach (var a in Boutique.articles)
                        {
                            ordre++;
                            if (a.bientot || a.prix <= 0) continue;
                            var q = new MySqlCommand("INSERT INTO portail_catalogue (id, categorie, nom, description, prix, qualite, type, item, quantite, ordre) VALUES (@i, @c, @n, @d, @p, @q, @t, @it, @qt, @o)", c, t);
                            q.Parameters.AddWithValue("@i", a.id);
                            q.Parameters.AddWithValue("@c", a.categorie ?? "");
                            q.Parameters.AddWithValue("@n", a.nom ?? "");
                            q.Parameters.AddWithValue("@d", (a.desc ?? "").Length > 250 ? a.desc.Substring(0, 250) : (a.desc ?? ""));
                            q.Parameters.AddWithValue("@p", a.prix);
                            q.Parameters.AddWithValue("@q", a.qualite ?? "");
                            q.Parameters.AddWithValue("@t", a.type);
                            q.Parameters.AddWithValue("@it", a.item);
                            q.Parameters.AddWithValue("@qt", a.quantite);
                            q.Parameters.AddWithValue("@o", ordre);
                            q.ExecuteNonQuery();
                        }
                        t.Commit();
                    }
                }
            }
            catch (Exception e) { Log("catalogue en jeu non publié : " + e.Message); }
        }

        // ------------------------------------------------------------------ sessions
        static string NouvelleSession(long compte)
        {
            var b = new byte[32];
            using (var r = RandomNumberGenerator.Create()) r.GetBytes(b);
            var jeton = BitConverter.ToString(b).Replace("-", "").ToLowerInvariant();
            using (var c = new MySqlConnection(ConnStr(C.bddRealmd)))
            {
                c.Open();
                new MySqlCommand("DELETE FROM portail_session WHERE expire < NOW()", c).ExecuteNonQuery();
                var q = new MySqlCommand("INSERT INTO portail_session (jeton, compte, expire) VALUES (@j, @c, NOW() + INTERVAL 30 DAY)", c);
                q.Parameters.AddWithValue("@j", jeton);
                q.Parameters.AddWithValue("@c", compte);
                q.ExecuteNonQuery();
            }
            return jeton;
        }

        static long CompteSession(HttpListenerRequest req)
        {
            var h = req.Headers["Authorization"] ?? "";
            var jeton = h.StartsWith("Bearer ") ? h.Substring(7).Trim() : "";
            if (!Regex.IsMatch(jeton, "^[0-9a-f]{64}$")) return 0;
            using (var c = new MySqlConnection(ConnStr(C.bddRealmd)))
            {
                c.Open();
                var q = new MySqlCommand("SELECT compte FROM portail_session WHERE jeton = @j AND expire > NOW()", c);
                q.Parameters.AddWithValue("@j", jeton);
                var v = q.ExecuteScalar();
                return v == null ? 0 : Convert.ToInt64(v);
            }
        }

        static int Solde(long compte)
        {
            using (var c = new MySqlConnection(ConnStr(C.bddRealmd)))
            {
                c.Open();
                var q = new MySqlCommand("SELECT solde FROM portail_gen WHERE compte = @c", c);
                q.Parameters.AddWithValue("@c", compte);
                var v = q.ExecuteScalar();
                return v == null ? 0 : Convert.ToInt32(v);
            }
        }

        static void Crediter(MySqlConnection c, MySqlTransaction t, long compte, int gen, decimal euros, string type, string reference, string detail)
        {
            var q = new MySqlCommand("INSERT INTO portail_gen (compte, solde) VALUES (@c, @g) ON DUPLICATE KEY UPDATE solde = solde + @g", c, t);
            q.Parameters.AddWithValue("@c", compte);
            q.Parameters.AddWithValue("@g", gen);
            q.ExecuteNonQuery();
            var o = new MySqlCommand("INSERT INTO portail_operation (compte, type, gen, euros, reference, detail, date) VALUES (@c, @t, @g, @e, @r, @d, NOW())", c, t);
            o.Parameters.AddWithValue("@c", compte);
            o.Parameters.AddWithValue("@t", type);
            o.Parameters.AddWithValue("@g", gen);
            o.Parameters.AddWithValue("@e", euros);
            o.Parameters.AddWithValue("@r", reference ?? "");
            o.Parameters.AddWithValue("@d", detail ?? "");
            o.ExecuteNonQuery();
        }

        // ------------------------------------------------------------------ routes
        static bool RouteBoutique(string p, HttpListenerRequest req, HttpListenerResponse rep)
        {
            switch (p)
            {
                case "/api/boutique":
                    EnvoyerJson(rep, new { Boutique.categories, Boutique.packs, Boutique.articles, paypal = C.paypalClientId, paypalMode = C.paypalMode });
                    return true;
                case "/api/moi":
                    EnvoyerJson(rep, Moi(CompteSession(req)));
                    return true;
                case "/api/acheter":
                    if (req.HttpMethod != "POST") return false;
                    EnvoyerJson(rep, Acheter(CompteSession(req), LireCorps(req)));
                    return true;
                case "/api/paypal/commande":
                    if (req.HttpMethod != "POST") return false;
                    EnvoyerJson(rep, CommandePaypal(CompteSession(req), LireCorps(req)));
                    return true;
                case "/api/paypal/capture":
                    if (req.HttpMethod != "POST") return false;
                    EnvoyerJson(rep, CapturePaypal(CompteSession(req), LireCorps(req)));
                    return true;
                case "/api/deconnexion":
                    var h = req.Headers["Authorization"] ?? "";
                    if (h.StartsWith("Bearer "))
                        using (var c = new MySqlConnection(ConnStr(C.bddRealmd)))
                        {
                            c.Open();
                            var q = new MySqlCommand("DELETE FROM portail_session WHERE jeton = @j", c);
                            q.Parameters.AddWithValue("@j", h.Substring(7).Trim());
                            q.ExecuteNonQuery();
                        }
                    EnvoyerJson(rep, new { ok = true });
                    return true;
            }
            return false;
        }

        static object Moi(long compte)
        {
            if (compte == 0) return Erreur("Session expirée, reconnecte-toi.");
            using (var c = new MySqlConnection(ConnStr(C.bddRealmd)))
            {
                c.Open();
                var n = new MySqlCommand("SELECT username FROM account WHERE id = @c", c);
                n.Parameters.AddWithValue("@c", compte);
                var nom = Convert.ToString(n.ExecuteScalar());
                var persos = new List<object>();
                var q = new MySqlCommand($"SELECT guid, name, level, race, class FROM `{C.bddPersos}`.characters WHERE account = @c ORDER BY level DESC", c);
                q.Parameters.AddWithValue("@c", compte);
                using (var r = q.ExecuteReader())
                    while (r.Read())
                        persos.Add(new { guid = Convert.ToInt64(r.GetValue(0)), nom = r.GetString(1), niveau = Convert.ToInt32(r.GetValue(2)), race = Convert.ToInt32(r.GetValue(3)), classe = Convert.ToInt32(r.GetValue(4)) });
                var hist = new List<object>();
                var hq = new MySqlCommand("SELECT type, gen, euros, detail, date FROM portail_operation WHERE compte = @c ORDER BY id DESC LIMIT 15", c);
                hq.Parameters.AddWithValue("@c", compte);
                using (var r = hq.ExecuteReader())
                    while (r.Read())
                        hist.Add(new { type = r.GetString(0), gen = Convert.ToInt32(r.GetValue(1)), euros = Convert.ToDecimal(r.GetValue(2)), detail = r.GetString(3), date = r.GetDateTime(4).ToString("dd/MM/yyyy HH:mm") });
                return new { ok = true, nom, solde = Solde(compte), persos, historique = hist };
            }
        }

        static object Acheter(long compte, Dictionary<string, object> d)
        {
            if (compte == 0) return Erreur("Session expirée, reconnecte-toi.");
            var a = Boutique.articles.FirstOrDefault(x => x.id == Champ(d, "article"));
            if (a == null || a.bientot) return Erreur("Cet article n'est pas disponible.");
            if (!long.TryParse(Champ(d, "perso"), out var guid)) return Erreur("Choisis le personnage qui recevra l'achat.");
            using (var c = new MySqlConnection(ConnStr(C.bddRealmd)))
            {
                c.Open();
                var pq = new MySqlCommand($"SELECT name FROM `{C.bddPersos}`.characters WHERE guid = @g AND account = @c", c);
                pq.Parameters.AddWithValue("@g", guid);
                pq.Parameters.AddWithValue("@c", compte);
                var perso = pq.ExecuteScalar() as string;
                if (perso == null) return Erreur("Ce personnage n'est pas sur ton compte.");
                if (a.type == 2)
                {
                    // un compagnon ne s'achète qu'une fois par personnage (déjà possédé ou en cours de livraison)
                    var dq = new MySqlCommand($"SELECT (SELECT COUNT(*) FROM `{C.bddPersos}`.custom_cpg WHERE proprio = @g AND cpg = @i) + (SELECT COUNT(*) FROM `{C.bddPersos}`.custom_boutique_livraison WHERE guid = @g AND type = 2 AND item = @i AND statut = 0)", c);
                    dq.Parameters.AddWithValue("@g", guid);
                    dq.Parameters.AddWithValue("@i", a.item);
                    long deja = 0;
                    try { deja = Convert.ToInt64(dq.ExecuteScalar()); } catch { }     // table custom_cpg créée au premier démarrage du serveur
                    if (deja > 0) return Erreur(perso + " possède déjà " + a.nom + ".");
                }
                using (var t = c.BeginTransaction())
                {
                    var deb = new MySqlCommand("UPDATE portail_gen SET solde = solde - @p WHERE compte = @c AND solde >= @p", c, t);
                    deb.Parameters.AddWithValue("@p", a.prix);
                    deb.Parameters.AddWithValue("@c", compte);
                    if (deb.ExecuteNonQuery() != 1) { t.Rollback(); return Erreur("Pas assez de Gen pour cet article."); }
                    var liv = new MySqlCommand($"INSERT INTO `{C.bddPersos}`.custom_boutique_livraison (guid, type, item, quantite, titre, statut, date) VALUES (@g, @ty, @i, @q, @n, 0, NOW())", c, t);
                    liv.Parameters.AddWithValue("@g", guid);
                    liv.Parameters.AddWithValue("@ty", a.type);
                    liv.Parameters.AddWithValue("@i", a.item);
                    liv.Parameters.AddWithValue("@q", a.quantite);
                    liv.Parameters.AddWithValue("@n", a.nom.Length > 90 ? a.nom.Substring(0, 90) : a.nom);
                    liv.ExecuteNonQuery();
                    var o = new MySqlCommand("INSERT INTO portail_operation (compte, type, gen, euros, reference, detail, date) VALUES (@c, 'achat', @g, 0, @r, @d, NOW())", c, t);
                    o.Parameters.AddWithValue("@c", compte);
                    o.Parameters.AddWithValue("@g", -a.prix);
                    o.Parameters.AddWithValue("@r", a.id);
                    o.Parameters.AddWithValue("@d", a.nom + " pour " + perso);
                    o.ExecuteNonQuery();
                    t.Commit();
                }
                Log("Achat : " + a.nom + " (" + a.prix + " Gen) pour " + perso);
                return new { ok = true, solde = Solde(compte), message = a.nom + " arrive dans la boîte aux lettres de " + perso + " (moins d'une minute si le serveur tourne)." };
            }
        }

        // ------------------------------------------------------------------ PayPal
        static string PaypalApi => C.paypalMode == "live" ? "https://api-m.paypal.com" : "https://api-m.sandbox.paypal.com";

        static string JetonPaypal()
        {
            ServicePointManager.SecurityProtocol |= SecurityProtocolType.Tls12;
            using (var m = new HttpRequestMessage(HttpMethod.Post, PaypalApi + "/v1/oauth2/token"))
            {
                m.Headers.Authorization = new AuthenticationHeaderValue("Basic", Convert.ToBase64String(Encoding.UTF8.GetBytes(C.paypalClientId + ":" + C.paypalSecret)));
                m.Content = new StringContent("grant_type=client_credentials", Encoding.UTF8, "application/x-www-form-urlencoded");
                var r = Http.SendAsync(m).Result;
                var t = r.Content.ReadAsStringAsync().Result;
                if (!r.IsSuccessStatusCode) throw new Exception("PayPal refuse les identifiants (" + (int)r.StatusCode + ")");
                return Json.Deserialize<Dictionary<string, object>>(t)["access_token"].ToString();
            }
        }

        static Dictionary<string, object> AppelPaypal(HttpMethod methode, string chemin, string corps, out int code)
        {
            using (var m = new HttpRequestMessage(methode, PaypalApi + chemin))
            {
                m.Headers.Authorization = new AuthenticationHeaderValue("Bearer", JetonPaypal());
                if (corps != null) m.Content = new StringContent(corps, Encoding.UTF8, "application/json");
                var r = Http.SendAsync(m).Result;
                code = (int)r.StatusCode;
                var t = r.Content.ReadAsStringAsync().Result;
                try { return Json.Deserialize<Dictionary<string, object>>(t) ?? new Dictionary<string, object>(); }
                catch { return new Dictionary<string, object>(); }
            }
        }

        static object CommandePaypal(long compte, Dictionary<string, object> d)
        {
            if (compte == 0) return Erreur("Connecte-toi pour acheter des Gen.");
            if (string.IsNullOrEmpty(C.paypalClientId)) return Erreur("Le paiement n'est pas encore ouvert.");
            var pack = Boutique.packs.FirstOrDefault(x => x.id == Champ(d, "pack"));
            if (pack == null) return Erreur("Pack inconnu.");
            var montant = pack.euros.ToString("0.00", CultureInfo.InvariantCulture);
            var corps = Json.Serialize(new
            {
                intent = "CAPTURE",
                purchase_units = new[] { new { reference_id = pack.id, custom_id = compte + ":" + pack.id, description = pack.gen + " Gen - " + C.nom, amount = new { currency_code = "EUR", value = montant } } },
                application_context = new { brand_name = C.nom, shipping_preference = "NO_SHIPPING", user_action = "PAY_NOW" }
            });
            var r = AppelPaypal(HttpMethod.Post, "/v2/checkout/orders", corps, out var code);
            if (code >= 300 || !r.ContainsKey("id")) return Erreur("PayPal n'a pas pu créer la commande (" + code + ").");
            var id = r["id"].ToString();
            using (var c = new MySqlConnection(ConnStr(C.bddRealmd)))
            {
                c.Open();
                var q = new MySqlCommand("INSERT INTO portail_commande (id, compte, pack, euros, gen, statut, date) VALUES (@i, @c, @p, @e, @g, 'creee', NOW())", c);
                q.Parameters.AddWithValue("@i", id);
                q.Parameters.AddWithValue("@c", compte);
                q.Parameters.AddWithValue("@p", pack.id);
                q.Parameters.AddWithValue("@e", pack.euros);
                q.Parameters.AddWithValue("@g", pack.gen);
                q.ExecuteNonQuery();
            }
            return new { ok = true, id };
        }

        static object CapturePaypal(long compte, Dictionary<string, object> d)
        {
            if (compte == 0) return Erreur("Session expirée, reconnecte-toi.");
            var id = Champ(d, "commande");
            if (!Regex.IsMatch(id, "^[A-Z0-9]{6,40}$")) return Erreur("Commande inconnue.");
            decimal euros; int gen; string statut;
            using (var c = new MySqlConnection(ConnStr(C.bddRealmd)))
            {
                c.Open();
                var q = new MySqlCommand("SELECT euros, gen, statut FROM portail_commande WHERE id = @i AND compte = @c", c);
                q.Parameters.AddWithValue("@i", id);
                q.Parameters.AddWithValue("@c", compte);
                using (var r = q.ExecuteReader())
                {
                    if (!r.Read()) return Erreur("Commande inconnue.");
                    euros = r.GetDecimal(0); gen = r.GetInt32(1); statut = r.GetString(2);
                }
            }
            if (statut == "payee") return new { ok = true, solde = Solde(compte), message = "Paiement déjà pris en compte." };
            var cap = AppelPaypal(HttpMethod.Post, "/v2/checkout/orders/" + id + "/capture", "{}", out var code);
            if (code >= 300) cap = AppelPaypal(HttpMethod.Get, "/v2/checkout/orders/" + id, null, out code);
            if (!PaiementValide(cap, euros, out var captureId)) return Erreur("Le paiement n'a pas abouti. Aucun Gen n'a été débité ni crédité.");
            using (var c = new MySqlConnection(ConnStr(C.bddRealmd)))
            {
                c.Open();
                using (var t = c.BeginTransaction())
                {
                    var u = new MySqlCommand("UPDATE portail_commande SET statut = 'payee' WHERE id = @i AND statut <> 'payee'", c, t);
                    u.Parameters.AddWithValue("@i", id);
                    if (u.ExecuteNonQuery() == 1)
                    {
                        Crediter(c, t, compte, gen, euros, "paiement", captureId, gen + " Gen (" + euros.ToString("0.00", CultureInfo.InvariantCulture) + " €)");
                        Log("Paiement : " + euros + " € → " + gen + " Gen (compte " + compte + ")");
                    }
                    t.Commit();
                }
            }
            return new { ok = true, solde = Solde(compte), message = "Merci ! " + gen + " Gen ont été ajoutés à ton compte." };
        }

        static bool PaiementValide(Dictionary<string, object> r, decimal euros, out string captureId)
        {
            captureId = "";
            try
            {
                if (!r.TryGetValue("status", out var st) || st.ToString() != "COMPLETED") return false;
                var pu = ((System.Collections.IList)r["purchase_units"])[0] as Dictionary<string, object>;
                var caps = (System.Collections.IList)((Dictionary<string, object>)pu["payments"])["captures"];
                var cap = (Dictionary<string, object>)caps[0];
                var am = (Dictionary<string, object>)cap["amount"];
                captureId = cap["id"].ToString();
                return cap["status"].ToString() == "COMPLETED" && am["currency_code"].ToString() == "EUR" &&
                       decimal.Parse(am["value"].ToString(), CultureInfo.InvariantCulture) == euros;
            }
            catch { return false; }
        }

        // ------------------------------------------------------------------ console d'administration
        static void Console_()
        {
            Log("Commandes : gen NOM MONTANT (ajoute ou retire des Gen), solde NOM, boutique (recharge boutique.json)");
            while (true)
            {
                var l = Console.ReadLine();
                if (l == null) return;
                var a = l.Trim().Split(new[] { ' ' }, StringSplitOptions.RemoveEmptyEntries);
                try
                {
                    if (a.Length == 0) continue;
                    if (a[0] == "boutique") { ChargerBoutique(); continue; }
                    if ((a[0] == "gen" && a.Length == 3) || (a[0] == "solde" && a.Length == 2))
                    {
                        using (var c = new MySqlConnection(ConnStr(C.bddRealmd)))
                        {
                            c.Open();
                            var q = new MySqlCommand("SELECT id FROM account WHERE username = @u", c);
                            q.Parameters.AddWithValue("@u", a[1].ToUpperInvariant());
                            var v = q.ExecuteScalar();
                            if (v == null) { Log("Compte inconnu : " + a[1]); continue; }
                            long compte = Convert.ToInt64(v);
                            if (a[0] == "gen")
                            {
                                int n = int.Parse(a[2]);
                                using (var t = c.BeginTransaction()) { Crediter(c, t, compte, n, 0, "admin", "", "Ajout par l'administrateur"); t.Commit(); }
                            }
                            Log(a[1].ToUpperInvariant() + " : " + Solde(compte) + " Gen");
                        }
                        continue;
                    }
                    Log("Commandes : gen NOM MONTANT, solde NOM, boutique");
                }
                catch (Exception e) { Log("Erreur : " + e.Message); }
            }
        }
    }
}
