// Portail : site web, inscription, connexion, état du serveur et distribution du jeu pour le launcher.
// Un seul exe, configuré par portail.json (à côté de l'exe).
using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Sockets;
using System.Numerics;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Threading.Tasks;
using System.Web.Script.Serialization;
using MySqlConnector;

namespace Portail
{
    class Config
    {
        public string nom = "Genesis";
        public string ecoute = "http://localhost:8080/";
        public string adressePublique = "http://localhost:8080";
        public string adresseRoyaume = "127.0.0.1";
        public string dossierClient = @"C:\wow";
        public string exeJeu = "WoW_classes.exe";
        public List<string> exclure = new List<string> { "WTF", "Screenshots", "Logs", "WDB", "Errors", "realmlist.wtf", "vanilla-tweaks*", "World of Warcraft Install Log.html", "launcher_cache.json" };
        public string bddHote = "127.0.0.1";
        public int bddPort = 3310;
        public string bddUtilisateur = "root";
        public string bddMotDePasse = "123456";
        public string bddRealmd = "classicrealmd";
        public string bddPersos = "classiccharacters";
        public int portMangos = 8085;
        public int portRealmd = 3724;
        public int comptesParIp = 3;
    }

    static class Srp6
    {
        static readonly BigInteger N = BigInteger.Parse("0894B645E89E1535BBDAD5B8B290650530801B18EBFBF5E8FAB3C82872A3E9BB7", System.Globalization.NumberStyles.HexNumber);
        static readonly BigInteger G = 7;

        static BigInteger FromLittle(byte[] b)
        {
            var t = new byte[b.Length + 1];
            Array.Copy(b, t, b.Length);
            return new BigInteger(t);                   // octet de poids fort à 0 : toujours positif
        }

        static byte[] ToLittle(BigInteger v)
        {
            var b = v.ToByteArray();
            int n = b.Length;
            while (n > 1 && b[n - 1] == 0) n--;
            return b.Take(n).ToArray();
        }

        public static BigInteger FromHex(string hex) => BigInteger.Parse("0" + hex, System.Globalization.NumberStyles.HexNumber);

        public static string ToHex(BigInteger v)
        {
            var b = ToLittle(v);
            var sb = new StringBuilder();
            for (int i = b.Length - 1; i >= 0; i--) sb.Append(b[i].ToString("X2"));
            return sb.ToString().TrimStart('0');
        }

        // même calcul que CMaNGOS (SRP6::CalculateVerifier) : x = H(sel | H(NOM:MOTDEPASSE)), v = g^x mod N
        public static string Verifier(string user, string pass, string selHex)
        {
            using (var sha = SHA1.Create())
            {
                var h = sha.ComputeHash(Encoding.UTF8.GetBytes(user.ToUpperInvariant() + ":" + pass.ToUpperInvariant()));
                var s = ToLittle(FromHex(selHex));
                var x = FromLittle(sha.ComputeHash(s.Concat(h).ToArray()));
                return ToHex(BigInteger.ModPow(G, x, N));
            }
        }

        public static string NouveauSel()
        {
            var b = new byte[32];
            using (var r = RandomNumberGenerator.Create())
                do r.GetBytes(b); while (b[31] < 0x10);  // pas de zéro en tête : longueur fixe
            return ToHex(FromLittle(b));
        }
    }

    class Fichier { public string chemin; public long taille; public string md5; public long date; }

    static class Program
    {
        static Config C;
        static string Racine;           // dossier de l'exe
        static string Site;             // dossier site
        static readonly JavaScriptSerializer Json = new JavaScriptSerializer { MaxJsonLength = int.MaxValue };
        static volatile List<Fichier> Manifeste = new List<Fichier>();
        static volatile bool ManifestePret;
        static readonly ConcurrentDictionary<string, List<DateTime>> Essais = new ConcurrentDictionary<string, List<DateTime>>();
        static string ConnStr(string db) => $"Server={C.bddHote};Port={C.bddPort};User ID={C.bddUtilisateur};Password={C.bddMotDePasse};Database={db};SslMode=None;AllowPublicKeyRetrieval=true;";

