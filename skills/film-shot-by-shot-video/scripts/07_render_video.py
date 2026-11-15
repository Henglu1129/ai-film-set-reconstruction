# -*- coding: utf-8 -*-
"""逐帧合成拉片视频：上原片（叠人物轮廓 + 景别/镜头运动/布光/色调标注），下拉片面板（剧情/表演/声音/分析注释），
顶部标题与右上角镜号+时间码，中间全段时间轴。Python 逐帧画好后经管道交给 ffmpeg 编码，2 核约 30 帧/秒。
用法：
  python3 07_render_video.py WORK_DIR still 290 612      # 抽几帧看版式（输出 WORK/verify/v3_<秒>.png）
  python3 07_render_video.py WORK_DIR full out.mp4       # 全片渲染（后台跑）
WORK_DIR 里需要：config.json、clip.mp4、frames/、shots.json、seg.pkl、analysis.py、anchors.py
"""
import json, sys, os, subprocess, pickle, re, numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter
WORK = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.abspath('.')
sys.path.insert(0, WORK)
from analysis import A, SCENES
from anchors import LIGHT, COLOR
CFG = json.load(open(os.path.join(WORK, 'config.json')))
P = lambda *a: os.path.join(WORK, *a)

W, H = 1080, 1440
FPS_NUM, FPS_DEN = 24000, 1001
FPS = FPS_NUM / FPS_DEN
FW, FH = 1080, 608
FILM_Y = 104
OFFSET = float(CFG['offset_seconds'])
SHOTS = json.load(open(P('shots.json')))
TOTAL = SHOTS[-1]['end']
NF = len([f for f in os.listdir(P('frames')) if f.startswith('f_')])
SUBS = json.load(open(P('subs_clean.json'))) if os.path.exists(P('subs_clean.json')) else []
SEG = None

WK = CFG['font_light']
_fc = {}
def F(size):
    if size not in _fc: _fc[size] = ImageFont.truetype(WK, size)
    return _fc[size]

BG = (13, 13, 15); AMBER = (236, 186, 98); TXT = (238, 234, 226); GREY = (150, 150, 156); DIM = (70, 70, 78)
CONT = (222, 218, 210)
L, R = 48, 1032

def tc(t):
    g = OFFSET + t
    return f"{int(g // 3600)}:{int(g % 3600 // 60):02d}:{int(g % 60):02d}"

NOEND = set('「『（【《“‘(')
NOSTART = set('，。、；：！？」』）】》…,.;:!?”’)')
def wrap(text, font, width):
    lines, cur = [], ''
    for ch in text:
        if font.getlength(cur + ch) <= width or (ch in NOSTART and cur):
            cur += ch
        else:
            if cur and cur[-1] in NOEND:
                lines.append(cur[:-1]); cur = cur[-1] + ch
            else:
                lines.append(cur); cur = ch
    if cur: lines.append(cur)
    return lines

def scene_of(n):
    for i, (a, b, lab) in enumerate(SCENES):
        if a <= n <= b: return i, lab
    return 0, ''

def kcount(size):
    if '空镜' in size: return 0
    for k, v in (('四人', 4), ('三人', 3), ('双人', 2), ('群像', 5)):
        if k in size: return v
    return 1

# ======================= 画面标注 =======================
GW, GH = 135, 76          # 占用栅格（1/8）
CELL = 8

def shot_frames(x):
    a = int(round(x['start'] * FPS)); b = int(round(x['end'] * FPS)) - 1
    return a, max(a, b)

def persons_at(i):
    return SEG['frames'].get(i, [])

