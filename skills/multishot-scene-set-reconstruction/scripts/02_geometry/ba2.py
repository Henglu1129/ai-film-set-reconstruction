import json, numpy as np, math, sys
from scipy.optimize import least_squares
from scipy.sparse import lil_matrix
import ba
OBS=ba.OBS; views=ba.views; pk=ba.pk
def init():
    import json as _j, os as _o
    cp=_j.load(open(_o.environ.get('CPRI','cpri.json')))
    cams0={v:(np.array(cp[v][0] if v in cp else c[0],float),c[1],c[2],0.0,c[3],0.0) for v,c in ba.CAM0.items() if v in views}
    ex0={}
    for v in views:
        ex0[v]={}
        for k in ba.exk[v]:
            if k.startswith('BB'): ex0[v][k]=10.0
        if 'chx' in ba.exk[v]: ex0[v]['chx']=0.0; ex0[v]['chy']=5.3
    return ba.pack(ba.P0,cams0,ex0)
def sparsity(x):
    # build by structure: residual rows per view depend on room params + that view's block
    n=len(x); rows=[]
    i=len(pk); blocks={}
    for v in views:
        nb=8+len(ba.exk[v]); blocks[v]=(i,i+nb); i+=nb
    m=[]
    for v in views:
        for nme in OBS[v]: m+= [v] if nme.startswith('VL') else [v,v]
        m.append(v)
    m+= ['prior']*len(ba.PRI)
    S=lil_matrix((len(m),n),dtype=int)
    for r,v in enumerate(m):
        S[r,:len(pk)]=1
        if v!='prior':
            a,b=blocks[v]; S[r,a:b]=1
    return S,blocks
def solve(x0,free_room=True,nfev=200):
    S,blocks=sparsity(x0)
    if not free_room:
        mask=np.ones(len(x0),bool); mask[:len(pk)]=False
        def f(xs):
            x=x0.copy(); x[mask]=xs; return ba.resid(x)
        sol=least_squares(f,x0[mask],loss='soft_l1',f_scale=2.0,max_nfev=nfev,jac_sparsity=S[:,mask],method='trf')
        x=x0.copy(); x[mask]=sol.x; return x
    sol=least_squares(ba.resid,x0,loss='soft_l1',f_scale=2.0,max_nfev=nfev,jac_sparsity=S,method='trf')
    return sol.x
def report(x):
    r,det=ba.resid(x,True); p,cams,ex=ba.unpack(x)
    print('rms px', round(float(np.sqrt(np.mean([d[4]**2 for d in det]))),2))
    print(' '.join(f"{k}={p[k]:.2f}" for k in pk))
    for v in views:
        C,yw,pt,rl,fl,k1=cams[v]; errs=[round(d[4],1) for d in det if d[0]==v]
        print(f"{v}: C=({C[0]:.2f},{C[1]:.2f},{C[2]:.2f}) yaw={yw:.1f} pit={pt:.1f} rol={rl:.1f} f={fl:.0f} hfov={math.degrees(2*math.atan(960/fl)):.1f} k1={k1:.3f} ex={ {k:round(vv,2) for k,vv in ex[v].items()} }\n    err={errs}")
if __name__=='__main__':
    import time; t=time.time()
    x=init()
    x=solve(x,free_room=False,nfev=300); print('stage1',time.time()-t); report(x)
    x=solve(x,free_room=True,nfev=400); print('stage2',time.time()-t); report(x)
    json.dump(dict(x=x.tolist()),open('ba_sol.json','w'))
