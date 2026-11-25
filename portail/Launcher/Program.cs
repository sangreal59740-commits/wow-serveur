// Launcher : fenêtre WebView2 qui affiche la page /launcher du portail, installe et met à jour le jeu, puis le lance.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Reflection;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Web.Script.Serialization;
using System.Windows.Forms;
using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.WinForms;

namespace Launcher
{
    static class Program
    {
        public static string Bin;
        public static string Donnees;

        [STAThread]
        static void Main()
        {
            Donnees = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "LauncherWoW");
            Bin = Path.Combine(Donnees, "bin");
            Directory.CreateDirectory(Bin);
            foreach (var n in new[] { "Microsoft.Web.WebView2.Core.dll", "Microsoft.Web.WebView2.WinForms.dll", "WebView2Loader.dll" })
                Extraire(n);
            AppDomain.CurrentDomain.AssemblyResolve += (s, e) =>
            {
                var f = Path.Combine(Bin, new AssemblyName(e.Name).Name + ".dll");
                return File.Exists(f) ? Assembly.LoadFrom(f) : null;
            };
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Demarrer();
        }

        static void Extraire(string nom)
        {
            var dest = Path.Combine(Bin, nom);
            using (var s = Assembly.GetExecutingAssembly().GetManifestResourceStream(nom))
            {
                if (s == null) return;
                if (File.Exists(dest) && new FileInfo(dest).Length == s.Length) return;
                try { using (var f = File.Create(dest)) s.CopyTo(f); } catch { }
            }
        }

