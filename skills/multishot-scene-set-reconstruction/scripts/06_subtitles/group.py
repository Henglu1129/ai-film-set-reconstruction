import json, re, difflib
R=[json.loads(l) for l in open('all.jsonl')]
def norm(s): return re.sub(r'[^一-鿿0-9A-Za-z，。？！、…—]','',s)
seq=[]
for r in R:
    txt=''.join(i['t'] for i in r['items'] if i['c']>0.6)
    txt=norm(txt)
    # keep only strings with some Chinese
    if not re.search(r'[一-鿿]',txt): txt=''
    seq.append(txt)
events=[]
cur=None
for k,t in enumerate(seq):
    if cur and t and difflib.SequenceMatcher(None,cur['t'],t).ratio()>0.6:
        cur['k1']=k; cur['all'].append(t)
    elif cur and not t and k-cur['k1']<=1:
        continue   # single dropout
    else:
        if cur: events.append(cur)
        cur=dict(k0=k,k1=k,t=t,all=[t]) if t else None
if cur: events.append(cur)
from collections import Counter
out=[]
for e in events:
    best=Counter(e['all']).most_common(1)[0][0]
    out.append(dict(k0=e['k0'],k1=e['k1'],f0=e['k0']*4,f1=e['k1']*4+4,t0=round(e['k0']*4/24,2),t1=round((e['k1']*4+4)/24,2),zh=best,n=len(e['all'])))
out=[e for e in out if e['n']>=2]
json.dump(out,open('events_raw.json','w'),ensure_ascii=False,indent=0)
print(len(out))
for i,e in enumerate(out): print(i,e['t0'],e['t1'],e['n'],e['zh'])
