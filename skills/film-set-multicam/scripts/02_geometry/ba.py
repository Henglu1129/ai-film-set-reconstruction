import json, numpy as np, math, sys
from scipy.optimize import least_squares
import os
OBS=json.load(open(os.environ.get('OBS','obs_v2.json')))
CX,CY=960.0,402.0
P0=dict(sW=10.3,W=10.4,Lf=17.5,ds=4.0,hs=0.55,xD=0.0,dW=1.45,hDT=2.45,hDX=2.0,oW=0.85,yAC=0.7,xACw=2.2,wAC=1.5,hAC=1.95,xSB=1.7,zSB=2.2,
        xP=0.0,wP=1.3,hP=1.7,zPb=1.95,yNW=16.0,wND=0.9,hND=2.1,yNE=16.0,ySW1=15.7,ySW2=16.9,ySE1=15.7,ySE2=16.9,zSS=2.2)
PRI=dict(hDX=(2.05,0.25),hND=(2.1,0.25),hAC=(1.9,0.2),wND=(0.9,0.2))   # weak priors
CAM0={'s110':([0,20.3,1.2],180,0,1997),'s054':([0,20.3,2.59],180,-16.5,1420),'s004':([0.3,21.7,1.3],180,0,4630),
      's127':([0.5,10.5,0.8],0,0,1330),'s010':([2.0,1.5,1.6],-3,0,1760),'s027':([-4.0,3.0,1.4],65,0,1300),'s055':([0,-3.0,1.5],0,0,3000),'s001':([0,17.5,1.3],180,0,1700)}
pk=list(P0)
def landmark(n,p,ext):
    W=p['W']; L=p['Lf']; t=0.25
    m={'DET':(p['xD']+p['dW'],0,p['hDT']),'DWT':(p['xD']-p['dW'],0,p['hDT']),'DEB':(p['xD']+p['dW'],0,0),'DWB':(p['xD']-p['dW'],0,0),
       'DXE':(p['xD']+p['dW'],0,p['hDX']),'DXW':(p['xD']-p['dW'],0,p['hDX']),'OEB':(p['xD']+p['oW'],0,0),'OWB':(p['xD']-p['oW'],0,0),
       'OETo':(p['xD']+p['oW'],-t,p['hDX']),'OWTo':(p['xD']-p['oW'],-t,p['hDX']),
       'ACWT':(p['xACw'],p['yAC'],p['hAC']),'ACET':(p['xACw']+p['wAC'],p['yAC'],p['hAC']),'ACWB':(p['xACw'],p['yAC'],0),'ACEB':(p['xACw']+p['wAC'],p['yAC'],0),
       'SCE':(p['xD']+p['xSB'],0.25,p['zSB']),'SCW':(p['xD']-p['xSB'],0.25,p['zSB']),
       'SFWT':(-p['sW']/2,L,p['hs']),'SFWB':(-p['sW']/2,L,0),'SFET':(p['sW']/2,L,p['hs']),'SFEB':(p['sW']/2,L,0),
       'PWT':(p['xP']-p['wP']/2,L+p['ds']-0.03,p['zPb']+p['hP']),'PET':(p['xP']+p['wP']/2,L+p['ds']-0.03,p['zPb']+p['hP']),
       'PWB':(p['xP']-p['wP']/2,L+p['ds']-0.03,p['zPb']),'PEB':(p['xP']+p['wP']/2,L+p['ds']-0.03,p['zPb']),
       'NDW_TS':(-W/2,p['yNW'],p['hND']),'NDW_TN':(-W/2,p['yNW']+p['wND'],p['hND']),'NDW_BS':(-W/2,p['yNW'],0),
       'NDE_TS':(W/2,p['yNE'],p['hND']),'NDE_TN':(W/2,p['yNE']+p['wND'],p['hND']),
       'SNW1':(-W/2+0.25,p['ySW1'],p['zSS']),'SNW2':(-W/2+0.25,p['ySW2'],p['zSS']),'SNE1':(W/2-0.25,p['ySE1'],p['zSS']),'SNE2':(W/2-0.25,p['ySE2'],p['zSS'])}
    if n in m: return np.array(m[n],float)
    if n.startswith('BBE'): return np.array([W/2,ext[n],0.0])
    if n.startswith('BBW'): return np.array([-W/2,ext[n],0.0])
    if n=='CH_H': return np.array([ext['chx'],ext['chy'],1.80])
    if n=='CH_Hx': return np.array([ext['chx'],ext['chy'],1.80])
    if n=='CH_F': return np.array([ext['chx'],ext['chy'],0.03])
    raise KeyError(n)
