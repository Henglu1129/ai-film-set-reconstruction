#!/usr/bin/env bash
# 把 03_subtitle_segments.py 存下的字幕带拼成校对页（每页 40 条、两列、左侧标编号），用 Read 逐页看图校对。
# OCR 错字很多（「纪录片」→「理录片」之类），一定要对着图逐条改，校对结果写进 fixsubs.py 的 T 字典。
# 两行字幕的第一行常被裁掉：对这些编号用 TALL=1 重新从视频取更高的一条（见 SKILL.md 第 4 步）。
# 用法：bash 03b_subtitle_sheets.sh WORK_DIR
W=$1; cd "$W"; mkdir -p sl verify
for f in strips/s_*.png; do k=$(basename $f .png)
  convert $f -crop 900x112+190+0 +repage -resize 600x -background black -fill yellow -pointsize 14 label:"${k#s_}" +swap -gravity west +append sl/$k.png
done
n=$(ls sl/*.png | wc -l); pages=$(( (n+39)/40 ))
for ((i=0;i<pages;i++)); do
  montage $(ls sl/*.png | sed -n "$((i*40+1)),$((i*40+40))p") -tile 2x -geometry +2+2 -background gray20 verify/subs_$i.jpg
done
echo "pages: $pages"
