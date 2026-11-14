import numpy as np, cv2, json
from rapidocr_onnxruntime import RapidOCR
def iso(im):
    mn=im.min(2); mx=im.max(2)
    white=(mn>185)&((mx.astype(int)-mn)<45)
    dark=(mx<95).astype(np.uint8)
    near=cv2.dilate(dark,np.ones((5,5),np.uint8))>0
    seed=(white&near)
    n,lab,st,_=cv2.connectedComponentsWithStats(white.astype(np.uint8),connectivity=8)
    good=np.zeros(n,bool)
    ids=np.unique(lab[seed]); ids=ids[ids>0]
    for s in ids:
        x,y,w,h,a=st[s]
        if 4<=a<=2500 and w<=60 and h<=45 and 8<=y+h/2<=70: good[s]=True
    keep=good[lab]
    return keep
N=2781; masks=[]; cnt=[]; cx=[]
for k in range(N):
    im=cv2.imread(f'band/b{k:05d}.jpg'); m=iso(im); masks.append(m)
    ys,xs=np.where(m); cnt.append(len(xs)); cx.append(float(xs.mean()) if len(xs) else -1)
cnt=np.array(cnt); cx=np.array(cx)
present=(cnt>60)&(np.abs(cx-480)<230)
# segment
ev=[]; cur=None
def sim(a,b):
    A=cv2.dilate(a.astype(np.uint8),np.ones((5,5),np.uint8))>0; B=cv2.dilate(b.astype(np.uint8),np.ones((5,5),np.uint8))>0
    return (A&B).sum()/max(1,(A|B).sum())
for k in range(N):
    if present[k]:
        if cur and k-cur['k1']<=2 and sim(masks[cur['ref']],masks[k])>0.45:
            cur['k1']=k
            if cnt[k]>cnt[cur['ref']]: cur['ref']=k
        else:
            if cur: ev.append(cur)
            cur=dict(k0=k,k1=k,ref=k)
if cur: ev.append(cur)
eng=RapidOCR()
out=[]
for e in ev:
    im=cv2.imread(f"band/b{e['ref']:05d}.jpg")
    m=masks[e['ref']]
    clean=np.full(im.shape[:2],255,np.uint8); clean[cv2.dilate(m.astype(np.uint8),np.ones((2,2),np.uint8))>0]=0
    clean=cv2.copyMakeBorder(clean,20,20,20,20,cv2.BORDER_CONSTANT,value=255)
    clean=cv2.resize(clean,None,fx=2,fy=2,interpolation=cv2.INTER_CUBIC)
    big=cv2.resize(im,None,fx=2,fy=2,interpolation=cv2.INTER_CUBIC)
    best=('',0)
    for img in (clean,big):
        r,_=eng(img)
        if r:
            t=''.join(x[1] for x in r); c=float(np.mean([float(x[2]) for x in r]))
            if c>best[1]: best=(t,c)
    out.append(dict(k0=e['k0'],k1=e['k1'],ref=e['ref'],t0=round(e['k0']*4/24,2),t1=round((e['k1']*4+4)/24,2),zh=best[0],conf=round(best[1],3)))
json.dump(out,open('events_v2.json','w'),ensure_ascii=False,indent=0)
print(len(out))
for i,e in enumerate(out): print(i,e['t0'],e['t1'],e['conf'],e['zh'])
