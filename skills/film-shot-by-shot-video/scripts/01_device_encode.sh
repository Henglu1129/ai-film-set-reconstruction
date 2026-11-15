#!/usr/bin/env bash
# 在【用户电脑】上跑（device_bash）。每次调用最多 180 秒、调用结束后台进程会被杀，
# 所以 4K HEVC 片段要按块转码：一次调用转一块，块长取 5760 帧（23.976fps 下 240.24 秒），
# 拼接时不会累积帧漂移。视频块不带音频，音频单独一次导出，最后 concat + 合流。
#
# 用法：
#   bash 01_device_encode.sh chunk SRC START_SEC TOTAL_SEC IDX OUTDIR   # 转第 IDX 块（从 0 开始）
#   bash 01_device_encode.sh audio SRC START_SEC TOTAL_SEC OUTDIR
#   bash 01_device_encode.sh concat OUTDIR FINAL.mp4                    # FINAL 放进连接文件夹，才能 stage 到云端
set -e
CH=240.24
mode=$1
if [ "$mode" = chunk ]; then
  SRC=$2; ST=$3; TOT=$4; IDX=$5; OUT=$6; mkdir -p "$OUT"
  S=$(python3 -c "print($ST+$IDX*$CH)"); D=$(python3 -c "print(max(0,min($CH,$TOT-$IDX*$CH)))")
  ffmpeg -y -v error -ss "$S" -i "$SRC" -t "$D" -map 0:v:0 -an -vf "scale=1280:-2" \
    -c:v libx264 -preset veryfast -crf 20 -pix_fmt yuv420p "$OUT/v$IDX.mp4"
  ls -la "$OUT/v$IDX.mp4"
elif [ "$mode" = audio ]; then
  SRC=$2; ST=$3; TOT=$4; OUT=$5; mkdir -p "$OUT"
  ffmpeg -y -v error -ss "$ST" -i "$SRC" -t "$TOT" -map 0:a:0 -vn -c:a aac -b:a 192k -ac 2 "$OUT/a.m4a"
elif [ "$mode" = concat ]; then
  OUT=$2; FINAL=$3
  ls "$OUT"/v*.mp4 | sort -V | sed "s|^|file |" > "$OUT/l.txt"
  ffmpeg -y -v error -f concat -safe 0 -i "$OUT/l.txt" -i "$OUT/a.m4a" -map 0:v -map 1:a -c copy "$FINAL"
  ffprobe -v error -show_entries format=duration "$FINAL"
fi
