# 合成每个镜头的面板（1080×1560）：标题 / 俯视现场+标注 / 时间轴 / [原片留空] / 字幕说明
# 用法：python3 compose_panels.py <work_dir> <data.json> <render_dir> <out_dir> [shot_n ...]
import json, math, os, sys
from PIL import Image, ImageDraw, ImageFont

WORK, DATA, RDIR, OUT = sys.argv[1:5]
ONLY = set(int(x) for x in sys.argv[5:]) if len(sys.argv) > 5 else None
D = json.load(open(DATA))
A = json.load(open(os.path.join(RDIR, 'anchors.json')))
os.makedirs(OUT, exist_ok=True)
FB = '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'
FR = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
def F(sz, bold=True): return ImageFont.truetype(FB if bold else FR, sz)

W, H = 1080, 1560
Y_FILM, H_FILM = 80, 452     # 原片
Y_TL, H_TL = 532, 150        # 时间轴（机位滚动条）
Y_TOP, H_TOP = 682, 620      # 拍摄机位还原（俯视）
Y_CAP = 1302                 # 机位文字介绍
BG = (24, 27, 33)
SETUP = {s['id']: s for s in D['setups']}
TOTAL = D['shots'][-1]['t1']
PH_NAME = {1: '对峙', 2: '离场·倒数', 3: '处决', 4: '台上终章'}
PH_COL = {1: (86, 110, 150), 2: (150, 112, 70), 3: (150, 62, 62), 4: (110, 80, 140)}
LIGHT_ROWS = [("L1", "西窗日光·透纱帘"), ("L2", "东窗日光·透纱帘"), ("L3", "天花日光灯盘"),
              ("L4", "球形壁灯"), ("L5", "画像背光光晕"), ("L6", "发光石雕"),
              ("L7", "门外走廊光(推测)"), ("L8", "布幔上方顶光(推测)"), ("L9", "门洞黑幕·负补光")]

def hexc(h): h = h.lstrip('#'); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
def s35(h): return 24.89 / (2 * math.tan(math.radians(h / 2)))
def tc(t):
    t += D['T0_frame'] / 24.0; h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h}:{m:02d}:{s:04.1f}"

def chip(d, x, y, text, fill, fg=(20, 20, 20), font=None, pad=(8, 3), r=7, outline=None):
    font = font or F(16)
    bb = d.textbbox((0, 0), text, font=font); tw, th = bb[2] - bb[0], bb[3] - bb[1]
    box = (x, y, x + tw + 2 * pad[0], y + th + 2 * pad[1] + 4)
    d.rounded_rectangle(box, r, fill=fill, outline=outline, width=2 if outline else 0)
    d.text((x + pad[0], y + pad[1] - bb[1] + 2), text, font=font, fill=fg)
    return box

def overlap(a, b, m=3):
    return not (a[2] + m < b[0] or b[2] + m < a[0] or a[3] + m < b[1] or b[3] + m < a[1])

# ---------- 时间轴（全局条，静态部分） ----------
TL_X0, TL_X1 = 20, 1060
def tx(t): return TL_X0 + (TL_X1 - TL_X0) * t / TOTAL
def draw_timeline(d, cur):
    y0 = Y_TL + 8
    # 阶段带
    ph = {}
    for sh in D['shots']: ph.setdefault(sh['phase'], [sh['t0'], sh['t1']]); ph[sh['phase']][1] = sh['t1']
    for p, (a, b) in ph.items():
        c = PH_COL[p]; on = (p == cur['phase'])
        d.rectangle((tx(a), y0, tx(b) - 1, y0 + 22), fill=c if on else tuple(int(v * 0.45) for v in c))
        d.text((tx(a) + 6, y0 + 1), PH_NAME[p], font=F(15), fill=(255, 255, 255) if on else (170, 170, 170))
    # 镜头条
    y1 = y0 + 28
    for sh in D['shots']:
        c = hexc(SETUP[sh['setup']]['color'])
        if sh['n'] != cur['n']: c = tuple(int(v * 0.55) for v in c)
        d.rectangle((tx(sh['t0']), y1, max(tx(sh['t0']) + 1, tx(sh['t1']) - 1), y1 + 30), fill=c)
    a, b = tx(cur['t0']), tx(cur['t1'])
    d.rectangle((a - 1, y1 - 3, b + 1, y1 + 33), outline=(255, 255, 255), width=2)
    # 放大条外框（内容由 ffmpeg 滚动叠加）
    y2 = y1 + 38
    d.rectangle((TL_X0 - 1, y2 - 1, TL_X1 + 1, y2 + 57), outline=(70, 75, 85), width=1)
    d.text((TL_X1 - 160, Y_TL - 2 + 140), "", font=F(12))

