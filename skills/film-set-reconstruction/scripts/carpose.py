# ==== 《大事件》(2004) 开场长镜头项目里的实际代码，原样保留作参考 ====
# 里面的路径（/tmp/claude-0/...、/mnt/user-data/...）、坐标、车辆尺寸、帧号区间都是那部片子的，换片时逐项改。
# 约定：机位 R 为 世界→相机（OpenCV：x 右 y 下 z 前），C 为相机中心；画面 1280×554 时 CX=640 CY=277、HFOV=42°。
# 用已知机位拟合静止车辆的地面位姿（中心 P、朝向 ψ），车身尺寸已知
# 约束：车身底面矩形四角（离地 0.15 m）的投影 → 横向范围对上检测框 x0/x1、最下沿对上 y1（框被画面切掉的边不用）
import json, math, numpy as np, sys
sys.path.insert(0, "/tmp/claude-0/pilot/sfm")
from ground_fit import least_squares
CX, CY = 640.0, 277.0
def load(camfile):
    CAM = json.load(open(camfile)); F = CX / math.tan(math.radians(CAM["hfov"] / 2)); return CAM["cams"], F
def corners(P, psi, L, W, hz=(0.15, 1.35)):
    c, s = math.cos(psi), math.sin(psi); f = np.array([c, s]); r = np.array([-s, c])
    out = []
    for z in hz:
        for a in (L / 2, -L / 2):
            for b in (W / 2, -W / 2):
                q = np.array(P) + a * f + b * r; out.append([q[0], q[1], z])
    return np.array(out)
def proj(cam, F, X):
    C = np.array(cam["C"]); R = np.array(cam["R"]); pc = (R @ (X - C).T).T
    z = pc[:, 2]; return np.c_[pc[:, 0] / np.maximum(z, 1e-3) * F + CX, pc[:, 1] / np.maximum(z, 1e-3) * F + CY], z
def fit(obs, cams, F, L, W, H=1.4, init=None, verbose=False):
    """obs: [(name, box1280)]；返回 P, psi, 残差"""
    obs = [(n, b) for n, b in obs if n in cams]
    if len(obs) < 3: return None
    def res(x):
        P, psi = x[:2], x[2]; r = []
        X = corners(P, psi, L, W, (0.12, H))
        for n, b in obs:
            uv, z = proj(cams[n], F, X)
            if np.any(z < 0.3): r += [3.0, 3.0, 3.0, 3.0]; continue
            sc = max(b[2] - b[0], 30)
            r.append((uv[:, 0].min() - b[0]) / sc if b[0] > 3 else 0.0)
            r.append((uv[:, 0].max() - b[2]) / sc if b[2] < 1277 else 0.0)
            r.append((uv[:4, 1].max() - b[3]) / sc if b[3] < 550 else 0.0)
            r.append((uv[4:, 1].min() - b[1]) / sc * 0.5 if b[1] > 3 else 0.0)
        return np.array(r)
    best = None
    P0 = init if init is not None else None
    if P0 is None:
        # 初值：各帧框底中点射线与地面交点的中位数
        G = []
        for n, b in obs:
            C = np.array(cams[n]["C"]); R = np.array(cams[n]["R"])
            d = R.T @ np.array([((b[0] + b[2]) / 2 - CX) / F, (min(b[3], 550) - CY) / F, 1.0])
            if d[2] < -0.01: G.append((C + (-C[2] / d[2]) * d)[:2])
        P0 = np.median(G, 0)
    for psi0 in np.radians(np.arange(0, 180, 15)):
        o = least_squares(res, [P0[0], P0[1], psi0], f_scale=0.1)
        if best is None or o.cost < best.cost: best = o
    r = res(best.x)
    return {"P": best.x[:2].tolist(), "psi_deg": float(math.degrees(best.x[2]) % 180), "med": float(np.median(np.abs(r[r != 0]))) if np.any(r != 0) else None, "n": len(obs)}