        static int Main(string[] args)
        {
            if (args.Length > 0 && args[0] == "--test")
            {
                Console.WriteLine(Srp6.Verifier("TEST", "test", "AABBCCDDEEFF00112233445566778899AABBCCDDEEFF00112233445566778899"));
                return 0;
            }
            Console.OutputEncoding = Encoding.UTF8;
            Racine = AppDomain.CurrentDomain.BaseDirectory;
            Site = Path.Combine(Racine, "site");
            var cfg = Path.Combine(Racine, "portail.json");
            if (File.Exists(cfg))
            {
                try { C = Json.Deserialize<Config>(File.ReadAllText(cfg, Encoding.UTF8)); }
                catch (Exception e) { Console.WriteLine("portail.json illisible : " + e.Message); return 1; }
            }
            else
            {
                C = new Config();
                File.WriteAllText(cfg, Json.Serialize(C), Encoding.UTF8);
            }
            Console.Title = "Portail " + C.nom;
            Log("Portail " + C.nom + " : " + C.ecoute);
            try { PreparerBase(); Log("Base de données : OK"); }
            catch (Exception e) { Log("Base de données injoignable (" + e.Message + "). Lance la base SPP (option 2)."); }
            Task.Run(() => CalculerManifeste());
            Task.Run(() => { while (true) { Thread.Sleep(TimeSpan.FromMinutes(2)); CalculerManifeste(); } });

            var l = new HttpListener();
            l.Prefixes.Add(C.ecoute);
            try { l.Start(); }
            catch (HttpListenerException e)
            {
                Log("Impossible d'écouter sur " + C.ecoute + " : " + e.Message);
                Log("Sur le VPS, lance le portail en administrateur pour le port 80.");
                Console.ReadLine();
                return 1;
            }
            Log("Site : " + C.adressePublique + "  (Ctrl+C pour arrêter)");
            while (true)
            {
                var ctx = l.GetContext();
                Task.Run(() => Traiter(ctx));
            }
        }

        static void Log(string s) => Console.WriteLine(DateTime.Now.ToString("HH:mm:ss") + "  " + s);

        // ------------------------------------------------------------------ base
        static void PreparerBase()
        {
            using (var c = new MySqlConnection(ConnStr(C.bddRealmd)))
            {
                c.Open();
                new MySqlCommand("CREATE TABLE IF NOT EXISTS portail_inscription (id INT UNSIGNED NOT NULL, ip VARCHAR(64) NOT NULL, date DATETIME NOT NULL, PRIMARY KEY (id), KEY ip (ip))", c).ExecuteNonQuery();
            }
        }

        // ------------------------------------------------------------------ HTTP
        static void Traiter(HttpListenerContext ctx)
        {
            var req = ctx.Request; var rep = ctx.Response;
            try
            {
                rep.AddHeader("Access-Control-Allow-Origin", "*");
                rep.AddHeader("Access-Control-Allow-Headers", "Content-Type");
                if (req.HttpMethod == "OPTIONS") { rep.StatusCode = 204; rep.Close(); return; }
                var p = Uri.UnescapeDataString(req.Url.AbsolutePath);
                if (p == "/api/statut") EnvoyerJson(rep, Statut());
                else if (p == "/api/manifeste") EnvoyerJson(rep, new { pret = ManifestePret, royaume = C.adresseRoyaume, exe = C.exeJeu, fichiers = Manifeste });
                else if (p == "/api/inscription" && req.HttpMethod == "POST") EnvoyerJson(rep, Inscription(LireCorps(req), Ip(req)));
                else if (p == "/api/connexion" && req.HttpMethod == "POST") EnvoyerJson(rep, Connexion(LireCorps(req), Ip(req)));
                else if (p.StartsWith("/client/")) EnvoyerClient(req, rep, p.Substring(8));
                else if (p == "/telecharger" || p == "/telecharger/") EnvoyerLauncher(rep);
                else EnvoyerSite(rep, p);
            }
            catch (Exception e)
            {
                try { rep.StatusCode = 500; Ecrire(rep, "text/plain; charset=utf-8", Encoding.UTF8.GetBytes("Erreur : " + e.Message)); } catch { }
                Log("Erreur " + req.Url.AbsolutePath + " : " + e.Message);
            }
        }

