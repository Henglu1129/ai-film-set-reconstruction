# ==== 《大事件》(2004) 开场长镜头项目里的实际代码，原样保留作参考 ====
# 里面的路径（/tmp/claude-0/...、/mnt/user-data/...）、坐标、车辆尺寸、帧号区间都是那部片子的，换片时逐项改。
# 约定：机位 R 为 世界→相机（OpenCV：x 右 y 下 z 前），C 为相机中心；画面 1280×554 时 CX=640 CY=277、HFOV=42°。
import json,glob,subprocess,sys
from PIL import Image, ImageDraw, ImageFont
U='/mnt/user-data/uploads/电影资源/大事件_长镜头拆解'
D={}
for fn in glob.glob(U+'/macdet_*.jsonl'):
    for l in open(fn):
        j=json.loads(l); D[j['f']]=j['d']
E=[(11,12),(11,13),(13,15),(12,14),(14,16),(11,23),(12,24),(23,24),(23,25),(25,27),(24,26),(26,28),(27,31),(28,32),(0,11),(0,12)]
F=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc',22,index=2)
def draw(f,off,out):
    subprocess.run(['ffmpeg','-y','-v','error','-i',U+'/det_src.mp4','-vf',f'select=eq(n\\,{f+off})','-frames:v','1','/tmp/fr.png'])
    im=Image.open('/tmp/fr.png').convert('RGB'); d=ImageDraw.Draw(im,'RGBA')
    cols={'person':(255,122,61),'car':(80,200,255),'truck':(80,200,255),'bus':(80,200,255),'motorbike':(160,255,120),'bicycle':(160,255,120)}
    for k in D[f]:
        if k['s']<0.4: continue
        x0,y0,x1,y1=k['b']; c=cols.get(k['k'],(255,255,255))
        d.rectangle([x0,y0,x1,y1],outline=c+(255,),width=3)
        lab={'person':'人','car':'车','truck':'货车','bus':'巴士','motorbike':'摩托','bicycle':'单车'}[k['k']]+f" {k['s']:.2f}"
        tw=d.textlength(lab,font=F); d.rectangle([x0,y0-30,x0+tw+12,y0],fill=c+(220,)); d.text((x0+6,y0-29),lab,font=F,fill=(10,10,10))
        if 'pose' in k:
            p=k['pose']['p2']
            for a,b in E:
                if a<len(p) and b<len(p): d.line([tuple(p[a]),tuple(p[b])],fill=(120,255,200,255),width=4)
            for q in p[:33]: d.ellipse([q[0]-4,q[1]-4,q[0]+4,q[1]+4],fill=(255,255,255,255))
    im.save(out)
for f in map(int,sys.argv[1:]):
    for off in (-1,0): draw(f,off,f'wx/det_{f}_{off+1}.jpg')
