# Générateur de sorts custom : une ligne spell_template (serveur, SQL) + une ligne Spell.dbc (client) par sort.
# Chaque sort est cloné d'un sort vanilla puis modifié par nom de colonne SQL.
import sys, struct, subprocess
sys.path.insert(0, '/home/claude/wow/fr')
from dbc import DBC

def q(sql, db='classicmangos'):
    r = subprocess.run(['mysql', '-N', '-B', db, '-e', sql], capture_output=True, text=True, check=True)
    return [l.split('\t') for l in r.stdout.splitlines()]

def esc(s):
    return s.replace('\\', '\\\\').replace("'", "\\'")

SQLCOLS = [r[0] for r in q("describe spell_template")]
SQLIDX = {c: i for i, c in enumerate(SQLCOLS)}
FLOAT_SQL = {'Speed', 'EffectDicePerLevel1', 'EffectDicePerLevel2', 'EffectDicePerLevel3', 'EffectRealPointsPerLevel1',
             'EffectRealPointsPerLevel2', 'EffectRealPointsPerLevel3', 'EffectMultipleValue1', 'EffectMultipleValue2',
             'EffectMultipleValue3', 'EffectPointsPerComboPoint1', 'EffectPointsPerComboPoint2', 'EffectPointsPerComboPoint3',
             'DmgMultiplier1', 'DmgMultiplier2', 'DmgMultiplier3', 'EffectBonusCoefficient1', 'EffectBonusCoefficient2',
             'EffectBonusCoefficient3', 'EffectBonusCoefficientFromAP1', 'EffectBonusCoefficientFromAP2', 'EffectBonusCoefficientFromAP3'}
SERVER_ONLY = {'EffectBonusCoefficient1', 'EffectBonusCoefficient2', 'EffectBonusCoefficient3', 'EffectBonusCoefficientFromAP1',
               'EffectBonusCoefficientFromAP2', 'EffectBonusCoefficientFromAP3', 'IsServerSide', 'AttributesServerside'}

def dbc_col(name):
    """colonne Spell.dbc 1.12 pour un nom de colonne spell_template"""
    i = SQLIDX[name]
    if i <= 115:
        return i
    if 116 <= i <= 118:            # SpellIconID, ActiveIconID, SpellPriority (le DBC a 2 visuels)
        return i + 1
    m = {'ManaCostPercentage': 156, 'StartRecoveryCategory': 157, 'StartRecoveryTime': 158, 'MaxTargetLevel': 159,
         'SpellFamilyName': 160, 'MaxAffectedTargets': 163, 'DmgClass': 164, 'PreventionType': 165, 'StanceBarOrder': 166,
         'DmgMultiplier1': 167, 'DmgMultiplier2': 168, 'DmgMultiplier3': 169, 'MinFactionId': 170, 'MinReputation': 171,
         'RequiredAuraVision': 172}
    return m.get(name)

def fbits(v):
    return struct.unpack('<I', struct.pack('<f', float(v)))[0]

SPELL = DBC('/home/claude/wow/fr/dbc_en/Spell.dbc')
SPR = {r[0]: r for r in SPELL.rows}
def icon(sid):
    return SPR[sid][117]
def visual(sid):
    return SPR[sid][115]

DUR = {0: 21, 1000: 36, 2000: 39, 3000: 27, 4000: 35, 5000: 28, 6000: 32, 8000: 31, 10000: 1, 12000: 29, 15000: 8, 20000: 18,
       30000: 9, 45000: 22, 60000: 3, 120000: 4, 300000: 5, 600000: 6, 1800000: 30, 3600000: 42, 7200000: 367, -1: 21}
CAST = {0: 1, 1000: 4, 1500: 16, 2000: 5, 2500: 19, 3000: 14, 3500: 22, 4000: 15, 5000: 6}
RADIUS = {2: 7, 3: 15, 5: 8, 8: 14, 10: 13, 13: 17, 20: 9, 30: 10, 45: 11, 100: 12}
RANGE = {0: 1, 5: 2, 20: 3, 30: 4, 40: 5, 100: 6, 10: 7, 15: 11, 25: 34, 35: 35, 45: 36, 50: 37}

