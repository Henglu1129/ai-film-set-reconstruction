# ==== 《大事件》(2004) 开场长镜头项目里的实际代码，原样保留作参考 ====
# 里面的路径（/tmp/claude-0/...、/mnt/user-data/...）、坐标、车辆尺寸、帧号区间都是那部片子的，换片时逐项改。
# 约定：机位 R 为 世界→相机（OpenCV：x 右 y 下 z 前），C 为相机中心；画面 1280×554 时 CX=640 CY=277、HFOV=42°。
# 试点窗口人物 → bake 实体（旧场景坐标）
# 规则：同一身份的观测合并成一条连续轨迹；观测之间 ≤4 秒的空档按直线补；首尾各延 2.5 秒（原地保持）；
#       位置做稳健平滑（中值 + 加权平均，脚点权重高）；速度上限 3 m/s；朝向取姿态朝向，否则取运动方向，否则面向机位
import json, math, sys, collections, numpy as np
sys.path.insert(0, "/tmp/claude-0/pilot/s2"); sys.path.insert(0, "/tmp/claude-0/pilot/s3")
sys.path.insert(0, '/tmp/claude-0/full'); import cam_full as cam2
I0, I1 = int(sys.argv[1]), int(sys.argv[2]); RAW = json.load(open(f"/tmp/claude-0/full/pp_raw_{I0}_{I1}.json"))
DT = 0.125; HOLD = int(2.5 / DT); GAPMAX = int(4.0 / DT)
WT = {"foot": 1.0, "torso": 0.45, "box": 0.2}
SEATS = {"CA": (-2.37, -3.35, 0.0), "CB": (-1.57, -3.35, 0.0)}      # 便衣车（中心 -2,-3.5，车头朝南）：右舵，司机在西侧
CAT = {"Y": ("元哥", "robber", "robber", "rifle"), "RD": ("劫匪司机", "robber", "robber", "pistol"), "RB": ("劫匪（黑开衫）", "robber", "robber", "pistol"),
       "RY": ("劫匪（米色夹克）", "robber", "robber", "pistol"), "RG": ("劫匪（灰夹克）", "robber", "robber", "pistol"), "RK": ("劫匪（黑夹克）", "robber", "robber", "pistol"),
       "robber": ("劫匪", "robber", "robber", "pistol"), "CH": ("便衣督察", "cop", "plainclothes", "pistol"), "cop": ("便衣", "cop", "plainclothes", "pistol"), "RR": ("劫匪（红衣）", "robber", "robber", "pistol"), "R5": ("劫匪（步枪）", "robber", "robber", "rifle"), "CA": ("便衣（驾驶座）", "cop", "plainclothes", "pistol"), "CB": ("便衣（副驾）", "cop", "plainclothes", "pistol"),
       "C3": ("白发便衣", "cop", "oldman", "pistol"), "CW": ("女便衣", "cop", "woman", "pistol"), "CF": ("胖便衣", "cop", "plainclothes", "pistol"),
       "police": ("巡警", "patrol", "police", None), "worker": (None, "extra", "worker", None), "woman": (None, "extra", "woman", None), "extra": (None, "extra", "extra", None)}
UNIQUE = {"Y", "RD", "RB", "RY", "RG", "RK", "C3", "CW", "CF", "CH", "RR", "R5"}
by = collections.defaultdict(list)
for k, v in RAW.items():
    lab, tid = k.split("|"); by[lab].append((tid, v))
