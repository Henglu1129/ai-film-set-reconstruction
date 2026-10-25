# 分段编码（带英文字幕）：在 v2 基础上用 libass 把 cues_en.json 烧进原片区（中文字幕正下方）
import json, subprocess, sys, os, time
W=os.path.dirname(os.path.abspath(__file__))
SRC=os.environ.get("FILM_SRC", "原片.mp4")   # 改成你的原片路径
D=json.load(open(W+'/plan/plan_data_v5.json')); PAN=sys.argv[1]; SEGDIR=sys.argv[2]; CUES=sys.argv[3]; idx=[int(x) for x in sys.argv[4:]]
LY=json.load(open(PAN+'/layout.json')); CU=json.load(open(CUES))
os.makedirs(SEGDIR,exist_ok=True)
shots=D['shots']; TOTAL=shots[-1]['t1']
segs=[]; cur=[]
for s in shots:
    cur.append(s)
    if cur[-1]['t1']-cur[0]['t0']>=40: segs.append(cur); cur=[]
if cur: segs.append(cur)
def ts(t):
    t=max(0,t); h=int(t//3600); m=int(t%3600//60); s=t%60
    return f"{h}:{m:02d}:{s:05.2f}"
YB = LY['y_film'] + LY['h_film'] - 4      # 字幕底边：原片区底部上方 4 px
HEAD=f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1560
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: D,Lato,32,&H00A8EBFF,&H00FFFFFF,&H00101010,&H80000000,-1,0,0,0,100,100,0,0,1,2.6,1.2,2,20,20,0,1
Style: H,Lato,29,&H00D6D6D6,&H00FFFFFF,&H00101010,&H80000000,0,-1,0,0,100,100,0,0,1,2.4,1.2,2,20,20,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
for k in idx:
    g=segs[k]; t0=g[0]['t0']; t1=g[-1]['t1']; nfr=g[-1]['f1']-g[0]['f0']
    ass=f"{SEGDIR}/sub_{k:02d}.ass"
    with open(ass,'w',encoding='utf-8') as fo:
        fo.write(HEAD)
        for c in CU:
            a=max(c['t0'],t0); b=min(c['t1'],t1)
            if b<=a: continue
            st='H' if c['kind']=='h' else 'D'
            fo.write(f"Dialogue: 0,{ts(a-t0)},{ts(b-t0)},{st},,0,0,0,,{{\\an2\\pos(540,{YB})}}{c['en']}\n")
    lst=f"{SEGDIR}/list_{k:02d}.txt"
    with open(lst,'w') as fo:
        for s in g: fo.write(f"file '{PAN}/panel_{s['n']:03d}.png'\nduration {(s['f1']-s['f0'])/24.0:.6f}\n")
        fo.write(f"file '{PAN}/panel_{g[-1]['n']:03d}.png'\n")
    fc=(f"[0:v]fps=24,setpts=N/24/TB,format=yuv420p[bg];"
        f"[1:v]crop=1920:804:0:138,scale=1080:452,fps=24,setpts=N/24/TB,format=yuv420p[film];"
        f"[bg][film]overlay=0:{LY['y_film']}[a];"
        f"[2:v]crop=1040:56:x='(t+{t0:.4f})*30':y=0,format=yuva420p[z];[a][z]overlay=20:{LY['y_strip']}[b];"
        f"[b][3:v]overlay=x='19+(t+{t0:.4f})*1040/{TOTAL}':y={LY['y_head']}[c];[c][4:v]overlay=x=539:y={LY['y_headz']},"
        f"subtitles=sub_{k:02d}.ass,format=yuv420p[v]")
    cmd=["ffmpeg","-nostdin","-hide_banner","-loglevel","error","-y","-f","concat","-safe","0","-i",lst,
         "-ss",f"{6306.57+t0:.4f}","-i",SRC,
         "-loop","1","-framerate","24","-i",f"{PAN}/zoom_strip.png","-loop","1","-framerate","24","-i",f"{PAN}/playhead.png",
         "-loop","1","-framerate","24","-i",f"{PAN}/playhead_zoom.png",
         "-filter_complex",fc,"-map","[v]","-frames:v",str(nfr),"-an","-c:v","libx264","-preset","veryfast","-crf","20","-r","24",
         f"seg_{k:02d}.mp4"]
    tt=time.time(); r=subprocess.run(cmd,capture_output=True,text=True,cwd=SEGDIR)
    print(k,'frames',nfr,'rc',r.returncode,round(time.time()-tt,1),'s',r.stderr[-400:])
