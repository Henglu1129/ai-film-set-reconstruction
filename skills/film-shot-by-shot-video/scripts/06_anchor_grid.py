"""为每个镜头生成带 10×6 坐标网格的三联帧（15% / 50% / 85% 处），7 镜一页，用来人工读出
光源位置（布光锚点）和主色区域（色调锚点），写进 anchors.py。网格：x 列 0–9 各占 0.1 宽，y 行 0–5 各占 1/6 高，
数字标在格子左上角。读坐标时取格子中心再估小数，光源锚点渲染时会自动吸附到附近 75px 内最亮的点。
★ 帧取自 ffmpeg 抽的 1fps 帧（frames/），不要用 OpenCV 的 CAP_PROP_POS_MSEC 跳帧：H.264 下跳帧不准，会拿到别的镜头的画面。
用法：python3 06_anchor_grid.py WORK_DIR"""
import json, cv2, subprocess, os, sys
W = sys.argv[1]
s = json.load(open(os.path.join(W, 'shots.json')))
os.makedirs(os.path.join(W, 'grid'), exist_ok=True)
NF = len([f for f in os.listdir(os.path.join(W, 'frames')) if f.startswith('f_')])
for x in s:
    ims = []
    for k in (0.15, 0.5, 0.85):
        t = x['start'] + (x['end'] - x['start']) * k
        fr = cv2.imread(os.path.join(W, 'frames', f'f_{max(1, min(NF, int(t) + 1)):05d}.jpg'))
        fr = cv2.resize(fr, (480, 270))
        for g in range(1, 10): cv2.line(fr, (g * 48, 0), (g * 48, 270), (0, 255, 255), 1)
        for g in range(1, 6): cv2.line(fr, (0, g * 45), (480, g * 45), (0, 255, 255), 1)
        for gx in range(10): cv2.putText(fr, str(gx), (gx * 48 + 2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 255), 1)
        for gy in range(6): cv2.putText(fr, str(gy), (2, gy * 45 + 26), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 255), 1)
        ims.append(fr)
    row = cv2.hconcat(ims)
    cv2.putText(row, f"#{x['n']}", (440, 262), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
    cv2.imwrite(os.path.join(W, 'grid', f"g_{x['n']:03d}.jpg"), row)
for b in range(0, len(s), 7):
    subprocess.run(['montage', *[os.path.join(W, 'grid', f"g_{n:03d}.jpg") for n in range(b + 1, min(len(s) + 1, b + 8))],
                    '-tile', '1x', '-geometry', '+0+3', '-background', 'gray20', os.path.join(W, 'verify', f'grid_{b // 7}.jpg')])
print('ok')
