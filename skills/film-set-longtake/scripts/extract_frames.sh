#!/bin/bash
# 第 1 步：从原片切出要还原的镜头，产出三种素材
#   take.mp4     —— 去黑边的 1920×H 原画（检测、对照、合成都用它；帧号 = take 帧号，从 0 开始）
#   sfm/f%05d.jpg —— 每 STEP 帧一张、缩到 1280 宽，给 SfM 和消失点用（文件名里的数字 = take 帧号）
#   sheet_*.jpg   —— 每 2 秒一张的接触印样，用来做“场景勘景清单”
# 用法：bash extract_frames.sh 原片.mp4 起点秒 终点秒 [STEP=3] [CROP=1920:832:0:124]
# 注意：起止点要精确到帧——先用 scene 检测找剪辑点（见 SKILL.md 第 1 步），别凭感觉。
set -e
SRC="$1"; T0="$2"; T1="$3"; STEP="${4:-3}"; CROP="${5:-1920:832:0:124}"
DUR=$(python3 -c "print($T1-$T0)")
mkdir -p sfm sheets
# 精确切：-ss 放在 -i 后面（逐帧解码，慢但准）
ffmpeg -hide_banner -loglevel error -y -i "$SRC" -ss "$T0" -t "$DUR" -vf "crop=$CROP" -an -c:v libx264 -crf 14 -preset fast take.mp4
ffmpeg -hide_banner -loglevel error -y -i take.mp4 -vf "select='not(mod(n\,$STEP))',scale=1280:-2" -vsync 0 -q:v 2 -frame_pts 1 sfm/f%05d.jpg
ffmpeg -hide_banner -loglevel error -y -i take.mp4 -vf "fps=1/2,scale=320:-2,tile=6x5" -q:v 3 sheets/sheet_%02d.jpg
echo "frames: $(ls sfm | wc -l)  (t = $T0 + f/24)"
