# ==== 《大事件》(2004) 开场长镜头项目里的实际代码，原样保留作参考 ====
# 里面的路径（/tmp/claude-0/...、/mnt/user-data/...）、坐标、车辆尺寸、帧号区间都是那部片子的，换片时逐项改。
# 约定：机位 R 为 世界→相机（OpenCV：x 右 y 下 z 前），C 为相机中心；画面 1280×554 时 CX=640 CY=277、HFOV=42°。
# 车辆检测框底边中点 → 地面交点（世界坐标），按图像空间 IoU 串成短轨迹
import json, math, numpy as np, collections
CAM = json.load(open("cams_world_v1.json")); cams = CAM["cams"]
CX, CY = 640.0, 277.0; F = CX / math.tan(math.radians(CAM["hfov"] / 2)); S = 1280 / 1920
def ray(R, u, v):
    d = np.array(R).T @ np.array([(u - CX) / F, (v - CY) / F, 1.0]); return d / np.linalg.norm(d)
def iou(a, b):
    x0, y0, x1, y1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    i = max(0, x1 - x0) * max(0, y1 - y0); u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i
    return i / u if u > 0 else 0
D = {}
for line in open('/tmp/claude-0/det/all.jsonl'):
    o = json.loads(line)
    if 2376 <= o['f'] <= 5988:
        D[o['f']] = [d for d in o['d'] if d['k'] in ('car', 'truck', 'bus') and d['s'] >= 0.4 and (d['b'][2] - d['b'][0]) > 40]
active, done = [], []
for fr in sorted(D):
    dets = D[fr]; used = set()
    for t in active:
        lb = t["obs"][-1]["b"]; best = None
        for k, d in enumerate(dets):
            if k in used: continue
            u = iou(lb, d['b'])
            if u > 0.35 and (best is None or u > best[0]): best = (u, k)
        if best: used.add(best[1]); t["obs"].append({"f": fr, "b": dets[best[1]]['b'], "k": dets[best[1]]['k'], "s": dets[best[1]]['s'], "col": dets[best[1]].get('col')}); t["last"] = fr
    for k, d in enumerate(dets):
        if k not in used: active.append({"obs": [{"f": fr, "b": d['b'], "k": d['k'], "s": d['s'], "col": d.get('col')}], "last": fr})
    keep = []
    for t in active:
        (done if fr - t["last"] > 6 else keep).append(t)
    active = keep
done += active
tracks = []
for n, t in enumerate(done):
    if len(t["obs"]) < 4: continue
    rows = []
    for ob in t["obs"]:
        nm = f"f{ob['f']:05d}.jpg"
        if nm not in cams: continue
        C = np.array(cams[nm]["C"]); R = cams[nm]["R"]
        x0, y0, x1, y1 = [v * S for v in ob["b"]]
        cut = y1 > 548 or x0 < 2 or x1 > 1278
        d = ray(R, (x0 + x1) / 2, y1)
        if d[2] > -0.01: continue
        lam = -C[2] / d[2]
        if lam > 80: continue
        X = C + lam * d
        # 车身宽度方向：框宽对应的地面距离（粗略尺寸）
        dl = ray(R, x0, y1); dr = ray(R, x1, y1)
        wl = C + (-C[2] / dl[2]) * dl if dl[2] < -0.01 else X; wr = C + (-C[2] / dr[2]) * dr if dr[2] < -0.01 else X
        rows.append({"f": ob["f"], "x": round(float(X[0]), 2), "y": round(float(X[1]), 2), "cut": cut, "w": round(float(np.linalg.norm(wr - wl)), 2), "dist": round(float(lam), 1), "col": ob["col"], "k": ob["k"], "b": [round(v, 1) for v in ob["b"]]})
    if len(rows) >= 4: tracks.append({"id": f"K{n:03d}", "rows": rows})
json.dump(tracks, open("cars_world_v1.json", "w"))
print(len(tracks))
for t in sorted(tracks, key=lambda t: -len(t["rows"]))[:40]:
    r = [x for x in t["rows"] if not x["cut"]] or t["rows"]
    xs = np.array([x["x"] for x in r]); ys = np.array([x["y"] for x in r])
    f0, f1 = t["rows"][0]["f"], t["rows"][-1]["f"]; t0, t1 = 80.8 + f0 / 24, 80.8 + f1 / 24
    col = np.median([x["col"] for x in r if x["col"]], 0).astype(int).tolist() if any(x["col"] for x in r) else None
    print(t["id"], len(t["rows"]), f"{int(t0//60)}:{t0%60:04.1f}-{int(t1//60)}:{t1%60:04.1f}", "x med", round(float(np.median(xs)), 1), "±", round(float(np.std(xs)), 1),
          "y med", round(float(np.median(ys)), 1), "±", round(float(np.std(ys)), 1), "dist", round(float(np.median([x["dist"] for x in r])), 1), "w", round(float(np.median([x["w"] for x in r])), 1), "col", col, r[0]["k"])