        static string Ip(HttpListenerRequest req) => req.RemoteEndPoint?.Address?.ToString() ?? "?";

        static Dictionary<string, object> LireCorps(HttpListenerRequest req)
        {
            using (var r = new StreamReader(req.InputStream, Encoding.UTF8))
            {
                var t = r.ReadToEnd();
                if (t.Length > 4096) return new Dictionary<string, object>();
                try { return Json.Deserialize<Dictionary<string, object>>(t) ?? new Dictionary<string, object>(); }
                catch { return new Dictionary<string, object>(); }
            }
        }

        static string Champ(Dictionary<string, object> d, string k) => d.TryGetValue(k, out var v) && v != null ? v.ToString().Trim() : "";

        static void Ecrire(HttpListenerResponse rep, string type, byte[] data)
        {
            rep.ContentType = type;
            rep.ContentLength64 = data.Length;
            rep.OutputStream.Write(data, 0, data.Length);
            rep.Close();
        }

        static void EnvoyerJson(HttpListenerResponse rep, object o)
        {
            rep.AddHeader("Cache-Control", "no-store");
            Ecrire(rep, "application/json; charset=utf-8", Encoding.UTF8.GetBytes(Json.Serialize(o)));
        }

        static readonly Dictionary<string, string> Types = new Dictionary<string, string>
        {
            [".html"] = "text/html; charset=utf-8", [".css"] = "text/css; charset=utf-8", [".js"] = "application/javascript; charset=utf-8",
            [".json"] = "application/json; charset=utf-8", [".svg"] = "image/svg+xml", [".png"] = "image/png", [".jpg"] = "image/jpeg",
            [".jpeg"] = "image/jpeg", [".webp"] = "image/webp", [".ico"] = "image/x-icon", [".woff2"] = "font/woff2", [".mp4"] = "video/mp4",
        };

        static void EnvoyerSite(HttpListenerResponse rep, string p)
        {
            if (p == "/" || p == "") p = "/index.html";
            if (!Path.HasExtension(p)) p += ".html";
            var f = Path.GetFullPath(Path.Combine(Site, p.TrimStart('/').Replace('/', '\\')));
            if (!f.StartsWith(Path.GetFullPath(Site), StringComparison.OrdinalIgnoreCase) || !File.Exists(f))
            {
                rep.StatusCode = 404;
                f = Path.Combine(Site, "404.html");
                if (!File.Exists(f)) { Ecrire(rep, "text/plain; charset=utf-8", Encoding.UTF8.GetBytes("Page introuvable")); return; }
            }
            var ext = Path.GetExtension(f).ToLowerInvariant();
            var type = Types.TryGetValue(ext, out var t) ? t : "application/octet-stream";
            byte[] data;
            if (ext == ".html" || ext == ".js" || ext == ".css")
            {
                rep.AddHeader("Cache-Control", "no-cache");
                data = Encoding.UTF8.GetBytes(File.ReadAllText(f, Encoding.UTF8).Replace("{{NOM}}", C.nom).Replace("{{ADRESSE}}", C.adressePublique));
            }
            else data = File.ReadAllBytes(f);
            Ecrire(rep, type, data);
        }

        // le launcher téléchargé porte l'adresse du portail à la fin du fichier
        static void EnvoyerLauncher(HttpListenerResponse rep)
        {
            var f = Path.Combine(Racine, "Launcher.exe");
            if (!File.Exists(f)) { rep.StatusCode = 404; Ecrire(rep, "text/plain; charset=utf-8", Encoding.UTF8.GetBytes("Launcher absent du portail")); return; }
            var exe = File.ReadAllBytes(f);
            var tag = Encoding.UTF8.GetBytes("##PORTAIL##" + C.adressePublique.TrimEnd('/') + "##FIN##");
            rep.AddHeader("Content-Disposition", "attachment; filename=\"" + NomFichier(C.nom) + ".exe\"");
            Ecrire(rep, "application/octet-stream", exe.Concat(tag).ToArray());
        }

