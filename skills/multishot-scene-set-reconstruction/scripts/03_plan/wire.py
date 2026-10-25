import json, sys, glob, math, numpy as np
from geom import Rmat
from room import segs
from PIL import Image, ImageDraw, ImageFont
CAMS=json.load(open(sys.argv[1])); out=sys.argv[2]
COL={'room':(0,255,255),'door':(255,80,80),'ac':(255,255,0),'port':(255,0,255),'sdoor':(80,255,80)}
CX,CY=960,402
def proj(X,C,R,f):
    q=R@(np.array(X)-C); return (CX+f*q[0]/q[2],CY+f*q[1]/q[2],q[2])
tiles=[]
fnt=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc',30)
for k,c in CAMS.items():
    fn=glob.glob(f"/home/claude/proj/frames_mid/{c['ref']}_*.jpg")[0]
    im=Image.open(fn).convert('RGB'); d=ImageDraw.Draw(im)
    C=np.array(c['C']); R=Rmat(c['yaw'],c['pitch'],c.get('roll',0)); f=960/math.tan(math.radians(c['hfov']/2))
    for a,b,t in segs():
        # clip by sampling
        pts=[]
        for s in np.linspace(0,1,40):
            X=np.array(a)*(1-s)+np.array(b)*s; u,v,z=proj(X,C,R,f)
            pts.append((u,v) if z>0.2 else None)
        for p0,p1 in zip(pts[:-1],pts[1:]):
            if p0 and p1 and -2000<p0[0]<4000 and -2000<p0[1]<3000: d.line([p0,p1],fill=COL[t],width=3)
    d.text((20,20),f"{k} {c['name']} ({c['ref']})",fill=(255,255,0),font=fnt)
    tiles.append(im.resize((960,402)))
H=402*((len(tiles)+1)//2); S=Image.new('RGB',(1920,H))
for i,t in enumerate(tiles): S.paste(t,((i%2)*960,(i//2)*402))
S.save(out,quality=88)
