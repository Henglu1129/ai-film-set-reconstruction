from PIL import Image, ImageDraw, ImageFont, ImageFilter
import glob, os
W,H=1080,1440
BG=(12,14,19); INK=(240,242,246); MUT=(150,158,170); ACC=(255,122,61); CYN=(94,220,230); PAN=(26,30,38)
IF='/usr/share/fonts/opentype/inter/'
def F(s,w='Bold'): return ImageFont.truetype(IF+f'Inter-{w}.otf',s)
N_TOTAL=9
def wrap(d,t,f,w):
    out=[];cur=''
    for word in t.split(' '):
        tt=(cur+' '+word).strip()
        if d.textlength(tt,font=f)>w and cur: out.append(cur); cur=word
        else: cur=tt
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
        f=F(23,'SemiBold'); tw=d.textlength(label,font=f)
        d.rounded_rectangle([x+14,y+14,x+14+tw+28,y+14+42],radius=21,fill=(0,0,0,190)); d.text((x+28,y+21),label,font=f,fill=col)
def bg_glow(c):
    g=Image.new('RGB',(W,H),BG); d=ImageDraw.Draw(g)
    d.ellipse((-300,-400,700,500),fill=(40,24,22)); d.ellipse((600,900,1500,1800),fill=(16,34,40))
    c.paste(g.filter(ImageFilter.GaussianBlur(160)))
def card(n,kicker,title,body):
    c=Image.new('RGB',(W,H),BG); bg_glow(c); d=ImageDraw.Draw(c,'RGBA')
    d.text((60,54),f'{n:02d}',font=F(34,'Black'),fill=ACC); d.text((120,62),f'/ {N_TOTAL:02d}    {kicker.upper()}',font=F(22,'SemiBold'),fill=MUT)
    y=118
    for ln in title.split('\n'):
        for l2 in wrap(d,ln,F(56,'Black'),960): d.text((60,y),l2,font=F(56,'Black'),fill=INK); y+=70
    y+=14
    for ln in wrap(d,body,F(28,'Regular'),960): d.text((60,y),ln,font=F(28,'Regular'),fill=(186,192,202)); y+=42
    return c,d,y+26
