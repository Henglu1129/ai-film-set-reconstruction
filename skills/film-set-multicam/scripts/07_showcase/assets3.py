import json, glob
from PIL import Image, ImageDraw, ImageFont, ImageFilter
FB='/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'
F=lambda s: ImageFont.truetype(FB,s,index=2)
P=json.load(open('/home/claude/proj/plan/plan_data.json')); SET={s['id']:s for s in P['setups']}
def hexc(h): return tuple(int(h[i:i+2],16) for i in (1,3,5))
def callouts(sid,items,out,dim=0.72):
    im=Image.open(glob.glob(f'/home/claude/proj/frames_mid/s{sid:03d}_*.jpg')[0]).convert('RGB')
    im=Image.eval(im,lambda v:int(v*dim)).convert('RGBA')
    lay=Image.new('RGBA',im.size,(0,0,0,0)); d=ImageDraw.Draw(lay)
    for (x,y),(lx,ly),t in items:
        d.line([(x,y),(lx,ly)],fill=(255,226,140,255),width=4)
        d.ellipse((x-16,y-16,x+16,y+16),outline=(255,226,140,255),width=5)
    glow=lay.filter(ImageFilter.GaussianBlur(5)); im.alpha_composite(glow); im.alpha_composite(lay)
    d=ImageDraw.Draw(im)
    for (x,y),(lx,ly),t in items:
        f=F(40); tw=d.textlength(t,font=f)
        x0=min(max(10,lx-tw/2-18),1920-tw-46); d.rounded_rectangle((x0,ly-30,x0+tw+36,ly+32),31,fill=(255,226,140)); d.text((x0+18,ly-27),t,font=f,fill=(20,20,20))
    im.convert('RGB').save(out,quality=92)
callouts(10,[((1700,150),(1560,600),'L2 窗光透纱帘'),((782,170),(560,90),'L5 画像背光'),((1545,230),(1240,210),'L4 壁灯'),
             ((515,350),(330,560),'L6 发光石雕'),((600,40),(960,60),'L8 布幔顶光')],'src/light_a.jpg')
callouts(4,[((800,160),(470,70),'L9 门洞黑幕'),((683,380),(330,430),'L6 发光石雕'),((1264,40),(1500,140),'L4 壁灯')],'src/light_b.jpg')
# clusters
rows=[('E',[9,23,25,28,30,32,34,36]),('U',[2,17,20,26,29,31,44,103]),('N',[82,84,87,91,93,105,109,124])]
tw,th=230,96; pad=8
W=8*(tw+pad)+pad; H=len(rows)*(th+70)+pad
C=Image.new('RGB',(W,H),(13,16,21)); d=ImageDraw.Draw(C)
for r,(k,ss) in enumerate(rows):
    s=SET[k]; col=hexc(s['color']); y=r*(th+70)+pad
    d.rounded_rectangle((pad,y,pad+56,y+46),10,fill=col); d.text((pad+12,y+2),k,font=F(32),fill=(15,15,15))
    n=sum(1 for x in P['shots'] if x['setup']==k); dur=sum(x['dur'] for x in P['shots'] if x['setup']==k)
    d.text((pad+72,y+2),f"{s['name']}  ·  {n} 个镜头  ·  {dur:.0f} 秒",font=F(32),fill=(236,239,243))
    for i,sn in enumerate(ss):
        im=Image.open(glob.glob(f'/home/claude/proj/frames_mid/s{sn:03d}_*.jpg')[0]).convert('RGB').crop((240,0,1680,600)).resize((tw,th),Image.LANCZOS)
        x=pad+i*(tw+pad); C.paste(im,(x,y+56)); d.rectangle((x,y+56+th-5,x+tw-1,y+56+th-1),fill=col)
C.save('src/clusters.png'); print(C.size)
