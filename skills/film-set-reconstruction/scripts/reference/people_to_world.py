# ==== 《大事件》(2004) 开场长镜头项目里的实际代码，原样保留作参考 ====
# 里面的路径（/tmp/claude-0/...、/mnt/user-data/...）、坐标、车辆尺寸、帧号区间都是那部片子的，换片时逐项改。
# 约定：机位 R 为 世界→相机（OpenCV：x 右 y 下 z 前），C 为相机中心；画面 1280×554 时 CX=640 CY=277、HFOV=42°。
import sys; sys.path.insert(0, '/tmp/claude-0/full/trk'); sys.path.insert(0, '/tmp/claude-0/full')
# 试点窗口内的人物：检测短轨迹 → 旧场景坐标 → 按身份合并 → 平滑 → 输出 bake 实体
import json, math, sys, collections, numpy as np
sys.path.insert(0, "/tmp/claude-0/pilot"); sys.path.insert(0, "/tmp/claude-0/pilot/s2"); sys.path.insert(0, "/tmp/claude-0/pilot/s3")
from pilot_labels import LAB
from full_labels import LAB as LAB2
LAB = dict(LAB); LAB.update(LAB2)
from to_old import V4, Wz, P, HFOV, nearest
import cam_full as cam2
_CC = {}
def camcv(name):
    f = int(name[1:6])
    if f not in _CC: _CC[f] = cam2.cam(f)
    return _CC[f]
I0, I1 = int(sys.argv[1]), int(sys.argv[2]); sys.path.insert(0, '/tmp/claude-0/full'); sys.path.insert(0, '/tmp/claude-0/full/trk')            # 采样序号范围（帧/3）
CX, CY = 640.0, 277.0; F = CX / math.tan(math.radians(HFOV / 2)); S = 1280 / 1920; DT = 0.125
T = json.load(open('/tmp/claude-0/full/trk/tracklets_A.json')) + json.load(open('/tmp/claude-0/pilot/tracklets.json')) + json.load(open('/tmp/claude-0/full/trk/tracklets_C.json'))
cams = V4["cams"]
def ray(name, u, v):
    R = camcv(name)[1]; d = R.T @ np.array([(u - CX) / F, (v - CY) / F, 1.0]); return d / np.linalg.norm(d)
def cpos(name): return np.array(camcv(name)[0])
BMAP = {"L": (11, 13, 15, 23, 25, 27), "R": (12, 14, 16, 24, 26, 28)}
def facing_from_pose(name, p):
    """MediaPipe 世界坐标 w3（相机朝向的局部坐标）→ 世界里的朝向（yaw，旧坐标 0=+Y 顺时针）"""
    V = p["v"]; w = np.array(p["w3"])
    if min(V[11], V[12], V[23], V[24]) < 0.6: return None
    R = camcv(name)[1]
    def tw(q): return R.T @ np.array([q[0], q[1], q[2]])   # MP 的 x 右 y 下 z 远离相机 ≈ 相机系
    rr = tw(w[24] - w[23]) + tw(w[12] - w[11]); rr[2] = 0
    if np.linalg.norm(rr) < 1e-4: return None
    rr /= np.linalg.norm(rr)
    # MediaPipe 左右：23=左髋、24=右髋；人的正面 = up × (左→右)？ 右手系：front = cross(up, right)… 这里 right = 24-23 指向人的右侧
    fr = np.cross([0, 0, 1.0], rr)          # 人的右侧 × ... 得到人的正前方
    return math.atan2(-fr[0], fr[1])
WX0, WX1 = -4.45, 7.6
ROOM = (1566, 2090)
def GZ(f): return 7.2 if ROOM[0] <= f <= ROOM[1] else 0.0
def fix_pt(C, X, t):
    """人不能在楼里、车里：沿视线（保持画面位置）滑到边界"""
    C = np.asarray(C, float); X = np.asarray(X, float); d = X - C
    if X[0] < WX0 and C[0] > WX0 and d[0] < 0: X = C + d * ((WX0 - C[0]) / d[0])
    if X[0] > WX1 and C[0] < WX1 and d[0] > 0: X = C + d * ((WX1 - C[0]) / d[0])
    boxes = [(-1.97, -3.0)] + ([(-0.85, -13.0)] if t > 231.5 else [])
    for (cx, cy) in boxes:
        x0, x1, y0, y1 = cx - 1.1, cx + 1.1, cy - 2.45, cy + 2.45
        if x0 < X[0] < x1 and y0 < X[1] < y1 and not (x0 < C[0] < x1 and y0 < C[1] < y1):
            lo, hi = 0.0, 1.0           # 二分：C + s·d 的最远可行点
            for _ in range(30):
                m = (lo + hi) / 2; P_ = C + d * m
                if x0 < P_[0] < x1 and y0 < P_[1] < y1: hi = m
                else: lo = m
            X = C + d * lo
    X[2] = 0.0 if abs(X[2]) < 0.6 else X[2]
    return X