def series(obs_lists):
    """多条观测 → 每个采样一条：取权重最高的那条的视线方向；深度在时间上稳健平滑后再沿视线放回（保证同机位下位置不偏）"""
    acc = collections.defaultdict(list)
    for v in obs_lists:
        for r in v: acc[r["i"]].append(r)
    ks = sorted(acc); best = {i: max(acc[i], key=lambda r: WT[r["m"]]) for i in ks}
    d = np.array([best[i]["d"] for i in ks]); w = np.array([WT[best[i]["m"]] for i in ks]); idx = np.array(ks)
    ds = np.zeros_like(d)
    md = np.array([np.median(d[max(0, k - 4): k + 5]) for k in range(len(d))])
    w2 = np.where(np.abs(d - md) > 0.25 * md + 0.5, w * 0.05, w)
    for k, i in enumerate(idx):
        g = np.exp(-0.5 * ((idx - i) * DT / 0.4) ** 2) * w2; ds[k] = (g * d).sum() / g.sum()
    out = {}
    for k, i in enumerate(ks):
        r = best[i]; yaws = [q["yaw"] for q in acc[i] if q["yaw"] is not None]
        out[i] = (r["cx"] + r["ux"] * ds[k], r["cy"] + r["uy"] * ds[k], float(w[k]), yaws[0] if yaws else None)
    return out
def smooth_track(ser):
    ks = sorted(ser);
    if not ks: return []
    segs = [[ks[0]]]
    for a, b in zip(ks, ks[1:]):
        (segs[-1].append(b) if b - a <= GAPMAX else segs.append([b]))
    rows_all = []
    for sg in segs:
        lo, hi = max(I0, sg[0] - HOLD), min(I1, sg[-1] + HOLD)
        idx = np.arange(sg[0], sg[-1] + 1)
        ox = np.array([ser[i][0] for i in sg]); oy = np.array([ser[i][1] for i in sg]); ow = np.array([ser[i][2] for i in sg])
        # 中值去野点
        mx = np.array([np.median(ox[max(0, k - 3): k + 4]) for k in range(len(sg))]); my = np.array([np.median(oy[max(0, k - 3): k + 4]) for k in range(len(sg))])
        bad = np.hypot(ox - mx, oy - my) > 1.5; ow = np.where(bad, ow * 0.05, ow)
        # 高斯核加权平滑到每个采样（σ = 0.5 s）
        xs, ys = [], []
        for i in idx:
            g = np.exp(-0.5 * ((np.array(sg) - i) * DT / 0.15) ** 2) * ow
            if g.sum() < 1e-6: g = np.exp(-0.5 * ((np.array(sg) - i) * DT / 2.0) ** 2) * ow
            xs.append((g * ox).sum() / g.sum()); ys.append((g * oy).sum() / g.sum())
        xs = np.array(xs); ys = np.array(ys)
        # 速度上限
        for k in range(1, len(xs)):
            d = math.hypot(xs[k] - xs[k - 1], ys[k] - ys[k - 1]); mx_ = 4.0 * DT
            if d > mx_: f = mx_ / d; xs[k] = xs[k - 1] + (xs[k] - xs[k - 1]) * f; ys[k] = ys[k - 1] + (ys[k] - ys[k - 1]) * f
        full = list(range(lo, sg[0])) + list(idx) + list(range(sg[-1] + 1, hi + 1))
        X = [xs[0]] * (sg[0] - lo) + list(xs) + [xs[-1]] * (hi - sg[-1]); Y = [ys[0]] * (sg[0] - lo) + list(ys) + [ys[-1]] * (hi - sg[-1])
        obsyaw = {i: ser[i][3] for i in sg if ser[i][3] is not None}
        rows = []
        for k, i in enumerate(full):
            vx = (X[min(k + 4, len(X) - 1)] - X[max(k - 4, 0)]); vy = (Y[min(k + 4, len(Y) - 1)] - Y[max(k - 4, 0)])
            sp = math.hypot(vx, vy) / (DT * (min(k + 4, len(X) - 1) - max(k - 4, 0)) or 1)
            near = [obsyaw[j] for j in range(i - 8, i + 9) if j in obsyaw]
            if sp > 0.5: yaw = math.atan2(-vx, vy)
            elif near: yaw = float(np.median(near))
            else:
                C = cam2.cam(3 * i)[0]; yaw = math.atan2(-(C[0] - X[k]), C[1] - Y[k])
            rows.append([int(i), round(float(X[k]), 3), round(float(Y[k]), 3), (7.2 if 1566 <= 3 * i <= 2090 and X[k] < -4.6 else 0.0), round(yaw, 4), "walk" if sp > 0.5 else "stand", 0.0, None])
        # 朝向平滑（避免原地乱转）：限制 120°/s
        for k in range(1, len(rows)):
            a = rows[k - 1][4]; b = rows[k][4]; d = (b - a + math.pi) % (2 * math.pi) - math.pi; mx_ = math.radians(120) * DT
            if abs(d) > mx_: rows[k][4] = round(a + math.copysign(mx_, d), 4)
        # 动作至少保持 0.75 秒
        k = 0
        while k < len(rows):
            j = k
            while j < len(rows) and rows[j][5] == rows[k][5]: j += 1
            if j - k < 6 and k > 0:
                for q in range(k, j): rows[q][5] = rows[k - 1][5]
            k = j
        rows_all.append(rows)
    return rows_all