def occupancy(x):
    a, b = shot_frames(x)
    idx = list(range(a, b + 1, 4)) or [a]
    occ = np.zeros((GH, GW), np.float32)
    boxes = []
    k = kcount(A[x['n']][0])
    for i in idx:
        ps = persons_at(i)
        m = np.zeros((GH, GW), np.uint8)
        for p in ps:
            pts = (p['poly'] * [GW, GH]).astype(np.int32)
            cv2.fillPoly(m, [pts], 1)
            bx = p['box']
            if (bx[3] - bx[1]) > 0.15:   # 脸部区域加权
                x0, y0, x1, y1 = int(bx[0] * GW), int(bx[1] * GH), int(bx[2] * GW), int(bx[1] * GH + (bx[3] - bx[1]) * GH * 0.32)
                occ[max(0, y0 - 2):y1 + 1, max(0, x0 - 1):x1 + 1] += 2.0 / len(idx)
        occ += m.astype(np.float32) / len(idx)
        sel = sorted(ps, key=lambda p: -(p['box'][2] - p['box'][0]) * (p['box'][3] - p['box'][1]))[:max(k, 1)]
        sel = [p for p in sel if (p['box'][2] - p['box'][0]) * (p['box'][3] - p['box'][1]) > 0.006]
        if sel and k > 0:
            bb = np.array([p['box'] for p in sel])
            boxes.append([bb[:, 0].min(), bb[:, 1].min(), bb[:, 2].max(), bb[:, 3].max()])
    # 亮区（白字难读）
    mid = (x['start'] + x['end']) / 2
    for tt in (x['start'] + 0.3, mid, x['end'] - 0.3):
        g = cv2.imread(P("frames", f"f_{max(1, min(NF, int(tt) + 1)):05d}.jpg"), 0)
        g = cv2.resize(g, (GW, GH), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
        occ += np.clip((g - 0.55) * 4, 0, 1.2) / 3
    # 硬字幕区
    occ[int(GH * 0.80):int(GH * 0.97), int(GW * 0.15):int(GW * 0.85)] += 3
    main = np.median(np.array(boxes), axis=0) if len(boxes) >= max(1, len(idx) // 4) else None
    return occ, main

def palette(x):
    mid = (x['start'] + x['end']) / 2
    f = P("frames", f"f_{max(1, min(NF, int(mid) + 1)):05d}.jpg")
    im = cv2.imread(f); im = cv2.resize(im, (128, 72)); px = im.reshape(-1, 3).astype(np.float32)
    _, lab, cen = cv2.kmeans(px, 7, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 40, 0.5), 4, cv2.KMEANS_PP_CENTERS)
    cnt = np.bincount(lab.flatten(), minlength=7).astype(float)
    hsv = cv2.cvtColor(cen.reshape(1, -1, 3).astype(np.uint8), cv2.COLOR_BGR2HSV)[0].astype(float)
    score = cnt * (0.2 + hsv[:, 1] / 255) * np.where(hsv[:, 2] > 35, 1.0, 0.25)
    order = np.argsort(-score)
    pick = []
    for o in order:
        if all(np.abs(cen[o] - cen[p]).sum() > 45 for p in pick): pick.append(o)
        if len(pick) == 3: break
    return [tuple(int(c) for c in cen[o][::-1]) for o in pick]

AVOID = []
def snap_light(x, la):
    fr = (x['start'] + x['end']) / 2
    if len(la) > 2: fr = x['start'] + (x['end'] - x['start']) * (la[2] + 1) / 2
    g = cv2.imread(P("frames", f"f_{max(1, min(NF, int(fr) + 1)):05d}.jpg"), 0)
    g = cv2.GaussianBlur(cv2.resize(g, (FW, FH)).astype(np.float32), (0, 0), 6)
    ax, ay = la[0] * FW, la[1] * FH; rad = 75
    x0, y0 = int(max(0, ax - rad)), int(max(0, ay - rad)); x1, y1 = int(min(FW, ax + rad)), int(min(FH, ay + rad))
    sub = g[y0:y1, x0:x1]
    my, mx = np.unravel_index(np.argmax(sub), sub.shape)
    if sub[my, mx] > g[int(min(FH-1, ay)), int(min(FW-1, ax))] + 12:
        return (x0 + mx, y0 + my)
    return (ax, ay)
TF, VF = 19, 22          # 标签标题/内容字号
def label_block(title, text, maxw=360, extra_title_w=0):
    lines = wrap(text, F(VF), maxw) if text else []
    tw = F(TF).getlength(title) + extra_title_w
    w = int(max([tw] + [F(VF).getlength(l) for l in lines])) + 4
    h = 26 + len(lines) * 30
    return {'title': title, 'lines': lines, 'w': w, 'h': h}

def place(occ, blk, placed, anchor=None, pref=None, allow_body=1.0):
    w, h = blk['w'] + 8, blk['h'] + 6
    cw, ch = int(np.ceil(w / CELL)), int(np.ceil(h / CELL))
    S = np.pad(occ, ((1, 0), (1, 0))).cumsum(0).cumsum(1)
    best = None
    for gy in range(2, GH - ch - 1):
        for gx in range(2, GW - cw - 1):
            s = S[gy + ch, gx + cw] - S[gy, gx + cw] - S[gy + ch, gx] + S[gy, gx]
            cost = s / (cw * ch) * 100 * allow_body
            px, py = gx * CELL, gy * CELL
            rect = (px, py, px + w, py + h)
            if any(not (rect[2] < q[0] - 6 or rect[0] > q[2] + 6 or rect[3] < q[1] - 6 or rect[1] > q[3] + 6) for q in placed):
                continue
            if any(rect[0] - 16 < qx < rect[2] + 16 and rect[1] - 16 < qy < rect[3] + 16 for qx, qy in AVOID):
                continue
            if anchor is not None:
                ax, ay = anchor
                if rect[0] - 14 < ax < rect[2] + 14 and rect[1] - 14 < ay < rect[3] + 14: continue
                dx = max(rect[0] - ax, 0, ax - rect[2]); dy = max(rect[1] - ay, 0, ay - rect[3])
                cost += 0.06 * (dx * dx + dy * dy) ** 0.5
            if pref == 'tl': cost += 0.03 * (px + py)
            if pref == 'edge': cost += 0.015 * min(px, py, FW - rect[2], FH - rect[3])
            if best is None or cost < best[0]: best = (cost, rect)
    return best[1] if best else (20, 20, 20 + w, 20 + h)

def text_layer(size, items):
    """items: list of (xy, text, font, fill)"""
    sh = Image.new('L', size, 0); ds = ImageDraw.Draw(sh)
    for xy, t, f, fill in items: ds.text(xy, t, font=f, fill=255)
    sh = sh.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(3))
    return sh

