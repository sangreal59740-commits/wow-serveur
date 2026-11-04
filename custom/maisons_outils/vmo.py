import struct
D='/mnt/user-data/uploads/SPP_Classics V2/SPP_Classics_V2/SPP_Server/Server/Modules/vanilla/vmaps/'
def bih(d,o):
    o+=24; ts,=struct.unpack_from('<I',d,o); o+=4+4*ts
    c,=struct.unpack_from('<I',d,o); o+=4+4*c
    return o
def load(name):
    d=open(D+name+'.vmo','rb').read(); o=8
    assert d[o:o+4]==b'WMOD'; o+=4; o+=4; root,=struct.unpack_from('<I',d,o); o+=4
    groups=[]
    if d[o:o+4]!=b'GMOD': return groups
    o+=4; n,=struct.unpack_from('<I',d,o); o+=4
    for i in range(n):
        b=struct.unpack_from('<6f',d,o); o+=24
        fl,gid=struct.unpack_from('<II',d,o); o+=8
        assert d[o:o+4]==b'VERT'; o+=4; o+=4; vc,=struct.unpack_from('<I',d,o); o+=4
        if not vc:
            groups.append(dict(b=b,fl=fl,gid=gid,nv=0)); continue
        o+=12*vc
        assert d[o:o+4]==b'TRIM'; o+=4; o+=4; tc,=struct.unpack_from('<I',d,o); o+=4+12*tc
        assert d[o:o+4]==b'MBIH'; o+=4; o=bih(d,o)
        assert d[o:o+4]==b'LIQU'; o+=4; cs,=struct.unpack_from('<I',d,o); o+=4
        if cs:
            tx,ty=struct.unpack_from('<II',d,o); o+=8+12+4+4*(tx+1)*(ty+1)+tx*ty
        groups.append(dict(b=b,fl=fl,gid=gid,nv=vc,nt=tc))
    return groups
