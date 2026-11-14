# ==== 《大事件》(2004) 开场长镜头项目里的实际代码，原样保留作参考 ====
# 里面的路径（/tmp/claude-0/...、/mnt/user-data/...）、坐标、车辆尺寸、帧号区间都是那部片子的，换片时逐项改。
# 约定：机位 R 为 世界→相机（OpenCV：x 右 y 下 z 前），C 为相机中心；画面 1280×554 时 CX=640 CY=277、HFOV=42°。
import sys, numpy as np, math
sys.path.insert(0, "/tmp/claude-0/full")
from compass import comp, VP, CAMS
def theta_series(f0, f1, guess, win=240, slope=False):
    """f0..f1 每 3 帧的偏航修正 θ（度）：罗盘值 a mod 90，θ 取 guess 附近的 (-a mod 90) 分支；稳健平滑"""
    pts = []
    for n in sorted(VP):
        f = int(n[1:6])
        if not (f0 - win <= f <= f1 + win) or n not in CAMS: continue
        c = comp(n)
        if not c: continue
        th = (-c[0]) % 90.0
        th = th + 90 * round((guess(f) - th) / 90)
        if abs(th - guess(f)) < 20: pts.append((f, th, c[1]))
    fr = np.arange(f0, f1 + 1, 3); P = np.array(pts) if pts else np.zeros((0, 3))
    out = []
    for f in fr:
        w = np.exp(-0.5 * ((P[:, 0] - f) / win) ** 2) * P[:, 2] if len(P) else np.array([])
        if len(P) == 0 or w.sum() < 1e-3: out.append(guess(f)); continue
        # 加权中位
        o = np.argsort(P[:, 1]); cw = np.cumsum(w[o]); out.append(float(P[o, 1][np.searchsorted(cw, cw[-1] / 2)]))
    return dict(zip(fr.tolist(), out)), pts