ZOOM_PX = 30.0   # 放大条：每秒 30 px
def make_zoom_strip(path):
    Wz = int(TOTAL * ZOOM_PX) + 1040
    im = Image.new('RGB', (Wz, 56), (34, 37, 44)); d = ImageDraw.Draw(im)
    off = 520
    for sh in D['shots']:
        a = off + sh['t0'] * ZOOM_PX; b = off + sh['t1'] * ZOOM_PX
        c = hexc(SETUP[sh['setup']]['color'])
        d.rectangle((a, 4, b - 2, 52), fill=c)
        lab = f"{sh['setup']}"; lab2 = f"#{sh['n']}"
        if b - a > 26: d.text((a + 4, 5), lab, font=F(20), fill=(15, 15, 15))
        if b - a > 34: d.text((a + 4, 31), lab2, font=F(14, False), fill=(30, 30, 30))
    for s in range(0, int(TOTAL) + 1, 5):
        x = off + s * ZOOM_PX; d.line((x, 52, x, 56), fill=(150, 150, 150))
    im.save(path)
    return off

# ---------- 俯视图标注 ----------
def draw_top(base, sh):
    an = A[str(sh['n'])]
    top = Image.open(os.path.join(RDIR, 'shot_%03d.png' % sh['n'])).convert('RGBA')
    layer = Image.new('RGBA', (W, H_TOP), BG + (255,)); layer.alpha_composite(top)
    d = ImageDraw.Draw(layer)
    placed = []
    phase_setups = {x['setup'] for x in D['shots'] if x['phase'] == sh['phase']}
    act = sh['setup']
    # 方位
    d.text((14, 12), "南 · 大门", font=F(17), fill=(200, 200, 200))
    d.text((W - 118, 12), "舞台 · 北 →", font=F(17), fill=(200, 200, 200))
    # 比例尺：用门宽 3.46 m 的投影估 5 m
    # 灯光编号
    for k, _ in LIGHT_ROWS:
        u, v, z = an['light:' + k]
        if 0 < u < W and 0 < v < H_TOP - 120:
            b = chip(d, u - 14, v - 12, k, (255, 236, 170), font=F(13), pad=(5, 1), r=5)
            placed.append(b)
    # 人物
    for key, text, col in (('chen', '陈桂林', (255, 70, 60)), ('leader', '尊者', (246, 195, 67))):
        u, v, z = an[key]
        b = chip(d, u - 26, v - 40, text, col, fg=(255, 255, 255) if key == 'chen' else (30, 30, 30), font=F(15), pad=(6, 1))
        placed.append(b)
    # 本阶段机位（暗）
    for k in sorted(phase_setups):
        if k == act: continue
        u, v, z = an['cam:' + k]
        col = hexc(SETUP[k]['color'])
        bb = None
        for dy in (-30, -52, 10, 32, -74):
            for dx in (-12, 14, -40):
                cand = d.textbbox((u + dx, v + dy), k, font=F(15))
                cand = (cand[0] - 5, cand[1] - 2, cand[2] + 5, cand[3] + 4)
                if not any(overlap(cand, p) for p in placed): bb = cand; break
            if bb: break
        bb = bb or (u - 12, v - 30, u + 14, v - 10)
        d.line((u, v, (bb[0] + bb[2]) / 2, bb[3] if bb[1] < v else bb[1]), fill=col + (160,), width=1)
        d.rounded_rectangle(bb, 5, fill=(40, 44, 52, 230), outline=col, width=2)
        d.text((bb[0] + 5, bb[1] + 1), k, font=F(15), fill=col)
        placed.append(bb)
    # 当前机位（亮）
    s = SETUP[act]; col = hexc(s['color'])
    u, v, z = an['cam:' + act]
    text = f"{act}  {s['name']}"
    f = F(21)
    tb = d.textbbox((0, 0), text, font=f); tw = tb[2] - tb[0] + 20; th = 36
    best = None
    for dy in (-70, 46, -110, 80):
        for dx in (-tw / 2, -tw + 30, -30):
            x0 = min(max(8, u + dx), W - tw - 8); y0 = min(max(40, v + dy), H_TOP - 160)
            cand = (x0, y0, x0 + tw, y0 + th)
            if not any(overlap(cand, p, 1) for p in placed[-40:]): best = cand; break
        if best: break
    best = best or (min(max(8, u - tw / 2), W - tw - 8), max(40, v - 70), 0, 0)
    x0, y0 = best[0], best[1]
    d.line((u, v, x0 + tw / 2, y0 + th if y0 < v else y0), fill=col + (255,), width=3)
    d.ellipse((u - 6, v - 6, u + 6, v + 6), outline=col + (255,), width=3)
    d.rounded_rectangle((x0, y0, x0 + tw, y0 + th), 8, fill=col + (255,))
    d.text((x0 + 10, y0 + 2 - tb[1] + 4), text, font=f, fill=(18, 18, 18))
    # 灯光图例（面板底部）
    ly = H_TOP - 104
    d.rectangle((0, ly - 8, W, H_TOP), fill=(30, 33, 40, 255))
    d.text((16, ly - 2), "灯光", font=F(16), fill=(255, 226, 150))
    for i, (k, name) in enumerate(LIGHT_ROWS):
        cx = 70 + (i % 3) * 335; cy = ly + (i // 3) * 31
        chip(d, cx, cy, k, (255, 236, 170), font=F(13), pad=(5, 1), r=5)
        d.text((cx + 34, cy - 2), name, font=F(17, False), fill=(225, 225, 225))
    base.paste(layer.convert('RGB'), (0, Y_TOP))

def draw_caption(d, sh):
    s = SETUP[sh['setup']]; col = hexc(s['color'])
    y = Y_CAP + 14
    d.text((24, y), f"#{sh['n']:03d}   {tc(sh['t0'])} – {tc(sh['t1'])}   ({sh['dur']:.1f} 秒)", font=F(20, False), fill=(200, 200, 200))
    pc = PH_COL[sh['phase']]
    chip(d, W - 150, y - 2, PH_NAME[sh['phase']], pc, fg=(255, 255, 255), font=F(18), pad=(10, 2))
    y += 40
    b = chip(d, 24, y, f" {s['id']} ", col, font=F(30), pad=(8, 0), r=8)
    d.text((b[2] + 14, y + 2), s['name'], font=F(30), fill=(255, 255, 255))
    y += 54
    h = sh['hfov']
    lens = f"水平视角约 {h:.0f}°（≈S35 {s35(h):.0f} mm）"
    d.text((24, y), f"机位：机高 {s['C'][2]:.1f} m · {s['rig']} · {s['move']}", font=F(21, False), fill=(230, 230, 230))
    y += 34
    d.text((24, y), f"镜头：{lens} · 位置可信度 {s['conf']}", font=F(21, False), fill=(230, 230, 230))
    y += 36
    note = s['note']
    # 自动换行
    f = F(19, False); line = ''; lines = []
    for ch in note:
        if d.textlength(line + ch, font=f) > W - 48: lines.append(line); line = ch
        else: line += ch
    lines.append(line)
    for ln in lines[:2]:
        d.text((24, y), ln, font=f, fill=(175, 182, 190)); y += 28

def panel(sh):
    im = Image.new('RGB', (W, H), BG); d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W, Y_TOP), fill=(16, 18, 22))
    d.text((24, 18), "《周处除三害》灵修堂 · 拍摄现场还原", font=F(34), fill=(255, 255, 255))
    draw_top(im, sh)
    d = ImageDraw.Draw(im)
    draw_timeline(d, sh)
    d.rectangle((0, Y_FILM, W, Y_FILM + H_FILM), fill=(0, 0, 0))
    draw_caption(d, sh)
    return im

