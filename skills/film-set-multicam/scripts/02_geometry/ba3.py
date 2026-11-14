import json, numpy as np, math, os, sys
from scipy.optimize import least_squares
import ba
FIX=json.load(open(os.environ.get('FIX','fix.json')))      # room params to hold fixed
FPRI=json.load(open(os.environ.get('FPRI','fpri.json')))   # per-view focal priors {view:[f,sigma]}
CPRI=json.load(open(os.environ.get('CPRI','cpri.json')))   # per-view centre priors {view:[[x,y,z],[sx,sy,sz]]}
P0=dict(ba.P0); P0.update(FIX)
_res=ba.resid
def resid(x,detail=False):
    out=_res(x,detail)
    r,det=(out if detail else (out,None))
    p,cams,ex=ba.unpack(x); extra=[]
    for v,(f0,s) in FPRI.items():
        if v in cams: extra.append((cams[v][4]-f0)/s)
    for v,(c0,s) in CPRI.items():
        if v in cams: extra+=list((np.array(cams[v][0])-np.array(c0))/np.array(s))
    for k,val in FIX.items(): extra.append((p[k]-val)/0.002)
    grp=[('s001',0.4),('s004',0.4),('s010',0.5),('s027',0.8)]
    ref='s004'
    for v,sg in grp:
        if v!=ref and v in ex and 'chx' in ex[v]:
            extra+=[(ex[v]['chx']-ex[ref]['chx'])/sg,(ex[v]['chy']-ex[ref]['chy'])/sg]
    for k,(m,sg) in json.load(open(os.environ.get('RPRI','rpri.json'))).items(): extra.append((p[k]-m)/sg)
    r=np.concatenate([r,extra])
    return (r,det) if detail else r
ba.resid_orig=_res
if __name__=='__main__':
    import ba2
    ba.P0=P0
    x=ba2.init()
    ba.resid=resid
    from scipy.sparse import lil_matrix
    S,blocks=ba2.sparsity(x)
    nextra=len(resid(x))-S.shape[0]
    S2=lil_matrix((S.shape[0]+nextra,S.shape[1]),dtype=int); S2[:S.shape[0]]=S; S2[S.shape[0]:,:]=1
    sol=least_squares(resid,x,loss='soft_l1',f_scale=2.0,max_nfev=500,jac_sparsity=S2,method='trf')
    ba2.ba.resid=lambda x,d=False: _res(x,d)
    ba2.report(sol.x)
    json.dump(dict(x=sol.x.tolist()),open(os.environ.get('OUT','ba3_sol.json'),'w'))
