# écriture d'un MPQ v1 simple (fichiers non compressés) ; réutilise mpqr.py pour les fonctions de hachage
import struct
import os; exec(open(os.path.join(os.path.dirname(__file__), 'mpq_lecture.py')).read())
def enc(data, key):
    s2 = 0xEEEEEEEE; o = []
    for (v,) in struct.iter_unpack('<I', data):
        s2 = (s2 + T[0x400 + (key & 0xFF)]) & 0xFFFFFFFF
        o.append(v ^ ((key + s2) & 0xFFFFFFFF))
        key = ((~key << 0x15) + 0x11111111 | (key >> 0x0B)) & 0xFFFFFFFF
        s2 = (v + s2 + (s2 << 5) + 3) & 0xFFFFFFFF
    return struct.pack('<%dI' % len(o), *o)
def ecrire(chemin, fichiers):   # fichiers : liste (nom, données)
    hn = 1
    while hn < len(fichiers) * 2: hn *= 2
    hn = max(hn, 16)
    corps = b''; blocs = []
    off = 32
    for nom, data in fichiers:
        blocs.append((off + len(corps), len(data), len(data), 0x80000000))
        corps += data
    ht = [(0xFFFFFFFF, 0xFFFFFFFF, 0xFFFF, 0xFFFF, 0xFFFFFFFF)] * hn
    for i, (nom, data) in enumerate(fichiers):
        a, b, k = h(nom, 1), h(nom, 2), h(nom, 0) % hn
        while ht[k][4] != 0xFFFFFFFF: k = (k + 1) % hn
        ht[k] = (a, b, 0, 0, i)
    htb = b''.join(struct.pack('<IIHHI', *e) for e in ht)
    btb = b''.join(struct.pack('<IIII', *e) for e in blocs)
    hp = 32 + len(corps); bp = hp + len(htb)
    total = bp + len(btb)
    entete = b'MPQ\x1a' + struct.pack('<IIHHIIII', 32, total, 0, 3, hp, bp, hn, len(blocs))
    open(chemin, 'wb').write(entete + corps + enc(htb, h('(hash table)', 3)) + enc(btb, h('(block table)', 3)))
