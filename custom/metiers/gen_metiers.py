# Génère les recettes bleues renforcées des métiers (6 métiers x 8 paliers x 4 rôles = 192 recettes).
# Sorties :
#   metiers.sql        base world : objets, sorts (fabrication, apprentissage, potions), maîtres de métier
#   metiers_rows.json  lignes à ajouter aux DBC (Spell, SkillLineAbility, SpellItemEnchantment)
import sys, json, math, subprocess
sys.path.insert(0, '/home/claude/wow/fr')
sys.path.insert(0, '/home/claude/wow/donjons')
from dbc import DBC

OUT = '/home/claude/wow/metiers/'

def q(sql):
    r = subprocess.run(['mysql', '-N', '-B', 'classicmangos', '-e', sql], capture_output=True, text=True, check=True)
    return [l.split('\t') for l in r.stdout.splitlines()]

def esc(s):
    return s.replace('\\', '\\\\').replace("'", "\\'")

spell = DBC('/home/claude/wow/fr/dbc_en/Spell.dbc')
SPR = {r[0]: r for r in spell.rows}
sla = DBC('/home/claude/wow/dbc_extra/SkillLineAbility.dbc')
ench = DBC('/home/claude/wow/fr/dbc_en/SpellItemEnchantment.dbc')

# sorts d'équipement existants (valeurs après l'étape 1), repris du générateur des donjons
CH = json.load(open('/home/claude/wow/stats/changes.json'))['spells']
def s32(x): return x - (1 << 32) if x >= 1 << 31 else x
SP = {}
FAM = {'sp': 'Increase Spell Dam ', 'heal': 'Increase Healing ', 'ap': 'Attack Power ',
       'crit': 'Increased Critical ', 'hit': 'Increased Hit Chance ', 'sta': 'Increased Stamina '}
for r in spell.rows:
    n = spell.str(r[120])
    for k, pre in FAM.items():
        if not n.startswith(pre) or (k == 'crit' and n.startswith('Increased Critical Spell')):
            continue
        effs = [e for e in range(3) if r[61 + e] == 6]
        if not effs:
            continue
        e = effs[0]
        c = CH.get(str(r[0]))
        v = c[str(e)][1] + 1 if (c and str(e) in c) else s32(r[76 + e]) + (1 if r[64 + e] >= 1 else 0)
        if v > 0:
            SP.setdefault(k, []).append((v, r[0]))
def pick(fam, target):
    v, i = min(SP[fam], key=lambda x: (abs(x[0] - target), x[1]))
    return i, v

ITEMS = {}
for row in q("select entry, name, Quality, class, subclass, InventoryType, ItemLevel, armor, Flags from bak_q1_item_template"):
    e, n, ql, cl, sc, it, il, ar, fl = row
    ITEMS[int(e)] = dict(name=n, q=int(ql), cl=int(cl), sc=int(sc), it=int(it), il=int(il), armor=int(ar), flags=int(fl))

# ---------------------------------------------------------------- paliers
LEVELS = [10, 20, 30, 35, 40, 45, 50, 55]
RANGS = ["du novice", "de l'apprenti", "du compagnon", "de l'expert", "de l'artisan", "du maître",
         "du grand maître", "du champion"]
def skill_of(L): return 5 * L
# pièce d'armure fabriquée à chaque palier (même ordre pour tous les rôles)
ARMSLOT = ['wrist', 'waist', 'feet', 'hands', 'shoulder', 'legs', 'head', 'chest']
INVTYPE = {'head': 1, 'shoulder': 3, 'chest': 5, 'waist': 6, 'legs': 7, 'feet': 8, 'wrist': 9, 'hands': 10}
SLOTMOD = {'head': 1.0, 'shoulder': 0.77, 'chest': 1.0, 'waist': 0.77, 'legs': 1.0, 'feet': 0.77, 'wrist': 0.56,
           'hands': 0.77, 'cloak': 0.56, 'trinket': 0.7}
