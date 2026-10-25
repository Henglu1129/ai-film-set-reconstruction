import json, math, os
from PIL import Image, ImageDraw, ImageFont
D=json.load(open('/home/claude/proj/plan/plan_data.json'))
A=json.load(open('render_overview_v1/anchors_overview.json'))
A={n:{k:(v[0]/2,v[1]/2,v[2]) for k,v in a.items()} for n,a in A.items()}
FB='/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'; FR='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
def F(s,b=True): return ImageFont.truetype(FB if b else FR,s)
def hexc(h): h=h.lstrip('#'); return tuple(int(h[i:i+2],16) for i in (0,2,4))
def s35(h): return 24.89/(2*math.tan(math.radians(h/2)))
SET={s['id']:s for s in D['setups']}
BG=(24,27,33)
PH={1:'第一段 · 对峙',2:'第二段 · 离场与倒数',3:'第三段 · 处决',4:'第四段 · 台上终章'}
LIGHTS=[("L1","西窗日光·透纱帘","主光源。四扇大窗+纱帘=巨型柔光箱，侧逆光，粉墙几乎无影"),
 ("L2","东窗日光·透纱帘","与 L1 对称，两侧夹击，形成高调、低反差的“圣洁”底色"),
 ("L3","天花日光灯盘","画内实景灯，均匀顶光，冷白，提整体照度"),
 ("L4","球形壁灯","画内实用光，暖色点缀，门两侧与壁柱"),
 ("L5","画像背光光晕","画像框后暖色光，让“尊主”像自己在发光"),
 ("L6","发光石雕","门口与台侧的白色石雕被打亮，画内高光点"),
 ("L7","门外走廊光（推测）","陈站在门口时的顶逆光来源，轮廓更硬"),
 ("L8","布幔上方顶光（推测）","垂坠布幔兼作柔光层，中部人群的顶部补光"),
 ("L9","门洞黑幕·负补光","门洞后挂深色幕，陈的深色衣服以黑底+亮框的方式“跳”出来")]
def ph_sets():
    r={}
    for sh in D['shots']: r.setdefault(sh['phase'],[]).append(sh['setup'])
    return {k:sorted(set(v),key=lambda x:[s['id'] for s in D['setups']].index(x)) for k,v in r.items()}
PS=ph_sets()
def tot_dur(k,phase=None): return sum(sh['dur'] for sh in D['shots'] if sh['setup']==k and (phase is None or sh['phase']==phase))
def nshots(k,phase=None): return sum(1 for sh in D['shots'] if sh['setup']==k and (phase is None or sh['phase']==phase))
def overlap(a,b,m=4): return not (a[2]+m<b[0] or b[2]+m<a[0] or a[3]+m<b[1] or b[3]+m<a[1])
def label_top(d,an,keys,placed,big=False):
    for k in keys:
        s=SET[k]; u,v,z=an['cam:'+k]; col=hexc(s['color'])
        text=f"{k} {s['name']}" if big else k
        f=F(26 if big else 22)
        tb=d.textbbox((0,0),text,font=f); tw=tb[2]-tb[0]+16; th=tb[3]-tb[1]+12
        best=None
        for r in (50,80,115,150,190):
            for ang in (-90,-60,-120,-30,-150,90,60,120,0,180,30,150):
                x0=u+r*math.cos(math.radians(ang))-tw/2; y0=v+r*math.sin(math.radians(ang))-th/2
                x0=min(max(6,x0),2160-tw-6); y0=min(max(60,y0),1240-th-6)
                c=(x0,y0,x0+tw,y0+th)
                if not any(overlap(c,p) for p in placed): best=c; break
            if best: break
        best=best or (u-tw/2,v-60,u+tw/2,v-60+th)
        x0,y0,x1,y1=best
        d.line((u,v,(x0+x1)/2,(y0+y1)/2),fill=col,width=3); d.ellipse((u-7,v-7,u+7,v+7),outline=col,width=3)
        d.rounded_rectangle(best,8,fill=col); d.text((x0+8,y0+6-tb[1]),text,font=f,fill=(18,18,18))
        placed.append(best)
def lights_top(d,an,placed):
    for k,_,_ in LIGHTS:
        u,v,z=an['light:'+k]
        if 0<u<2160 and 0<v<1240:
            f=F(20); tb=d.textbbox((0,0),k,font=f); b=(u-22,v-18,u-22+tb[2]-tb[0]+14,v-18+tb[3]-tb[1]+10)
            d.rounded_rectangle(b,6,fill=(255,236,170)); d.text((b[0]+7,b[1]+5-tb[1]),k,font=f,fill=(30,30,30)); placed.append(b)
def wrap(d,text,f,w):
    out=[];line=''
    for ch in text:
        if d.textlength(line+ch,font=f)>w: out.append(line); line=ch
        else: line+=ch
    out.append(line); return out
