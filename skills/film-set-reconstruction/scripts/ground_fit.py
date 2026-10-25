# ==== 《大事件》(2004) 开场长镜头项目里的实际代码，原样保留作参考 ====
# 里面的路径（/tmp/claude-0/...、/mnt/user-data/...）、坐标、车辆尺寸、帧号区间都是那部片子的，换片时逐项改。
# 约定：机位 R 为 世界→相机（OpenCV：x 右 y 下 z 前），C 为相机中心；画面 1280×554 时 CX=640 CY=277、HFOV=42°。
# 用"站着的人"同时求地面和比例：脚点在地面上，头顶在脚点正上方 H 处（H = 1.70 m）
# 未知量：up 方向（2）、地面偏移 g（1）、人高 H（SfM 单位，1）
import json, math, sys, numpy as np

class _R: pass
def least_squares(fun, x0, loss='soft_l1', f_scale=0.05, iters=60):
    x = np.array(x0, float); lam = 1e-2
    def cost(x):
        r = fun(x); z = (r / f_scale) ** 2
        return float(np.sum(2 * f_scale ** 2 * (np.sqrt(1 + z) - 1))), r
    c, r = cost(x)
    for it in range(iters):
        w = 1 / np.sqrt(np.sqrt(1 + (r / f_scale) ** 2))   # soft_l1 的 IRLS 权重
        J = np.zeros((len(r), len(x)))
        for k in range(len(x)):
            h = 1e-6 * max(1, abs(x[k])); xp = x.copy(); xp[k] += h; J[:, k] = (fun(xp) - r) / h
        Jw = J * w[:, None]; rw = r * w
        A = Jw.T @ Jw; b = Jw.T @ rw
        ok = False
        for _ in range(10):
            dx = -np.linalg.solve(A + lam * np.diag(np.diag(A) + 1e-9), b)
            c2, r2 = cost(x + dx)
            if c2 < c: x, c, r = x + dx, c2, r2; lam = max(lam / 3, 1e-7); ok = True; break
            lam *= 4
        if not ok or np.linalg.norm(dx) < 1e-9: break
    o = _R(); o.x = x; o.cost = c; return o
CX, CY = 640.0, 277.0; S = 1280 / 1920

def load_obs():
    D = {}
    for line in open('/tmp/claude-0/det/all.jsonl'):
        o = json.loads(line)
        if not (2376 <= o['f'] <= 5988): continue
        L = []
        for d in o['d']:
            if d['k'] != 'person' or d['s'] < 0.5 or not d.get('pose'): continue
            p = d['pose']; v = p['v']; q = p['p2']
            if min(v[27], v[28]) < 0.6 or v[0] < 0.6: continue
            x0, y0, x1, y1 = d['b']
            if y1 > 825 or y0 < 2 or (y1 - y0) < 70: continue
            # 腿要大致竖直（排除坐、蹲、弯腰）：髋在脚上方且身高/宽度比合理
            hip_y = (q[23][1] + q[24][1]) / 2; ank_y = (q[27][1] + q[28][1]) / 2
            if not (ank_y - hip_y > 0.35 * (y1 - y0)): continue
            fx = np.mean([q[k][0] for k in (27, 28, 29, 30, 31, 32)]); fy = max(np.mean([q[k][1] for k in (29, 30, 31, 32)]), ank_y)
            L.append((fx * S, fy * S, q[0][0] * S, y0 * S, (y1 - y0) * S))
        if L: D[o['f']] = L
    return D

def basis(u):
    a = np.array([1.0, 0, 0]) if abs(u[0]) < 0.9 else np.array([0, 1.0, 0])
    e1 = np.cross(u, a); e1 /= np.linalg.norm(e1); e2 = np.cross(u, e1)
    return e1, e2

def fit(model, f, OBS, verbose=True):
    cams = model["cams"]; rows = []
    for name, (C, R) in cams.items():
        fr = int(name[1:6])
        for ob in OBS.get(fr, []): rows.append((np.array(C), np.array(R), ob))
    if len(rows) < 15: return None
    Cs = np.array([r[0] for r in rows]); Rs = np.array([r[1] for r in rows]); ob = np.array([r[2] for r in rows])
    df = np.einsum('nji,nj->ni', Rs, np.c_[(ob[:, 0] - CX) / f, (ob[:, 1] - CY) / f, np.ones(len(ob))])
    u0 = -np.mean([np.array(v[1])[1] for v in cams.values()], 0); u0 /= np.linalg.norm(u0)
    e1, e2 = basis(u0)
    Call = np.array([v[0] for v in cams.values()])
    def unpack(x):
        u = u0 + x[0] * e1 + x[1] * e2; u /= np.linalg.norm(u); return u, x[2], math.exp(x[3])
    def res(x):
        u, g, H = unpack(x)
        den = df @ u; lam = (g - Cs @ u) / np.where(np.abs(den) < 1e-6, -1e-6, den)
        Xf = Cs + lam[:, None] * df; Xh = Xf + H * u
        pc = np.einsum('nij,nj->ni', Rs, Xh - Cs)
        z = np.maximum(pc[:, 2], 1e-6)
        pu = pc[:, 0] / z * f + CX; pv = pc[:, 1] / z * f + CY
        r = (pv - ob[:, 3]) / ob[:, 4]
        r = np.where(lam > 0, r, 3.0)
        return r
    # 初值：地面在相机下方 ~1.6 个"相机间距"单位
    spread = np.median(np.linalg.norm(Call - Call.mean(0), axis=1)) + 1e-6
    best = None
    for gk in (0.5, 1, 2, 4, 8):
        for hk in (0.5, 1, 2):
            g0 = np.median(Call @ u0) - gk * spread; H0 = hk * gk * spread
            x0 = [0, 0, g0, math.log(H0)]
            try:
                s = least_squares(res, x0, loss='soft_l1', f_scale=0.05)
            except Exception as ex:
                continue
            if best is None or s.cost < best.cost: best = s
    u, g, H = unpack(best.x)
    r = res(best.x)
    scale = 1.70 / H
    hc = (Call @ u - g) * scale
    out = {"up": u.tolist(), "g": float(g), "scale": float(scale), "n": len(rows), "med_abs_res": float(np.median(np.abs(r))),
           "inl": float(np.mean(np.abs(r) < 0.08)), "tilt_vs_cam": round(math.degrees(math.acos(min(1, u @ u0))), 1),
           "cam_h": [round(float(np.percentile(hc, q)), 2) for q in (5, 50, 95)]}
    if verbose: print(json.dumps(out))
    return out

if __name__ == "__main__":
    M = json.load(open(sys.argv[1])); hf = float(sys.argv[2]); f = 640 / math.tan(math.radians(hf) / 2)
    OBS = load_obs(); print("frames with obs", len(OBS), sum(len(v) for v in OBS.values()))
    AL = {}
    for k, m in M.items():
        if len(m["cams"]) < 20: continue
        names = sorted(m["cams"]); print("model", k, len(names), names[0], names[-1])
        AL[k] = fit(m, f, OBS)
    json.dump(AL, open(sys.argv[3], "w"))