NOUNS = {
    1: {'head': 'Capuche', 'shoulder': 'Mantelet', 'chest': 'Robe', 'waist': 'Ceinture', 'legs': 'Jambières',
        'feet': 'Sandales', 'wrist': 'Brassards', 'hands': 'Gants'},
    2: {'head': 'Coiffe', 'shoulder': 'Épaulières', 'chest': 'Tunique', 'waist': 'Ceinturon', 'legs': 'Pantalon',
        'feet': 'Bottes', 'wrist': 'Brassards', 'hands': 'Gants'},
    3: {'head': 'Camail', 'shoulder': 'Spallières', 'chest': 'Haubert', 'waist': 'Ceinture', 'legs': 'Jambières',
        'feet': 'Bottes', 'wrist': 'Manchettes', 'hands': 'Gantelets'},
    4: {'head': 'Heaume', 'shoulder': 'Épaulières', 'chest': 'Cuirasse', 'waist': 'Ceinture', 'legs': 'Cuissards',
        'feet': 'Solerets', 'wrist': 'Brassards', 'hands': 'Gantelets'},
}
STATID = {'agi': 3, 'str': 4, 'int': 5, 'spi': 6, 'sta': 7}
COST = {'sp': 0.86, 'heal': 0.45, 'ap': 0.5}
D_TANK = {'sta': .50, 'str': .30, 'agi': .20}
D_SOINS = {'int': .35, 'spi': .20, 'sta': .20, 'heal': .25}
D_FORCE = {'str': .45, 'sta': .30, 'agi': .10, 'ap': .15}
D_AGI = {'agi': .45, 'sta': .30, 'str': .10, 'ap': .15}
D_CHASSE = {'agi': .40, 'sta': .30, 'int': .15, 'ap': .15}
D_SORTS_M = {'int': .35, 'sta': .30, 'str': .10, 'sp': .25}
D_SORTS = {'int': .40, 'sta': .25, 'spi': .10, 'sp': .25}
D_CAPE = {'agi': .35, 'sta': .40, 'str': .25}
D_BIJOU = {'sta': .60, 'str': .20, 'agi': .20}

RENFORT = 1.4     # bleu renforcé
ETAPE1 = 1.5      # tous les objets du monde ont déjà +50 %

def budget(ilvl, slotmod):
    return (ilvl - 1.84) / 1.6 * slotmod * 1.25     # bleu normal

def make_stats(ilvl, slotmod, dist):
    P = budget(ilvl, slotmod) * RENFORT * ETAPE1
    stats, bonus = {}, {}
    for k, f in dist.items():
        if k in STATID:
            stats[k] = max(1, round(P * f))
        else:
            bonus[k] = P * f / COST[k]
    return stats, bonus

def dps(kind, ilvl):
    return {'1h': 0.6 * ilvl + 2, '2h': 0.78 * ilvl + 2.5, 'gun': 0.45 * ilvl + 2}[kind] * ETAPE1 * 1.15

# ---------------------------------------------------------------- recettes existantes (réactifs, outils, apparence)
RECIPES = {}   # métier -> [(compétence jaune, sort, objet créé)]
for r in sla.rows:
    s = SPR.get(r[2])
    if not s or s[61] not in (24, 53) or r[1] not in (164, 165, 171, 197, 202, 333):
        continue
    if 'zz' in spell.str(s[120]).lower() or 'test' in spell.str(s[120]).lower():
        continue
    RECIPES.setdefault(r[1], []).append((r[11], s[0], s[103] if s[61] == 24 else 0))

# recettes enseignées par un maître de métier (pas de recette rare ni de réputation)
TAUGHT = set()
_tr = set(int(x[0]) for x in q("select distinct spell from npc_trainer"))
for r in spell.rows:
    if r[0] in _tr and r[61] == 36:
        TAUGHT.add(r[109])
for r in sla.rows:
    if r[9]:
        TAUGHT.add(r[2])

