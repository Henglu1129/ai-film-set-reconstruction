# ==== 《大事件》(2004) 开场长镜头项目里的实际代码，原样保留作参考 ====
# 里面的路径（/tmp/claude-0/...、/mnt/user-data/...）、坐标、车辆尺寸、帧号区间都是那部片子的，换片时逐项改。
# 约定：机位 R 为 世界→相机（OpenCV：x 右 y 下 z 前），C 为相机中心；画面 1280×554 时 CX=640 CY=277、HFOV=42°。
# 组装试点窗口的 bake 片段（旧场景坐标）：逐采样机位、吊臂底座、观察机位、车、人物、剧组、场景道具
import json, math, sys, numpy as np
sys.path.insert(0, "/tmp/claude-0/pilot/s2"); sys.path.insert(0, "/tmp/claude-0/pilot/s3")
from to_old import HFOV
sys.path.insert(0, '/tmp/claude-0/full'); import cam_full as cam2
I0, I1 = int(sys.argv[1]), int(sys.argv[2])
fr_cam = {}
Cs, Ms, Fs = [], [], []
for i in range(I0, I1 + 1):
    C, R = cam2.cam(3 * i); M = cam2.M_from_cv(R); f = R[2]
    Cs.append(np.array(C)); Ms.append(M); Fs.append(f)
Cs = np.array(Cs); Fs = np.array(Fs)
def smooth(a, sig):
    out = np.zeros_like(a); n = len(a)
    for k in range(n):
        lo, hi = max(0, k - 3 * sig), min(n, k + 3 * sig + 1); w = np.exp(-0.5 * ((np.arange(lo, hi) - k) / sig) ** 2); out[k] = (a[lo:hi] * w[:, None]).sum(0) / w.sum()
    return out
fh = Fs.copy(); fh[:, 2] = 0; fh /= np.linalg.norm(fh, axis=1)[:, None]; fh_s = smooth(fh, 8); fh_s /= np.linalg.norm(fh_s, axis=1)[:, None]
right = np.c_[fh_s[:, 1], -fh_s[:, 0], np.zeros(len(fh_s))]
up = np.array([0, 0, 1.0])
near_o = Cs - fh_s * 2.4 + up * 1.15 + right * 0.7
near_t = Cs + fh_s * 6.0 - up * 0.7
# 观察机位不能进楼、不能埋进车里：夹在街道范围内，落在车顶范围时抬高
near_o[:, 0] = np.clip(near_o[:, 0], -4.3, 7.5)
for (cx, cy, L_, W_) in [(-1.97, -3.0, 4.3, 1.7), (-0.85, -13.0, 4.4, 1.7), (4.3, -2.0, 4.2, 1.8)]:
    m = (np.abs(near_o[:, 0] - cx) < W_ / 2 + 0.4) & (np.abs(near_o[:, 1] - cy) < L_ / 2 + 0.4)
    near_o[m, 2] = np.maximum(near_o[m, 2], 2.4)
near_o[:, 2] = np.maximum(near_o[:, 2], 1.5)
near_o = smooth(near_o, 8); near_t = smooth(near_t, 8)
base = np.c_[np.full(len(Cs), 2.2), Cs[:, 1] + 1.5]; base = smooth(base, 16)
frames = {}
for k, i in enumerate(range(I0, I1 + 1)):
    C, M = Cs[k], Ms[k]; f = Fs[k]
    yaw = math.degrees(math.atan2(f[0], f[1])); pitch = math.degrees(math.asin(max(-1, min(1, f[2]))))
    frames[i] = {"cam": [round(float(C[0]), 3), round(float(C[1]), 3), round(float(C[2]), 3), round(yaw, 3), round(pitch, 3), HFOV],
                 "camM": [round(float(v), 6) for v in M.reshape(-1)], "base": [round(float(base[k][0]), 3), round(float(base[k][1]), 3)],
                 "near": [round(float(v), 3) for v in list(near_o[k]) + list(near_t[k])]}
# 车：便衣车静止；银车按拟合轨迹倒车入位后静止
SIL = [(218.0, 0.25, -25.0), (221.3, 0.30, -25.0), (225.0, -0.10, -18.6), (228.8, -0.40, -14.9), (231.5, -0.85, -13.0)]
def silver_at(t):
    if t < 217.0: return None
    if t <= SIL[0][0]: return [SIL[0][1], SIL[0][2], 180.0]
    for a, b in zip(SIL, SIL[1:]):
        if a[0] <= t <= b[0]:
            u = (t - a[0]) / (b[0] - a[0]); u = u * u * (3 - 2 * u)
            return [round(a[1] + (b[1] - a[1]) * u, 3), round(a[2] + (b[2] - a[2]) * u, 3), 180.0]
    return [SIL[-1][1], SIL[-1][2], 180.0]