def rank_levels(first, n=None):
    """un rang tous les 8 niveaux à partir du niveau d'apprentissage, dernier rang au niveau 60"""
    lv = list(range(first, 60, 8))
    if not lv or lv[-1] != 60:
        lv.append(60)
    if n is not None:
        lv = lv[-n:] if len(lv) >= n else lv
    return lv

def rank_value(v60, level):
    return v60 * (0.05 + 0.95 * (level / 60.0) ** 1.4)

class Gen:
    def __init__(self, family, flag_bits):
        self.family = family
        self.free_bits = list(flag_bits)
        self.masks = {}                 # clé de sort -> bit de famille
        self.spells = []                # dicts
        self.chain = []                 # (id, prev, first, rank)
        self.by_key = {}                # clé -> [ids des rangs]

    def mask(self, key):
        if key not in self.masks:
            self.masks[key] = 1 << self.free_bits.pop(0)
        return self.masks[key]

    def add(self, sid, base, name, desc, rank='', tooltip='', key=None, sets=None, family=True):
        sets = dict(sets or {})
        if family:
            sets.setdefault('SpellFamilyName', self.family)
            sets.setdefault('SpellFamilyFlags', self.mask(key or name))
        self.spells.append(dict(id=sid, base=base, name=name, desc=desc, rank=rank, tooltip=tooltip, sets=sets))
        if key:
            self.by_key.setdefault(key, []).append(sid)
        return sid

    # ---------------------------------------------------------------- sorties
    def sql(self, first, last):
        L = ["DELETE FROM spell_template WHERE Id BETWEEN %d AND %d;" % (first, last),
             "DELETE FROM spell_chain WHERE spell_id BETWEEN %d AND %d;" % (first, last),
             "DROP TEMPORARY TABLE IF EXISTS tmp_sp;", "CREATE TEMPORARY TABLE tmp_sp LIKE spell_template;"]
        for s in self.spells:
            L.append("INSERT INTO tmp_sp SELECT * FROM spell_template WHERE Id=%d;" % s['base'])
            sets = ["Id=%d" % s['id'], "SpellName='%s'" % esc(s['name']), "Rank1='%s'" % esc(s['rank'])]
            for k, v in s['sets'].items():
                if k in FLOAT_SQL:
                    sets.append("%s=%s" % (k, repr(float(v))))
                else:
                    sets.append("%s=%d" % (k, int(v)))
            L.append("UPDATE tmp_sp SET %s WHERE Id=%d;" % (", ".join(sets), s['base']))
        L.append("INSERT INTO spell_template SELECT * FROM tmp_sp;")
        L.append("DROP TEMPORARY TABLE tmp_sp;")
        for sid, prev, firstr, rk in self.chain:
            L.append("INSERT INTO spell_chain (spell_id, prev_spell, first_spell, `rank`, req_spell) VALUES (%d, %d, %d, %d, 0);" % (sid, prev, firstr, rk))
        return L

    def dbc_rows(self):
        rows = []
        for s in self.spells:
            r = list(SPR[s['base']])
            r[0] = s['id']
            for k, v in s['sets'].items():
                if k in SERVER_ONLY:
                    continue
                if k == 'SpellFamilyFlags':
                    r[161] = int(v) & 0xffffffff
                    r[162] = (int(v) >> 32) & 0xffffffff
                    continue
                c = dbc_col(k)
                if c is None:
                    continue
                r[c] = fbits(v) if k in FLOAT_SQL else int(v) & 0xffffffff
            for c in range(120, 156):
                if c not in (128, 137, 146, 155):
                    r[c] = 0
            r[120] = s['name']
            r[129] = s['rank']
            r[138] = s['desc']
            r[147] = s['tooltip']
            rows.append(r)
        return rows

    def chain_ranks(self, ids):
        for i, sid in enumerate(ids):
            self.chain.append((sid, ids[i - 1] if i else 0, ids[0], i + 1))
