import cv2, numpy as np, glob, json, sys
exec(open('/mnt/skills/plugins/film-set-reconstruction/scripts/vp_focal.py').read().split('R = {}')[0].replace('cx, cy = 640.0, 277.0','cx, cy = 960.0, 402.0'))
out={}
for sid in sys.argv[1:]:
    fn=glob.glob(f'frames_mid/s{int(sid):03d}_*.jpg')[0]
    g=cv2.imread(fn,0); L=lsd.detect(g)[0].reshape(-1,4).astype(float)
    ln=np.hypot(L[:,2]-L[:,0],L[:,3]-L[:,1]); m=(ln>45); L,ln=L[m],ln[m]
    V=vps(L,ln,k=3,iters=3000)
    info=[]; fs=[]
    for a in range(len(V)):
        va=V[a][1]; fin=abs(va[2])>1e-6*np.linalg.norm(va)
        info.append((V[a][2], (va[:2]/va[2]).round(0).tolist() if fin else ('inf',(va[:2]/np.linalg.norm(va[:2])).round(3).tolist())))
        for b in range(a+1,len(V)):
            vb=V[b][1]
            if not fin or abs(vb[2])<1e-6*np.linalg.norm(vb): continue
            pa=va[:2]/va[2]-[cx,cy]; pb=vb[:2]/vb[2]-[cx,cy]; f2=-(pa@pb)
            if f2>0: f=np.sqrt(f2); fs.append((round(float(np.degrees(2*np.arctan(cx/f))),1),round(float(f)),a,b))
    print(sid, info, fs)