def build_overlay(n, phase):
    """静态标注层（RGBA，1080x608）"""
    x = SHOTS[n - 1]
    occ, main = OCC[n]
    size, move, light, color = A[n][:4]
    ov = Image.new('RGBA', (FW, FH), (0, 0, 0, 0))
    items = []; rings = []; leaders = []; dots = []
    placed = []
    AVOID.clear()
    for v in (LIGHT.get(n), COLOR.get(n)):
        if v is not None: AVOID.append((v[0] * FW, v[1] * FH))
    def put(blk, rect, dot_rgb=None):
        x0, y0 = rect[0] + 4, rect[1] + 3
        items.append(((x0, y0), blk['title'], F(TF), AMBER))
        if dot_rgb:
            tx = x0 + F(TF).getlength(blk['title']) + 12
            for j, c in enumerate(dot_rgb): dots.append((tx + 8 + j * 20, y0 + 11, c))
        for j, ln in enumerate(blk['lines']):
            items.append(((x0, y0 + 26 + j * 30), ln, F(VF), (248, 246, 240)))
    # 2 景别
    b1 = label_block('景别', size, 300)
    anc = None
    if main is not None:
        bx = main * [FW, FH, FW, FH]
        cands = [(bx[2] + 10, bx[1] + 0.38 * (bx[3] - bx[1])), (bx[0] - 10, bx[1] + 0.38 * (bx[3] - bx[1]))]
        best = None
        for c in cands:
            if not (0 < c[0] < FW): continue
            r = place(occ, b1, placed, anchor=c, allow_body=0.6)
            sc = abs((r[0] + r[2]) / 2 - c[0]) + abs((r[1] + r[3]) / 2 - c[1])
            if best is None or sc < best[0]: best = (sc, r)
        r1 = best[1] if best else place(occ, b1, placed, pref='edge')
    else:
        r1 = place(occ, b1, placed, pref='edge')
    placed.append(r1); put(b1, r1)
    # 3 布光
    la = LIGHT.get(n); a_ok = la is not None and (len(la) < 3 or phase == 1)
    b2 = label_block('布光', light, 340)
    if la is not None:
        ap = snap_light(x, la)
        AVOID.append(ap)
        r2 = place(occ, b2, placed, anchor=ap)
        if a_ok: rings.append(ap); leaders.append((ap, r2))
    else:
        r2 = place(occ, b2, placed, pref='edge')
    placed.append(r2); put(b2, r2)
    # 4 色调
    ca = COLOR.get(n); c_ok = ca is not None and (len(ca) < 3 or phase == 1)
    pal = PAL[n]
    b3 = label_block('色调', color, 340, extra_title_w=76)
    if ca is not None:
        ap = (ca[0] * FW, ca[1] * FH)
        r3 = place(occ, b3, placed, anchor=ap)
        if c_ok: rings.append(ap); leaders.append((ap, r3))
    else:
        r3 = place(occ, b3, placed, pref='edge')
    placed.append(r3); put(b3, r3, pal)
    # 5 镜头运动
    b4 = label_block('镜头运动', move, 360)
    r4 = place(occ, b4, placed, pref='edge'); placed.append(r4); put(b4, r4)

    # 阴影
    sh = text_layer((FW, FH), items)
    shadow = Image.new('RGBA', (FW, FH), (0, 0, 0, 0)); shadow.putalpha(sh.point(lambda v: min(255, int(v * 1.25))))
    ov = Image.alpha_composite(ov, shadow)
    d = ImageDraw.Draw(ov)
    for (ax, ay), rect in leaders:
        tx = min(max(ax, rect[0]), rect[2]); ty = min(max(ay, rect[1]), rect[3])
        vx, vy = tx - ax, ty - ay; dd = (vx * vx + vy * vy) ** 0.5
        if dd > 16:
            sx, sy = ax + vx / dd * 11, ay + vy / dd * 11
            d.line([(sx + 1, sy + 1), (tx + 1, ty + 1)], fill=(0, 0, 0, 120), width=1)
            d.line([(sx, sy), (tx, ty)], fill=(255, 255, 255, 170), width=1)
    for ax, ay in rings:
        d.ellipse([ax - 10, ay - 10, ax + 10, ay + 10], outline=(0, 0, 0, 110), width=3)
        d.ellipse([ax - 9, ay - 9, ax + 9, ay + 9], outline=(255, 255, 255, 220), width=1)
        d.ellipse([ax - 2, ay - 2, ax + 2, ay + 2], fill=(255, 255, 255, 230))
    for cx, cy, c in dots:
        d.ellipse([cx - 8, cy - 8, cx + 8, cy + 8], fill=c + (255,), outline=(255, 255, 255, 150), width=1)
    for xy, t, f, fill in items:
        d.text(xy, t, font=f, fill=fill + (255,))
    arr = np.asarray(ov).astype(np.float32)
    return arr[:, :, :3], arr[:, :, 3:4] / 255.0