rows_by = collections.defaultdict(list)
for t in T:
    lab = LAB.get(t["id"], "extra")
    if lab == "drop": continue
    for ob in t["obs"]:
        i = ob["i"]
        if not (I0 <= i <= I1): continue
        n = f"f{3 * i:05d}.jpg"
        if (3 * i) % 3: continue
        C = cpos(n); x0, y0, x1, y1 = [v * S for v in ob["b"]]
        p = ob.get("pose"); V = p["v"] if p else None; Q = [[a * S, b * S] for a, b in p["p2"]] if p else None
        ok = lambda *ids: V is not None and all(V[k] > 0.6 for k in ids)
        X = None; m = None
        if y1 < 548 and ok(27, 28) and (Q[27][1] + Q[28][1]) / 2 > (Q[23][1] + Q[24][1]) / 2 + 0.3 * (y1 - y0):
            fu = np.mean([Q[k][0] for k in (27, 28, 29, 30, 31, 32)]); fv = max(np.mean([Q[k][1] for k in (29, 30, 31, 32)]), (Q[27][1] + Q[28][1]) / 2)
            d = ray(n, fu, fv)
            gz = GZ(3 * i)
            if d[2] < -0.02 and -(C[2] - gz) / d[2] < 40: X = C - (C[2] - gz) / d[2] * d; m = "foot"
        if X is None and ok(11, 12, 23, 24):
            sh = (np.array(Q[11]) + np.array(Q[12])) / 2; hp = (np.array(Q[23]) + np.array(Q[24])) / 2; L = np.linalg.norm(sh - hp)
            if L > 8:
                mid = (sh + hp) / 2; d = ray(n, mid[0], mid[1])
                zc = F * 0.50 / L; fwd = camcv(n)[1][2]
                if y1 >= 545 and y1 - y0 > 150: zc = min(zc, F * 1.35 / (y1 - y0))      # 下半身被裁：至少头到膝都在画面里
                lam = zc / max(d @ fwd, 0.2); X = C + lam * d; m = "torso"
        if X is None and x1 - x0 > 10:
            d = ray(n, (x0 + x1) / 2, (y0 + y1) / 2); fwd = camcv(n)[1][2]
            zc = F * 0.55 / (x1 - x0); X = C + zc / max(d @ fwd, 0.2) * d; m = "box"
        if X is None: continue
        if lab in ("C3", "CF") and 1776 <= i <= 1815:      # 05:02–05:08 近景扭打：躯干/框估深不可靠，按 2.3 m 沿视线放
            dh = np.array([X[0] - C[0], X[1] - C[1], 0.0]); dh /= max(np.linalg.norm(dh), 1e-6); X = np.array([C[0], C[1], 0.0]) + dh * 2.3
        if ROOM[0] <= 3 * i <= ROOM[1] and C[0] < -4.4:     # 房间里：近景框太大，深度按肩宽 0.45 m 估，限 1–3.5 m
            rr_ = ray(n, (x0 + x1) / 2, (y0 + y1) / 2); rh_ = np.array([rr_[0], rr_[1], 0.0]); rh_ /= max(np.linalg.norm(rh_), 1e-6)
            dd_ = float(np.clip(F * 0.45 / max(x1 - x0, 1), 1.4, 3.5)); X = np.array([C[0] + rh_[0] * dd_, C[1] + rh_[1] * dd_, 7.2]); m = "torso"
        if ROOM[0] <= 3 * i <= ROOM[1] and C[0] < -4.4:
            bx0, bx1, by0, by1 = -9.25, -5.25, -26.15, -19.35; d_ = X - C; lo, hi = 0.0, 1.0
            inside = lambda P_: bx0 <= P_[0] <= bx1 and by0 <= P_[1] <= by1
            if not inside(X):
                if not inside(C + d_ * 0.05): X = np.array([min(max(X[0], bx0), bx1), min(max(X[1], by0), by1), X[2]])
                else:
                    for _ in range(30):
                        m_ = (lo + hi) / 2
                        if inside(C + d_ * m_): lo = m_
                        else: hi = m_
                    X = C + d_ * lo
        if lab not in ("CA", "CB") and not (ROOM[0] <= 3 * i <= ROOM[1] or 1290 <= 3 * i < 1566):
            X = fix_pt(C, X, 80.8 + i * 3 / 24)
            dh = np.array([X[0] - C[0], X[1] - C[1]]); dd = np.linalg.norm(dh)
            if dd < 1.4:
                rr = ray(n, (x0 + x1) / 2, (y0 + y1) / 2); rh = np.array([rr[0], rr[1]]); rh /= max(np.linalg.norm(rh), 1e-6)
                X = np.array([C[0] + rh[0] * 1.4, C[1] + rh[1] * 1.4, 0.0])
        yaw = facing_from_pose(n, p) if (p and p.get("w3")) else None
        dv = np.array([X[0] - C[0], X[1] - C[1]]); dist = float(np.linalg.norm(dv)); dv = dv / max(dist, 1e-6)
        rows_by[(lab, t["id"])].append({"i": i, "x": float(X[0]), "y": float(X[1]), "m": m, "yaw": yaw, "h": y1 - y0, "z": GZ(3 * i), "cx": float(C[0]), "cy": float(C[1]), "ux": float(dv[0]), "uy": float(dv[1]), "d": dist})
json.dump({f"{k[0]}|{k[1]}": v for k, v in rows_by.items()}, open(f"/tmp/claude-0/full/pp_raw_{I0}_{I1}.json", "w"))
c = collections.Counter();
for (lab, tid), v in rows_by.items(): c[lab] += len(v)
print(len(rows_by), "tracklets;", dict(c))
