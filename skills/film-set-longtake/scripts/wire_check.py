# ==== 《大事件》(2004) 开场长镜头项目里的实际代码，原样保留作参考 ====
# 里面的路径（/tmp/claude-0/...、/mnt/user-data/...）、坐标、车辆尺寸、帧号区间都是那部片子的，换片时逐项改。
# 约定：机位 R 为 世界→相机（OpenCV：x 右 y 下 z 前），C 为相机中心；画面 1280×554 时 CX=640 CY=277、HFOV=42°。
# 把旧坐标世界里的关键物体线框投影到原片帧上（不用 Blender 的快速对位检查）
import math, numpy as np
from PIL import Image, ImageDraw
CX, CY = 640.0, 277.0
def Rcam(yaw, pitch, roll=0.0):
    y, p = math.radians(yaw), math.radians(pitch)
    fw = np.array([math.sin(y) * math.cos(p), math.cos(y) * math.cos(p), math.sin(p)])
    rt = np.array([math.cos(y), -math.sin(y), 0.0]); dn = np.cross(fw, rt)
    R = np.array([rt, dn, fw])
    if roll:
        c, s = math.cos(math.radians(roll)), math.sin(math.radians(roll)); Rz = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]]); R = Rz @ R
    return R
def box(x0, x1, y0, y1, z0, z1):
    P = [(x, y, z) for z in (z0, z1) for (x, y) in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
    E = [(0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4), (0, 4), (1, 5), (2, 6), (3, 7)]
    return np.array(P, float), E
def car(cx, cy, L=4.4, W=1.7, H=1.45):
    return box(cx - W / 2, cx + W / 2, cy - L / 2, cy + L / 2, 0.1, H)
def scene(eastX=4.6):
    S = []
    S.append(("cop", (40, 90, 255)) + car(-1.97, -3.0))
    S.append(("silver", (230, 230, 230)) + car(-0.85, -13.0))
    for k, (a, b, c, d) in enumerate([(-6.4, -4.75, -17.4, -14.2), (-3.4, -2.6, -16.2, -13.6)]):
        S.append((f"drum{k}", (60, 60, 255)) + box(a, b, c, d, 0.15, 1.95))
    S.append(("suv", (0, 255, 120)) + box(4.3 - 0.88, 4.3 + 0.88, -3.6 - 2.1, -3.6 + 2.1, 0.2, 1.8))
    S.append(("roadworks", (255, 120, 0)) + box(3.0, 6.0, -26, -14, 0, 1.05))
    S.append(("sign24", (0, 255, 255)) + box(-4.2, -3.6, -4.64, -4.56, 0.3, 1.8))
    for x in (-4.6, eastX):
        for y0 in range(-40, 30, 10):
            S.append((f"fac{x}", (255, 255, 0)) + box(x, x, y0, y0 + 10, 0, 3.1))
    S.append(("kerbW", (0, 255, 0)) + box(-3.0, -3.0, -40, 30, 0.15, 0.15))
    return S
def draw(img, C, R, F=CX / math.tan(math.radians(21)), S=None, label=""):
    im = img.convert("RGB").copy(); d = ImageDraw.Draw(im); C = np.array(C, float)
    for name, col, P, E in (S or scene()):
        pc = (R @ (P - C).T).T
        for a, b in E:
            pa, pb = pc[a], pc[b]
            if pa[2] < 0.2 and pb[2] < 0.2: continue
            if pa[2] < 0.2: t = (0.2 - pa[2]) / (pb[2] - pa[2]); pa = pa + t * (pb - pa)
            if pb[2] < 0.2: t = (0.2 - pb[2]) / (pa[2] - pb[2]); pb = pb + t * (pa - pb)
            ua = (pa[0] / pa[2] * F + CX, pa[1] / pa[2] * F + CY); ub = (pb[0] / pb[2] * F + CX, pb[1] / pb[2] * F + CY)
            if max(abs(ua[0]), abs(ub[0]), abs(ua[1]), abs(ub[1])) > 1e5: continue
            d.line([ua, ub], fill=col, width=2)
    d.text((8, 8), label, fill=(255, 255, 0))
    return im
