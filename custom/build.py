import sys,os,json,glob
sys.path.insert(0,'.')
from dbc import DBC,rebuild,append_rows
import mpq
T={}
for f in sorted(glob.glob('out/*.json')):
    if f.endswith('ranks.json'): continue
    T.update(json.load(open(f,encoding='utf-8')))
R=json.load(open('out/ranks.json',encoding='utf-8'))
D=json.load(open('out2/_all.json',encoding='utf-8'))
skip=set()
import re
CH=json.load(open('/home/claude/wow/stats/changes.json',encoding='utf-8'))
MET=json.load(open('/home/claude/wow/metiers/metiers_rows.json',encoding='utf-8'))
LEG=json.load(open('/home/claude/wow/donjons/legendaires_rows.json',encoding='utf-8'))
CLS=json.load(open('/home/claude/wow/classes/classes_rows.json',encoding='utf-8'))
SRT=json.load(open('/home/claude/wow/classes/sorts_rows.json',encoding='utf-8'))
files={}; stats=[]
for f in sorted(os.listdir('dbc_en')):
    try: d=DBC('dbc_en/'+f)
    except Exception: continue
    if not d.nrec: continue
    cols=[c for c in d.string_cols() if (f,c) not in skip]
    if not cols and f!='Spell.dbc': continue
    rs={}
    if f=='Spell.dbc':
        for i,r in enumerate(d.rows):
            c=CH['spells'].get(str(r[0]))
            if c:
                for e,(old,nb) in c.items(): r[76+int(e)]=nb&0xffffffff
            pt=SRT.get('spell_patch',{}).get(str(r[0]))
            if pt:
                for col,v in pt.items(): r[int(col)]=v
            tx=SRT.get('spell_text',{}).get(str(r[0]))
            if tx:
                for col,ops in tx.items():
                    col=int(col); en=d.str(r[col])
                    if not en: continue
                    fr=(R if col==129 else D if col in (138,147) else T).get(en,en)
                    for op in ops:
                        if op[0]=='+': fr=fr.rstrip()+op[1]
                        else: fr=re.sub(op[0],op[1],fr)
                    rs[(i,col)]=fr
    if f=='SpellItemEnchantment.dbc':
        for i,r in enumerate(d.rows):
            c=CH['ench'].get(str(r[0]))
            if c and r[13]:
                en=d.str(r[13]); fr=T.get(en,en)
                pat=r'(?<![\d.])%d(?![\d.])'%abs(c[0])
                if len(re.findall(pat,fr))==1: rs[(i,13)]=re.sub(pat,str(abs(c[1])),fr)
        print('noms enchantements',len(rs))
    if f=='TalentTab.dbc':
        for i,r in enumerate(d.rows):
            m=SRT['talenttab_meta'].get(str(r[0]))
            if m:
                rs[(i,1)]=m[0]; rs[(i,14)]=m[2]; r[10]=m[1]
    if f=='SkillLine.dbc':
        for i,r in enumerate(d.rows):
            if str(r[0]) in SRT['rename_skill']: rs[(i,3)]=SRT['rename_skill'][str(r[0])]
    if f=='SpellShapeshiftForm.dbc':
        for i,r in enumerate(d.rows):
            fp=SRT.get('form_patch',{}).get(str(r[0]))
            if fp:
                r[1]=fp[1]; r[11]=7; r[12]=0xffffffff
                for c in range(2,10): rs[(i,c)]=fp[0]
    if f=='ChrClasses.dbc':
        for i,r in enumerate(d.rows):
            if str(r[0]) in CLS['rename']: rs[(i,5)]=CLS['rename'][str(r[0])]
    cm={c:(R if (f=='Spell.dbc' and c==129) else D if (f=='Spell.dbc' and c in (138,147)) else T) for c in cols}
    data,n=rebuild(d,cm,rs)
    if f=='ItemSet.dbc':
        sys.path.insert(0,'/home/claude/wow/donjons')
        import itemset_rows
        data=append_rows(data, itemset_rows.rows(d.rows[0][9]))
        n+=1
    if f=='Spell.dbc':
        data=append_rows(data, MET['spell']+LEG['spell']+SRT['spell']); n+=1
    if f=='ChrClasses.dbc':
        data=append_rows(data, CLS['chr_new']); n+=1
    if f=='SkillLine.dbc':
        data=append_rows(data, SRT['skilllines']); n+=1
    if f=='TalentTab.dbc':
        data=append_rows(data, SRT['talenttab_new']); n+=1
    if f=='SpellItemEnchantment.dbc':
        data=append_rows(data, MET['ench']+LEG['ench']); n+=1
    if n:
        files['DBFilesClient\\'+f]=data; stats.append((f,n))
# visuels des buffs permanents sans effet continu (copies sans StateKit)
if SRT.get('spellvisual_new'):
    files['DBFilesClient\\SpellVisual.dbc']=append_rows(open('/home/claude/wow/classes/dbc/SpellVisual.dbc','rb').read(), SRT['spellvisual_new'])
    stats.append(('SpellVisual.dbc',len(SRT['spellvisual_new'])))
# métiers : nouvelles recettes connues du client
files['DBFilesClient\\SkillLineAbility.dbc']=append_rows(open('/home/claude/wow/dbc_extra/SkillLineAbility.dbc','rb').read(), MET['sla']+SRT['sla'])
stats.append(('SkillLineAbility.dbc',len(MET['sla'])))
# classes custom : paires race/classe, tenues de création, compétences
for f in ('CharBaseInfo.dbc','CharStartOutfit.dbc','SkillRaceClassInfo.dbc'):
    files['DBFilesClient\\'+f]=open('/home/claude/wow/classes/out/'+f,'rb').read(); stats.append((f,'classes'))
files['DBFilesClient\\Talent.dbc']=open('/home/claude/wow/classes/out/Talent.dbc','rb').read(); stats.append(('Talent.dbc','classes'))
os.makedirs('build',exist_ok=True)
mpq.write('build/patch-3.MPQ',files)
g=mpq.read('build/patch-3.MPQ')
for k,v in files.items(): assert g(k)==v
for s in stats: print(*s)
print('MPQ', os.path.getsize('build/patch-3.MPQ'))