        static string NomFichier(string s)
        {
            var n = s.Normalize(NormalizationForm.FormD);
            var sb = new StringBuilder();
            foreach (var ch in n)
                if (char.IsLetterOrDigit(ch) && ch < 128) sb.Append(ch);
                else if (ch == ' ' || ch == '-' || ch == '\'') sb.Append('_');
            return "Launcher_" + sb.ToString().Trim('_');
        }

        // ------------------------------------------------------------------ jeu
        static bool Exclu(string rel)
        {
            var top = rel.Split('\\', '/')[0];
            foreach (var e in C.exclure)
            {
                if (e.EndsWith("*") ? top.StartsWith(e.TrimEnd('*'), StringComparison.OrdinalIgnoreCase) : string.Equals(top, e, StringComparison.OrdinalIgnoreCase))
                    return true;
            }
            return false;
        }

        static readonly Dictionary<string, Fichier> CacheMd5 = new Dictionary<string, Fichier>(StringComparer.OrdinalIgnoreCase);
        static readonly object VerrouManifeste = new object();

        static void CalculerManifeste()
        {
            lock (VerrouManifeste)
            {
                try
                {
                    if (!Directory.Exists(C.dossierClient)) { Log("Dossier du jeu introuvable : " + C.dossierClient); return; }
                    var root = Path.GetFullPath(C.dossierClient).TrimEnd('\\') + "\\";
                    var liste = new List<Fichier>();
                    int calcules = 0;
                    foreach (var f in Directory.EnumerateFiles(root, "*", SearchOption.AllDirectories))
                    {
                        var rel = f.Substring(root.Length);
                        if (Exclu(rel)) continue;
                        var fi = new FileInfo(f);
                        long date = fi.LastWriteTimeUtc.Ticks;
                        if (!CacheMd5.TryGetValue(rel, out var e) || e.taille != fi.Length || e.date != date)
                        {
                            using (var md5 = MD5.Create())
                            using (var s = new FileStream(f, FileMode.Open, FileAccess.Read, FileShare.ReadWrite, 1 << 20))
                                e = new Fichier { chemin = rel.Replace('\\', '/'), taille = fi.Length, date = date, md5 = BitConverter.ToString(md5.ComputeHash(s)).Replace("-", "").ToLowerInvariant() };
                            CacheMd5[rel] = e;
                            calcules++;
                        }
                        liste.Add(e);
                    }
                    Manifeste = liste;
                    if (!ManifestePret || calcules > 0)
                        Log("Jeu : " + liste.Count + " fichiers, " + (liste.Sum(x => x.taille) / 1048576) + " Mo" + (calcules > 0 ? " (" + calcules + " recalculés)" : ""));
                    ManifestePret = true;
                }
                catch (Exception e) { Log("Manifeste : " + e.Message); }
            }
        }

        static void EnvoyerClient(HttpListenerRequest req, HttpListenerResponse rep, string rel)
        {
            rel = rel.Replace('/', '\\');
            var root = Path.GetFullPath(C.dossierClient).TrimEnd('\\') + "\\";
            var f = Path.GetFullPath(Path.Combine(root, rel));
            if (!f.StartsWith(root, StringComparison.OrdinalIgnoreCase) || Exclu(rel) || !File.Exists(f))
            {
                rep.StatusCode = 404; rep.Close(); return;
            }
            using (var s = new FileStream(f, FileMode.Open, FileAccess.Read, FileShare.ReadWrite, 1 << 20))
            {
                long debut = 0, len = s.Length;
                var range = req.Headers["Range"];
                var m = range != null ? Regex.Match(range, @"bytes=(\d+)-") : null;
                if (m != null && m.Success)
                {
                    debut = Math.Min(long.Parse(m.Groups[1].Value), len);
                    rep.StatusCode = 206;
                    rep.AddHeader("Content-Range", "bytes " + debut + "-" + (len - 1) + "/" + len);
                }
                rep.ContentType = "application/octet-stream";
                rep.ContentLength64 = len - debut;
                rep.SendChunked = false;
                s.Seek(debut, SeekOrigin.Begin);
                try { s.CopyTo(rep.OutputStream, 1 << 20); } catch (HttpListenerException) { }
                try { rep.Close(); } catch { }
            }
        }