def chip(d,x,y,t,fg=(15,15,15),bg=ACC,f=None,h=50,pad=20):
    f=f or F(25,'SemiBold'); tw=d.textlength(t,font=f); d.rounded_rectangle([x,y,x+tw+2*pad,y+h],radius=h//2,fill=bg); d.text((x+pad,y+(h-30)//2),t,font=f,fill=fg); return x+tw+2*pad
def footer(c):
    d=ImageDraw.Draw(c); d.line([(60,H-80),(W-60,H-80)],fill=(44,50,60),width=2)
    d.text((60,H-60),'The Pig, the Snake and the Pigeon  |  AI set reconstruction',font=F(21,'Medium'),fill=(118,126,138))
    t='Claude × Blender'; d.text((W-60-d.textlength(t,font=F(21,'SemiBold')),H-60),t,font=F(21,'SemiBold'),fill=(118,126,138))
def save(c,name): os.makedirs('cards_en',exist_ok=True); c.save('cards_en/'+name,quality=93)
S='src/'; FM='/home/claude/proj/frames_mid/'
def fm(n): return Image.open(glob.glob(FM+f's{n:03d}_*.jpg')[0])
def top(name):
    im=Image.open(S+'render_overview_v1/'+name).convert('RGBA'); b=Image.new('RGBA',im.size,BG+(255,)); b.alpha_composite(im); return b.convert('RGB')

# 01 cover
c=Image.new('RGB',(W,H),BG); bg_glow(c)
hero=top('phase3.png').crop((40,60,2120,1180)); hh=int(W*hero.height/hero.width); hero=hero.resize((W,hh),Image.LANCZOS)
m=Image.new('L',(1,hh))
for i in range(hh): m.putpixel((0,i),int(255*min(1,i/170)*min(1,(hh-i)/170)))
c.paste(hero,(0,600),m.resize((W,hh)))
d=ImageDraw.Draw(c,'RGBA')
d.text((62,76),'AN AI FILM-BREAKDOWN EXPERIMENT',font=F(26,'SemiBold'),fill=ACC)
y=130
for ln in ['A 7-minute scene.','How was it actually','shot?']:
    d.text((60,y),ln,font=F(74,'Black'),fill=INK); y+=90
y+=16
for ln in ['From the finished film alone, Claude reverse-','engineered the crew\'s camera and lighting plan,','then rebuilt the set in 3D.']:
    d.text((62,y),ln,font=F(29,'Regular'),fill=(186,192,202)); y+=44
x=60; yy=1222
for t,col in [('138 shots',INK),('25 cameras',ACC),('9 lights',(255,226,140)),('1 rebuilt set',CYN)]:
    x=chip(d,x,yy,t,bg=(30,34,42),fg=col,f=F(27,'SemiBold'),h=54)+12
footer(c); save(c,'01_cover.jpg')

# 02 shots
c,d,y=card(2,'Step 1 · Find the cuts','First, split the scene\ninto 138 shots','Compare every frame with the next: a sudden jump means an edit. Muzzle flashes also make the image jump, so 22 gunshots were detected and ruled out.')
paste(c,Image.open(S+'cut_signal.png'),60,y,960,320,rad=16)
d=ImageDraw.Draw(c,'RGBA'); x=chip(d,80,y+252,'● Cut',fg=ACC,bg=(0,0,0,180),f=F(21,'SemiBold'),h=40,pad=14); chip(d,x+10,y+252,'× Muzzle flash (not a cut)',fg=(255,212,59),bg=(0,0,0,180),f=F(21,'SemiBold'),h=40,pad=14)
y+=344
paste(c,Image.open(S+'mosaic.png'),60,y,960,H-110-y,rad=16,label='All 138 shots · color bar = which camera')
footer(c); save(c,'02_find_the_cuts.jpg')

# 03 setups
c,d,y=card(3,'Step 2 · Group the shots','138 shots came from\nonly 25 camera setups','Same background, same camera. The two busiest sat back-to-back in the middle of the crowd, one facing the door, one the stage, and filmed nearly half the scene.')
cl=Image.open(S+'clusters_en.png'); h=int(960*cl.height/cl.width); paste(c,cl,60,y+10,960,h,rad=14,mode='contain')
y+=h+40
paste(c,Image.open(S+'overview_en.jpg'),60,y,960,H-110-y,rad=16,label='Where all 25 cameras stood',col=CYN)
footer(c); save(c,'03_camera_setups.jpg')

# 04 ruler
c,d,y=card(4,'Step 3 · Measure the room','Use the frame\nas a ruler','No blueprints. But the door frame, the AC unit, the portrait and the stage edge never move, and the actor is 1.80 m tall. That was enough to solve the hall: 10.4 m wide, 22.6 m long.')
paste(c,Image.open(S+'ruler_s110_en.jpg'),60,y,960,402,rad=16)
y+=430
paste(c,top('overview_all.png').crop((380,180,2160,1240)),60,y,960,H-110-y,rad=16,label='Solved hall: 10.4 × 22.6 m, stage 0.5 m high',col=(255,212,59))
footer(c); save(c,'04_measure_the_room.jpg')

# 05 cameras
c,d,y=card(5,'Step 4 · Solve the cameras','Fit the room back\ninto every shot','With each camera\'s position, height and lens solved, the room\'s wireframe is projected back onto the footage. Door, AC unit and portrait line up: the camera is right.')
hh=(H-110-y-2*18)//3
for i,(k,lab,col) in enumerate([('B','Camera B: on stage, 24° long lens across the hall',ACC),('N','Camera N: 1 m off the floor, dead center',CYN),('H','Camera H: high stand at the back of the stage',(255,212,59))]):
    paste(c,Image.open(S+f'wire_{k}.jpg'),60,y+i*(hh+18),960,hh,rad=16,label=lab,col=col)
footer(c); save(c,'05_solve_the_cameras.jpg')

# 06 lights
c,d,y=card(6,'Step 5 · Read the light','Then work out\nwhere the light comes from','Two walls of curtained windows act as giant softboxes: that\'s the key light, and why the hall feels bright and "holy". Sconces, the portrait and glowing sculptures add accents. A black drape in the doorway makes Chen\'s dark clothes pop.')
hh=(H-110-y-18)//2
paste(c,Image.open(S+'light_a_en.jpg'),60,y,960,hh,rad=16)
paste(c,Image.open(S+'light_b_en.jpg'),60,y+hh+18,960,hh,rad=16)
footer(c); save(c,'06_read_the_light.jpg')

# 07 build
c,d,y=card(7,'Step 6 · Build the set','Rebuild the set\nin Blender','Hall, stage, doors and windows at solved scale. 25 cameras with their fields of view, 9 lights, and 162 extras seated on their cushions.')
paste(c,top('phase3.png').crop((40,60,2120,1180)),60,y,960,520,rad=16,label='Execution: 10 cameras and what each one sees',col=ACC)
y+=540
paste(c,top('phase1.png').crop((40,60,2120,1180)),60,y,960,H-110-y,rad=16,label='Standoff: cameras in the crowd and on stage',col=CYN)
footer(c); save(c,'07_build_the_set.jpg')

# 08 verify
c,d,y=card(8,'Step 7 · Verify','Same spot,\nshoot it again','Re-render each shot from the solved camera, same position and lens, and put it next to the film. Walls, door, portrait and stage all line up.')
pairs=[(127,'N'),(4,'B'),(10,'B2'),(54,'H')]
hh=(H-110-y-3*14)//4; ww=(960-14)//2
for i,(sn,k) in enumerate(pairs):
    yy=y+i*(hh+14)
    paste(c,fm(sn),60,yy,ww,hh,rad=12,label='Film' if i==0 else None,col=INK)
    paste(c,Image.open(S+f'qa_v5/qa_{k}_s{sn:03d}.jpg'),60+ww+14,yy,ww,hh,rad=12,label='3D rebuild, same camera' if i==0 else f'Camera {k}',col=CYN)
footer(c); save(c,'08_verify.jpg')

# 09 final
c,d,y=card(9,'Final · The video','One video:\nevery second, which camera','')
fr=Image.open(S+'final_en_26.jpg'); fw=600; fh=int(fw*1560/1080)
paste(c,fr,60,y-20,fw,fh,rad=16)
x0=60+fw+34; yy=y-14; d=ImageDraw.Draw(c,'RGBA')
for t,desc in [('Film','Top: the finished scene'),('Camera timeline','All 138 shots, colored by camera, scrolling with playback'),('The set','The active camera lights up with its field of view'),('Specs','Height, rig, lens, confidence')]:
    d.text((x0,yy),t,font=F(30,'Black'),fill=INK); yy+=42
    for ln in wrap(d,desc,F(23,'Regular'),W-60-x0): d.text((x0,yy),ln,font=F(23,'Regular'),fill=(176,182,192)); yy+=32
    yy+=22
yy+=6; d.line([(x0,yy),(W-60,yy)],fill=(60,66,78),width=2); yy+=22
d.text((x0,yy),'Surprises',font=F(28,'Black'),fill=ACC); yy+=46
for t in ['The doorway shots of Chen were taken from the stage, on a long lens across the hall','The execution master sits just 1 m off the floor, perfectly symmetric','Over 40% of the scene came from two cameras back-to-back in the crowd']:
    d.ellipse((x0,yy+11,x0+10,yy+21),fill=ACC)
    for ln in wrap(d,t,F(22,'Regular'),W-60-x0-22): d.text((x0+22,yy),ln,font=F(22,'Regular'),fill=(200,206,214)); yy+=31
    yy+=12
footer(c); save(c,'09_the_video.jpg')
print(sorted(os.listdir('cards_en')))
