import json, math, numpy as np
from pnp_fit import fit
O=json.load(open('obs_v4.json'))
# fixed focal from SfM HFOV (1920 px) except s054 from vanishing points
F={'s001':1663,'s004':4630,'s054':1420,'s110':1997,'s049':2425,'s056':2766,'s135':2818}
out={}
for v,f in F.items():
    obs={k:val for k,val in O[v].items() if not k.startswith('BB') and not k.startswith('VL')}
    r=fit(obs,([0,18,1.4],180,0,f),fprior=(f,f*0.01))
    out[v]=r; print(v,{k:r[k] for k in r if k!='err'},'\n   ',r['err'])
json.dump(out,open('pnp_south.json','w'),indent=0)