for k, i in enumerate(range(I0, I1 + 1)):
    t = 80.8 + i * 3 / 24
    van = None
    if t >= 434.0:
        u = min(1.0, (t - 434.0) / 4.0); u = u * u * (3 - 2 * u); van = [round(14.0 + (0.2 - 14.0) * u, 3), -42.3, 270.0]
    grey = [0.3, 7.0, 180.0] if t >= 386.0 else None; teal = [2.4, 11.5, 185.0] if t >= 386.0 else None
    frames[i]["cars"] = [[-1.97, -3.0, 180.0], silver_at(t), van, grey, teal]
    frames[i]["flash"] = []
# 人物
ents = json.load(open(f"/tmp/claude-0/full/ents_full_{I0}_{I1}.json"))
for e in ents:
    if e["cat"] == "RD": e["tpl"] = "robber"
    if e["cat"] in ("RY", "RG"): e["tpl"] = "extra" if e["cat"] == "RG" else "robber"
    LOOK = {"Y": ("robber", None), "RD": ("youth", None), "RB": ("extra", [0.45, 0.45, 0.5]), "RY": ("plainclothes", [1.0, 0.92, 0.72]), "RG": ("extra", [0.8, 0.8, 0.78]),
            "RK": ("youth", [0.5, 0.5, 0.55]), "RR": ("extra", [1.0, 0.42, 0.38]), "R5": ("robber", [0.75, 0.8, 0.7]), "CH": ("plainclothes", [0.85, 0.72, 0.55]),
            "CF": ("plainclothes", [0.8, 0.82, 0.85]), "CW": ("woman", [0.5, 0.5, 0.55])}
    if e["cat"] in LOOK: e["tpl"], e["tint"] = LOOK[e["cat"]]
    if e.get("tpl_force"): e["tpl"], e["tint"] = e["tpl_force"]
    if e["cat"] in ("robber", "cop") and not e.get("tint"):
        k_ = int(e["id"][2:5]); e["tpl"] = ("youth", "extra", "plainclothes")[k_ % 3]
        e["tint"] = [[0.6, 0.6, 0.62], [0.75, 0.7, 0.62], [0.55, 0.6, 0.7]][(k_ // 3) % 3]
# 剧组：在机位身后（视线反方向）
crew = []
for name, (back, side, lab) in {"op": (1.7, 0.8, "吊臂操作员"), "focus": (1.2, -0.9, "跟焦员"), "grip": (2.5, 0.2, "推轨员"), "dir": (3.8, -0.6, "导演 / 监视器")}.items():
    rows = []
    for k, i in enumerate(range(I0, I1 + 1)):
        p = Cs[k] - fh_s[k] * back + right[k] * side
        t_ = 80.8 + i * 3 / 24
        for (cx, cy, L_, W_) in [(-1.97, -3.0, 4.4, 1.8), (4.3, -2.0, 4.6, 1.9)] + ([(silver_at(t_)[0], silver_at(t_)[1], 4.6, 1.8)] if silver_at(t_) else []):
            if abs(p[0] - cx) < W_ / 2 + 0.45 and abs(p[1] - cy) < L_ / 2 + 0.45:
                p = p.copy(); p[0] = cx + W_ / 2 + 0.6 + 0.5 * abs(side)        # 推到车的东侧（街心一侧）
        p = p.copy(); p[0] = min(max(p[0], -4.35), 7.5)
        rows.append([i, round(float(p[0]), 3), round(float(p[1]), 3), 0.0, round(math.atan2(-fh_s[k][0], fh_s[k][1]), 4), "stand", 0.0, None])
    xy = smooth(np.array([[r[1], r[2]] for r in rows]), 10)
    for r, q in zip(rows, xy): r[1], r[2] = round(float(q[0]), 3), round(float(q[1]), 3)
    crew.append({"id": "CREW_" + name, "cat": "crew", "src": ["layout"], "tpl": "crew", "role": "crew", "label": lab, "prop": None, "main": False, "s": rows, "aim": []})
world_patch = {"barrels": [{"x": [-6.4, -4.75], "y": [-17.4, -16.2]}, {"x": [-4.0, -3.4], "y": [-17.6, -16.6], "stack": 2}, {"x": [-4.6, -4.0], "y": [-16.0, -15.2], "stack": 1}, {"x": [1.8, 4.2], "y": [-43.9, -43.0]}],
               "roadworks": {"x": [3.0, 5.6], "y": [-26.0, -17.5]},
               "recess": {"x": [-7.5, -4.6], "y": [-17.6, -12.6], "z": 3.4},
               "street": {"x": [-4.6, 7.8], "y": [-64, 50], "road": [-3, 6.0]},
               "crossStreet": [-44.0, -36.0],
               "blocksW": [[-70, -44, 16], [-36, -27.5, 17], [-17.8, -10.5, 16], [-10.5, 2, 16], [2, 14, 19], [14, 28, 22], [34, 50, 19]],
               "blocksE": [[-70, -44, 14], [-36, -20, 19], [-20, 6, 19], [6, 20, 16], [26, 50, 22]],
               "robberBldg": {"y": [-27.5, -17.8], "h": 19, "floorZ": 7.2, "ceilZ": 10.6, "room": {"x": [-9.6, -4.9], "y": [-26.5, -19.0]}, "win": {"y": [-24.4, -20.4], "z": [8.3, 10.3]}, "door": {"y": [-21.2, -20.0]}, "hall": {"x": [-9.6, -4.6]}, "stairs": {"x": [-9.4, -5.4]}, "corridor": {"x": [-9.6, -6.6]}},
               "canopies": [[-64, -44], [-36, -27.5], [-17.8, 0], [2, 26]],
               "sign24": {"x": -3.9, "y": -4.6}, "pallets": {"x": [-4.4, -3.6], "y": [-18.7, -17.7]},
               "track": {"x": 2.2, "y": [-30, 8]},
               "props": [[-4.4, -3.2, -25.2, -23.8, 0.15, 1.3, [0.75, 0.75, 0.72]], [-4.62, -4.52, -19.9, -19.25, 1.3, 2.0, [0.85, 0.65, 0.2]], [-4.62, -4.55, -22.6, -21.4, 3.0, 4.4, [0.12, 0.12, 0.12]],
                         [-3.4, -3.0, -17.6, -17.25, 0.15, 0.75, [0.75, 0.18, 0.14]], [-3.4, -3.05, -17.15, -16.85, 0.15, 0.65, [0.2, 0.3, 0.7]],
                         [7.0, 7.7, -4.9, -4.2, 0.15, 1.3, [0.62, 0.63, 0.6]], [7.1, 7.6, -4.8, -4.3, 1.3, 1.5, [0.15, 0.15, 0.15]], [6.3, 6.5, -3.6, -2.8, 0.15, 0.75, [0.85, 0.8, 0.2]],
                         [7.0, 7.7, -5.9, -5.2, 0.15, 1.05, [0.55, 0.65, 0.55]], [7.1, 7.75, -6.8, -6.1, 0.15, 0.6, [0.7, 0.7, 0.68]], [7.1, 7.75, -6.8, -6.1, 0.6, 1.1, [0.6, 0.6, 0.58]],
                         [7.1, 7.75, -7.7, -7.0, 0.15, 1.75, [0.62, 0.7, 0.6]], [7.45, 7.5, -9.9, -8.9, 0.15, 2.2, [0.72, 0.62, 0.42]],
                         [7.76, 7.82, -10.9, -9.9, 0.15, 2.3, [0.02, 0.02, 0.02]], [7.7, 7.8, -11.0, -10.9, 0.15, 2.4, [0.2, 0.2, 0.18]], [7.7, 7.8, -9.9, -9.8, 0.15, 2.4, [0.2, 0.2, 0.18]],
                         [5.9, 6.0, -11.4, -11.0, 0.85, 0.95, [0.85, 0.2, 0.18]], [5.9, 6.0, -11.0, -10.6, 0.85, 0.95, [0.92, 0.92, 0.9]], [5.9, 6.0, -10.6, -10.2, 0.85, 0.95, [0.85, 0.2, 0.18]], [5.9, 6.0, -10.2, -9.8, 0.85, 0.95, [0.92, 0.92, 0.9]], [5.9, 6.0, -11.45, -11.35, 0.15, 0.95, [0.92, 0.92, 0.9]], [5.9, 6.0, -9.85, -9.75, 0.15, 0.95, [0.92, 0.92, 0.9]],
                         [7.7, 7.8, -20.5, -12.2, 0.15, 2.6, [0.33, 0.27, 0.2]], [7.62, 7.7, -13.6, -12.4, 0.9, 2.3, [0.45, 0.75, 0.35]], [7.62, 7.7, -14.6, -13.7, 0.9, 2.0, [0.85, 0.45, 0.55]], [7.62, 7.7, -15.0, -14.6, 2.0, 2.4, [0.9, 0.75, 0.3]],
                         [-4.62, -4.5, -12.6, -12.3, 0.5, 3.0, [0.85, 0.7, 0.3]], [-4.62, -4.55, -11.0, -9.7, 0.9, 2.3, [0.88, 0.88, 0.85]], [-4.63, -4.56, -11.0, -9.7, 2.1, 2.3, [0.75, 0.15, 0.12]],
                         [-4.7, -4.6, -12.4, -12.3, 0.0, 2.6, [0.2, 0.2, 0.18]], [-4.7, -4.6, -11.1, -11.0, 0.0, 2.6, [0.2, 0.2, 0.18]],
                         [1.0, 4.2, -45.26, -45.2, 2.8, 3.4, [0.2, 0.35, 0.3]], [-4.5, 0.5, -45.2, -44.4, 2.7, 2.9, [0.85, 0.75, 0.4]],
                         [-4.2, -0.8, -45.26, -45.2, 2.95, 3.5, [0.95, 0.95, 0.95]], [-4.2, -0.8, -45.27, -45.2, 3.1, 3.25, [0.15, 0.3, 0.75]], [-4.0, 0.0, -45.22, -45.2, 0.0, 2.6, [0.1, 0.1, 0.1]],
                         [-3.0, -2.92, -44.0, -43.92, 0.0, 3.2, [0.5, 0.5, 0.5]], [-3.3, -2.6, -44.0, -43.95, 2.6, 3.2, [0.15, 0.3, 0.75]]] + [[-8.6, -5.0 - 0.32 * k, -12.3, -11.1, 0.0, 0.25 * (k + 1), [0.3, 0.3, 0.29]] for k in range(11)] + [[-8.8, -4.6, -12.3, -11.1, 2.95, 3.0, [0.05, 0.05, 0.05]],
                         [-3.9, -3.3, -36.4, -36.2, 0.15, 1.5, [0.95, 0.3, 0.2]], [-4.3, -3.6, -35.8, -35.2, 0.15, 0.85, [0.75, 0.72, 0.65]], [-3.4, -3.1, -35.6, -35.3, 0.15, 0.6, [0.9, 0.9, 0.9]], [-4.0, -3.7, -35.0, -34.7, 0.15, 0.6, [0.9, 0.9, 0.9]]],
               "tires": [[6.5, -4.0, 1], [6.2, -4.6, 1], [6.9, -14.3, 4], [6.3, -14.9, 3], [6.9, -16.3, 4], [6.3, -16.9, 2], [6.4, -18.0, 5], [4.9, -18.2, 3], [3.6, -21.5, 3]],
               "cuts": [{"x": [-8.8, -4.6], "y": [-12.3, -11.1], "z": 3.0}],
               "blocksS": [[-14.0, 14.0, -60.0, -45.2, 14.0]],
               "parked": [[5.1, 15, 0], [5.1, 31, 0], [5.1, 39, 0], [-2.2, 9, 180], [-2.2, 14, 180], [-2.2, 20, 180]]}
json.dump({"I0": I0, "I1": I1, "frames": {str(k): v for k, v in frames.items()}, "entities": ents + crew, "world_patch": world_patch,
           "cars2": [{"id": "POLO", "tpl": "car_silver", "static": [5.0, -42.6, 90.0]}, {"id": "PKX1", "tpl": "car_silver", "static": [-8.5, -41.6, 90.0]}, {"id": "SUV", "tpl": "suv", "static": [4.3, -2.0, 200.0]}, {"id": "PW1", "tpl": "car_silver", "static": [-2.05, 7.6, 180.0]}, {"id": "PW2", "tpl": "car_silver", "static": [-2.05, 12.8, 180.0]}, {"id": "PW3", "tpl": "car_navy", "static": [-2.05, 18.0, 180.0]}, {"id": "PW4", "tpl": "car_silver", "static": [-2.05, 23.2, 180.0]}, {"id": "PE1", "tpl": "van", "static": [5.0, 19.0, 0.0]}, {"id": "PE2", "tpl": "van", "static": [5.0, 26.5, 0.0]}]}, open(f"/mnt/user-data/outputs/full_pieces.json", "w"), ensure_ascii=False)
print("frames", len(frames), "entities", len(ents), "+ crew", len(crew))
