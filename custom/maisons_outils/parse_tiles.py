import struct, glob, os, json
D='/mnt/user-data/uploads/SPP_Classics V2/SPP_Classics_V2/SPP_Server/Server/Modules/vanilla/vmaps/'
spawns={}
for f in sorted(glob.glob(D+'00[01]_*.vmtile')):
    m=int(os.path.basename(f)[:3])
    d=open(f,'rb').read(); o=8
    n,=struct.unpack_from('<I',d,o); o+=4
    for i in range(n):
        flags,=struct.unpack_from('<I',d,o); o+=4
        adt,=struct.unpack_from('<H',d,o); o+=2
        sid,=struct.unpack_from('<I',d,o); o+=4
        pos=struct.unpack_from('<3f',d,o); o+=12
        rot=struct.unpack_from('<3f',d,o); o+=12
        sc,=struct.unpack_from('<f',d,o); o+=4
        bound=None
        if flags&4:
            bound=struct.unpack_from('<6f',d,o); o+=24
        nl,=struct.unpack_from('<I',d,o); o+=4
        name=d[o:o+nl].decode('latin1'); o+=nl
        o+=4
        spawns[(m,sid,name)]=dict(m=m,id=sid,flags=flags,pos=pos,rot=rot,sc=sc,bound=bound,name=name)
json.dump(list(spawns.values()),open('spawns.json','w'))
import collections
wmo=[s for s in spawns.values() if not s['flags']&1]
print(len(spawns), 'wmo', len(wmo))
c=collections.Counter(s['name'] for s in wmo)
for k,v in c.most_common(200): print(v,k)
