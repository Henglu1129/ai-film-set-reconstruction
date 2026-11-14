# ==== 《大事件》(2004) 开场长镜头项目里的实际代码，原样保留作参考 ====
# 里面的路径（/tmp/claude-0/...、/mnt/user-data/...）、坐标、车辆尺寸、帧号区间都是那部片子的，换片时逐项改。
# 约定：机位 R 为 世界→相机（OpenCV：x 右 y 下 z 前），C 为相机中心；画面 1280×554 时 CX=640 CY=277、HFOV=42°。
# 手工量取的车辆像素特征 → 解相机位姿 (x,y,z,yaw,pitch)
import sys, json, math, numpy as np
sys.path.insert(0, "/tmp/claude-0/pilot/sfm"); sys.path.insert(0, ".")
from ground_fit import least_squares
from wire import Rcam
F = 640 / math.tan(math.radians(21)); CX, CY = 640.0, 277.0
CARS = {"cop": (-1.97, -3.0, 4.3, 1.7, 1.45), "silver": (-0.85, -13.0, 4.4, 1.7, 1.42)}   # 车头朝南
def pts(car):
    """车身：保险杠到保险杠 z 0.25–0.95；车顶：中段 z=H；车轮触地点"""
    cx, cy, L, W, H = CARS[car]
    d = {}
    for nx, xx in (("W", cx - W / 2), ("E", cx + W / 2)):
        for ny, yy in (("F", cy - L / 2), ("R", cy + L / 2)):
            d[ny + nx + "b"] = np.array([xx, yy, 0.25]); d[ny + nx + "m"] = np.array([xx, yy, 0.95])
        xi = cx - W / 2 + 0.18 if nx == "W" else cx + W / 2 - 0.18
        d["roofF" + nx] = np.array([xi, cy - L * 0.08, H]); d["roofR" + nx] = np.array([xi, cy + L * 0.22, H])
        d["wF" + nx] = np.array([cx - W / 2 + 0.1 if nx == "W" else cx + W / 2 - 0.1, cy - L / 2 + 0.85, 0.0])
        d["wR" + nx] = np.array([cx - W / 2 + 0.1 if nx == "W" else cx + W / 2 - 0.1, cy + L / 2 - 0.85, 0.0])
    return d
def project(C, R, X):
    p = R @ (X - C); return np.array([p[0] / p[2] * F + CX, p[1] / p[2] * F + CY]), p[2]
def solve(obs, x0):
    """obs: list of (car, kind, value, weight)  kind: xmin/xmax/ymin/ymax 或 'u:FEb' / 'v:FEb' 某角点像素坐标"""
    def fun(q):
        C = q[:3]; R = Rcam(q[3], q[4]); r = []
        for car, kind, val, w in obs:
            P = pts(car); U = {}; Z = {}
            for k, X in P.items(): U[k], Z[k] = project(C, R, X)
            if min(Z.values()) < 0.3: r.append(50.0 * w); continue
            body = [k for k in P if not k.startswith("w")]; us = np.array([U[k][0] for k in body]); vs = np.array([U[k][1] for k in body])
            if kind == "xmin": e = us.min() - val
            elif kind == "xmax": e = us.max() - val
            elif kind == "ymin": e = vs.min() - val
            elif kind == "ymax": e = vs.max() - val
            else:
                a, k = kind.split(":"); e = U[k][0 if a == "u" else 1] - val
            r.append(e / 10.0 * w)
        return np.array(r)
    best = None
    for dx in (-1.5, 0, 1.5):
        for dy in (-1.5, 0, 1.5):
            for dyaw in (-10, 0, 10):
                q = list(x0); q[0] += dx; q[1] += dy; q[3] += dyaw
                o = least_squares(fun, q, f_scale=3.0, iters=80)
                if best is None or o.cost < best.cost: best = o
    r = fun(best.x) * 10
    return best.x, r
if __name__ == "__main__":
    J = json.load(open(sys.argv[1]))
    for key, item in J.items():
        q, r = solve([tuple(o) for o in item["obs"]], item["x0"])
        print(key, "C", np.round(q[:3], 2), "yaw", round(q[3], 1), "pitch", round(q[4], 1), "res px", np.round(r, 0))
