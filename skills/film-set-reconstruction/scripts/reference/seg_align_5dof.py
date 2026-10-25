# ==== 《大事件》(2004) 开场长镜头项目里的实际代码，原样保留作参考 ====
# 里面的路径（/tmp/claude-0/...、/mnt/user-data/...）、坐标、车辆尺寸、帧号区间都是那部片子的，换片时逐项改。
# 约定：机位 R 为 世界→相机（OpenCV：x 右 y 下 z 前），C 为相机中心；画面 1280×554 时 CX=640 CY=277、HFOV=42°。
# 一段 globF 机位 → 旧坐标的 5 自由度相似变换（θ, tx, ty, tz, log s），按已知车辆检测框拟合
import json, numpy as np, math, sys
sys.path.insert(0, "/tmp/claude-0/full"); sys.path.insert(0, "/tmp/claude-0/pilot/s2"); sys.path.insert(0, "/tmp/claude-0/pilot/sfm")
from gfr import CAMS, yaw_of, pitch_of
from xf import Rz_cw
from carpose import corners
from ground_fit import least_squares
F = 640 / math.tan(math.radians(21)); CX, CY = 640.0, 277.0
DET = {}
for l in open("/tmp/claude-0/det/all.jsonl"):
    r = json.loads(l); DET[r["f"]] = [[v * 1280 / 1920 for v in d["b"]] for d in r["d"] if d["k"] in ("car", "truck") and d["s"] > 0.5]
def apply(x, C, R, piv):
    th, tx, ty, tz, ls = x
    return math.exp(ls) * (Rz_cw(th) @ (C - piv)) + np.array([tx, ty, tz]), R @ Rz_cw(th).T
def proj(C, R, X):
    pc = (R @ (X - C).T).T; z = pc[:, 2]; return np.c_[pc[:, 0] / np.maximum(z, 1e-3) * F + CX, pc[:, 1] / np.maximum(z, 1e-3) * F + CY], z
def boxres(C, R, X, b):
    uv, z = proj(C, R, X)
    if np.any(z < 0.4): return [2.0] * 4
    sc = max(b[2] - b[0], 20); pb = [uv[:, 0].min(), uv[:, 1].min(), uv[:, 0].max(), uv[:4, 1].max()]
    return [(pb[0] - b[0]) / sc if b[0] > 3 else 0, (pb[2] - b[2]) / sc if b[2] < 1277 else 0, (pb[1] - b[1]) / sc * 0.5 if b[1] > 3 else 0, (pb[3] - b[3]) / sc if b[3] < 548 else 0]
def solve(frames, car, x0, piv, assoc_x=None, prior=None, iters=60):
    Pc, psi, L, W, H = car; X = corners(Pc, psi, L, W, (0.12, H))
    # 关联：用初值把预测框和检测框按 IoU 配对，固定下来
    xa = assoc_x if assoc_x is not None else x0; obs = []
    for f in frames:
        n = f"f{f:05d}.jpg"
        if n not in CAMS or f not in DET: continue
        C, R = apply(xa, CAMS[n][1], CAMS[n][2], piv); uv, z = proj(C, R, X)
        if np.any(z < 0.4): continue
        pb = [uv[:, 0].min(), uv[:, 1].min(), uv[:, 0].max(), uv[:4, 1].max()]
        def iou(a, b):
            x0_, y0_, x1_, y1_ = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3]); i = max(0, x1_ - x0_) * max(0, y1_ - y0_)
            return i / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i + 1e-6)
        cand = sorted(DET[f], key=lambda b: -iou(pb, b))
        if cand and iou(pb, cand[0]) > 0.15: obs.append((n, cand[0]))
    def fun(x):
        r = []
        for n, b in obs:
            C, R = apply(x, CAMS[n][1], CAMS[n][2], piv); r += boxres(C, R, X, b)
        if prior:
            for k, (v, sg) in prior.items(): r.append((x[k] - v) / sg)
        return np.array(r)
    o = least_squares(fun, list(x0), f_scale=0.1, iters=iters); r = fun(o.x)
    return o.x, float(np.median(np.abs(r[r != 0]))) if np.any(r != 0) else 9, len(obs)
def grid_init(frames, car, ref, ys, xs, zs, yaws, ss):
    """粗搜：参考帧 ref 的旧坐标位置/朝向 + 比例；按检测框（最近中心）误差打分"""
    Pc, psi, L, W, H = car; X = corners(Pc, psi, L, W, (0.12, H)); n0 = f"f{ref:05d}.jpg"; piv = CAMS[n0][1]; best = []
    for s in ss:
        for yd in yaws:
            th = yd - yaw_of(CAMS[n0][2])
            for x_ in xs:
                for y_ in ys:
                    for z_ in zs:
                        x = [th, x_, y_, z_, math.log(s)]; e = []
                        for f in frames:
                            n = f"f{f:05d}.jpg"
                            if n not in CAMS or f not in DET or not DET[f]: continue
                            C, R = apply(x, CAMS[n][1], CAMS[n][2], piv); uv, z = proj(C, R, X)
                            if np.any(z < 0.4): e.append(3); continue
                            pb = [uv[:, 0].min(), uv[:, 1].min(), uv[:, 0].max(), uv[:4, 1].max()]
                            e.append(min(min(3, (abs(pb[0] - b[0]) + abs(pb[2] - b[2]) + abs(pb[1] - b[1])) / max(b[2] - b[0], 30) / 3) for b in DET[f]))
                        if e: best.append((float(np.median(e)), x))
    best.sort(key=lambda a: a[0]); return best, piv
