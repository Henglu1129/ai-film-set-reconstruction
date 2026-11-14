# ==== 《大事件》(2004) 开场长镜头项目里的实际代码，原样保留作参考 ====
# 里面的路径（/tmp/claude-0/...、/mnt/user-data/...）、坐标、车辆尺寸、帧号区间都是那部片子的，换片时逐项改。
# 约定：机位 R 为 世界→相机（OpenCV：x 右 y 下 z 前），C 为相机中心；画面 1280×554 时 CX=640 CY=277、HFOV=42°。
import sys, numpy as np, math
sys.path.insert(0, "/tmp/claude-0/full")
from gfr import CAMS, yaw_of, pitch_of
from xf import Rz_cw
def names_in(model, f0, f1): return [n for n in sorted(CAMS) if CAMS[n][0] == model and f0 <= int(n[1:6]) <= f1]
def integrate(model, f0, f1, th_of, s_of, anchor_f, anchor_pos, maxstep=None):
    """沿时间累加 SfM 位移增量（每步按该时刻 θ 旋转、按 s 缩放），在 anchor_f 处等于 anchor_pos"""
    ns = names_in(model, f0, f1); P = {}; acc = np.zeros(3); prev = None
    for n in ns:
        f = int(n[1:6])
        if prev is not None:
            d = CAMS[n][1] - CAMS[prev][1]
            if maxstep is not None and np.linalg.norm(d) * s_of(f) > maxstep * (f - int(prev[1:6])) / 3: d = d * 0   # 跳变：不累加
            acc = acc + s_of(f) * (Rz_cw(th_of(f)) @ d)
        P[f] = acc.copy(); prev = n
    a = P[min(P, key=lambda k: abs(k - anchor_f))]
    return {f: p - a + np.asarray(anchor_pos) for f, p in P.items()}
