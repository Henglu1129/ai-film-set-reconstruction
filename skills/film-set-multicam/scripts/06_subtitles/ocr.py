import sys, json, time, os
from rapidocr_onnxruntime import RapidOCR
eng=RapidOCR()
ks=[int(x) for x in sys.argv[2:]] if len(sys.argv)>2 else range(2781)
out=open(sys.argv[1],'a')
t=time.time()
for k in ks:
    res,_=eng(f'band/b{k:05d}.jpg')
    items=[]
    for box,txt,conf in (res or []):
        xs=[p[0] for p in box]; ys=[p[1] for p in box]
        items.append(dict(t=txt,c=round(float(conf),3),x0=min(xs),x1=max(xs),y0=min(ys),y1=max(ys)))
    out.write(json.dumps(dict(k=k,items=items),ensure_ascii=False)+'\n'); out.flush()
print('time',time.time()-t)