ents = []; vid = 0
def add(lab, rows, src):
    global vid; vid += 1
    lb, role, tpl, prop = CAT[lab]
    ents.append({"id": f"PP{vid:03d}_{lab}", "cat": lab, "src": src, "tpl": tpl, "role": role, "label": lb, "prop": prop, "main": lb is not None, "s": rows, "aim": []})
for lab, L in by.items():
    if lab in ("CA", "CB"):
        EXIT = 6252 // 3                     # 05:41 两人下车
        x, y, z = SEATS[lab]
        seat = [[i, x, y, 0.0, math.pi, "sit", 0.0, None] for i in range(I0, min(I1, EXIT) + 1)]
        after = [(t, [r for r in v if r["i"] > EXIT]) for t, v in L]; after = [(t, v) for t, v in after if v]
        tr = smooth_track(series([v for _, v in after])) if after else []
        if seat: add(lab, seat, [t for t, _ in L])
        for rows in tr: add(lab, rows, [t for t, _ in after])
        continue
    if lab in UNIQUE:
        for rows in smooth_track(series([v for _, v in L])): add(lab, rows, [t for t, _ in L])
    elif lab in ("police", "worker", "cop", "robber"):
        # 按短轨迹分人：时间上重叠的短轨迹必属不同的人；不重叠时接到"末端最近"的那个人（≤4 m）
        tl = []
        for tid, v in L:
            if len(v) < 4: continue
            v = sorted(v, key=lambda r: r["i"]); tl.append((v[0]["i"], v[-1]["i"], tid, v))
        tl.sort()
        persons = []
        def endpos(v, at_end=True):
            seg = v[-6:] if at_end else v[:6]; w = np.array([WT[r["m"]] for r in seg])
            return np.array([(w * [r["x"] for r in seg]).sum() / w.sum(), (w * [r["y"] for r in seg]).sum() / w.sum()])
        for i0, i1, tid, v in tl:
            best = None
            for p in persons:
                if any(not (i1 < a0 or i0 > a1) for a0, a1, _ in p["span"]): continue   # 时间重叠
                last = max(p["span"], key=lambda s_: s_[1]); gap = i0 - last[1]
                if gap < 0 or gap > int(6 / DT): continue
                d = np.linalg.norm(endpos(p["obs"][last[2]]) - endpos(v, False))
                if d < 4.0 + 1.5 * gap * DT and (best is None or d < best[0]): best = (d, p)
            if best: p = best[1]
            else: p = {"span": [], "obs": {}}; persons.append(p)
            p["span"].append((i0, i1, tid)); p["obs"][tid] = v
        for p in persons:
            for rows in smooth_track(series(list(p["obs"].values()))): add(lab, rows, list(p["obs"].keys()))
    else:   # 女路人、路人：每条短轨迹单独一人，至少 1 秒
        for tid, v in L:
            if len(v) < 8: continue
            for rows in smooth_track(series([v])): add(lab, rows, [tid])