# ======================= 下方面板 =======================
TL_Y, TL_H = 728, 10
def tx_of(t): return L + (R - L) * t / TOTAL
ROWS = ['剧情', '表演', '声音', '分析注释']
PILL_W = 124
CX = L + PILL_W + 20
BODY_Y = 786
FSZ = 27; LH = int(FSZ * 1.55); GAP = 22

def body_height(n):
    fc = F(FSZ)
    plot, perf, sound, note = A[n][4:]
    nl = sum(len(wrap(v, fc, R - CX)) for v in (plot, perf, sound, note))
    return nl * LH + (len(ROWS) - 1) * GAP

def build_panel(n):
    im = Image.new('RGB', (W, H), BG); d = ImageDraw.Draw(im)
    f1 = F(36)
    d.text((L, 18), CFG['header_prefix'], font=f1, fill=AMBER)
    d.text((L + f1.getlength(CFG['header_prefix']) + 18, 18), CFG['header_title'], font=f1, fill=TXT)
    d.text((L, 66), CFG['header_sub'], font=F(22), fill=GREY)
    shot = SHOTS[n - 1]
    d.text((R, 20), f'镜号 {n:02d}', font=F(30), fill=AMBER, anchor='ra')
    d.text((R, 66), f'{tc(shot["start"])} → {tc(shot["end"])}', font=F(22), fill=TXT, anchor='ra')
    si, slab = scene_of(n)
    for x in SHOTS:
        x0, x1 = tx_of(x['start']), tx_of(x['end'])
        col = AMBER if x['n'] == n else ((92, 92, 100) if x['n'] % 2 else (66, 66, 74))
        d.rectangle([x0 + 1, TL_Y, max(x0 + 1, x1 - 1), TL_Y + TL_H], fill=col)
    for i, (a, b, lab) in enumerate(SCENES):
        s0 = SHOTS[a - 1]['start']; e0 = SHOTS[b - 1]['end']; x0, x1 = tx_of(s0), tx_of(e0)
        d.line([x0, TL_Y + TL_H + 3, x0, TL_Y + TL_H + 10], fill=DIM, width=1)
        d.text(((x0 + x1) / 2, TL_Y + TL_H + 13), lab, font=F(18), fill=AMBER if i == si else GREY, anchor='ma')
    plot, perf, sound, note = A[n][4:]
    texts = {'剧情': plot, '表演': perf, '声音': sound, '分析注释': note}
    fc = F(FSZ); flab = F(24)
    y = BODY_Y
    for k in ROWS:
        lines = wrap(texts[k], fc, R - CX)
        d.rounded_rectangle([L, y + LH / 2 - 19, L + PILL_W, y + LH / 2 + 19], radius=9, fill=(54, 45, 30))
        d.text((L + PILL_W / 2, y + LH / 2), k, font=flab, fill=AMBER, anchor='mm')
        for i, ln in enumerate(lines):
            d.text((CX, y + LH / 2 + i * LH), ln, font=fc, fill=CONT, anchor='lm')
        y += len(lines) * LH + GAP
    return im

