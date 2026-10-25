import json, math
from PIL import Image, ImageDraw, ImageFont
P=json.load(open('/home/claude/proj/plan/plan_data.json')); SET={s['id']:s for s in P['setups']}
A=json.load(open('src/render_overview_v1/anchors_overview.json'))['overview_all']
A={k:(v[0]/2,v[1]/2,v[2]) for k,v in A.items()}
F=lambda s: ImageFont.truetype('/usr/share/fonts/opentype/inter/Inter-Bold.otf',s)
BG=(12,14,19)
im=Image.open('src/render_overview_v1/overview_all.png').convert('RGBA'); b=Image.new('RGBA',im.size,BG+(255,)); b.alpha_composite(im)
d=ImageDraw.Draw(b)
def hexc(h): return tuple(int(h[i:i+2],16) for i in (1,3,5))
def ov(a,c,m=4): return not (a[2]+m<c[0] or c[2]+m<a[0] or a[3]+m<c[1] or c[3]+m<a[1])
placed=[]
for key,t,col,fg in (('chen','Chen',(255,70,60),(255,255,255)),('leader','Leader',(246,195,67),(30,30,30))):
    u,v,z=A[key]; f=F(24); tw=d.textlength(t,font=f); bx=(u-tw/2-10,v-62,u+tw/2+10,v-28)
    d.rounded_rectangle(bx,8,fill=col); d.text((bx[0]+10,bx[1]+4),t,font=f,fill=fg); placed.append(bx)
for k in [s['id'] for s in P['setups']]:
    u,v,z=A['cam:'+k]; col=hexc(SET[k]['color']); f=F(24); tw=d.textlength(k,font=f)+18; th=34
    best=None
    for r in (50,80,115,150):
        for ang in (-90,-60,-120,-30,-150,90,60,120,0,180):
            x0=u+r*math.cos(math.radians(ang))-tw/2; y0=v+r*math.sin(math.radians(ang))-th/2
            x0=min(max(6,x0),2160-tw-6); y0=min(max(60,y0),1240-th-6); c=(x0,y0,x0+tw,y0+th)
            if not any(ov(c,p) for p in placed): best=c; break
        if best: break
    best=best or (u-tw/2,v-60,u+tw/2,v-26)
    d.line((u,v,(best[0]+best[2])/2,(best[1]+best[3])/2),fill=col,width=3); d.ellipse((u-7,v-7,u+7,v+7),outline=col,width=3)
    d.rounded_rectangle(best,8,fill=col); d.text((best[0]+9,best[1]+3),k,font=f,fill=(18,18,18)); placed.append(best)
d.text((150,1180),'← South: main door',font=F(30),fill=(220,220,220)); d.text((1720,1180),'North: stage →',font=F(30),fill=(220,220,220))
b.convert('RGB').save('src/overview_en.jpg',quality=92)
