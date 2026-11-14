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


# ---------- English localisation ----------
FB = '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'
FR = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
def F(sz, bold=True): return ImageFont.truetype(FB if bold else FR, sz, index=2)
EN_SETUP = {
 'A': ("Low reverse from stage", "On stage among the seated followers, at seated eye level, looking at the door. Establishes Chen's entrance."),
 'B': ("Long lens from stage", "West side of the stage. The long lens compresses the whole crowd and pins Chen in the doorway."),
 'C': ("Low angle at stage edge", "On the floor just below the stage, behind the followers: a low angle on the standoff."),
 'E': ("In crowd, zoom toward door", "In the middle of the crowd on a zoom: wide end for Chen and the door, long end for his close-ups. Shot #53 zooms in about 2x."),
 'U': ("In crowd, long lens to stage", "Back-to-back with E, long lens on the leader, stage followers, portrait and guitarist. Likely an A/B pair rolling with E."),
 'V': ("Low, beside Chen, to stage", "Near Chen, below the heads of the seated followers, facing the leader on the steps (Chen's eyeline)."),
 'B2': ("Over Chen's shoulder", "West of the door, over Chen's right shoulder toward the stage."),
 'M': ("Handheld at floor level", "Right on the floor: Chen's legs in the foreground, a follower crawling."),
 'F': ("Wide diagonal from SW corner", "SW corner of the hall, diagonal across the whole crowd; Chen aims at the leader, frame right."),
 'W': ("Profile of the leader", "East side of the stage: the leader in profile, before and after he is shot."),
 'G2': ("Follow shot up the stairs", "Stairwell outside the hall (off set), following Chen up the stairs."),
 'G': ("Long lens from the corridor", "From the corridor outside, through the doorway under the 'Auditorium' sign."),
 'H': ("High angle from back of stage", "High at the back of the stage, over the crowd to the door. Followers rush the door during the countdown."),
 'J': ("Handheld close-up at door", "The countdown, 'ten, nine, eight...': handheld close on Chen's face, door behind him."),
 'K': ("Fanny-pack inserts", "Handheld inserts: fanny pack, reloading, drawing the gun."),
 'I': ("At the door, behind Chen", "Behind Chen, just inside the door during the countdown; followers run past on both sides toward camera."),
 'I2': ("Handheld behind Chen", "Handheld, following behind Chen toward the stage."),
 'O': ("Stage edge, toward door", "Stage edge, slightly low: drapes, AC unit and door behind, Chen full figure."),
 'X': ("Handheld up-angle from floor", "Handheld at floor level looking up (victim's POV), ceiling lights and drapes behind, with whip pans."),
 'N': ("Symmetric master wide", "Center line just inside the door, at seated eye level, perfectly symmetric on the stage: the master shot of the execution."),
 'P': ("Ultra-wide at cushion level", "Floor level by the stage, ultra-wide lens skimming the cushions, looking toward the door."),
 'Q1': ("East wall, toward windows", "Against the east wall facing west: sheer-curtained windows as backlight while Chen moves across frame."),
 'Q2': ("Over-shoulder, toward windows", "Over Chen's back, facing the west windows."),
 'S': ("On stage, toward door (finale)", "On stage looking down: Chen on the stage, bodies across the floor."),
 'T': ("Top-down over stage", "Straight down: the leader's body, and the final shot of the guitarist beside him."),
}
EN_RIG = {'低三脚架': 'Low tripod', '三脚架': 'Tripod', '手持': 'Handheld', '手持/斯坦尼康': 'Handheld/Steadicam', '高脚架': 'High stand', '顶拍架': 'Overhead rig'}
EN_MOVE = {'固定': 'Locked-off', '固定·#53变焦推': 'Locked-off, zoom-in on #53', '手持': 'Handheld', '跟拍': 'Follow', '手持·甩': 'Handheld, whip pans'}
EN_CONF = {'高': 'High', '中': 'Medium', '低': 'Low'}
for _k, _s in SETUP.items():
    _s['name'], _s['note'] = EN_SETUP[_k]
    _s['rig'] = EN_RIG[_s['rig']]; _s['move'] = EN_MOVE[_s['move']]; _s['conf'] = EN_CONF[_s['conf']]
PH_NAME = {1: 'Standoff', 2: 'Exodus & countdown', 3: 'Execution', 4: 'Finale on stage'}
LIGHT_ROWS = [("L1", "West windows, daylight thru sheers"), ("L2", "East windows, daylight thru sheers"), ("L3", "Ceiling fluorescent panels"),
              ("L4", "Globe wall sconces"), ("L5", "Portrait backlight halo"), ("L6", "Glowing stone sculptures"),
              ("L7", "Corridor light (inferred)"), ("L8", "Top light above drapes (inferred)"), ("L9", "Black drape in door (neg. fill)")]