# 去重：同类两人同一时刻 < 0.6 m 且重叠 >1 秒 → 删短的
def overlap(a, b, thr=0.6):
    A = {r[0]: r for r in a["s"]}; n = 0
    for r in b["s"]:
        q = A.get(r[0])
        if q and math.hypot(q[1] - r[1], q[2] - r[2]) < thr: n += 1
    return n
ents.sort(key=lambda e: -len(e["s"])); keep = []
for e in ents:
    if any(k["cat"] == e["cat"] and (overlap(k, e) > 8 or (e["cat"] in UNIQUE and overlap(k, e, 1.2) > 4)) for k in keep): continue
    keep.append(e)
# ---- 同一身份同一时刻只能有一个人：重叠时段只保留较长那条 ----
byc = collections.defaultdict(list)
for e_ in keep: byc[e_["cat"]].append(e_)
for cat_, L_ in byc.items():
    if cat_ not in UNIQUE: continue
    L_.sort(key=lambda z: -len(z["s"])); taken = set()
    for e_ in L_:
        e_["s"] = [r for r in e_["s"] if r[0] not in taken]; taken.update(r[0] for r in e_["s"])
keep = [e_ for e_ in keep if len(e_["s"]) >= 6]
# ---- 房间里的人不能出房间 ----
for e_ in keep:
    for r in e_["s"]:
        if r[3] > 6: r[1] = round(min(max(r[1], -9.3), -5.2), 3); r[2] = round(min(max(r[2], -26.2), -19.3), 3)
# ---- 06:12–06:28 元哥蹲在油桶后 ----
for e_ in keep:
    if e_["cat"] == "Y":
        for r in e_["s"]:
            if 6960 <= 3 * r[0] <= 7300:
                ff = 3 * r[0]; r[1] = round(float(np.interp(ff, [6960, 7056, 7128, 7200, 7300], [-5.6, -5.6, -5.4, -5.3, -5.3])), 3)
                r[2] = round(float(np.interp(ff, [6960, 7056, 7128, 7200, 7300], [-14.9, -15.0, -15.5, -15.9, -15.9])), 3)
# ---- 按原片画面摆位的几处 ----
for e_ in keep:
    if any(t in ("A130", "A132") for t in e_["src"]): e_["tpl_force"] = ("plainclothes", [0.55, 0.42, 0.3])
