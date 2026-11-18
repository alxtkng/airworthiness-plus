import json,re,sys,collections
src,catf,out=sys.argv[1:4]
d=json.load(open(src)); cat=json.load(open(catf))
def chapters(raw):
    raw=raw.replace('Supp 2','Supplement 2')
    raw=re.sub(r'^A21 ','A8-21 ',raw)
    res=[]
    for m in re.finditer(r'(A\d)-(\d+(?:/\d+)*)( Supplement 2)?',raw):
        nums=m.group(2).split('/')
        for i,n in enumerate(nums):
            res.append(f'{m.group(1)}-{int(n)}'+(m.group(3) or '' if i==0 else ''))
    return list(dict.fromkeys(res))
NAMES={'A8-1':'Primary Companies','A8-2':'Suppliers','A8-3':'Overhaulers','A8-6':'Test Houses','A8-8':'Design Organisations','A8-9':'Flight Under B Conditions','A8-10':'Welders',
'A8-15':'Aeroplanes and Rotorcraft Not Exceeding 2,730 Kilograms, Maintenance','A8-21':'Design or Production','A8-22':'Qualified Entities',
'A8-23':'Maintenance of Non-Part 21 Aircraft','A8-24':'Maintenance of Non-Part 21 Aircraft Below 5,700 Kilograms or Single Engined Helicopters',
'A8-25':'Continuing Airworthiness Management Organisation','A8-25 Supplement 2':'Initial Permit to Fly Reports, Military Design and Service','A8-26':'Supporting Recreational Aviation'}
def nm(x): return x+(' '+NAMES[x] if x in NAMES else '')
c=collections.Counter(); none=0
for o in d['orgs']:
    if o['a']!='BCAR': continue
    ch=chapters(cat.get(o['r'],'')) or chapters(o.get('x',''))[:1]
    if not ch and o['n'].endswith('(TRA)'): ch=['Type Responsibility Agreement']
    if not ch: none+=1; continue
    o['bc']='BCAR '+', '.join(nm(x) for x in ch)
    o['rf']=[f for f in o.get('rf',[]) if not f.startswith('BCAR|')]+['BCAR|'+x for x in ch]
    for x in ch: d['labels']['BCAR|'+x]='BCAR '+nm(x); c[x]+=1
json.dump(d,open(out,'w'),separators=(',',':'))
print(c,'no chapter:',none)
