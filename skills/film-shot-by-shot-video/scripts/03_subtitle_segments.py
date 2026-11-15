"""硬字幕分段：只看字幕带（白字 + 黑描边）的二值 mask，按 IoU 判断「是不是同一条字幕」，
得到每条字幕的起止时间；每段取中间帧放大 2 倍做 OCR（rapidocr），并把字幕带存成 strips/ 供人工校对。
Y0/Y1 是 720p 画面里字幕带的位置，换片要先看一帧确认；两行字幕要往上多留。
用法：python3 03_subtitle_segments.py WORK_DIR"""
import cv2, numpy as np, json, os, sys
WORK = sys.argv[1] if len(sys.argv) > 1 else '.'
from rapidocr_onnxruntime import RapidOCR
ocr=RapidOCR()
cap=cv2.VideoCapture(os.path.join(WORK,'clip.mp4'))
fps=cap.get(cv2.CAP_PROP_FPS); step=max(1,round(fps/6))
Y0,Y1=600,712
def mask(strip):
    hsv=cv2.cvtColor(strip,cv2.COLOR_BGR2HSV)
    m=((hsv[:,:,2]>215)&(hsv[:,:,1]<40)).astype(np.uint8)
    # text must have dark outline nearby: dilate dark mask
    dark=(hsv[:,:,2]<70).astype(np.uint8)
    near=cv2.dilate(dark,np.ones((5,5),np.uint8))
    return m&near
i=0; samples=[]
while True:
    if not cap.grab(): break
    if i%step==0:
        _,fr=cap.retrieve(); st=fr[Y0:Y1,:].copy()
        samples.append((i/fps, mask(st), st))
    i+=1
# segment
segs=[]; cur=None
for t,m,st in samples:
    on=m.sum()>60
    if cur is not None:
        inter=(cur['m']&m).sum(); uni=(cur['m']|m).sum()+1
        same= on and inter/uni>0.55
        if same:
            cur['e']=t+1/6; cur['m']=cur['m']|m if False else cur['m']; cur['frames'].append((t,st)); continue
        segs.append(cur); cur=None
    if on: cur={'s':t,'e':t+1/6,'m':m,'frames':[(t,st)]}
if cur: segs.append(cur)
segs=[s for s in segs if s['e']-s['s']>=0.45]
os.makedirs(os.path.join(WORK,'strips'),exist_ok=True)
out=[]
for k,s in enumerate(segs):
    t,st=s['frames'][len(s['frames'])//2]
    cv2.imwrite(os.path.join(WORK,'strips',f's_{k:03d}.png'),st)
    big=cv2.resize(st,None,fx=2,fy=2,interpolation=cv2.INTER_CUBIC)
    r,_=ocr(big)
    txt=' '.join(x[1] for x in (r or []))
    out.append({'k':k,'s':round(s['s'],2),'e':round(s['e'],2),'ocr':txt})
json.dump(out,open(os.path.join(WORK,'subseg.json'),'w'),ensure_ascii=False,indent=0)
print('DONE',len(out))
