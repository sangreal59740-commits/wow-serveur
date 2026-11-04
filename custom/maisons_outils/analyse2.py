import sys, json, math, subprocess, collections
sys.path.insert(0,'/tmp/claude-0/maisons')
import vmo
MID=32*533.3333333
S=json.load(open('spawns.json'))
def rotm(rx,ry,rz):
    a,b,c=map(math.radians,(ry,rx,rz))  # Z by rot.y, Y by rot.x, X by rot.z
    Rz=[[math.cos(a),-math.sin(a),0],[math.sin(a),math.cos(a),0],[0,0,1]]
    Ry=[[math.cos(b),0,math.sin(b)],[0,1,0],[-math.sin(b),0,math.cos(b)]]
    Rx=[[1,0,0],[0,math.cos(c),-math.sin(c)],[0,math.sin(c),math.cos(c)]]
    mm=lambda A,B:[[sum(A[i][k]*B[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
    return mm(Rz,mm(Ry,Rx))
def q(sql):
    r=subprocess.run(['mysql','-N','-B','classicmangos','-e',sql],capture_output=True,text=True,check=True)
    return [l.split('\t') for l in r.stdout.splitlines()]
import struct
d=open('/mnt/user-data/uploads/SPP_Classics V2/SPP_Classics_V2/SPP_Server/Server/Modules/vanilla/dbc/FactionTemplate.dbc','rb').read()
n_,f_,rs_,ss_=struct.unpack('<4I',d[4:20]); FT={}
for i in range(n_):
    r=struct.unpack('<%dI'%f_,d[20+i*rs_:20+(i+1)*rs_]); FT[r[0]]=r
def amical(fac):
    r=FT.get(fac); return bool(r) and bool((r[3]|r[4])&6)
NPC=collections.defaultdict(list)
for m,x,y,z,e,nf,fa in q("select c.map,c.position_x,c.position_y,c.position_z,c.id,t.NpcFlags,t.Faction from creature c join creature_template t on t.Entry=c.id where c.map in (0,1)"):
    NPC[int(m)].append((float(x),float(y),float(z),int(e),int(nf),amical(int(fa)) or int(nf)>0))
places={0:[(-8750,720,'Hurlevent',550),(-4900,-950,'Forgefer',600),(1600,240,'Fossoyeuse',500),(-9460,60,'Comté-de-l\'Or',350),(-8900,-140,'Comté du Nord',350),(-6200,330,'Frigoval',350),(-5600,-500,'Kharanos',350),(1900,1600,'Clairière de Deathknell',350),(2250,250,'Brill',350)],
        1:[(1700,-4450,'Orgrimmar',550),(-1250,70,'Pitons-du-Tonnerre',450),(9850,2250,'Darnassus',550),(-600,-4250,'Vallée des Épreuves',350),(300,-4700,'Tranchecolline',350),(-2900,-250,'Camp Narache',350),(-2350,-350,'Sabot-de-Sang',350),(10300,830,'Sombrevallon',350),(9850,950,'Dolanaar',350)]}
cache={}
res={}
for m,ps in places.items():
    for px,py,pname,rad in ps:
        boxes=[]
        for s in S:
            if s['m']!=m or s['flags']&1: continue
            wx=MID-s['pos'][0]; wy=MID-s['pos'][1]
            if (wx-px)**2+(wy-py)**2>rad*rad: continue
            if s['name'] not in cache:
                try: cache[s['name']]=vmo.load(s['name'])
                except Exception as e: print('ERR',s['name'],e); cache[s['name']]=[]
            R=rotm(*s['rot']); sc=s['sc']
            for g in cache[s['name']]:
                fl=g['fl']
                if not (fl&0x2000) or (fl&0x40) or (fl&0x8): continue
                lo=g['b'][:3]; hi=g['b'][3:]
                pts=[]
                for cx in (lo[0],hi[0]):
                    for cy in (lo[1],hi[1]):
                        for cz in (lo[2],hi[2]):
                            v=[cx*sc,cy*sc,cz*sc]
                            w=[sum(R[i][k]*v[k] for k in range(3))+s['pos'][i] for i in range(3)]
                            pts.append((MID-w[0],MID-w[1],w[2]))
                xs=[p[0] for p in pts]; ys=[p[1] for p in pts]; zs=[p[2] for p in pts]
                if max(xs)-min(xs)>55 or max(ys)-min(ys)>55: continue
                boxes.append([min(xs),min(ys),min(zs),max(xs),max(ys),max(zs),s['name']])
        # union-find on overlapping boxes
        n=len(boxes); par=list(range(n))
        def f(i):
            while par[i]!=i: par[i]=par[par[i]]; i=par[i]
            return i
        mg=0.3
        for i in range(n):
            a=boxes[i]
            for j in range(i+1,n):
                b=boxes[j]
                if a[0]-mg<=b[3] and b[0]-mg<=a[3] and a[1]-mg<=b[4] and b[1]-mg<=a[4] and a[2]-mg<=b[5] and b[2]-mg<=a[5]:
                    par[f(i)]=f(j)
        cl=collections.defaultdict(list)
        for i in range(n): cl[f(i)].append(boxes[i])
        out=[]
        for k,bs in cl.items():
            x0=min(b[0] for b in bs); y0=min(b[1] for b in bs); z0=min(b[2] for b in bs)
            x1=max(b[3] for b in bs); y1=max(b[4] for b in bs); z1=max(b[5] for b in bs)
            npcs=[e for e in NPC[m] if any(b[0]<=e[0]<=b[3] and b[1]<=e[1]<=b[4] and b[2]-1<=e[2]<=b[5] for b in bs)]
            out.append(dict(box=(x0,y0,z0,x1,y1,z1),dx=x1-x0,dy=y1-y0,dz=z1-z0,npc=sum(1 for e in npcs if e[5]),mob=sum(1 for e in npcs if not e[5]),npcs=[e[3] for e in npcs][:6],model=bs[0][6],ng=len(bs)))
        res[pname]=out
json.dump(res,open('res.json','w'),default=str)
for p,out in res.items():
    tot=len(out); pnj=[o for o in out if o['npc']>0]; mob=[o for o in out if o['npc']==0 and o['mob']>0]; vide=[o for o in out if o['npc']==0 and o['mob']==0]
    print('%-25s interieurs %3d  avec PNJ %3d  avec monstres %3d  vides %3d' % (p,tot,len(pnj),len(mob),len(vide)))
