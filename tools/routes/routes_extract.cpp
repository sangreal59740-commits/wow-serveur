// Extracteur des routes et chemins pour le module « routes » du serveur
// Lit les cartes du client (terrain.MPQ, patch.MPQ) : pour chaque morceau de terrain, les textures posées au sol et leur opacité.
// Une case de 2 m est une route si les textures de route ou de chemin y couvrent plus de la moitié du sol.
// Sortie : routes.bin (lu par le serveur), routes_textures.txt (toutes les textures, celles retenues marquées ROUTE).
// Utilisation : routes_extract.exe <dossier Data du client> <fichier routes.bin> [fichier de mots-clés]
#include <StormLib.h>
#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <map>
#include <string>
#include <vector>

static std::vector<HANDLE> archives;

static bool Lire(const std::string& nom, std::vector<uint8_t>& out)
{
    for (HANDLE a : archives)
    {
        HANDLE f;
        if (!SFileOpenFileEx(a, nom.c_str(), 0, &f))
            continue;
        DWORD hi = 0, taille = SFileGetFileSize(f, &hi);
        out.resize(taille);
        DWORD lu = 0;
        bool ok = SFileReadFile(f, out.data(), taille, &lu, nullptr) || lu == taille;
        SFileCloseFile(f);
        if (ok && lu == taille)
            return true;
    }
    return false;
}

static uint32_t U32(const std::vector<uint8_t>& d, size_t o) { uint32_t v; memcpy(&v, &d[o], 4); return v; }

static std::string Minuscules(std::string s) { for (char& c : s) c = (char)tolower((unsigned char)c); return s; }

struct MotsCles { std::vector<std::string> oui, non; };

static bool EstRoute(const std::string& tex, const MotsCles& m)
{
    std::string t = Minuscules(tex);
    for (auto& n : m.non) if (t.find(n) != std::string::npos) return false;
    for (auto& o : m.oui) if (t.find(o) != std::string::npos) return true;
    return false;
}

