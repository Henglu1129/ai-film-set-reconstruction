import json, sys, glob, math, numpy as np
sys.path.insert(0,'/home/claude/proj/plan')
from geom import Rmat
from room import segs
from PIL import Image, ImageDraw, ImageFont, ImageFilter
FB='/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'
F=lambda s: ImageFont.truetype(FB,s,index=2)
CAMS=json.load(open('/home/claude/proj/plan/cams_v2.json'))
COL={'room':(94,220,230),'door':(255,122,61),'ac':(255,212,59),'port':(240,101,255),'sdoor':(105,219,124)}
def overlay(k,out):
    c=CAMS[k]; fn=glob.glob(f"/home/claude/proj/frames_mid/{c['ref']}_*.jpg")[0]
    im=Image.open(fn).convert('RGB'); base=im.copy()
    lay=Image.new('RGBA',im.size,(0,0,0,0)); d=ImageDraw.Draw(lay)
    C=np.array(c['C']); R=Rmat(c['yaw'],c['pitch'],c.get('roll',0)); f=960/math.tan(math.radians(c['hfov']/2))
    for a,b,t in segs():
        pts=[]
        for s in np.linspace(0,1,60):
            X=np.array(a)*(1-s)+np.array(b)*s; q=R@(X-C)
            pts.append((960+f*q[0]/q[2],402+f*q[1]/q[2]) if q[2]>0.2 else None)
        for p0,p1 in zip(pts[:-1],pts[1:]):
            if p0 and p1 and -3000<p0[0]<5000 and -3000<p0[1]<4000: d.line([p0,p1],fill=COL[t]+(255,),width=5)
    glow=lay.filter(ImageFilter.GaussianBlur(7))
    dark=Image.eval(base,lambda v:int(v*0.62))
    out_im=dark.convert('RGBA'); out_im.alpha_composite(glow); out_im.alpha_composite(glow); out_im.alpha_composite(lay)
    out_im.convert('RGB').save(out,quality=92)
for k in ['B','N','H','B2']: overlay(k,f'src/wire_{k}.jpg')
# landmark ruler on s110 (stage->door medium)
O=json.load(open('/home/claude/proj/geo/obs_v4.json'))['s110']
im=Image.open(glob.glob('/home/claude/proj/frames_mid/s110_*.jpg')[0]).convert('RGB')
im=Image.eval(im,lambda v:int(v*0.7)).convert('RGBA'); lay=Image.new('RGBA',im.size,(0,0,0,0)); d=ImageDraw.Draw(lay)
def P(n): return tuple(O[n])
door=[P('DWT'),P('DET'),P('DEB'),P('DWB')]
d.line(door+[door[0]],fill=(255,122,61,255),width=6)
ac=[P('ACWT'),P('ACET'),P('ACEB'),P('ACWB')]
d.line(ac+[ac[0]],fill=(255,212,59,255),width=6)
for n in O:
    x,y=O[n]; d.ellipse((x-9,y-9,x+9,y+9),fill=(94,220,230,255),outline=(255,255,255,255),width=2)
# person height bar at Chen
glow=lay.filter(ImageFilter.GaussianBlur(6)); im.alpha_composite(glow); im.alpha_composite(lay)
d=ImageDraw.Draw(im)
def tag(x,y,t,c):
    f=F(34); tw=d.textlength(t,font=f); d.rounded_rectangle((x,y,x+tw+28,y+52),26,fill=c); d.text((x+14,y+3),t,font=f,fill=(15,15,15))
tag(800,250,'门框：宽 3.46 m · 高 2.9 m',(255,122,61))
tag(380,660,'空调柜：高 2.15 m',(255,212,59))
tag(1180,560,'陈桂林：身高 1.80 m',(255,255,255))
# height bar beside Chen (approx from frame: head ~ (1040,330) feet ~ (1040,790)?)
im.convert('RGB').save('src/ruler_s110.jpg',quality=92)
print('ok')