for e_ in keep:
    if e_["cat"] == "Y":
        e_["s"] = [r for r in e_["s"] if not (1250 <= 3 * r[0] <= 1340)]
        if any(1600 <= 3 * r[0] <= 1910 for r in e_["s"]):
            e_["s"] = [r for r in e_["s"] if not (1975 <= 3 * r[0] <= 2065)] + [[i_, -7.3, -24.4, 7.2, 0.0, "stand", 0.0, None] for i_ in range(1980 // 3, 2061 // 3)]
        if any(1100 <= 3 * r[0] <= 1249 for r in e_["s"]):          # 02:13–02:16 走进门洞
            for i_ in range(1251 // 3, 1335 // 3):
                u = (3 * i_ - 1251) / 84; e_["s"].append([i_, round(-4.0 - 1.4 * u, 3), round(-19.9 - 0.7 * u, 3), 0.0, round(math.atan2(1.0, -0.5), 4), "walk", (3 * i_ % 24) / 24, None])
        e_["s"].sort(key=lambda r: r[0])
    if e_.get("tpl_force"):
        e_["s"] = [r for r in e_["s"] if not (1975 <= 3 * r[0] <= 2065)] + [[i_, -6.3, -23.75, 7.2, -2.61, "stand", 0.0, None] for i_ in range(1980 // 3, 2061 // 3)]
        e_["s"].sort(key=lambda r: r[0])
    if e_["cat"] not in ("Y",) and e_["role"] == "robber":
        e_["s"] = [r for r in e_["s"] if not (6960 <= 3 * r[0] <= 7300 and r[1] > -6.0)]
    if e_["cat"] in ("RB", "RY", "RG", "Y", "robber"):
        for r in e_["s"]:
            if 3150 <= 3 * r[0] <= 3320:
                C_ = cam2.cam(3 * r[0])[0]; r[1] = round(C_[0] + (r[1] - C_[0]) * 1.2, 3); r[2] = round(C_[1] + (r[2] - C_[1]) * 1.2, 3); r[1] = max(r[1], -4.4)
for e_ in keep:
    if e_["role"] == "robber" and e_["cat"] != "Y" and not e_.get("tpl_force"):
        for r in e_["s"]:
            if 1975 <= 3 * r[0] <= 2065 and r[3] > 6: r[1] = min(r[1], -8.4); r[2] = min(r[2], -24.6)
keep = [e_ for e_ in keep if len(e_["s"]) >= 6]
# ---- 第二轮：按原片逐段摆位 ----
def drop(f0, f1, pred):
    for e_ in keep:
        e_["s"] = [r for r in e_["s"] if not (f0 <= 3 * r[0] <= f1 and pred(e_, r))]
def path(f0, f1, P, kind, yaw=None, z=0.0):
    """P: [(f, x, y)] 关键帧；yaw None = 沿运动方向"""
    rows = []
    for i_ in range(f0 // 3, f1 // 3 + 1):
        ff = 3 * i_; x = float(np.interp(ff, [p[0] for p in P], [p[1] for p in P])); y = float(np.interp(ff, [p[0] for p in P], [p[2] for p in P]))
        zz = float(np.interp(ff, [p[0] for p in P], [p[3] if len(p) > 3 else z for p in P]))
        if yaw is None:
            x2 = float(np.interp(ff + 6, [p[0] for p in P], [p[1] for p in P])); y2 = float(np.interp(ff + 6, [p[0] for p in P], [p[2] for p in P]))
            yw = math.atan2(-(x2 - x), y2 - y) if math.hypot(x2 - x, y2 - y) > 1e-3 else (rows[-1][4] if rows else 0.0)
        else: yw = yaw
        rows.append([i_, round(x, 3), round(y, 3), round(zz, 3), round(yw, 4), kind, (ff % 24) / 24, None])
    return rows
def put(cat, rows_list, tpl=None, tint=None, label=True, prop=None):
    tgt = next((k for k in keep if k["cat"] == cat), None) if label else None
    if tgt is None:
        lb, role, tp, pr = CAT.get(cat, (None, "extra", "extra", None))
        tgt = {"id": f"PPS_{cat}_{len(keep)}", "cat": cat, "src": ["layout"], "tpl": tpl or tp, "role": role, "label": lb if label else None, "prop": prop if prop is not None else pr, "main": bool(lb) and label, "s": [], "aim": []}
        if tint: tgt["tint"] = tint
        keep.append(tgt)
    taken = set()
    for rows in rows_list:
        for r in rows: taken.add(r[0])
    tgt["s"] = [r for r in tgt["s"] if r[0] not in taken] + [r for rows in rows_list for r in rows]; tgt["s"].sort(key=lambda r: r[0])
    return tgt
# 05:46–06:08 东侧旧货店 → 修路区
drop(6380, 6890, lambda e_, r: r[1] > 2.5 and -21 < r[2] < 0 and e_["cat"] not in ("CA", "CB"))
put("C3", [path(6380, 6395, [(6380, 5.4, -2.6), (6395, 5.2, -3.4)], "run"), path(6396, 6510, [(6396, 5.2, -3.4), (6510, 5.2, -3.4)], "crouch_aim", yaw=math.pi * 0.85),
           path(6511, 6545, [(6511, 5.4, -4.2), (6545, 6.8, -7.6)], "run"), path(6546, 6650, [(6546, 6.8, -7.6), (6650, 6.8, -7.6)], "crouch", yaw=-math.pi / 2)])
put("CF", [path(6440, 6462, [(6440, 6.2, -5.0), (6462, 6.6, -5.8)], "run"), path(6463, 6890, [(6463, 6.9, -6.0), (6530, 6.4, -7.9), (6890, 6.4, -7.9)], "lie", yaw=-math.pi)])
put("worker", [path(6640, 6900, [(6640, 7.2, -15.0), (6900, 7.2, -15.0)], "crouch", yaw=math.pi / 2)], label=False, tpl="worker")
put("worker", [path(6640, 6900, [(6640, 7.1, -14.1), (6900, 7.1, -14.1)], "crouch", yaw=math.pi / 2)], label=False, tpl="worker")
put("robber", [path(6730, 6900, [(6730, 6.95, -18.4), (6900, 6.95, -18.4)], "crouch_aim", yaw=0.785)], label=False, tpl="extra", tint=[0.95, 0.85, 0.7], prop="pistol")
# 06:22–06:28 楼梯门口
drop(7230, 7430, lambda e_, r: r[1] < -1.5 and -16.5 < r[2] < -9 and e_["cat"] != "Y")
put("robber", [path(7230, 7310, [(7230, -3.2, -12.6), (7310, -2.2, -10.6)], "crouch", yaw=-0.64)], label=False, tpl="extra", tint=[0.62, 0.64, 0.66], prop="pistol")
for e_ in keep:
    if e_["cat"] == "Y" and any(6960 <= 3 * r[0] <= 7300 for r in e_["s"]):
        e_["s"] = [r for r in e_["s"] if not (7201 <= 3 * r[0] <= 7430)] + path(7201, 7430, [(7201, -5.3, -15.9), (7290, -5.0, -11.7), (7430, -5.0, -11.7)], "aim", yaw=-math.pi / 2)
        e_["s"].sort(key=lambda r: r[0])
# 07:00–07:12 攀窗劫匪：身体探出二楼窗口 → 跳到檐篷
put("R5", [path(8130, 8250, [(8130, -4.3, -21.6, 6.6), (8250, -4.3, -21.8, 6.7)], "stand", yaw=-math.pi / 2), path(8251, 8330, [(8251, -4.3, -21.9, 7.3), (8330, -4.3, -21.9, 7.4)], "crouch", yaw=-math.pi / 2),
           path(8331, 8400, [(8331, -4.3, -21.9, 7.4), (8352, -4.0, -24.2, 5.2), (8400, -3.8, -24.5, 1.3)], "jump", yaw=-math.pi / 2),
           path(8401, 8445, [(8401, -3.8, -24.5, 1.3), (8445, -3.8, -24.5, 1.3)], "crouch", yaw=-math.pi / 2)])
# 07:19–07:42 路口
drop(8590, 9170, lambda e_, r: r[2] < -26 or (e_["cat"] in ("CH",) and 8700 <= 3 * r[0] <= 8830))
put("R5", [path(8590, 8990, [(8590, -0.4, -35.6), (8990, -0.7, -34.6)], "kneel_aim", yaw=math.pi), path(8991, 9170, [(8991, -0.7, -34.6), (9170, -1.0, -32.4)], "aim", yaw=math.pi)])
put("RB", [path(8880, 8999, [(8880, -3.2, -34.0), (8999, -1.6, -35.6)], "walk"), path(9000, 9030, [(9000, -1.6, -35.6), (9030, -1.6, -35.6)], "crouch", yaw=2.5),
           path(9031, 9170, [(9031, -1.6, -35.6), (9170, 0.2, -41.4)], "walk")])
put("police", [path(8590, 8800, [(8590, 2.6, -43.6), (8800, 2.4, -43.4)], "stand", yaw=0.0)], label=False, tpl="police")
put("robber", [path(8590, 8700, [(8590, -1.8, -43.1), (8700, -3.6, -43.3)], "run")], label=False, tpl="extra", tint=[0.4, 0.4, 0.42])
put("CH", [path(8760, 8820, [(8760, -1.6, -30.7), (8820, -1.6, -30.7)], "aim", yaw=-math.pi / 2)])
keep.append({"id": "PPW_paper", "cat": "robber", "src": ["layout"], "tpl": "extra", "role": "robber", "label": None, "prop": None, "main": False, "tint": [0.5, 0.5, 0.52],
             "s": [[i_, -6.3, -23.2, 7.2, round(-math.pi / 2, 4), "sit", 0.0, None] for i_ in range(1470 // 3, 1640 // 3)], "aim": []})
# ---- 指定的面对面（对话 / 推搡）----
PAIRS = [(5250, 5480, "C3", "CF"), (5560, 5990, "police", "RG"), (5560, 5990, "police", "RD"), (6000, 6140, "police", "RD")]
byi = collections.defaultdict(dict)
for e_ in keep:
    for r in e_["s"]: byi[r[0]].setdefault(e_["cat"], []).append(r)
for f0, f1, a_, b_ in PAIRS:
    for i_ in range(f0 // 3, f1 // 3 + 1):
        A_, B_ = byi[i_].get(a_, []), byi[i_].get(b_, [])
        for ra in A_:
            for rb in B_:
                if math.hypot(ra[1] - rb[1], ra[2] - rb[2]) < 4.0:
                    ra[4] = round(math.atan2(-(rb[1] - ra[1]), rb[2] - ra[2]), 4); rb[4] = round(math.atan2(-(ra[1] - rb[1]), ra[2] - rb[2]), 4)
                    if ra[5] == "walk": ra[5] = "stand"
                    if rb[5] == "walk": rb[5] = "stand"
# ---- 02:47–02:50 窗边望向窗外的人（棕色外套）----
keep.append({"id": "PPW_win", "cat": "robber", "src": ["layout"], "tpl": "plainclothes", "role": "robber", "label": None, "prop": None, "main": False, "tint": [0.55, 0.42, 0.3],
             "s": [[i_, -5.3, -23.45, 7.2, -0.3, "stand", 0.0, None] for i_ in range(2060 // 3, 2130 // 3)], "aim": []})
# ---- 朝向规则 ----
idx = collections.defaultdict(list)
for e_ in keep:
    for r in e_["s"]: idx[r[0]].append((e_, r))
for i_, L_ in idx.items():
    f_ = 3 * i_
    for e_, r in L_:
        if r[5] in ("sit", "walk") or e_["cat"] in ("CA", "CB") and f_ < 6252: continue
        if 1975 <= f_ <= 2130 and (e_["cat"] == "Y" or e_.get("tpl_force") or e_["id"] == "PPW_win"): continue
        if 2000 <= f_ <= 2200 and r[3] > 6:                     # 劫匪房间：望向窗外（东）
            r[4] = round(-math.pi / 4, 4); continue
        if e_["cat"] == "Y" and 6960 <= f_ <= 7360:               # 油桶后蹲着开枪，朝街
            r[5] = "aim"; r[4] = round(-math.pi / 2, 4); continue
        best = None
        for e2, r2 in L_:
            if e2 is e_ or e2["cat"] in ("CA", "CB") and f_ < 6252: continue
            dd = math.hypot(r2[1] - r[1], r2[2] - r[2])
            if dd < 2.5 and (best is None or dd < best[0]): best = (dd, r2)
        if best: r[4] = round(math.atan2(-(best[1][1] - r[1]), best[1][2] - r[2]), 4)   # 两人说话/推搡：面对面
keep = [e_ for e_ in keep if len(e_["s"]) >= 3]
json.dump(keep, open(f"/tmp/claude-0/full/ents_full_{I0}_{I1}.json", "w"), ensure_ascii=False)
print(len(ents), "->", len(keep), collections.Counter(e["cat"] for e in keep))
for e in keep:
    s = e["s"]; print(e["id"], e["label"], len(s), round(80.8 + s[0][0] * 3 / 24, 1), round(80.8 + s[-1][0] * 3 / 24, 1), "pos", s[len(s) // 2][1:3])