def Rmat(yaw,pitch,roll):
    y,p,r=map(math.radians,(yaw,pitch,roll))
    f=np.array([math.sin(y)*math.cos(p),math.cos(y)*math.cos(p),math.sin(p)])
    r0=np.array([math.cos(y),-math.sin(y),0.0]); u0=np.cross(r0,f)
    rr=r0*math.cos(r)+u0*math.sin(r); uu=-r0*math.sin(r)+u0*math.cos(r)
    return np.vstack([rr,-uu,f])
def proj(X,C,R,fl,k1=0):
    q=R@(X-C); x=q[0]/q[2]; y=q[1]/q[2]; r2=(x*x+y*y)
    d=1+k1*r2
    return np.array([CX+fl*x*d,CY+fl*y*d]), q[2]
views=list(OBS)
# extras per view
exk={}
for v in views:
    ks=[]
    for n in OBS[v]:
        if n.startswith('BB'): ks.append(n)
    if 'CH_H' in OBS[v]: ks+=['chx','chy']
    exk[v]=ks
def pack(p,cams,ex):
    x=[p[k] for k in pk]
    for v in views:
        C,yw,pt,rl,fl,k1=cams[v]; x+=list(C)+[yw,pt,rl,math.log(fl),k1]
        x+=[ex[v][k] for k in exk[v]]
    return np.array(x,float)
def unpack(x):
    p=dict(zip(pk,x[:len(pk)])); i=len(pk); cams={}; ex={}
    for v in views:
        C=x[i:i+3]; yw,pt,rl,lf,k1=x[i+3:i+8]; i+=8
        cams[v]=(C,yw,pt,rl,math.exp(lf),k1)
        ex[v]={k:x[i+j] for j,k in enumerate(exk[v])}; i+=len(exk[v])
    return p,cams,ex
SIG=4.0
def resid(x,detail=False):
    p,cams,ex=unpack(x); r=[]; det=[]
    for v in views:
        C,yw,pt,rl,fl,k1=cams[v]; R=Rmat(yw,pt,rl)
        for n,uv in OBS[v].items():
            if n.startswith('VL'):
                (u1,v1),(u2,v2)=uv
                vz=R@np.array([0,0,1.0]);
                # vanishing point of world-up (could be at infinity): direction from p2 towards VP
                p2=np.array([u2,v2],float); p1=np.array([u1,v1],float)
                # back-project p2 to a ray, move up 1m along world z, project
                ray=np.linalg.inv(np.array([[fl,0,CX],[0,fl,CY],[0,0,1]]))@np.array([u2,v2,1.0])
                Xc=ray*8.0; Xw=R.T@Xc+C; Xu=Xw+np.array([0,0,3.0]); pu,_=proj(Xu,C,R,fl,0)
                dvec=pu-p2; dvec/=np.linalg.norm(dvec); w=p1-p2
                perp=w[0]*dvec[1]-w[1]*dvec[0]
                r+=[perp/SIG]; det.append((v,n,[0,0],[0,0],abs(perp))); continue
            X=landmark(n,p,ex[v]); pr,z=proj(X,C,R,fl,k1)
            e=(pr-np.array(uv))/SIG
            if z<0.1: e=e*0+50
            r+=list(e); det.append((v,n,pr.round(1).tolist(),uv,float(np.hypot(*(pr-uv)))))
        r.append(k1/0.05)  # small distortion prior
    for k,(m,s) in PRI.items(): r.append((p[k]-m)/s)
    return (np.array(r),det) if detail else np.array(r)
if __name__=='__main__':
    cams0={v:(np.array(c[0],float),c[1],c[2],0.0,c[3],0.0) for v,c in CAM0.items() if v in views}
    ex0={}
    for v in views:
        ex0[v]={}
        for k in exk[v]:
            if k.startswith('BB'): ex0[v][k]=10.0
        if 'chx' in exk[v]: ex0[v]['chx']=0.0; ex0[v]['chy']=5.3
    x0=pack(P0,cams0,ex0)
    # stage 1: per-view only with room fixed? just solve all
    sol=least_squares(resid,x0,loss='soft_l1',f_scale=2.0,max_nfev=3000,x_scale='jac',verbose=1)
    r,det=resid(sol.x,True); p,cams,ex=unpack(sol.x)
    print('cost',sol.cost, 'rms px', np.sqrt(np.mean([d[4]**2 for d in det])))
    for k in pk: print(f"  {k}={p[k]:.3f}",end='')
    print()
    for v in views:
        C,yw,pt,rl,fl,k1=cams[v]
        errs=[d[4] for d in det if d[0]==v]
        print(f"{v}: C=({C[0]:.2f},{C[1]:.2f},{C[2]:.2f}) yaw={yw:.1f} pitch={pt:.1f} roll={rl:.1f} f={fl:.0f} hfov={math.degrees(2*math.atan(960/fl)):.1f} k1={k1:.3f} ex={ {k:round(vv,2) for k,vv in ex[v].items()} } err={np.round(errs,1).tolist()}")
    json.dump(dict(x=sol.x.tolist()),open('ba_sol.json','w'))
