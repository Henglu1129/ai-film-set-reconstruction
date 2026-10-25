from PIL import Image, ImageDraw, ImageFont, ImageFilter
W,H=1080,1560; BG=(12,14,19); INK=(240,242,246); MUT=(170,178,190); ACC=(255,122,61); CYN=(94,220,230); YEL=(255,226,140)
IF='/usr/share/fonts/opentype/inter/'
def F(s,w='Bold'): return ImageFont.truetype(IF+f'Inter-{w}.otf',s)
def hero():
    im=Image.open('/home/claude/show/src/render_overview_v1/phase3.png').convert('RGBA')
    b=Image.new('RGBA',im.size,BG+(255,)); b.alpha_composite(im); im=b.convert('RGB').crop((40,60,2120,1180))
    r=W/im.width; return im.resize((W,int(im.height*r)),Image.LANCZOS)
def glow(c):
    g=Image.new('RGB',(W,H),BG); d=ImageDraw.Draw(g)
    d.ellipse((-300,-300,700,600),fill=(44,26,22)); d.ellipse((500,1000,1500,1900),fill=(16,36,44))
    c.paste(g.filter(ImageFilter.GaussianBlur(170)))
def fade_band(c,y,h,top=True):
    m=Image.new('L',(1,h)); 
    for i in range(h): m.putpixel((0,i),int(255*(1-i/h) if top else 255*(i/h)))
    c.paste(Image.new('RGB',(W,h),BG),(0,y),m.resize((W,h)))
def chip(d,x,y,t,fg,bg=(30,34,42),f=None,h=58,pad=22):
    f=f or F(28,'SemiBold'); tw=d.textlength(t,font=f); d.rounded_rectangle([x,y,x+tw+2*pad,y+h],radius=h//2,fill=bg); d.text((x+pad,y+(h-34)//2),t,font=f,fill=fg); return x+tw+2*pad
# title
c=Image.new('RGB',(W,H),BG); glow(c)
hi=hero(); m=Image.new('L',(1,hi.height))
for i in range(hi.height):
    a=min(1,i/200)*min(1,(hi.height-i)/220); m.putpixel((0,i),int(255*a))
c.paste(hi,(0,800),m.resize((W,hi.height)))
d=ImageDraw.Draw(c)
d.text((64,150),'THE PIG, THE SNAKE AND THE PIGEON',font=F(30,'SemiBold'),fill=ACC)
y=210
for ln in ['How was this','scene actually shot?']:
    d.text((60,y),ln,font=F(84,'Black'),fill=INK); y+=100
y+=20
for ln in ['Given only the finished film, Claude reverse-','engineered the camera and lighting plan','of a 7-minute scene, then rebuilt the set in 3D.']:
    d.text((64,y),ln,font=F(34,'Regular'),fill=MUT); y+=50
y+=40; x=64
for t,col in [('138 shots',INK),('25 camera setups',ACC),('9 lights',YEL)]:
    x=chip(d,x,y,t,col)+14
chip(d,64,y+74,'1 rebuilt 3D set',CYN)
d.text((64,H-110),'Made with Claude + Blender',font=F(30,'SemiBold'),fill=(140,148,160))
c.save('title.png')
# end
c=Image.new('RGB',(W,H),BG); glow(c); d=ImageDraw.Draw(c)
y=420
for ln in ['Every second:','which camera,','where it stood,','which lens.']:
    d.text((60,y),ln,font=F(88,'Black'),fill=INK if ln!='Every second:' else ACC); y+=110
y+=40
for ln in ['Reverse-engineered from the finished film','with Claude + Blender.']:
    d.text((64,y),ln,font=F(36,'Regular'),fill=MUT); y+=54
d.text((64,H-110),'The Pig, the Snake and the Pigeon (2023)',font=F(28,'Medium'),fill=(130,138,150))
c.save('end.png')
