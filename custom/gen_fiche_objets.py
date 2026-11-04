# Statistiques des objets équipables (base du serveur) pour la comparaison d'objets de l'addon FicheStats
import subprocess
def q(sql):
    r = subprocess.run(['mysql', '-N', '-B', 'classicmangos', '-e', sql], capture_output=True, text=True, check=True)
    return [l.split('\t') for l in r.stdout.splitlines()]
AURA = {13: 'sd', 135: 'so', 52: 'cc', 57: 'cs', 54: 'tm', 55: 'ts', 85: 'mp', 99: 'pa', 124: 'pad', 49: 'es', 47: 'par', 51: 'bl',
        158: 'vb', 161: 'rv'}
SP = {}
cols = ",".join("Effect%d,EffectApplyAuraName%d,EffectBasePoints%d,EffectMiscValue%d" % (i, i, i, i) for i in (1, 2, 3))
for r in q("SELECT Id," + cols + " FROM spell_template"):
    sid = int(r[0]); eff = []
    for k in range(3):
        e, a, bp, mv = (int(x) for x in r[1 + 4 * k:5 + 4 * k])
        if e != 6:
            continue
        v = bp + 1
        if a == 13 and not (mv & 126):          # dégâts physiques : ignorés
            continue
        if a == 85 and mv != 0:
            continue
        if a == 30:
            if mv == 95: eff.append(('def', v))
            continue
        if a in AURA:
            eff.append((AURA[a], v))
    if eff:
        SP[sid] = eff
STAT = {1: 'v', 0: 'm', 3: 'a', 4: 's', 5: 'i', 6: 'p', 7: 'e'}
RES = ['rsa', 'rfeu', 'rnat', 'rgiv', 'romb', 'rarc']
sel = ("entry,InventoryType," + ",".join("stat_type%d,stat_value%d" % (i, i) for i in range(1, 11)) + ",armor,holy_res,fire_res,nature_res,frost_res,shadow_res,arcane_res,"
       "dmg_min1,dmg_max1,delay,block," + ",".join("spellid_%d,spelltrigger_%d" % (i, i) for i in range(1, 6)))
out = []
for r in q("SELECT " + sel + " FROM item_template WHERE InventoryType > 0 AND InventoryType NOT IN (18, 24, 27, 28) AND class IN (2, 4)"):
    r = [int(float(x)) for x in r]
    d = {}
    for i in range(10):
        t, v = r[2 + 2 * i], r[3 + 2 * i]
        if v and t in STAT:
            d[STAT[t]] = d.get(STAT[t], 0) + v
    o = 22
    if r[o]: d['ar'] = r[o]
    for k in range(6):
        if r[o + 1 + k]: d[RES[k]] = r[o + 1 + k]
    dmin, dmax, delay, block = r[o + 7], r[o + 8], r[o + 9], r[o + 10]
    if dmax and delay:
        d['dps'] = round((dmin + dmax) / 2.0 / (delay / 1000.0), 1)
    if block: d['vb'] = d.get('vb', 0) + block
    for i in range(5):
        sid, trig = r[o + 11 + 2 * i], r[o + 12 + 2 * i]
        if sid and trig == 1 and sid in SP:
            for k, v in SP[sid]:
                d[k] = d.get(k, 0) + v
    if d:
        out.append("%d=%d;%s" % (r[0], r[1], ",".join("%s:%s" % (k, ("%g" % v)) for k, v in sorted(d.items()))))
# blocs de lignes pour limiter la taille des chaînes
L = ["-- Statistiques des objets (généré depuis la base du serveur par gen_fiche_objets.py)", "FicheStats_Objets = {"]
bloc = []
for x in out:
    bloc.append(x)
    if len(bloc) >= 200:
        L.append('"' + "|".join(bloc) + '",'); bloc = []
if bloc: L.append('"' + "|".join(bloc) + '",')
L.append("}")
open('/home/claude/wow/addons/FicheStats/Objets.lua', 'w', encoding='utf-8').write("\n".join(L) + "\n")
print(len(out), 'objets', len(SP), 'sorts')