        // ------------------------------------------------------------------ statut
        static bool PortOuvert(int port)
        {
            try
            {
                using (var t = new TcpClient())
                {
                    var ar = t.BeginConnect("127.0.0.1", port, null, null);
                    bool ok = ar.AsyncWaitHandle.WaitOne(800);
                    if (ok) t.EndConnect(ar);
                    return ok && t.Connected;
                }
            }
            catch { return false; }
        }

        static object Statut()
        {
            bool monde = PortOuvert(C.portMangos), connexion = PortOuvert(C.portRealmd);
            long joueurs = 0, comptes = 0;
            try
            {
                using (var c = new MySqlConnection(ConnStr(C.bddRealmd)))
                {
                    c.Open();
                    comptes = Convert.ToInt64(new MySqlCommand("SELECT COUNT(*) FROM account WHERE username NOT LIKE 'RNDBOT%'", c).ExecuteScalar());
                    // tous les personnages connectés comptent comme joueurs en ligne
                    joueurs = Convert.ToInt64(new MySqlCommand($"SELECT COUNT(*) FROM `{C.bddPersos}`.characters WHERE online = 1", c).ExecuteScalar());
                }
            }
            catch { }
            return new { nom = C.nom, enLigne = monde && connexion, monde, connexion, joueurs, comptes, royaume = C.adresseRoyaume, jeuPret = ManifestePret };
        }

        // ------------------------------------------------------------------ comptes
        static bool TropDEssais(string ip, int max, TimeSpan fenetre)
        {
            var l = Essais.GetOrAdd(ip, _ => new List<DateTime>());
            lock (l)
            {
                l.RemoveAll(d => DateTime.UtcNow - d > fenetre);
                if (l.Count >= max) return true;
                l.Add(DateTime.UtcNow);
                return false;
            }
        }

        static object Erreur(string m) => new { ok = false, message = m };