int main(int argc, char** argv)
{
    if (argc < 3)
    {
        printf("routes_extract.exe <dossier Data du client> <routes.bin> [mots-cles.txt]\n");
        return 1;
    }
    std::string data = argv[1];
    for (const char* nom : { "patch-2.MPQ", "patch.MPQ", "terrain.MPQ" })
    {
        HANDLE h;
        std::string p = data + "\\" + nom;
        if (SFileOpenArchive(p.c_str(), 0, MPQ_OPEN_READ_ONLY, &h))
            archives.push_back(h);
        else
            printf("archive absente : %s\n", p.c_str());
    }
    if (archives.empty())
    {
        printf("aucune archive trouvee dans %s\n", data.c_str());
        return 1;
    }
    MotsCles mots;
    mots.oui = { "road", "path", "cobble", "trail", "street", "pave" };
    mots.non = { "grasspath" };
    if (argc >= 4)
    {
        std::ifstream f(argv[3]);
        std::string l;
        if (f)
        {
            mots.oui.clear(); mots.non.clear();
            while (std::getline(f, l))
            {
                while (!l.empty() && (l.back() == '\r' || l.back() == ' ')) l.pop_back();
                if (l.size() < 2) continue;
                if (l[0] == '+') mots.oui.push_back(Minuscules(l.substr(1)));
                else if (l[0] == '-') mots.non.push_back(Minuscules(l.substr(1)));
            }
        }
    }

    struct Tuile { uint8_t map, tx, ty; std::vector<uint8_t> bits; };
    std::vector<Tuile> tuiles;
    std::map<std::string, std::pair<uint64_t, bool>> textures;      // texture -> (cases où elle domine, route ?)
    const char* cartes[2] = { "Azeroth", "Kalimdor" };
    uint64_t total = 0, casesRoute = 0, lus = 0, rates = 0;

    for (uint8_t m = 0; m < 2; ++m)
    {
        for (int tx = 0; tx < 64; ++tx)
        for (int ty = 0; ty < 64; ++ty)
        {
            char nom[128];
            snprintf(nom, sizeof(nom), "World\\Maps\\%s\\%s_%d_%d.adt", cartes[m], cartes[m], tx, ty);
            std::vector<uint8_t> d;
            if (!Lire(nom, d) || d.size() < 64)
                continue;
            // MTEX et MCIN
            std::vector<std::string> tex;
            std::vector<uint32_t> mcnk(256, 0);
            size_t o = 0;
            while (o + 8 <= d.size())
            {
                uint32_t magic = U32(d, o), taille = U32(d, o + 4);
                if (o + 8 + taille > d.size()) break;
                if (magic == 0x4D544558)                      // 'MTEX'
                {
                    size_t p = o + 8, fin = o + 8 + taille;
                    while (p < fin)
                    {
                        std::string s((const char*)&d[p]);
                        p += s.size() + 1;
                        if (!s.empty()) tex.push_back(s);
                    }
                }
                else if (magic == 0x4D43494E)                 // 'MCIN'
                {
                    for (int i = 0; i < 256; ++i) mcnk[i] = U32(d, o + 8 + i * 16);
                }
                if (magic == 0x4D434E4B) break;               // 'MCNK' : fin des en-têtes
                o += 8 + taille;
            }
            std::vector<bool> route(tex.size());
            for (size_t i = 0; i < tex.size(); ++i) route[i] = EstRoute(tex[i], mots);

            Tuile t;
            t.map = m; t.tx = (uint8_t)tx; t.ty = (uint8_t)ty;
            t.bits.assign(256 * 256 / 8, 0);
            bool aRoute = false;
            for (int c = 0; c < 256; ++c)
            {
                uint32_t off = mcnk[c];
                if (!off || off + 8 + 128 > d.size() || U32(d, off) != 0x4D434E4B)
                    continue;
                size_t h = off + 8;
                uint32_t ix = U32(d, h + 4), iy = U32(d, h + 8), nLayers = U32(d, h + 12);
                uint32_t ofsLayer = U32(d, h + 28), ofsAlpha = U32(d, h + 36);
                if (ix > 15 || iy > 15 || nLayers == 0 || nLayers > 4) continue;
                size_t ly = off + ofsLayer, al = off + ofsAlpha;
                if (ly + 8 <= d.size() && U32(d, ly) != 0x4D434C59) { ly += 8; al += 8; }     // décalage selon la version
                if (ly + 8 + nLayers * 16 > d.size() || U32(d, ly) != 0x4D434C59) { ++rates; continue; }     // 'MCLY'
                ++lus;
                bool alphaOk = al + 8 <= d.size() && U32(d, al) == 0x4D43414C;               // 'MCAL'
                // poids de chaque couche par texel (64 x 64), mélange de haut en bas
                static float poids[4][64][64];
                uint32_t texId[4];
                for (uint32_t l = 0; l < nLayers; ++l)
                {
                    texId[l] = U32(d, ly + 8 + l * 16);
                    uint32_t flags = U32(d, ly + 8 + l * 16 + 4), ofs = U32(d, ly + 8 + l * 16 + 8);
                    for (int r = 0; r < 64; ++r)
                    for (int k = 0; k < 64; ++k)
                    {
                        float a = 1.0f;
                        if (l > 0)
                        {
                            a = 0.0f;
                            size_t b = al + 8 + ofs + r * 32 + k / 2;
                            if (alphaOk && (flags & 0x100) && b < d.size())
                                a = ((k & 1) ? (d[b] >> 4) : (d[b] & 0x0F)) / 15.0f;
                            for (uint32_t p = 0; p < l; ++p) poids[p][r][k] *= (1.0f - a);
                        }
                        poids[l][r][k] = a;
                    }
                }
                // cases de 4 x 4 texels (environ 2 m)
                for (int cr = 0; cr < 16; ++cr)
                for (int cc = 0; cc < 16; ++cc)
                {
                    float w[4] = { 0, 0, 0, 0 }, wr = 0;
                    for (int r = cr * 4; r < cr * 4 + 4; ++r)
                    for (int k = cc * 4; k < cc * 4 + 4; ++k)
                    for (uint32_t l = 0; l < nLayers; ++l)
                    {
                        w[l] += poids[l][r][k];
                        if (texId[l] < route.size() && route[texId[l]]) wr += poids[l][r][k];
                    }
                    uint32_t dom = 0;
                    for (uint32_t l = 1; l < nLayers; ++l) if (w[l] > w[dom]) dom = l;
                    if (texId[dom] < tex.size()) textures[tex[texId[dom]]].first++;
                    ++total;
                    if (wr >= 8.0f)                                     // plus de la moitié des 16 texels
                    {
                        uint32_t row = iy * 16 + cr, col = ix * 16 + cc, bit = row * 256 + col;
                        t.bits[bit >> 3] |= uint8_t(1 << (bit & 7));
                        aRoute = true;
                        ++casesRoute;
                    }
                }
            }
            for (size_t i = 0; i < tex.size(); ++i) textures[tex[i]].second = route[i];
            if (aRoute)
                tuiles.push_back(std::move(t));
        }
        printf("%s : %zu tuiles avec des routes\n", cartes[m], tuiles.size());
    }

    FILE* f = fopen(argv[2], "wb");
    if (!f) { printf("ecriture impossible : %s\n", argv[2]); return 1; }
    uint32_t entete[3] = { 0x54554F52, 1, (uint32_t)tuiles.size() };     // 'ROUT', version, nombre de tuiles
    fwrite(entete, 4, 3, f);
    for (auto& t : tuiles)
    {
        uint8_t e[4] = { t.map, t.tx, t.ty, 0 };
        fwrite(e, 1, 4, f);
        fwrite(t.bits.data(), 1, t.bits.size(), f);
    }
    fclose(f);

    std::string liste = argv[2];
    size_t s = liste.find_last_of("\\/");
    liste = (s == std::string::npos ? std::string() : liste.substr(0, s + 1)) + "routes_textures.txt";
    FILE* g = fopen(liste.c_str(), "w");
    if (g)
    {
        std::vector<std::pair<uint64_t, std::string>> tri;
        for (auto& kv : textures) tri.push_back({ kv.second.first, kv.first });
        std::sort(tri.rbegin(), tri.rend());
        for (auto& p : tri)
            fprintf(g, "%s\t%llu\t%s\n", textures[p.second].second ? "ROUTE" : "-", (unsigned long long)p.first, p.second.c_str());
        fclose(g);
    }
    printf("cases de terrain : %llu, dont routes : %llu (%.2f %%)\n", (unsigned long long)total, (unsigned long long)casesRoute,
           total ? 100.0 * casesRoute / total : 0.0);
    printf("morceaux de terrain lus : %llu, illisibles : %llu\n", (unsigned long long)lus, (unsigned long long)rates);
    printf("termine : %s\n", argv[2]);
    for (HANDLE a : archives) SFileCloseArchive(a);
    return 0;
}
