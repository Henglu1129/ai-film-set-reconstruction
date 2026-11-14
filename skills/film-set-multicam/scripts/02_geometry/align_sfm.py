import json, numpy as np, math, sys
sys.path.insert(0,'.')
import ba
M=json.load(open('../sfm_models.json')); R1=json.load(open('room_v1.json'))
def umeyama(A,B,with_scale=True):
    mA=A.mean(0); mB=B.mean(0); A0=A-mA; B0=B-mB
    U,S,Vt=np.linalg.svd(B0.T@A0/len(A)); D=np.eye(3)
    if np.linalg.det(U@Vt)<0: D[2,2]=-1
    Rm=U@D@Vt; s=(S*np.diag(D)).sum()/((A0**2).sum()/len(A)) if with_scale else 1.0
    t=mB-s*Rm@mA; return s,Rm,t
def world_cams(k, refs):
    m=M[k]['images']
    A=np.array([m[n]['C'] for n in refs]); B=np.array([R1['cams'][n.split('_')[0]]['C'] for n in refs])
    # also use orientation consistency: add points 1m ahead of each camera
    A2=[];B2=[]
    for n in refs:
        Rs=np.array(m[n]['R']); A2.append(np.array(m[n]['C'])+Rs[2]*3); 
        c=R1['cams'][n.split('_')[0]]; Rw=ba.Rmat(c['yaw'],c['pitch'],c['roll']); B2.append(np.array(c['C'])+Rw[2]*3)
    AA=np.vstack([A,A2]); BB=np.vstack([B,B2])
    s,Rm,t=umeyama(AA,BB)
    res=np.linalg.norm((s*(Rm@AA.T)).T+t-BB,axis=1)
    print('model',k,'scale m/unit',round(s,3),'fit resid',res.round(2))
    out={}
    for n,d in m.items():
        C=s*Rm@np.array(d['C'])+t; Rw=np.array(d['R'])@Rm.T
        f=Rw[2]; yaw=math.degrees(math.atan2(f[0],f[1])); pitch=math.degrees(math.asin(np.clip(f[2],-1,1)))
        r0=np.array([math.cos(math.radians(yaw)),-math.sin(math.radians(yaw)),0]); roll=math.degrees(math.asin(np.clip(-Rw[1]@np.cross(r0,f)*0+Rw[0]@np.array([0,0,1.0]),-1,1)))
        out[n]=dict(C=C.round(2).tolist(),yaw=round(yaw,1),pitch=round(pitch,1),roll=round(roll,1),f=round(d['f']*1.5),hfov=round(math.degrees(2*math.atan(640/d['f'])),1))
    return out
w0=world_cams('0',['s001_f00033.jpg','s004_f00203.jpg','s054_f06281.jpg','s110_f09001.jpg'])
for n in sorted(w0): print(n[:4],w0[n])
json.dump(w0,open('sfm0_world.json','w'),indent=0)