        static object Inscription(Dictionary<string, object> d, string ip)
        {
            var nom = Champ(d, "nom").ToUpperInvariant();
            var mdp = Champ(d, "motdepasse");
            if (!Regex.IsMatch(nom, "^[A-Z0-9]{3,16}$")) return Erreur("Le nom de compte doit faire 3 à 16 caractères : lettres et chiffres, sans accent ni espace.");
            if (nom.StartsWith("RNDBOT")) return Erreur("Ce nom est réservé.");
            if (mdp.Length < 4 || mdp.Length > 16) return Erreur("Le mot de passe doit faire 4 à 16 caractères.");
            if (!Regex.IsMatch(mdp, "^[\\x21-\\x7E]+$")) return Erreur("Le mot de passe ne peut contenir ni espace ni accent.");
            if (TropDEssais("i" + ip, 10, TimeSpan.FromMinutes(10))) return Erreur("Trop d'essais, réessaie dans quelques minutes.");
            using (var c = new MySqlConnection(ConnStr(C.bddRealmd)))
            {
                c.Open();
                bool local = ip == "127.0.0.1" || ip == "::1";
                if (!local && C.comptesParIp > 0)
                {
                    var cmd = new MySqlCommand("SELECT COUNT(*) FROM portail_inscription WHERE ip = @ip", c);
                    cmd.Parameters.AddWithValue("@ip", ip);
                    if (Convert.ToInt64(cmd.ExecuteScalar()) >= C.comptesParIp) return Erreur("Nombre maximum de comptes atteint pour ta connexion.");
                }
                var ex = new MySqlCommand("SELECT COUNT(*) FROM account WHERE username = @u", c);
                ex.Parameters.AddWithValue("@u", nom);
                if (Convert.ToInt64(ex.ExecuteScalar()) > 0) return Erreur("Ce nom de compte est déjà pris.");
                var sel = Srp6.NouveauSel();
                var v = Srp6.Verifier(nom, mdp, sel);
                var ins = new MySqlCommand("INSERT INTO account (username, gmlevel, v, s, joindate, expansion) VALUES (@u, 0, @v, @s, NOW(), 0)", c);
                ins.Parameters.AddWithValue("@u", nom);
                ins.Parameters.AddWithValue("@v", v);
                ins.Parameters.AddWithValue("@s", sel);
                ins.ExecuteNonQuery();
                long id = ins.LastInsertedId;
                new MySqlCommand("INSERT INTO realmcharacters (realmid, acctid, numchars) SELECT realmlist.id, account.id, 0 FROM realmlist, account LEFT JOIN realmcharacters ON acctid = account.id WHERE acctid IS NULL", c).ExecuteNonQuery();
                var tr = new MySqlCommand("INSERT INTO portail_inscription (id, ip, date) VALUES (@id, @ip, NOW())", c);
                tr.Parameters.AddWithValue("@id", id);
                tr.Parameters.AddWithValue("@ip", ip);
                tr.ExecuteNonQuery();
                Log("Nouveau compte : " + nom + " (" + ip + ")");
                return new { ok = true, nom, message = "Compte créé, bienvenue " + nom + " !" };
            }
        }

        static object Connexion(Dictionary<string, object> d, string ip)
        {
            var nom = Champ(d, "nom").ToUpperInvariant();
            var mdp = Champ(d, "motdepasse");
            if (nom.Length == 0 || mdp.Length == 0) return Erreur("Entre ton nom de compte et ton mot de passe.");
            if (TropDEssais("c" + ip, 15, TimeSpan.FromMinutes(5))) return Erreur("Trop d'essais, réessaie dans quelques minutes.");
            using (var c = new MySqlConnection(ConnStr(C.bddRealmd)))
            {
                c.Open();
                var cmd = new MySqlCommand("SELECT id, v, s, locked FROM account WHERE username = @u", c);
                cmd.Parameters.AddWithValue("@u", nom);
                long id; string v, s; bool verrou;
                using (var r = cmd.ExecuteReader())
                {
                    if (!r.Read()) return Erreur("Nom de compte ou mot de passe incorrect.");
                    id = Convert.ToInt64(r.GetValue(0));
                    v = r.IsDBNull(1) ? "" : r.GetString(1);
                    s = r.IsDBNull(2) ? "" : r.GetString(2);
                    verrou = !r.IsDBNull(3) && Convert.ToInt32(r.GetValue(3)) != 0;
                }
                if (v.Length == 0 || s.Length == 0 || !string.Equals(Srp6.Verifier(nom, mdp, s), v.TrimStart('0'), StringComparison.OrdinalIgnoreCase))
                    return Erreur("Nom de compte ou mot de passe incorrect.");
                if (verrou) return Erreur("Ce compte est verrouillé.");
                var persos = new List<object>();
                try
                {
                    var q = new MySqlCommand($"SELECT name, level, race, class FROM `{C.bddPersos}`.characters WHERE account = @id ORDER BY level DESC LIMIT 10", c);
                    q.Parameters.AddWithValue("@id", id);
                    using (var r = q.ExecuteReader())
                        while (r.Read())
                            persos.Add(new { nom = r.GetString(0), niveau = Convert.ToInt32(r.GetValue(1)), race = Convert.ToInt32(r.GetValue(2)), classe = Convert.ToInt32(r.GetValue(3)) });
                }
                catch { }
                return new { ok = true, nom, persos };
            }
        }
    }
}