PANEL = {}
def panel_with_sub(n, sub=None):
    if n in PANEL: return PANEL[n]
    if len(PANEL) > 4: PANEL.clear()
    PANEL[n] = np.asarray(build_panel(n)).copy()
    return PANEL[n]

def sub_at(t, shot):
    best = None
    for s in SUBS:
        if s['s'] - 0.05 > t: break
        if t < s['e'] + 2.5 and s['e'] > shot['start'] + 0.2: best = s
    return best

def shot_at(t):
    for x in SHOTS:
        if x['start'] <= t < x['end']: return x
    return SHOTS[-1]

# ======================= 合成 =======================
OVL = {}
def overlay(n, t):
    x = SHOTS[n - 1]
    la = LIGHT.get(n); ca = COLOR.get(n)
    thr = max([v[2] for v in (la, ca) if v is not None and len(v) > 2] + [0])
    phase = 1 if (thr == 0 or (t - x['start']) / (x['end'] - x['start']) >= thr) else 0
    key = (n, phase)
    if key not in OVL:
        if len(OVL) > 4: OVL.clear()
        OVL[key] = build_overlay(n, phase)
    return OVL[key]

STATE = {'n': None, 'm': None}
def contours(fr, i, n):
    k = kcount(A[n][0])
    if STATE['n'] != n: STATE['n'] = n; STATE['m'] = None
    if k == 0: return fr
    ps = sorted(persons_at(i), key=lambda p: -(p['box'][2] - p['box'][0]) * (p['box'][3] - p['box'][1]))[:k]
    ps = [p for p in ps if (p['box'][2] - p['box'][0]) * (p['box'][3] - p['box'][1]) > 0.006]
    m = np.zeros((FH // 2, FW // 2), np.float32)
    for p in ps:
        cv2.fillPoly(m, [(p['poly'] * [FW // 2, FH // 2]).astype(np.int32)], 1.0)
    m = cv2.GaussianBlur(m, (5, 5), 0)
    STATE['m'] = m if STATE['m'] is None else 0.55 * STATE['m'] + 0.45 * m
    b = (STATE['m'] > 0.5).astype(np.uint8)
    cs, _ = cv2.findContours(b, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    cs = [cv2.approxPolyDP(c, 0.8, True) * 2 for c in cs if cv2.contourArea(c) > 300]
    if not cs: return fr
    lm = np.zeros((FH, FW), np.uint8)
    cv2.polylines(lm, cs, True, 255, 2, cv2.LINE_AA)
    lm[:6, :] = 0; lm[-6:, :] = 0; lm[:, :6] = 0; lm[:, -6:] = 0
    a = (lm.astype(np.float32) / 255.0 * 0.55)[:, :, None]
    return fr * (1 - a) + 255 * a

def render_frame(fr_film, i):
    t = i / FPS
    shot = shot_at(t); n = shot['n']
    f = fr_film.astype(np.float32)
    f = contours(f, i, n)
    rgb, al = overlay(n, t)
    f = f * (1 - al) + rgb * al
    can = panel_with_sub(n).copy()
    can[FILM_Y:FILM_Y + FH] = np.clip(f, 0, 255).astype(np.uint8)
    x = int(tx_of(t)); can[TL_Y - 5:TL_Y + TL_H + 5, max(0, x - 1):x + 2] = (255, 255, 255)
    return can

def init():
    global SEG, OCC, PAL, H
    hb = max(body_height(x['n']) for x in SHOTS)
    H = int(np.ceil((BODY_Y + hb + 34) / 8) * 8)
    print('H =', H, flush=True)
    SEG = pickle.load(open(P('seg.pkl'), 'rb'))
    OCC = {x['n']: occupancy(x) for x in SHOTS}
    PAL = {x['n']: palette(x) for x in SHOTS}

if __name__ == '__main__':
    init()
    os.makedirs(P('verify'), exist_ok=True)
    mode = sys.argv[2]
    if mode == 'still':
        for t in map(float, sys.argv[3:]):
            i = int(round(t * FPS))
            cap = cv2.VideoCapture(P(CFG.get('clip', 'clip.mp4'))); cap.set(cv2.CAP_PROP_POS_FRAMES, i)
            ok, fr = cap.read(); fr = cv2.resize(fr, (FW, FH), interpolation=cv2.INTER_AREA)[:, :, ::-1]
            STATE['n'] = None
            Image.fromarray(render_frame(fr, i)).save(P('verify', f'v3_{t:.0f}.png'))
    else:
        out = sys.argv[3]
        dec = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', P(CFG.get('clip', 'clip.mp4')), '-vf', f'scale={FW}:{FH}:flags=lanczos',
                                '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
        enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
                                '-r', f'{FPS_NUM}/{FPS_DEN}', '-i', '-', '-i', P(CFG.get('clip', 'clip.mp4')),
                                '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20',
                                '-pix_fmt', 'yuv420p', '-c:a', 'copy', '-movflags', '+faststart', '-shortest', out], stdin=subprocess.PIPE)
        fsz = FW * FH * 3; i = 0
        while True:
            buf = dec.stdout.read(fsz)
            if len(buf) < fsz: break
            enc.stdin.write(render_frame(np.frombuffer(buf, np.uint8).reshape(FH, FW, 3), i).tobytes())
            i += 1
            if i % 1200 == 0: print('frame', i, flush=True)
        enc.stdin.close(); enc.wait(); print('DONE', i, flush=True)