def poster(name,img,an,keys,title,sub,phase=None):
    Wd=2160; topH=1240
    rows=len(keys); tableH=110+52*rows; lightH=90+len(LIGHTS)*44 if phase is None else 0
    H=150+topH+tableH+lightH+60
    im=Image.new('RGB',(Wd,H),BG); d=ImageDraw.Draw(im)
    d.text((48,30),title,font=F(52),fill=(255,255,255)); d.text((50,100),sub,font=F(26,False),fill=(170,176,186))
    top=Image.open(img).convert('RGBA'); lay=Image.new('RGBA',top.size,BG+(255,)); lay.alpha_composite(top)
    dd=ImageDraw.Draw(lay); placed=[]
    dd.text((24,18),"南 · 大门（← 门外走廊、楼梯）",font=F(26),fill=(210,210,210)); dd.text((1840,18),"舞台 · 北 →",font=F(26),fill=(210,210,210))
    for key,t,c in (('chen','陈桂林',(255,70,60)),('leader','尊者',(246,195,67))):
        u,v,z=an[key]; f=F(22); tb=dd.textbbox((0,0),t,font=f); b=(u-36,v-58,u-36+tb[2]-tb[0]+16,v-58+tb[3]-tb[1]+10)
        dd.rounded_rectangle(b,7,fill=c); dd.text((b[0]+8,b[1]+5-tb[1]),t,font=f,fill=(255,255,255) if key=='chen' else (30,30,30)); placed.append(b)
    lights_top(dd,an,placed)
    label_top(dd,an,keys,placed,big=phase is not None)
    im.paste(lay.convert('RGB'),(0,150)); d=ImageDraw.Draw(im)
    y=150+topH+30
    d.text((48,y),"摄影机方案",font=F(34),fill=(255,255,255)); y+=60
    cols=[48,170,560,780,1000,1290,1440,1580]
    hdr=["机位","名称","机高","支架/运动","水平视角 (≈S35 焦距)","镜头数","出画时长","可信度"]
    for x,hh in zip(cols,hdr): d.text((x,y),hh,font=F(22),fill=(150,158,170))
    y+=40
    for k in keys:
        s=SET[k]; col=hexc(s['color'])
        d.rounded_rectangle((cols[0],y,cols[0]+80,y+36),7,fill=col); d.text((cols[0]+10,y+2),k,font=F(24),fill=(18,18,18))
        d.text((cols[1],y+2),s['name'],font=F(24),fill=(240,240,240))
        d.text((cols[2],y+4),f"{s['C'][2]:.1f} m",font=F(22,False),fill=(220,220,220))
        d.text((cols[3],y+4),f"{s['rig']} · {s['move']}",font=F(20,False),fill=(220,220,220))
        hf=s['hfov']; ht=" → ".join(f"{h:.0f}°" for h in hf); lt=" → ".join(f"{s35(h):.0f}" for h in hf)
        d.text((cols[4],y+4),f"{ht}（{lt} mm）",font=F(22,False),fill=(220,220,220))
        d.text((cols[5],y+4),str(nshots(k,phase)),font=F(22,False),fill=(220,220,220))
        d.text((cols[6],y+4),f"{tot_dur(k,phase):.1f} s",font=F(22,False),fill=(220,220,220))
        d.text((cols[7],y+4),s['conf'],font=F(22,False),fill=(220,220,220))
        fl=F(19,False); ln=wrap(d,s['note'],fl,2160-1680-40)[0]
        d.text((1680,y+6),ln,font=fl,fill=(160,166,176))
        y+=52
    if phase is None:
        y+=30; d.text((48,y),"灯光方案",font=F(34),fill=(255,255,255)); y+=60
        for k,n,note in LIGHTS:
            d.rounded_rectangle((48,y,118,y+34),6,fill=(255,236,170)); d.text((60,y+2),k,font=F(22),fill=(30,30,30))
            d.text((140,y+2),n,font=F(24),fill=(240,240,240)); d.text((520,y+4),note,font=F(22,False),fill=(190,196,206)); y+=44
    d.text((48,H-44),"还原方法：门框/空调柜/画像/舞台边等标定点 + 人高 1.80 m 定比例，SfM 交叉校验；“可信度”反映解算残差与可见标定点数量。灯光中“推测”项无画内直接证据。",font=F(19,False),fill=(130,136,146))
    im.save(name,quality=92); print(name,im.size)
os.makedirs('out',exist_ok=True)
order=[s['id'] for s in D['setups']]
poster('out/总图_全部机位与灯光.jpg','render_overview_v1/overview_all.png',A['overview_all'],order,
       "《周处除三害》灵修堂 · 拍摄现场还原总图","旧士林分局三楼礼堂实景 · 约 10.4 m × 22.6 m · 1:45:06–1:52:50 共 138 个镜头 → 25 个机位方案 · 9 组光源")
for p in (1,2,3,4):
    sh=[x for x in D['shots'] if x['phase']==p]
    poster(f'out/分段{p}_{PH[p].split(" · ")[1]}.jpg',f'render_overview_v1/phase{p}.png',A[f'phase{p}'],PS[p],
           f"灵修堂 · {PH[p]}",f"#{sh[0]['n']}–#{sh[-1]['n']} · {len(sh)} 个镜头 · {sh[-1]['t1']-sh[0]['t0']:.0f} 秒 · 本段用到 {len(PS[p])} 个机位（视锥=该机位最广视角）",phase=p)