BLACKLIST = ('Souldarite', 'Bloodvine', 'Mojo', 'Primal Bat', 'Primal Tiger', 'Fiery Core', 'Lava Core',
             'Core Leather', 'Blood of the Mountain', 'Sulfuron', 'Elementium', 'Ichor of Undeath', 'Nexus Crystal',
             'Zulian', 'Hakkari', 'Guardian Stone', 'Dark Rune', 'Coin', 'Onyxia', 'Scarab', 'Idol')
def reagents_ok(item):
    it = ITEMS.get(item)
    return it and not any(b in it['name'] for b in BLACKLIST) and (it['cl'] in (5, 7, 15) or (it['cl'] == 0 and 'Vial' in it['name'])) and it['q'] <= 3

def near_recipes(prof, S, filt, n=2):
    lst = [x for x in RECIPES[prof] if filt(x) and abs(x[0] - (S + 20)) <= 30 and ITEMS.get(x[2], {'q': 0})['q'] <= 3 and all(reagents_ok(SPR[x[1]][42 + i]) for i in range(8) if SPR[x[1]][42 + i])]
    lst.sort(key=lambda x: (abs(x[0] - (S + 20)) // 10, x[1] not in TAUGHT, abs(x[0] - (S + 20)), x[1]))
    return lst[:n]

def merge_reagents(recs, mult):
    tot = {}
    for _, sid, _ in recs:
        s = SPR[sid]
        for i in range(8):
            if s[42 + i]:
                tot[s[42 + i]] = max(tot.get(s[42 + i], 0), s[50 + i])
    items = sorted(tot.items(), key=lambda x: -x[1])[:6]
    return [(i, min(20, math.ceil(c * mult))) for i, c in items]

def creates(pred):
    def f(x):
        it = ITEMS.get(x[2])
        return bool(x[2]) and it is not None and pred(it)
    return f
ARMURE = creates(lambda it: it['cl'] == 4 and it['it'] in INVTYPE.values())
ARME = creates(lambda it: it['cl'] == 2)
POTION = creates(lambda it: it['cl'] == 0)
SAC = creates(lambda it: it['cl'] == 1 and it['sc'] == 0)
CAPE = creates(lambda it: it['cl'] == 4 and it['it'] == 16)
TETE = creates(lambda it: it['cl'] == 4 and it['it'] == 1)
BIJOU = creates(lambda it: it['cl'] == 4 and it['it'] == 12)
FUSIL = creates(lambda it: it['cl'] == 2 and it['sc'] == 3)
def ENCHANT(x): return x[2] == 0
TOUT = creates(lambda it: True)

def display_src(cl, sc, it, ilvl, k=0):
    """Objet existant servant de modèle (apparence, matériau, son) : même type, niveau proche."""
    c = [e for e, d in ITEMS.items() if d['cl'] == cl and d['sc'] == sc and d['it'] == it and d['q'] in (2, 3)
         and not any(w in d['name'] for w in ('Monster', 'DEPRECATED', 'Test', 'OLD', 'QA', 'Deprecated'))]
    c.sort(key=lambda e: (abs(ITEMS[e]['il'] - ilvl), -ITEMS[e]['q'], e))
    return c[min(k, len(c) - 1)]

# ---------------------------------------------------------------- définition des métiers
def armure(sub_lt40, sub_ge40, dist, suffixe, role):
    return dict(kind='armure', sub=(sub_lt40, sub_ge40), dist=dist, suffixe=suffixe, role=role, filt=ARMURE)

FORGE_ARMES = [('Épée', 7, 13, '1h'), ('Hache', 0, 13, '1h'), ('Masse', 4, 13, '1h'), ('Grande hache', 1, 17, '2h'),
               ('Dague', 15, 13, '1h'), ('Marteau de guerre', 5, 17, '2h'), ('Lame', 7, 13, '1h'),
               ('Grande épée', 8, 17, '2h')]
PROFS = [
    (164, 'Forge', [
        armure(3, 4, D_TANK, 'du Rempart', 'Tank'),
        armure(3, 4, D_SOINS, "de l'Aube sacrée", 'Soins'),
        armure(3, 4, D_FORCE, 'de la Furie', 'DPS'),
        dict(kind='arme_forge', dist=D_FORCE, role='DPS', filt=ARME),
    ]),
    (165, 'Travail du cuir', [
        armure(2, 2, D_AGI, 'du Rôdeur nocturne', 'DPS mêlée'),
        armure(2, 3, D_CHASSE, 'du Traqueur', 'DPS distance'),
        armure(2, 3, D_SOINS, 'des Marées', 'Soins'),
        armure(2, 3, D_SORTS_M, "de l'Orage", 'Sorts'),
    ]),
    (197, 'Couture', [
        armure(1, 1, D_SORTS, "de l'Arcaniste", 'Sorts'),
        armure(1, 1, D_SOINS, 'de la Lumière', 'Soins'),
        dict(kind='cape', dist=D_CAPE, role='Physique', filt=CAPE),
        dict(kind='sac', role='Tous', filt=SAC),
    ]),
    (202, 'Ingénierie', [
        dict(kind='fusil', dist=D_CHASSE, role='DPS distance', filt=FUSIL),
        dict(kind='lunettes', sub=2, dist=D_AGI, nom='Lunettes de combat', role='DPS mêlée', filt=TETE),
        dict(kind='lunettes', sub=1, dist=D_SORTS, nom='Lunettes mystiques', role='Sorts et soins', filt=TETE),
        dict(kind='bijou', dist=D_BIJOU, role='Tank', filt=BIJOU),
    ]),
    (171, 'Alchimie', [
        dict(kind='potion', effet='vie', role='Tous', filt=POTION),
        dict(kind='potion', effet='mana', role='Soins et sorts', filt=POTION),
        dict(kind='potion', effet='ap', role='Physique', filt=POTION),
        dict(kind='potion', effet='sp', role='Sorts', filt=POTION),
    ]),
    (333, 'Enchantement', [
        dict(kind='enchant', effet='frappe', role='Physique', filt=ENCHANT),
        dict(kind='enchant', effet='sorts', role='Sorts', filt=ENCHANT),
        dict(kind='enchant', effet='soins', role='Soins', filt=ENCHANT),
        dict(kind='enchant', effet='endurance', role='Tank', filt=ENCHANT),
    ]),
]

# potions : (niveau requis, valeur moyenne) des potions existantes ; au-delà du dernier palier +30 par niveau
LADDER = {
    'vie': [(1, 80), (3, 160), (12, 320), (21, 520), (35, 800), (45, 1400)],
    'mana': [(5, 160), (14, 320), (22, 520), (31, 800), (41, 1200), (49, 1800)],
}
def ladder(eff, L):
    """Meilleure potion existante utilisable à ce niveau, +2 % par niveau au-delà de son niveau requis."""
    req, val = max(p for p in LADDER[eff] if p[0] <= L)
    return val * (1 + 0.02 * (L - req))
POTION_BASE = {   # sort et objet modèles
    'vie': (17534, 13446), 'mana': (17531, 13444), 'ap': (16329, 9206), 'sp': (17539, 13454),
}
ENCH_BASE = {'frappe': 20031, 'sorts': 22749, 'soins': 23802, 'endurance': 20026}
TEACH_BASE = 2746

SPELL_BASE, ITEM_BASE, ENCH_ID_BASE, SLA_BASE = 60000, 994000, 3000, 20000

# ---------------------------------------------------------------- génération
items = []       # objets à créer
spells = []      # sorts : dict(id, base, kind, champs serveur, ligne DBC)
slarows = []
enchrows = []
trainer = []     # (métier, sort d'apprentissage, prix, compétence, niveau)
recap = []
nsp = [SPELL_BASE]
def newspell():
    nsp[0] += 1
    return nsp[0] - 1
nit = [ITEM_BASE]
def newitem():
    nit[0] += 1
    return nit[0] - 1

for prof, profnom, roles in PROFS:
    for t, L in enumerate(LEVELS):
        S = skill_of(L)
        ilvl = L + 5
        for k, R in enumerate(roles):
            kind = R['kind']
            recs = near_recipes(prof, S, R['filt'], 6) or near_recipes(prof, S, TOUT if kind != 'enchant' else ENCHANT, 6)
            if len(recs) > 2:     # un couple de recettes différent par rôle pour varier les réactifs
                o = (k * 2) % (len(recs) - 1)
                recs = recs[o:o + 2]
            if len(recs) < 2:
                recs += [x for x in near_recipes(prof, S, TOUT if kind != 'enchant' else ENCHANT, 3) if x not in recs][:2 - len(recs)]
            assert recs, (prof, L, kind)
            reag = merge_reagents(recs, 2.0 if prof in (171, 333) else 1.3)
            craftbase = recs[0][1]
            created = 0
            name = None
            if kind in ('armure', 'arme_forge', 'cape', 'lunettes', 'bijou', 'fusil', 'sac'):
                it = dict(entry=newitem(), ilvl=ilvl, req=L, stats={}, bonus={}, armor=0)
                if kind == 'armure':
                    slot = ARMSLOT[t]
                    sub = R['sub'][0] if L < 40 else R['sub'][1]
                    it['src'] = display_src(4, sub, INVTYPE[slot], ilvl, k)
                    it['name'] = "%s %s" % (NOUNS[sub][slot], R['suffixe'])
                    it['stats'], it['bonus'] = make_stats(ilvl, SLOTMOD[slot], R['dist'])
                    src = ITEMS[it['src']]
                    it['armor'] = round(src['armor'] * ilvl / max(src['il'], 1) * 1.1 * ETAPE1)
                elif kind == 'arme_forge':
                    nom, sc, inv, wk = FORGE_ARMES[t]
                    it['src'] = display_src(2, sc, inv, ilvl)
                    it['name'] = "%s %s" % (nom, RANGS[t])
                    it['stats'], it['bonus'] = make_stats(ilvl, 0.42 if wk == '1h' else 0.8, R['dist'])
                    spd = {'1h': 2600, '2h': 3500}[wk] if sc != 15 else 1800
                    avg = dps(wk, ilvl) * spd / 1000
                    it['weapon'] = (round(avg * 0.75), round(avg * 1.25), spd)
                elif kind == 'fusil':
                    it['src'] = display_src(2, 3, 26, ilvl)
                    it['name'] = "Fusil %s" % RANGS[t]
                    it['stats'], it['bonus'] = make_stats(ilvl, 0.3, R['dist'])
                    avg = dps('gun', ilvl) * 2800 / 1000
                    it['weapon'] = (round(avg * 0.75), round(avg * 1.25), 2800)
                elif kind == 'cape':
                    it['src'] = display_src(4, 1, 16, ilvl)
                    it['name'] = "Cape %s" % RANGS[t]
                    it['stats'], it['bonus'] = make_stats(ilvl, SLOTMOD['cloak'], R['dist'])
                    src = ITEMS[it['src']]
                    it['armor'] = round(src['armor'] * ilvl / max(src['il'], 1) * 1.1 * ETAPE1)
                elif kind == 'lunettes':
                    it['src'] = display_src(4, R['sub'], 1, ilvl, 0)
                    it['name'] = "%s %s" % (R['nom'], RANGS[t])
                    it['stats'], it['bonus'] = make_stats(ilvl, 1.0, R['dist'])
                    src = ITEMS[it['src']]
                    it['armor'] = round(src['armor'] * ilvl / max(src['il'], 1) * 1.1 * ETAPE1)
                elif kind == 'bijou':
                    it['src'] = display_src(4, 0, 12, ilvl)
                    it['name'] = "Gadget protecteur %s" % RANGS[t]
                    it['stats'], it['bonus'] = make_stats(ilvl, SLOTMOD['trinket'], R['dist'])
                elif kind == 'sac':
                    it['src'] = display_src(1, 0, 18, ilvl)
                    it['name'] = "Sac renforcé %s" % RANGS[t]
                    it['slots'] = [10, 12, 12, 14, 14, 16, 16, 18][t]
                # gadgets d'ingénieur : apparence de l'objet de la recette existante la plus proche
                rit = ITEMS.get(recs[0][2])
                if kind in ('lunettes', 'fusil', 'bijou') and rit and rit['cl'] == ITEMS[it['src']]['cl'] and rit['it'] == ITEMS[it['src']]['it']:
                    it['src'] = recs[0][2]
                items.append(it)
                created = it['entry']
                name = it['name']
            elif kind == 'potion':
                eff = R['effet']
                bsp, bit = POTION_BASE[eff]
                psid = newspell()
                if eff in ('vie', 'mana'):
                    avg = ladder(eff, L) * RENFORT
                    bp, die = round(avg * 0.85) - 1, round(avg * 0.3) + 1
                    pname = {'vie': 'Potion de soins', 'mana': 'Potion de mana'}[eff]
                    desc = {'vie': 'Rend $s1 points de vie.', 'mana': 'Rend $s1 points de mana.'}[eff]
                    sets = dict(EffectBasePoints1=bp, EffectDieSides1=die)
                else:
                    val = round(0.75 * L * RENFORT)
                    pname = {'ap': 'Élixir de puissance', 'sp': 'Élixir des arcanes'}[eff]
                    desc = {'ap': "Augmente la puissance d'attaque de $s1 pendant $d.",
                            'sp': 'Augmente les dégâts infligés par les sorts de $s1 au maximum pendant $d.'}[eff]
                    sets = dict(EffectBasePoints1=val - 1, EffectDieSides1=1, DurationIndex=42, SpellLevel=L)
                name = "%s %s" % (pname, RANGS[t])
                spells.append(dict(id=psid, base=bsp, name=name, desc=desc, sets=sets))
                it = dict(entry=newitem(), src=bit, name=name, ilvl=ilvl, req=L, potion=psid)
                items.append(it)
                created = it['entry']
            elif kind == 'enchant':
                eff = R['effet']
                eid = ENCH_ID_BASE + len(enchrows)
                if eff == 'frappe':
                    v = max(2, round(L / 12 * RENFORT * ETAPE1))
                    row = [eid, 2, 0, 0, v, 0, 0, v, 0, 0, 0, 0, 0] + ["Dégâts de l'arme +%d" % v] + [0] * 7 + [ench.rows[0][21], 0, 0]
                    name = "Enchantement d'arme - Frappe %s" % RANGS[t]
                    desc = "Enchante de manière permanente une arme de mêlée : +%d aux dégâts." % v
                else:
                    fam, coef, txt, dtxt = {
                        'sorts': ('sp', 0.5, 'Sorts +%d', "Enchante de manière permanente une arme : augmente les dégâts et les soins des sorts de %d au maximum."),
                        'soins': ('heal', 0.4, 'Soins +%d', "Enchante de manière permanente des bracelets : augmente les soins prodigués par les sorts de %d au maximum."),
                        'endurance': ('sta', 0.2, 'Endurance +%d', "Enchante de manière permanente un plastron : +%d à l'Endurance."),
                    }[eff]
                    sid, v = pick(fam, coef * L * RENFORT * ETAPE1)
                    row = [eid, 3, 0, 0, 0, 0, 0, 0, 0, 0, sid, 0, 0] + [txt % v] + [0] * 7 + [ench.rows[0][21], 0, 0]
                    name = "Enchantement %s - %s %s" % ({'sorts': "d'arme", 'soins': 'de bracelets', 'endurance': 'de plastron'}[eff],
                                                       {'sorts': 'Puissance des sorts', 'soins': 'Soins', 'endurance': 'Endurance'}[eff], RANGS[t])
                    desc = dtxt % v
                enchrows.append(row)
                craftbase = ENCH_BASE[eff]
            # sort de fabrication
            csid = newspell()
            sets = {}
            for i in range(8):
                sets['Reagent%d' % (i + 1)] = reag[i][0] if i < len(reag) else 0
                sets['ReagentCount%d' % (i + 1)] = reag[i][1] if i < len(reag) else 0
            if kind == 'enchant':
                sets['EffectMiscValue1'] = eid
                sets['Totem1'] = SPR[recs[0][1]][40]     # baguette du palier
                cdesc = desc
            else:
                sets.update(EffectItemType1=created, EffectBasePoints1=0, EffectDieSides1=1)
                cdesc = ''
            spells.append(dict(id=csid, base=craftbase, name=name, desc=cdesc, sets=sets))
            # sort d'apprentissage
            tsid = newspell()
            spells.append(dict(id=tsid, base=TEACH_BASE, name=name, desc='', sets=dict(EffectTriggerSpell1=csid)))
            slarows.append([SLA_BASE + len(slarows), prof, csid, 0, 0, 0, 0, 1, 0, 0, S + 40, S + 20, 0, 0, 0])
            trainer.append((prof, tsid, L * L * 25, S, L))
            recap.append(dict(metier=profnom, niveau=L, competence=S, role=R['role'], nom=name,
                              reactifs=[(ITEMS[i]['name'], c) for i, c in reag]))

# ---------------------------------------------------------------- SQL
L_ = []
w = L_.append
w("-- Recettes bleues renforcées des métiers (généré)")
w("SET NAMES utf8mb4;")
w("DELETE FROM item_template WHERE entry BETWEEN %d AND %d;" % (ITEM_BASE, ITEM_BASE + 999))
w("DELETE FROM spell_template WHERE Id BETWEEN %d AND %d;" % (SPELL_BASE, SPELL_BASE + 1999))
w("DELETE FROM npc_trainer WHERE spell BETWEEN %d AND %d;" % (SPELL_BASE, SPELL_BASE + 1999))
w("")
w("-- Objets")
w("DROP TEMPORARY TABLE IF EXISTS tmp_it;")
w("CREATE TEMPORARY TABLE tmp_it LIKE item_template;")
for it in items:
    w("INSERT INTO tmp_it SELECT * FROM item_template WHERE entry=%d;" % it['src'])
    s = ["entry=%d" % it['entry'], "name='%s'" % esc(it['name']), "Quality=3", "ItemLevel=%d" % it['ilvl'],
         "RequiredLevel=%d" % it['req'], "AllowableClass=-1", "AllowableRace=-1", "RequiredSkill=0",
         "RequiredSkillRank=0", "requiredspell=0", "requiredhonorrank=0", "RequiredCityRank=0",
         "RequiredReputationFaction=0", "RequiredReputationRank=0", "description=''", "PageText=0",
         "startquest=0", "lockid=0", "RandomProperty=0", "itemset=0", "area=0", "Map=0", "ScriptName=''",
         "SellPrice=%d" % (it['ilvl'] * 20 if 'potion' in it else it['ilvl'] ** 2 * 4),
         "BuyPrice=%d" % (it['ilvl'] * 80 if 'potion' in it else it['ilvl'] ** 2 * 16)]
    if 'potion' in it:
        s += ["spellid_1=%d" % it['potion']]
    else:
        s += ["Flags=0", "maxcount=0", "stackable=1", "bonding=2", "holy_res=0", "fire_res=0", "nature_res=0",
              "frost_res=0", "shadow_res=0", "arcane_res=0"]
        st = list(it['stats'].items())
        for n in range(10):
            if n < len(st):
                s += ["stat_type%d=%d" % (n + 1, STATID[st[n][0]]), "stat_value%d=%d" % (n + 1, st[n][1])]
            else:
                s += ["stat_type%d=0" % (n + 1), "stat_value%d=0" % (n + 1)]
        if 'weapon' in it:
            mn, mx, spd = it['weapon']
            s += ["dmg_min1=%d" % mn, "dmg_max1=%d" % mx, "dmg_type1=0", "delay=%d" % spd, "armor=0"]
            for n in range(2, 6):
                s += ["dmg_min%d=0" % n, "dmg_max%d=0" % n]
        else:
            s += ["armor=%d" % it['armor']]
        if 'slots' in it:
            s += ["ContainerSlots=%d" % it['slots']]
        sp_ = [pick(f, v)[0] for f, v in it['bonus'].items()]
        for n in range(5):
            sid = sp_[n] if n < len(sp_) else 0
            s += ["spellid_%d=%d" % (n + 1, sid), "spelltrigger_%d=%d" % (n + 1, 1 if sid else 0),
                  "spellcharges_%d=0" % (n + 1), "spellcooldown_%d=-1" % (n + 1), "spellcategory_%d=0" % (n + 1),
                  "spellcategorycooldown_%d=-1" % (n + 1)]
    w("UPDATE tmp_it SET %s WHERE entry=%d;" % (", ".join(s), it['src']))
w("INSERT INTO item_template SELECT * FROM tmp_it;")
w("DROP TEMPORARY TABLE tmp_it;")
w("")
w("-- Sorts (fabrication, apprentissage, effets des potions)")
w("DROP TEMPORARY TABLE IF EXISTS tmp_sp;")
w("CREATE TEMPORARY TABLE tmp_sp LIKE spell_template;")
for sp_ in spells:
    w("INSERT INTO tmp_sp SELECT * FROM spell_template WHERE Id=%d;" % sp_['base'])
    s = ["Id=%d" % sp_['id'], "SpellName='%s'" % esc(sp_['name']), "Rank1=''"] + \
        ["%s=%d" % (k, v) for k, v in sp_['sets'].items()]
    w("UPDATE tmp_sp SET %s WHERE Id=%d;" % (", ".join(s), sp_['base']))
w("INSERT INTO spell_template SELECT * FROM tmp_sp;")
w("DROP TEMPORARY TABLE tmp_sp;")
w("")
w("-- Maîtres de métier : tous les PNJ qui enseignent déjà ce métier")
for prof, tsid, cost, S, L in trainer:
    w("INSERT IGNORE INTO npc_trainer (entry, spell, spellcost, reqskill, reqskillvalue, reqlevel, condition_id) "
      "SELECT DISTINCT entry, %d, %d, %d, %d, %d, 0 FROM npc_trainer WHERE reqskill=%d AND spell<%d;"
      % (tsid, cost, prof, S, L, prof, SPELL_BASE))
w("")
w("SELECT 'Metiers OK' AS resultat;")
open(OUT + 'metiers.sql', 'w', encoding='utf-8').write("\n".join(L_) + "\n")

# ---------------------------------------------------------------- lignes DBC
# colonnes Spell.dbc : 15 focus, 40 totem, 42-49 réactifs, 50-57 nombres, 76 points de base, 64 dés,
# 30 durée, 29 niveau, 103 objet créé, 106 valeur divers, 109 sort déclenché, 120 nom, 129 rang, 138 description, 147 infobulle
DBCCOL = {'Reagent%d' % i: 41 + i for i in range(1, 9)}
DBCCOL.update({'ReagentCount%d' % i: 49 + i for i in range(1, 9)})
DBCCOL.update(EffectBasePoints1=76, EffectDieSides1=64, DurationIndex=30, SpellLevel=29, EffectItemType1=103,
              EffectMiscValue1=106, EffectTriggerSpell1=109, Totem1=40)
spellrows = []
for sp_ in spells:
    r = list(SPR[sp_['base']])
    r[0] = sp_['id']
    for k, v in sp_['sets'].items():
        r[DBCCOL[k]] = v
    for c in range(120, 156):
        r[c] = 0
    r[120] = sp_['name']
    r[128] = SPR[sp_['base']][128]
    r[137] = SPR[sp_['base']][137]
    r[146] = SPR[sp_['base']][146]
    r[155] = SPR[sp_['base']][155]
    if sp_['desc']:
        r[138] = sp_['desc']
    spellrows.append(r)
json.dump(dict(spell=spellrows, sla=slarows, ench=enchrows), open(OUT + 'metiers_rows.json', 'w', encoding='utf-8'),
          ensure_ascii=False)
json.dump(recap, open(OUT + 'recap.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('objets', len(items), 'sorts', len(spells), 'recettes', len(slarows), 'enchantements', len(enchrows))
