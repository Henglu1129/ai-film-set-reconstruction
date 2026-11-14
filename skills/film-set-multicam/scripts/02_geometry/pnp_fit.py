import json, numpy as np, math, sys
from scipy.optimize import least_squares
sys.path.insert(0,'.')
from ba import Rmat, proj
RM=json.load(open('room_final.json'))
def L(n,chen=None):
    W=RM['W']; Lf=RM['Lf']; d=RM['door']; a=RM['ac']; p=RM['portrait']; yN=Lf+RM['ds']-0.03
    xD=d['xc']; t=0.25
    m={'DET':(xD+d['half'],0,d['top']),'DWT':(xD-d['half'],0,d['top']),'DEB':(xD+d['half'],0,0),'DWB':(xD-d['half'],0,0),
       'DXE':(xD+d['half'],0,d['cross']),'DXW':(xD-d['half'],0,d['cross']),'OEB':(xD+d['open_half'],0,0),'OWB':(xD-d['open_half'],0,0),
       'OETo':(xD+d['open_half'],-t,d['cross']),'OWTo':(xD-d['open_half'],-t,d['cross']),'OET':(xD+d['open_half'],0,d['cross']),'OWT':(xD-d['open_half'],0,d['cross']),
       'ACWT':(a['x0'],a['y1'],a['h']),'ACET':(a['x1'],a['y1'],a['h']),'ACWB':(a['x0'],a['y1'],0),'ACEB':(a['x1'],a['y1'],0),
       'SCE':(xD+RM['sconce_back']['dx'],0.25,RM['sconce_back']['z']),'SCW':(xD-RM['sconce_back']['dx'],0.25,RM['sconce_back']['z']),
       'SFWT':(-W/2,Lf,RM['hs']),'SFWB':(-W/2,Lf,0),'SFET':(W/2,Lf,RM['hs']),'SFEB':(W/2,Lf,0),
       'PWT':(p['xc']-p['w']/2,yN,p['zb']+p['h']),'PET':(p['xc']+p['w']/2,yN,p['zb']+p['h']),'PWB':(p['xc']-p['w']/2,yN,p['zb']),'PEB':(p['xc']+p['w']/2,yN,p['zb']),
       'NDW_TS':(-W/2,RM['side_door_W']['y0'],RM['side_door_W']['h']),'NDW_TN':(-W/2,RM['side_door_W']['y1'],RM['side_door_W']['h']),'NDW_BS':(-W/2,RM['side_door_W']['y0'],0),
       'NDE_TS':(W/2,RM['side_door_E']['y0'],RM['side_door_E']['h']),'NDE_TN':(W/2,RM['side_door_E']['y1'],RM['side_door_E']['h']),'NDE_BS':(W/2,RM['side_door_E']['y0'],0)}
    if n in m: return np.array(m[n],float)
    if n.startswith('SW') or n.startswith('SE'):   # side sconce by index e.g. SW3 -> sconce_side_W[3]
        side=n[1]; i=int(n[2:]); y=RM['sconce_side_'+side][i]; x=(-W/2+0.25) if side=='W' else (W/2-0.25)
        return np.array([x,y,RM['sconce_side_z']])
    if n=='SNW1': return L('SW4')
    if n=='SNW2': return L('SW5')
    if n=='SNE1': return L('SE4')
    if n=='SNE2': return L('SE5')
    if n.startswith('XYZ:'): return np.array(list(map(float,n[4:].split(','))))
    raise KeyError(n)
def fit(obs, init, fprior=None, cprior=None, chen=None, k1free=False, verbose=True):
    names=[n for n in obs if not n.startswith('CH') and not n.startswith('VL')]
    X=[L(n) for n in names]; U=np.array([obs[n] for n in names],float)
    chen_obs=[(n,obs[n]) for n in obs if n.startswith('CH')]
    C0,yaw0,pit0,f0=init
    x0=list(C0)+[yaw0,pit0,0.0,math.log(f0)]+([0.0] if k1free else [])
    if chen_obs: x0+= list(chen if chen else [0,6])
    def res(x):
        C=x[:3]; R=Rmat(x[3],x[4],x[5]); f=math.exp(x[6]); k1=x[7] if k1free else 0.0
        r=[]
        for Xi,ui in zip(X,U):
            pr,z=proj(Xi,C,R,f,k1); r+=list((pr-ui)/3.0) if z>0.1 else [50,50]
        if chen_obs:
            j=8 if k1free else 7
            cx,cy=x[j],x[j+1]
            for n,uv in chen_obs:
                Z=1.80 if n=='CH_H' else 0.03
                pr,z=proj(np.array([cx,cy,Z]),C,R,f,k1); r+=list((pr-np.array(uv))/3.0)
        if fprior: r.append((f-fprior[0])/fprior[1])
        if cprior: r+=list((np.array(C)-np.array(cprior[0]))/np.array(cprior[1]))
        if k1free: r.append(k1/0.05)
        return np.array(r)
    s=least_squares(res,x0,loss='soft_l1',f_scale=2.0,max_nfev=3000)
    x=s.x; C=x[:3]; f=math.exp(x[6])
    rr=res(x)[:2*len(names)].reshape(-1,2)*3.0
    out=dict(C=[round(float(c),2) for c in C],yaw=round(float(x[3]),1),pitch=round(float(x[4]),1),roll=round(float(x[5]),1),f=round(f),hfov=round(math.degrees(2*math.atan(960/f)),1))
    if k1free: out['k1']=round(float(x[7]),3)
    if chen_obs: j=8 if k1free else 7; out['chen']=[round(float(x[j]),2),round(float(x[j+1]),2)]
    out['err']={n:round(float(np.hypot(*e)),1) for n,e in zip(names,rr)}
    out['rms']=round(float(np.sqrt(np.mean([np.sum(e**2) for e in rr]))),1)
    return out
if __name__=='__main__':
    O=json.load(open('obs_v3.json'))
    inits={'s110':([0,20.5,1.5],180,0,2100),'s054':([0,21.5,2.3],180,-15,1470),'s004':([0,20.5,1.3],180,-1,4500),'s001':([0.5,19.5,1.0],180,-3,1650),
           's127':([1,9,0.9],-5,-1,1360),'s010':([-2,3.2,1.3],10,-2,2040),'s027':([-1,0.1,1.35],21,-3,2140),'s055':([0.3,-5,2.2],-1,0.7,3100)}
    res={}
    for v in O:
        obs={k:val for k,val in O[v].items() if not k.startswith('BB')}
        r=fit(obs,inits[v],k1free=(v=='s127'))
        res[v]=r; print(v,{k:r[k] for k in r if k!='err'}); print('   ',r['err'])
    json.dump(res,open('pnp_room_final.json','w'),indent=0)
