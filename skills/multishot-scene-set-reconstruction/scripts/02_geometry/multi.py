import json, numpy as np, math, os, sys, itertools
os.environ['OBS']='obs_v3.json'
import ba, ba2, ba3
from scipy.optimize import least_squares
from scipy.sparse import lil_matrix
def run(Lf,ds,f127,nfev=400):
    P=dict(ba.P0); P.update(Lf=Lf,ds=ds,yNW=Lf-1.5,yNE=Lf-1.5,ySW1=Lf-1.8,ySW2=Lf-0.6,ySE1=Lf-1.8,ySE2=Lf-0.6,zPb=0.5+0.6,hP=2.0,wP=1.6)
    ba.P0=P; ba3.P0=P
    C=dict(ba.CAM0)
    C['s127']=([0.3,Lf-9.6*f127/1300,0.8],0,0,f127)
    C['s010']=([1.5,3.5,1.6],0,0,2400)
    C['s027']=([-3.0,2.0,1.4],22,0,2400)
    ba.CAM0=C
    x=ba2.init()
    ba.resid=ba3.resid
    r0=ba3.resid(x); S2=lil_matrix((len(r0),len(x)),dtype=int)
    for j in range(len(x)):
        xx=x.copy(); xx[j]+=1e-4*(1+abs(x[j])); d=ba3.resid(xx)-r0
        for i in np.nonzero(np.abs(d)>1e-12)[0]: S2[i,j]=1
    # ensure camera blocks rows fully connected within a view (nonlinear coupling)

    sol=least_squares(ba3.resid,x,loss='soft_l1',f_scale=2.0,max_nfev=nfev,jac_sparsity=S2,method='trf')
    ba.resid=ba3._res
    r,det=ba3._res(sol.x,True)
    rms=float(np.sqrt(np.mean([d[4]**2 for d in det])))
    return sol, rms
if __name__=="__main__":
    res=[]
    for Lf,ds,f in itertools.product([14,17,20],[3,6],[1300,2400]):
        sol,rms=run(Lf,ds,f,nfev=250)
        p,cams,ex=ba.unpack(sol.x)
        res.append((sol.cost,rms,Lf,ds,f,p['Lf'],p['ds'],p['W'],[ (v,np.round(cams[v][0],1).tolist(),round(cams[v][4])) for v in ['s127','s010','s027','s001','s054','s110']]))
        print(round(sol.cost,1),round(rms,2),'init',Lf,ds,f,'->Lf %.2f ds %.2f W %.2f sW %.2f'%(p['Lf'],p['ds'],p['W'],p['sW']),res[-1][-1],flush=True)
        json.dump(dict(x=sol.x.tolist()),open(f'ms_{Lf}_{ds}_{f}.json','w'))
    