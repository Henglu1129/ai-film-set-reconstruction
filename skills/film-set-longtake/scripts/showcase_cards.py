# ==== 《大事件》(2004) 开场长镜头项目里的实际代码，原样保留作参考 ====
# 里面的路径（/tmp/claude-0/...、/mnt/user-data/...）、坐标、车辆尺寸、帧号区间都是那部片子的，换片时逐项改。
# 约定：机位 R 为 世界→相机（OpenCV：x 右 y 下 z 前），C 为相机中心；画面 1280×554 时 CX=640 CY=277、HFOV=42°。
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os
W,H=1080,1440
BG=(13,16,21); INK=(236,239,243); MUT=(150,159,169); ACC=(255,122,61); PANEL=(26,31,38); CY=(94,220,230)
def F(s,b=False): return ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-%s.ttc'%('Bold' if b else 'Regular'),s,index=2)
S='src/'
def wrap(d,t,f,w):
    out=[];cur=''
    for ch in t:
        if ch=='\n': out.append(cur); cur=''; continue
        if d.textlength(cur+ch,font=f)>w: out.append(cur); cur=ch
        else: cur+=ch
    if cur: out.append(cur)
    return out
def text(d,xy,t,f,fill,w,lh):
    x,y=xy
    for ln in wrap(d,t,f,w): d.text((x,y),ln,font=f,fill=fill); y+=lh
    return y
def fit(im,w,h):
    im=im.convert('RGB'); r=max(w/im.width,h/im.height); im=im.resize((round(im.width*r),round(im.height*r)),Image.LANCZOS)
    l=(im.width-w)//2; t=(im.height-h)//2; return im.crop((l,t,l+w,t+h))
def paste(c,im,x,y,w,h,rad=14,label=None,lab_col=ACC):
    im=fit(im,w,h); m=Image.new('L',(w,h),0); ImageDraw.Draw(m).rounded_rectangle([0,0,w-1,h-1],radius=rad,fill=255)
    c.paste(im,(x,y),m)
    if label:
        d=ImageDraw.Draw(c,'RGBA'); f=F(22,True); tw=d.textlength(label,font=f)
        d.rounded_rectangle([x+12,y+12,x+12+tw+24,y+12+36],radius=18,fill=(0,0,0,170)); d.text((x+24,y+15),label,font=f,fill=lab_col)
def chip(d,x,y,t,f=None,fg=INK,bg=PANEL,pad=16,h=44):
    f=f or F(22,True); tw=d.textlength(t,font=f); d.rounded_rectangle([x,y,x+tw+2*pad,y+h],radius=h//2,fill=bg); d.text((x+pad,y+(h-30)//2),t,font=f,fill=fg); return x+tw+2*pad
def card(n,kicker,title,body,y_img=None):
    c=Image.new('RGB',(W,H),BG); d=ImageDraw.Draw(c,'RGBA')
    d.text((60,52),f'{n:02d}',font=F(30,True),fill=ACC); d.text((112,56),'/ 10   '+kicker,font=F(24,True),fill=MUT)
    y=110
    for ln in wrap(d,title,F(52,True),960): d.text((60,y),ln,font=F(52,True),fill=INK); y+=70
    y+=6; y=text(d,(60,y),body,F(27),MUT,960,42)
    return c,d,y+24
def footer(c,d):
    d.line([(60,H-78),(W-60,H-78)],fill=(40,46,54),width=2)
    d.text((60,H-62),'《大事件》开场长镜头 · AI 还原拍摄现场',font=F(22),fill=(110,118,128))
    d.text((W-60-d.textlength('Claude × Blender',font=F(22,True)),H-62),'Claude × Blender',font=F(22,True),fill=(110,118,128))
def save(c,name): c.save('cards/'+name,quality=92)
