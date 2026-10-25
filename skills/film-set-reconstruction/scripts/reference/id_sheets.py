# ==== 《大事件》(2004) 开场长镜头项目里的实际代码，原样保留作参考 ====
# 里面的路径（/tmp/claude-0/...、/mnt/user-data/...）、坐标、车辆尺寸、帧号区间都是那部片子的，换片时逐项改。
# 约定：机位 R 为 世界→相机（OpenCV：x 右 y 下 z 前），C 为相机中心；画面 1280×554 时 CX=640 CY=277、HFOV=42°。
import json, cv2, numpy as np, collections
from PIL import Image, ImageDraw, ImageFont
exec(open('/tmp/claude-0/v6/labels.py').read())
import sys
PFX = sys.argv[1]; T = json.load(open(f'tracklets_{PFX}.json')); C = json.load(open('/tmp/claude-0/det/census2.json'))
CB = collections.defaultdict(list)
for p in C['people']:
    for s in p['s']: CB[s['f']].append((p['id'], s['b']))
def iou(a, b):
    x0, y0, x1, y1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, x1 - x0) * max(0, y1 - y0); ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0
pref = {}
for t in T:
    votes = collections.Counter()
    for o in t['obs']:
        for cid, b in CB.get(o['i'] * 3, []):
            if iou(b, o['b']) > 0.6: votes[L.get(cid, 'extra') + ':' + cid] += 1
    pref[t['id']] = votes.most_common(2)
json.dump(pref, open(f'prefill_{PFX}.json', 'w'), ensure_ascii=False)
F = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", 15, index=2)
cap = cv2.VideoCapture("/mnt/user-data/uploads/电影资源/大事件_长镜头拆解/det_src.mp4")
need = {}
for t in T:
    n = len(t['obs']); t['_p'] = []
    for q in (0.1, 0.5, 0.9):
        k0 = int(q * (n - 1)); win = t['obs'][max(0, k0 - 2):k0 + 3]
        best = max(win, key=lambda o: o['b'][3] - o['b'][1]); t['_p'].append(best); need[best['i'] * 3] = None
for f in sorted(need):
    cap.set(cv2.CAP_PROP_POS_FRAMES, f); ok, fr = cap.read(); need[f] = fr if ok else None
def crop(o):
    fr = need.get(o['i'] * 3)
    if fr is None: return Image.new('RGB', (110, 170))
    x0, y0, x1, y1 = o['b']; w, h = x1 - x0, y1 - y0
    x0 = max(0, int(x0 - 0.1 * w)); x1 = min(1920, int(x1 + 0.1 * w)); y0 = max(0, int(y0 - 0.05 * h)); y1 = min(832, int(y1 + 0.03 * h))
    im = Image.fromarray(cv2.cvtColor(fr[y0:y1, x0:x1], cv2.COLOR_BGR2RGB)); sc = 170 / im.height
    return im.resize((max(1, min(116, int(im.width * sc))), 170))
mm = lambda i: (lambda t: f"{int(t//60):02d}:{t%60:04.1f}")(80.8 + i * 3 / 24)
CW, CH, PER = 360, 214, 20
for sh in range(0, len(T), PER):
    cv_ = Image.new('RGB', (CW * 4, CH * 5), (20, 22, 26)); d = ImageDraw.Draw(cv_)
    for k, t in enumerate(T[sh:sh + PER]):
        cx, cy = (k % 4) * CW, (k // 4) * CH
        for j, o in enumerate(t['_p']): cv_.paste(crop(o), (cx + 4 + j * 118, cy + 40))
        o0, o1 = t['obs'][0], t['obs'][-1]
        d.text((cx + 4, cy + 2), f"{t['id']}  {mm(o0['i'])}–{mm(o1['i'])}  x{int((o0['b'][0]+o0['b'][2])/2)}", font=F, fill=(255, 200, 80))
        pf = pref[t['id']]; txt = ' / '.join(f"{a.split(':')[0]}({a.split(':')[1]})×{c}" for a, c in pf) or '-'
        d.text((cx + 4, cy + 20), txt[:44], font=F, fill=(190, 205, 215))
        d.rectangle([cx, cy, cx + CW - 1, cy + CH - 1], outline=(60, 66, 74))
    cv_.save(f"/tmp/claude-0/full/trk/sheet_{PFX}_{sh // PER:02d}.jpg", quality=86)
print('sheets', (len(T) + PER - 1) // PER)
