from PIL import Image, ImageDraw, ImageFont, ImageFilter
import glob, os
W,H=1080,1440
BG=(12,14,19); INK=(240,242,246); MUT=(150,158,170); ACC=(255,122,61); CYN=(94,220,230); PAN=(26,30,38)
def F(s,w='Bold'): return ImageFont.truetype(f'/usr/share/fonts/opentype/noto/NotoSansCJK-{w}.ttc',s,index=2)
N_TOTAL=9
def wrap(d,t,f,w):
    out=[];cur=''
    for ch in t:
        if ch=='\n': out.append(cur); cur=''; continue
        if d.textlength(cur+ch,font=f)>w and ch not in '，。、：；！？）」』”…—':
            if cur and cur[-1] in '（「『“': out.append(cur[:-1]); cur=cur[-1]+ch
            else: out.append(cur); cur=ch
        else: cur+=ch
    if cur: out.append(cur)
    return out
def fit(im,w,h,anchor=0.5):
    im=im.convert('RGB'); r=max(w/im.width,h/im.height); im=im.resize((round(im.width*r),round(im.height*r)),Image.LANCZOS)
    l=int((im.width-w)*anchor); t=(im.height-h)//2; return im.crop((l,t,l+w,t+h))
def contain(im,w,h,bg=BG):
    im=im.convert('RGBA'); r=min(w/im.width,h/im.height); im=im.resize((round(im.width*r),round(im.height*r)),Image.LANCZOS)
    c=Image.new('RGBA',(w,h),bg+(255,)); c.alpha_composite(im,((w-im.width)//2,(h-im.height)//2)); return c.convert('RGB')
def paste(c,im,x,y,w,h,rad=18,label=None,col=ACC,mode='fit'):
    im=fit(im,w,h) if mode=='fit' else contain(im,w,h)
    m=Image.new('L',(w,h),0); ImageDraw.Draw(m).rounded_rectangle([0,0,w-1,h-1],radius=rad,fill=255); c.paste(im,(x,y),m)
    d=ImageDraw.Draw(c,'RGBA'); d.rounded_rectangle([x,y,x+w-1,y+h-1],radius=rad,outline=(255,255,255,28),width=2)
    if label:
        f=F(24); tw=d.textlength(label,font=f)
        d.rounded_rectangle([x+14,y+14,x+14+tw+28,y+14+42],radius=21,fill=(0,0,0,185)); d.text((x+28,y+16),label,font=f,fill=col)
def bg_glow(c):
    g=Image.new('RGB',(W,H),BG); d=ImageDraw.Draw(g)
    d.ellipse((-300,-400,700,500),fill=(40,24,22)); d.ellipse((600,900,1500,1800),fill=(16,34,40))
    g=g.filter(ImageFilter.GaussianBlur(160)); c.paste(g)
def card(n,kicker,title,body):
    c=Image.new('RGB',(W,H),BG); bg_glow(c); d=ImageDraw.Draw(c,'RGBA')
    d.text((60,50),f'{n:02d}',font=F(34,'Black'),fill=ACC); d.text((118,58),f'/ {N_TOTAL:02d}    {kicker}',font=F(24),fill=MUT)
    y=112
    for ln in title.split('\n'):
        for l2 in wrap(d,ln,F(58,'Black'),960): d.text((60,y),l2,font=F(58,'Black'),fill=INK); y+=78
    y+=8
    for ln in wrap(d,body,F(29,'Regular'),960): d.text((60,y),ln,font=F(29,'Regular'),fill=(186,192,202)); y+=46
    return c,d,y+26
def chip(d,x,y,t,fg=(15,15,15),bg=ACC,f=None,h=50,pad=20):
    f=f or F(26); tw=d.textlength(t,font=f); d.rounded_rectangle([x,y,x+tw+2*pad,y+h],radius=h//2,fill=bg); d.text((x+pad,y+(h-36)//2),t,font=f,fill=fg); return x+tw+2*pad
def footer(c):
    d=ImageDraw.Draw(c); d.line([(60,H-80),(W-60,H-80)],fill=(44,50,60),width=2)
    d.text((60,H-62),'《周处除三害》灵修堂 · AI 还原拍摄现场',font=F(23,'Medium'),fill=(118,126,138))
    t='Claude × Blender'; d.text((W-60-d.textlength(t,font=F(23)),H-62),t,font=F(23),fill=(118,126,138))
def save(c,name): os.makedirs('cards',exist_ok=True); c.save('cards/'+name,quality=93)
S='src/'; FM='/home/claude/proj/frames_mid/'
def fm(n): return Image.open(glob.glob(FM+f's{n:03d}_*.jpg')[0])
def top(name):
    im=Image.open(S+'render_overview_v1/'+name).convert('RGBA'); b=Image.new('RGBA',im.size,BG+(255,)); b.alpha_composite(im); return b.convert('RGB')

# 01 封面
c=Image.new('RGB',(W,H),BG); bg_glow(c); d=ImageDraw.Draw(c,'RGBA')
hero=top('phase3.png').crop((40,60,2120,1180))
paste(c,hero,0,560,W,640,rad=0)
grad=Image.new('L',(1,640)); [grad.putpixel((0,i),int(255*max(0,1-i/170))) for i in range(640)]
fade=Image.new('RGB',(W,640),BG); c.paste(fade,(0,560),grad.resize((W,640)))
grad2=Image.new('L',(1,640)); [grad2.putpixel((0,i),int(255*max(0,(i-470)/170))) for i in range(640)]
c.paste(fade,(0,560),grad2.resize((W,640)))
d=ImageDraw.Draw(c,'RGBA')
d.text((60,70),'AI 拉片实验',font=F(30),fill=ACC)
y=130
for ln in ['一场 7 分 43 秒的戏','当年是怎么拍出来的？']:
    d.text((60,y),ln,font=F(76,'Black'),fill=INK); y+=100
d.text((60,y+14),'《周处除三害》灵修堂 —— 只看成片，反推出剧组的',font=F(30,'Regular'),fill=(186,192,202))
d.text((60,y+60),'摄影机方案和灯光方案，再在 3D 里把现场搭回来。',font=F(30,'Regular'),fill=(186,192,202))
x=60; yy=1210
for t,col in [('138 个镜头',INK),('→',MUT),('25 个机位',ACC),('9 组灯光',(255,226,140)),('1 个 3D 现场',CYN)]:
    if t=='→': d.text((x,yy+4),t,font=F(32),fill=MUT); x+=48; continue
    x=chip(d,x,yy,t,bg=(30,34,42),fg=col,f=F(28))+14
footer(c); save(c,'01_封面.jpg')

# 02 拆镜头
c,d,y=card(2,'第一步 · 拆镜头','先把整场戏\n拆成 138 个镜头','逐帧比较前后画面，突然跳变的地方就是剪辑点。开枪时的闪光也会让画面突变——22 处枪口闪光被单独认出来、排除掉。')
sig=Image.open(S+'cut_signal.png'); paste(c,sig,60,y,960,320,rad=16,mode='fit')
d=ImageDraw.Draw(c,'RGBA'); x=chip(d,80,y+252,'● 剪辑点',fg=ACC,bg=(0,0,0,170),f=F(22),h=40,pad=14); chip(d,x+10,y+252,'✕ 枪口闪光（不算）',fg=(255,212,59),bg=(0,0,0,170),f=F(22),h=40,pad=14)
y+=344
mos=Image.open(S+'mosaic.png'); paste(c,mos,60,y,960,H-110-y,rad=16,mode='fit',label='138 个镜头 · 底部色条 = 来自哪台机')
footer(c); save(c,'02_拆镜头.jpg')

# 03 归机位
c,d,y=card(3,'第二步 · 归机位','138 个镜头\n其实只来自 25 个机位','背景构图一样的镜头，就是同一台机拍的。最忙的 E、U 两台背靠背架在人群中间，一台对着门、一台对着台，加起来拍了全场将近一半。')
cl=Image.open(S+'clusters.png'); h=int(960*cl.height/cl.width); paste(c,cl,60,y+10,960,h,rad=14,mode='contain')
y+=h+40
ov=Image.open(S+'poster_all.jpg').crop((0,150,2160,1390)); paste(c,ov,60,y,960,H-110-y,rad=16,label='25 个机位在现场的位置',col=CYN)
footer(c); save(c,'03_归机位.jpg')

# 04 找尺子
c,d,y=card(4,'第三步 · 找尺子','用画面里的东西\n当尺子','门框、空调柜、画像、舞台边——这些东西不会动，尺寸也能估。再拿演员身高 1.80 m 定比例，就能把整个礼堂反推出来：约 10.4 米宽、22.6 米长。')
r=Image.open(S+'ruler_s110.jpg'); paste(c,r,60,y,960,402,rad=16)
y+=430
# room schematic numbers on top render
sch=top('overview_all.png').crop((380,180,2160,1240))
paste(c,sch,60,y,960,H-110-y,rad=16,label='算出来的礼堂：10.4 m × 22.6 m，舞台高 0.5 m',col=(255,212,59))
footer(c); save(c,'04_找尺子.jpg')

# 05 反求机位
c,d,y=card(5,'第四步 · 算机位','把礼堂“套”回\n每一个镜头里','算出每台机的位置、高度和焦距后，把礼堂的线框投回原片：门框、空调柜、画像都严丝合缝，说明机位算对了。')
hh=(H-110-y-2*18)//3
for i,(k,lab,col) in enumerate([('B','B 机：站在舞台上，24° 长焦隔着整个大厅拍门口',ACC),('N','N 机：门内正中、离地 1 米，对称大全',CYN),('H','H 机：舞台后部高脚架，俯拍整个人群',(255,212,59))]):
    paste(c,Image.open(S+f'wire_{k}.jpg'),60,y+i*(hh+18),960,hh,rad=16,label=lab,col=col)
footer(c); save(c,'05_算机位.jpg')

# 06 灯光
c,d,y=card(6,'第五步 · 推灯光','再看光从哪里来','两侧大窗挂着纱帘，像两只巨大的柔光箱——这是主光，所以整个礼堂又亮又“圣洁”。壁灯、画像背光、发光石雕负责点缀；门洞后挂着黑幕，让陈桂林的深色衣服从背景里“跳”出来。')
hh=(H-110-y-18)//2
paste(c,Image.open(S+'light_a.jpg'),60,y,960,hh,rad=16)
paste(c,Image.open(S+'light_b.jpg'),60,y+hh+18,960,hh,rad=16)
footer(c); save(c,'06_推灯光.jpg')

# 07 搭现场
c,d,y=card(7,'第六步 · 搭现场','在 Blender 里\n把现场搭出来','礼堂、舞台、门窗按算出的尺寸 1:1 建模；25 台摄影机带着各自的取景范围摆进去，9 组灯、162 个群演按座位排好。')
paste(c,top('phase3.png').crop((40,60,2120,1180)),60,y,960,520,rad=16,label='处决段落用到的 10 台机 + 取景范围',col=ACC)
y+=540
paste(c,top('phase1.png').crop((40,60,2120,1180)),60,y,960,H-110-y,rad=16,label='对峙段落：机位集中在人群中和舞台上',col=CYN)
footer(c); save(c,'07_搭现场.jpg')

# 08 验证
c,d,y=card(8,'第七步 · 验证','同一个位置，\n再“拍”一遍','在 3D 现场里，用算出来的机位和焦距重新渲染，和原片并排对比：墙、门、画像、舞台都对得上。')
pairs=[(127,'N'),(4,'B'),(10,'B2'),(54,'H')]
hh=(H-110-y-3*14)//4; ww=(960-14)//2
for i,(sn,k) in enumerate(pairs):
    yy=y+i*(hh+14)
    paste(c,fm(sn),60,yy,ww,hh,rad=12,label='原片' if i==0 else None,col=INK)
    paste(c,Image.open(S+f'qa_v5/qa_{k}_s{sn:03d}.jpg'),60+ww+14,yy,ww,hh,rad=12,label='3D 还原 · 同机位' if i==0 else f'{k} 机',col=CYN)
footer(c); save(c,'08_同机位验证.jpg')

# 09 成片
c,d,y=card(9,'最后 · 合成','合成一条视频：\n每一秒都知道是哪台机拍的','')
fr=Image.open(S+'final_26.0.jpg'); fw=600; fh=int(fw*1560/1080)
paste(c,fr,60,y-20,fw,fh,rad=16)
x0=60+fw+34; yy=y-14; d=ImageDraw.Draw(c,'RGBA')
for t,col,desc in [('原片','',"上：成片画面"),('机位时间轴','',"中：138 个镜头按机位着色，跟着播放滚动"),('俯视现场','',"下：当前机位亮起，显示位置和取景范围"),('镜头参数','',"底：机高、支架、焦距、可信度")]:
    d.text((x0,yy),t,font=F(32,'Black'),fill=INK); yy+=48
    for ln in wrap(d,desc,F(24,'Regular'),W-60-x0): d.text((x0,yy),ln,font=F(24,'Regular'),fill=(176,182,192)); yy+=36
    yy+=22
yy+=10; d.line([(x0,yy),(W-60,yy)],fill=(60,66,78),width=2); yy+=24
d.text((x0,yy),'几个发现',font=F(30,'Black'),fill=ACC); yy+=50
for t in ['门口的陈桂林，是从舞台上用长焦隔着整个大厅拍的','处决主镜头离地只有 1 米，左右完全对称','全场四成以上画面，来自人群中背靠背的两台机']:
    d.ellipse((x0,yy+12,x0+10,yy+22),fill=ACC)
    for ln in wrap(d,t,F(24,'Regular'),W-60-x0-22): d.text((x0+22,yy),ln,font=F(24,'Regular'),fill=(200,206,214)); yy+=36
    yy+=14
footer(c); save(c,'09_成片.jpg')
print(sorted(os.listdir('cards')))
