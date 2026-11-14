# ==== 《大事件》(2004) 开场长镜头项目里的实际代码，原样保留作参考 ====
# 里面的路径（/tmp/claude-0/...、/mnt/user-data/...）、坐标、车辆尺寸、帧号区间都是那部片子的，换片时逐项改。
# 约定：机位 R 为 世界→相机（OpenCV：x 右 y 下 z 前），C 为相机中心；画面 1280×554 时 CX=640 CY=277、HFOV=42°。
#!/bin/bash
# 全片合成 v3：上 = 拍摄现场（render_full）· 中 = 原片 · 下 = 一句剧情 + 一句镜头（无俯视图），画幅 1080×1488
SF=$2; NF=$3; FS=$(python3 -c "print(round(80.8+($SF-1)/24,4))"); DUR=$(python3 -c "print($NF/24)")
FILM="${FILM:-../原片.mp4}"; CAP=pilot/capV3
LIST=$CAP/list_$SF.txt
python3 - "$FS" "$DUR" "$CAP" "$LIST" <<'PY'
import json,sys
fs,dur,cap,lst=float(sys.argv[1]),float(sys.argv[2]),sys.argv[3],sys.argv[4]
T=json.load(open(cap+'/times.json'))+[1e9]; fe=fs+dur; L=[]
for i in range(len(T)-1):
    a,b=max(T[i],fs),min(T[i+1],fe)
    if b>a: L.append((i,b-a))
with open(lst,'w') as f:
    for i,d in L: f.write(f"file 'c{i:02d}.png'\nduration {d:.4f}\n")
    f.write(f"file 'c{L[-1][0]:02d}.png'\n")
PY
ffmpeg -hide_banner -loglevel error -y \
  -f lavfi -i "color=c=0x0E1115:s=1080x1488:r=24:d=$DUR" \
  -framerate 24 -start_number $SF -i render_full/%05d.jpg \
  -ss $FS -t $DUR -i "$FILM" \
  -f concat -safe 0 -i $LIST \
  -loop 1 -framerate 24 -i $CAP/chrome_v3.png \
  -filter_complex "\
[1:v]scale=1080:780,setsar=1[top];[2:v]setpts=PTS-STARTPTS,crop=1920:832:0:124,scale=1080:468,setsar=1[film];[3:v]fps=24,setsar=1[cap];[4:v]format=rgba[chrome];\
[0][top]overlay=0:96:eof_action=pass[a];[a][film]overlay=0:880[c];[c][cap]overlay=0:1348:eof_action=repeat[d];[d][chrome]overlay=0:0:shortest=0[v]" \
  -map "[v]" -map 2:a:1 -t $DUR -r 24 -c:v libx264 -preset veryfast -crf 20 -pix_fmt yuv420p -c:a aac -b:a 160k "$1"
