import json, numpy as np, math
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
M=json.load(open('sfm_models.json'))
def rot_to(a,b):
    a=a/np.linalg.norm(a); b=b/np.linalg.norm(b); v=np.cross(a,b); c=a@b
    if np.linalg.norm(v)<1e-9: return np.eye(3)
    vx=np.array([[0,-v[2],v[1]],[v[2],0,-v[0]],[-v[1],v[0],0]])
    return np.eye(3)+vx+vx@vx*(1/(1+c))
res={}
fig,axs=plt.subplots(1,3,figsize=(21,7))
for ax,k in zip(axs,['0','3','2']):
    m=M[k]; ims=m['images']; P=np.array(m['points'])
    ups=[]; fw=[]
    for n,d in ims.items():
        R=np.array(d['R']); ups.append(-R[1]); fw.append(R[2])
    up=np.mean(ups,0); up/=np.linalg.norm(up)
    G=rot_to(up,np.array([0,0,1.]))
    X=(G@P[:,:3].T).T
    good=(P[:,6]>=3)&(P[:,7]<1.5)
    C={n:G@np.array(d['C']) for n,d in ims.items()}
    F={n:G@np.array(d['R'])[2] for n,d in ims.items()}
    ax.scatter(X[good,0],X[good,1],s=2,c=P[good,3:6]/255.)
    for n in ims:
        c=C[n]; f=F[n]; ax.plot(c[0],c[1],'r^'); ax.arrow(c[0],c[1],f[0]*0.5,f[1]*0.5,color='r',width=0.005)
        ax.text(c[0],c[1],n[1:4],fontsize=7)
    ax.set_aspect('equal'); ax.set_title('model '+k)
    # stats
    hf={n:math.degrees(2*math.atan(640/d['f'])) for n,d in ims.items()}
    res[k]=dict(G=G.tolist(),hfov=hf,zs={n:float(C[n][2]) for n in ims})
    print('model',k,'up dev deg', np.degrees(np.arccos(np.clip([u@up for u in ups],-1,1))).round(1).tolist()[:10])
    print(' z range pts', np.percentile(X[good,2],[2,50,98]).round(2), 'cam z', np.round(sorted(res[k]['zs'].values()),2)[:5],'...')
    print(' hfov', {n[:4]:round(v,1) for n,v in hf.items()})
plt.tight_layout(); plt.savefig('/tmp/claude-0/-home-claude/d518d837-5c78-547f-a7cd-4645529d86c6/scratchpad/sfm_top.png',dpi=70)
json.dump(res,open('sfm_grav.json','w'))