def wrap_words(d, text, f, w):
    out = []; cur = ''
    for word in text.split(' '):
        t = (cur + ' ' + word).strip()
        if d.textlength(t, font=f) > w and cur: out.append(cur); cur = word
        else: cur = t
    if cur: out.append(cur)
    return out
def fit_font(d, text, w, start, bold=True, minsz=14):
    sz = start
    while sz > minsz and d.textlength(text, font=F(sz, bold)) > w: sz -= 1
    return F(sz, bold)

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
        d.text((tx(a) + 6, y0 + 1), PH_NAME[p], font=fit_font(d, PH_NAME[p], tx(b) - tx(a) - 10, 15), fill=(255, 255, 255) if on else (170, 170, 170))
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
    d.text((14, 12), "\u2190 South: main door", font=F(17), fill=(200, 200, 200))
    d.text((W - 150, 12), "North: stage \u2192", font=F(17), fill=(200, 200, 200))
    # 比例尺：用门宽 3.46 m 的投影估 5 m
    # 灯光编号
    for k, _ in LIGHT_ROWS:
        u, v, z = an['light:' + k]
        if 0 < u < W and 0 < v < H_TOP - 120:
            b = chip(d, u - 14, v - 12, k, (255, 236, 170), font=F(13), pad=(5, 1), r=5)
            placed.append(b)
    # 人物
    for key, text, col in (('chen', 'Chen Kui-lin', (255, 70, 60)), ('leader', 'Cult leader', (246, 195, 67))):
        u, v, z = an[key]
        b = chip(d, u - 40, v - 40, text, col, fg=(255, 255, 255) if key == 'chen' else (30, 30, 30), font=F(15), pad=(6, 1))
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
    d.text((14, ly - 2), "Lights", font=F(16), fill=(255, 226, 150))
    for i, (k, name) in enumerate(LIGHT_ROWS):
        cx = 72 + (i % 3) * 336; cy = ly + (i // 3) * 31
        chip(d, cx, cy, k, (255, 236, 170), font=F(13), pad=(5, 1), r=5)
        d.text((cx + 34, cy - 2), name, font=fit_font(d, name, 296, 17, False), fill=(225, 225, 225))
    base.paste(layer.convert('RGB'), (0, Y_TOP))

def draw_caption(d, sh):
    s = SETUP[sh['setup']]; col = hexc(s['color'])
    y = Y_CAP + 14
    d.text((24, y), f"#{sh['n']:03d}   {tc(sh['t0'])} – {tc(sh['t1'])}   ({sh['dur']:.1f} s)", font=F(20, False), fill=(200, 200, 200))
    pc = PH_COL[sh['phase']]
    _f = F(18); _tw = d.textlength(PH_NAME[sh['phase']], font=_f)
    chip(d, W - 34 - _tw, y - 2, PH_NAME[sh['phase']], pc, fg=(255, 255, 255), font=_f, pad=(10, 2))
    y += 40
    b = chip(d, 24, y, f" {s['id']} ", col, font=F(30), pad=(8, 0), r=8)
    d.text((b[2] + 14, y + 2), s['name'], font=fit_font(d, s['name'], W - b[2] - 40, 30), fill=(255, 255, 255))
    y += 54
    h = sh['hfov']
    lens = f"~{h:.0f}\u00b0 horizontal FOV (\u2248{s35(h):.0f} mm on Super 35)"
    t1 = f"Camera: height {s['C'][2]:.1f} m  |  {s['rig']}" + ("" if s['move'] == s['rig'] else f"  |  {s['move']}")
    d.text((24, y), t1, font=fit_font(d, t1, W - 48, 21, False), fill=(230, 230, 230))
    y += 34
    t2 = f"Lens: {lens}  |  Confidence: {s['conf']}"
    d.text((24, y), t2, font=fit_font(d, t2, W - 48, 21, False), fill=(230, 230, 230))
    y += 36
    note = s['note']
    # 自动换行
    f = F(19, False); lines = wrap_words(d, note, f, W - 48)
    for ln in lines[:2]:
        d.text((24, y), ln, font=f, fill=(175, 182, 190)); y += 28

def panel(sh):
    im = Image.new('RGB', (W, H), BG); d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W, Y_TOP), fill=(16, 18, 22))
    _t = "The Pig, the Snake and the Pigeon: Cult Hall Set Reconstruction"
    d.text((24, 20), _t, font=fit_font(d, _t, W - 48, 34), fill=(255, 255, 255))
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