if __name__ == '__main__':
    off = make_zoom_strip(os.path.join(OUT, 'zoom_strip.png'))
    ph = Image.new('RGB', (3, 36), (255, 255, 255)); ph.save(os.path.join(OUT, 'playhead.png'))
    ph2 = Image.new('RGB', (3, 60), (255, 255, 255)); ph2.save(os.path.join(OUT, 'playhead_zoom.png'))
    lst = []
    for sh in D['shots']:
        p = os.path.join(OUT, 'panel_%03d.png' % sh['n'])
        if ONLY is None or sh['n'] in ONLY:
            panel(sh).save(p)
        lst.append((p, sh['f1'] - sh['f0']))
    with open(os.path.join(OUT, 'panels.txt'), 'w') as fo:
        for p, n in lst: fo.write(f"file '{p}'\nduration {n / 24.0:.6f}\n")
        fo.write(f"file '{lst[-1][0]}'\n")
    json.dump(dict(zoom_px=ZOOM_PX, zoom_off=off, total=TOTAL, tl_x0=TL_X0, tl_x1=TL_X1, y_tl=Y_TL, y_film=Y_FILM, h_film=H_FILM, y_strip=Y_TL + 74, y_head=Y_TL + 33, y_headz=Y_TL + 72), open(os.path.join(OUT, 'layout.json'), 'w'))
    print('panels done', len(lst))