        [MethodImpl(MethodImplOptions.NoInlining)]
        static void Demarrer() => Application.Run(new Fenetre());
    }

    class Reglages
    {
        public string dossier = "";
        public string compte = "";
    }

    class Fenetre : Form
    {
        [DllImport("user32.dll")] static extern bool ReleaseCapture();
        [DllImport("user32.dll")] static extern IntPtr SendMessage(IntPtr h, int msg, int w, int l);

        readonly WebView2 web = new WebView2();
        readonly JavaScriptSerializer json = new JavaScriptSerializer { MaxJsonLength = int.MaxValue };
        readonly HttpClient http = new HttpClient { Timeout = Timeout.InfiniteTimeSpan };
        readonly string portail;
        Reglages reglages = new Reglages();
        string fichierReglages;
        CancellationTokenSource annulation;
        bool occupe;

        public Fenetre()
        {
            portail = LireAdresse();
            fichierReglages = Path.Combine(Program.Donnees, "launcher.json");
            try { if (File.Exists(fichierReglages)) reglages = json.Deserialize<Reglages>(File.ReadAllText(fichierReglages)) ?? new Reglages(); } catch { }
            Text = "Launcher";
            try { Icon = Icon.ExtractAssociatedIcon(Application.ExecutablePath); } catch { }
            FormBorderStyle = FormBorderStyle.None;
            StartPosition = FormStartPosition.CenterScreen;
            ClientSize = new Size(1180, 700);
            MinimumSize = new Size(960, 600);
            BackColor = Color.FromArgb(10, 11, 16);
            web.Dock = DockStyle.Fill;
            web.DefaultBackgroundColor = Color.FromArgb(10, 11, 16);
            Controls.Add(web);
            Load += async (s, e) => await Init();
        }

        // adresse du portail : écrite par le portail à la fin de l'exe téléchargé, sinon portail.txt, sinon local
        static string LireAdresse()
        {
            try
            {
                var exe = Application.ExecutablePath;
                using (var f = File.OpenRead(exe))
                {
                    int n = (int)Math.Min(2048, f.Length);
                    f.Seek(-n, SeekOrigin.End);
                    var b = new byte[n];
                    f.Read(b, 0, n);
                    var t = Encoding.UTF8.GetString(b);
                    int i = t.LastIndexOf("##PORTAIL##", StringComparison.Ordinal), j = t.LastIndexOf("##FIN##", StringComparison.Ordinal);
                    if (i >= 0 && j > i) return t.Substring(i + 11, j - i - 11).TrimEnd('/');
                }
                var txt = Path.Combine(Path.GetDirectoryName(exe), "portail.txt");
                if (File.Exists(txt)) return File.ReadAllText(txt).Trim().TrimEnd('/');
            }
            catch { }
            return "http://localhost:8080";
        }

        async Task Init()
        {
            try
            {
                CoreWebView2Environment.SetLoaderDllFolderPath(Program.Bin);
                var env = await CoreWebView2Environment.CreateAsync(null, Path.Combine(Program.Donnees, "WebView2"));
                await web.EnsureCoreWebView2Async(env);
            }
            catch (WebView2RuntimeNotFoundException)
            {
                if (MessageBox.Show("Il manque le composant Microsoft Edge WebView2.\nL'installer maintenant ?", "Launcher", MessageBoxButtons.YesNo) == DialogResult.Yes)
                    Process.Start("https://go.microsoft.com/fwlink/p/?LinkId=2124703");
                Close();
                return;
            }
            catch (Exception ex)
            {
                MessageBox.Show("Le launcher n'a pas pu démarrer : " + ex.Message, "Launcher");
                Close();
                return;
            }
            var st = web.CoreWebView2.Settings;
            st.AreDefaultContextMenusEnabled = false;
            st.IsZoomControlEnabled = false;
            st.AreDevToolsEnabled = true;
            st.IsStatusBarEnabled = false;
            web.CoreWebView2.WebMessageReceived += Message;
            web.CoreWebView2.NewWindowRequested += (s, e) => { e.Handled = true; Ouvrir(e.Uri); };
            web.CoreWebView2.NavigationCompleted += (s, e) =>
            {
                if (!e.IsSuccess && !web.CoreWebView2.Source.StartsWith("data:"))
                    web.CoreWebView2.NavigateToString(PageHorsLigne());
            };
            web.CoreWebView2.Navigate(portail + "/launcher");
        }

        string PageHorsLigne() => @"<!doctype html><html><head><meta charset='utf-8'><style>
body{margin:0;height:100vh;display:flex;align-items:center;justify-content:center;background:radial-gradient(circle at 50% 30%,#1c2033,#0a0b10);color:#e8e2d0;font-family:Segoe UI,sans-serif;user-select:none}
.b{text-align:center}.t{font-size:28px;letter-spacing:2px;color:#d9b36c;margin-bottom:10px}p{color:#9aa0b4}
button{margin:8px;padding:12px 26px;border:1px solid #d9b36c;background:transparent;color:#d9b36c;font-size:15px;cursor:pointer;border-radius:4px}
button:hover{background:#d9b36c22}.x{position:fixed;top:10px;right:14px;border:none;font-size:20px;color:#9aa0b4}
.top{position:fixed;top:0;left:0;right:60px;height:40px}</style></head><body>
<div class='top' onmousedown=""chrome.webview.postMessage({cmd:'fenetre',action:'deplacer'})""></div>
<button class='x' onclick=""chrome.webview.postMessage({cmd:'fenetre',action:'fermer'})"">✕</button>
<div class='b'><div class='t'>Serveur injoignable</div><p>Impossible de joindre " + portail + @"</p><p>Le serveur est peut-être éteint ou en maintenance.</p>
<button onclick=""chrome.webview.postMessage({cmd:'recharger'})"">Réessayer</button></div></body></html>";

        void Envoyer(object o)
        {
            var s = json.Serialize(o);
            if (InvokeRequired) BeginInvoke(new Action(() => { try { web.CoreWebView2?.PostWebMessageAsJson(s); } catch { } }));
            else try { web.CoreWebView2?.PostWebMessageAsJson(s); } catch { }
        }

        void Sauver()
        {
            try { Directory.CreateDirectory(Program.Donnees); File.WriteAllText(fichierReglages, json.Serialize(reglages)); } catch { }
        }

        static void Ouvrir(string url)
        {
            if (url != null && (url.StartsWith("http://") || url.StartsWith("https://")))
                try { Process.Start(new ProcessStartInfo(url) { UseShellExecute = true }); } catch { }
        }

        string DossierParDefaut(string nom)
        {
            var propre = new string((nom ?? "Jeu").Where(c => char.IsLetterOrDigit(c) || c == ' ').ToArray()).Trim();
            if (propre.Length == 0) propre = "Jeu";
            return Path.Combine(Path.GetPathRoot(Environment.SystemDirectory) ?? @"C:\", "Jeux", propre);
        }

        async void Message(object sender, CoreWebView2WebMessageReceivedEventArgs e)
        {
            if (!e.Source.StartsWith(portail, StringComparison.OrdinalIgnoreCase) && !e.Source.StartsWith("data:")) return;
            Dictionary<string, object> m;
            try { m = json.Deserialize<Dictionary<string, object>>(e.WebMessageAsJson); } catch { return; }
            string cmd = m.TryGetValue("cmd", out var c) ? c as string : "";
            string Arg(string k) => m.TryGetValue(k, out var v) && v != null ? v.ToString() : "";
            switch (cmd)
            {
                case "fenetre":
                    var a = Arg("action");
                    if (a == "fermer") Close();
                    else if (a == "reduire") WindowState = FormWindowState.Minimized;
                    else if (a == "deplacer") { ReleaseCapture(); SendMessage(Handle, 0xA1, 2, 0); }
                    break;
                case "recharger":
                    web.CoreWebView2.Navigate(portail + "/launcher");
                    break;
                case "ouvrir":
                    Ouvrir(Arg("url"));
                    break;
                case "etat":
                    if (string.IsNullOrEmpty(reglages.dossier)) reglages.dossier = DossierParDefaut(Arg("nom"));
                    EnvoyerEtat();
                    break;
                case "dossier":
                    if (occupe) break;
                    using (var d = new FolderBrowserDialog { Description = "Dossier d'installation du jeu", SelectedPath = Directory.Exists(reglages.dossier) ? reglages.dossier : "" })
                        if (d.ShowDialog(this) == DialogResult.OK)
                        {
                            reglages.dossier = d.SelectedPath;
                            Sauver();
                        }
                    EnvoyerEtat();
                    break;
                case "compte":
                    reglages.compte = Arg("nom");
                    Sauver();
                    break;
                case "verifier":
                case "installer":
                    if (occupe) break;
                    occupe = true;
                    annulation = new CancellationTokenSource();
                    try { await Synchroniser(cmd == "installer", annulation.Token); }
                    catch (OperationCanceledException) { Envoyer(new { type = "annule" }); }
                    catch (Exception ex) { Envoyer(new { type = "erreur", message = ex.Message }); }
                    finally { occupe = false; }
                    break;
                case "annuler":
                    annulation?.Cancel();
                    break;
                case "jouer":
                    Jouer(Arg("compte"));
                    break;
            }
        }

        void EnvoyerEtat()
        {
            bool installe = File.Exists(Path.Combine(reglages.dossier, "WoW_classes.exe"));
            Envoyer(new { type = "etat", dossier = reglages.dossier, compte = reglages.compte, installe, version = Application.ProductVersion });
        }

        class Distant { public string chemin; public long taille; public string md5; }
        class Manifeste { public bool pret; public string royaume; public string exe; public List<Distant> fichiers; }
        Manifeste dernier;

        // cache local des empreintes : chemin -> taille|date|md5
        Dictionary<string, string> LireCache(string dossier)
        {
            try { return json.Deserialize<Dictionary<string, string>>(File.ReadAllText(Path.Combine(dossier, "launcher_cache.json"))) ?? new Dictionary<string, string>(); }
            catch { return new Dictionary<string, string>(); }
        }

        static string Md5(string f)
        {
            using (var md5 = MD5.Create())
            using (var s = new FileStream(f, FileMode.Open, FileAccess.Read, FileShare.Read, 1 << 20))
                return BitConverter.ToString(md5.ComputeHash(s)).Replace("-", "").ToLowerInvariant();
        }

        async Task Synchroniser(bool telecharger, CancellationToken ct)
        {
            var dossier = reglages.dossier;
            Envoyer(new { type = "progres", etape = "Récupération de la liste des fichiers…", fait = 0L, total = 0L });
            var txt = await http.GetStringAsync(portail + "/api/manifeste");
            dernier = json.Deserialize<Manifeste>(txt);
            if (dernier == null || !dernier.pret || dernier.fichiers == null || dernier.fichiers.Count == 0)
                throw new Exception("Le serveur prépare encore les fichiers du jeu, réessaie dans une minute.");
            Directory.CreateDirectory(dossier);
            var cache = LireCache(dossier);
            var manquants = new List<Distant>();
            long totalVerif = dernier.fichiers.Sum(f => f.taille), faitVerif = 0;
            var chrono = Stopwatch.StartNew();
            await Task.Run(() =>
            {
                foreach (var f in dernier.fichiers)
                {
                    ct.ThrowIfCancellationRequested();
                    var local = Path.Combine(dossier, f.chemin.Replace('/', '\\'));
                    var fi = new FileInfo(local);
                    bool ok = false;
                    if (fi.Exists && fi.Length == f.taille)
                    {
                        var cle = fi.Length + "|" + fi.LastWriteTimeUtc.Ticks;
                        string md5;
                        if (cache.TryGetValue(f.chemin, out var v) && v.StartsWith(cle + "|")) md5 = v.Substring(cle.Length + 1);
                        else { md5 = Md5(local); cache[f.chemin] = cle + "|" + md5; }
                        ok = md5 == f.md5;
                    }
                    if (!ok) manquants.Add(f);
                    faitVerif += f.taille;
                    if (chrono.ElapsedMilliseconds > 150)
                    {
                        chrono.Restart();
                        Envoyer(new { type = "progres", etape = "Vérification des fichiers…", fait = faitVerif, total = totalVerif });
                    }
                }
            }, ct);
            try { File.WriteAllText(Path.Combine(dossier, "launcher_cache.json"), json.Serialize(cache)); } catch { }
            long aTelecharger = manquants.Sum(f => f.taille);
            Envoyer(new { type = "verif", fichiers = manquants.Count, octets = aTelecharger, total = totalVerif });
            if (!telecharger || manquants.Count == 0)
            {
                if (manquants.Count == 0) Envoyer(new { type = "fini" });
                return;
            }

            long fait = 0;
            var vitesse = Stopwatch.StartNew();
            long depuis = 0;
            double debit = 0;
            foreach (var f in manquants)
            {
                ct.ThrowIfCancellationRequested();
                var local = Path.Combine(dossier, f.chemin.Replace('/', '\\'));
                Directory.CreateDirectory(Path.GetDirectoryName(local));
                var part = local + ".part";
                long deja = File.Exists(part) ? new FileInfo(part).Length : 0;
                if (deja > f.taille) { File.Delete(part); deja = 0; }
                var url = portail + "/client/" + string.Join("/", f.chemin.Split('/').Select(Uri.EscapeDataString));
                using (var req = new HttpRequestMessage(HttpMethod.Get, url))
                {
                    if (deja > 0) req.Headers.Range = new System.Net.Http.Headers.RangeHeaderValue(deja, null);
                    using (var rep = await http.SendAsync(req, HttpCompletionOption.ResponseHeadersRead, ct))
                    {
                        rep.EnsureSuccessStatusCode();
                        if (deja > 0 && rep.StatusCode != System.Net.HttpStatusCode.PartialContent) deja = 0;
                        fait += deja;
                        using (var src = await rep.Content.ReadAsStreamAsync())
                        using (var dst = new FileStream(part, deja > 0 ? FileMode.Append : FileMode.Create, FileAccess.Write, FileShare.None, 1 << 20))
                        {
                            var buf = new byte[1 << 18];
                            int n;
                            while ((n = await src.ReadAsync(buf, 0, buf.Length, ct)) > 0)
                            {
                                await dst.WriteAsync(buf, 0, n, ct);
                                fait += n;
                                if (vitesse.ElapsedMilliseconds > 250)
                                {
                                    debit = (fait - depuis) * 1000.0 / vitesse.ElapsedMilliseconds;
                                    depuis = fait;
                                    vitesse.Restart();
                                    Envoyer(new { type = "progres", etape = "Téléchargement : " + f.chemin, fait, total = aTelecharger, debit = (long)debit });
                                }
                            }
                        }
                    }
                }
                var md5 = await Task.Run(() => Md5(part), ct);
                if (md5 != f.md5)
                {
                    File.Delete(part);
                    throw new Exception("Fichier corrompu pendant le téléchargement (" + f.chemin + "), relance la mise à jour.");
                }
                if (File.Exists(local)) File.Delete(local);
                File.Move(part, local);
                var fi = new FileInfo(local);
                cache[f.chemin] = fi.Length + "|" + fi.LastWriteTimeUtc.Ticks + "|" + md5;
            }
            try { File.WriteAllText(Path.Combine(dossier, "launcher_cache.json"), json.Serialize(cache)); } catch { }
            Envoyer(new { type = "fini" });
            EnvoyerEtat();
        }

        void Jouer(string compte)
        {
            var dossier = reglages.dossier;
            var exe = Path.Combine(dossier, dernier?.exe ?? "WoW_classes.exe");
            if (!File.Exists(exe)) { Envoyer(new { type = "erreur", message = "Jeu introuvable dans " + dossier + ", lance l'installation." }); return; }
            try
            {
                var royaume = dernier?.royaume;
                if (string.IsNullOrEmpty(royaume))
                {
                    var st = json.Deserialize<Dictionary<string, object>>(http.GetStringAsync(portail + "/api/statut").Result);
                    royaume = st.TryGetValue("royaume", out var r) ? r as string : null;
                }
                if (string.IsNullOrEmpty(royaume)) royaume = new Uri(portail).Host;
                File.WriteAllText(Path.Combine(dossier, "realmlist.wtf"), "set realmlist " + royaume + "\r\n");
                if (!string.IsNullOrEmpty(compte))
                {
                    var wtf = Path.Combine(dossier, "WTF");
                    Directory.CreateDirectory(wtf);
                    var cfg = Path.Combine(wtf, "Config.wtf");
                    var lignes = File.Exists(cfg) ? File.ReadAllLines(cfg).ToList() : new List<string>();
                    lignes.RemoveAll(l => l.StartsWith("SET accountName ", StringComparison.OrdinalIgnoreCase));
                    lignes.Add("SET accountName \"" + compte.ToUpperInvariant() + "\"");
                    File.WriteAllLines(cfg, lignes);
                }
                Process.Start(new ProcessStartInfo(exe) { WorkingDirectory = dossier, UseShellExecute = true });
                Envoyer(new { type = "lance" });
                var t = new System.Windows.Forms.Timer { Interval = 2500 };
                t.Tick += (s, e) => { t.Stop(); WindowState = FormWindowState.Minimized; };
                t.Start();
            }
            catch (Exception ex) { Envoyer(new { type = "erreur", message = "Lancement impossible : " + ex.Message }); }
        }
    }
}
