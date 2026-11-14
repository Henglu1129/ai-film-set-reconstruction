# ==== 《大事件》(2004) 开场长镜头项目里的实际代码，原样保留作参考 ====
# 里面的路径（/tmp/claude-0/...、/mnt/user-data/...）、坐标、车辆尺寸、帧号区间都是那部片子的，换片时逐项改。
# 约定：机位 R 为 世界→相机（OpenCV：x 右 y 下 z 前），C 为相机中心；画面 1280×554 时 CX=640 CY=277、HFOV=42°。
# 逐帧检测：YOLOX-m（人、车）+ MediaPipe Pose（3D 骨骼关键点）
# 用法：python3 -I detect.py <video> <out.jsonl> <start_frame> <end_frame> <step>
import sys, json, math
import numpy as np, cv2 as cv, onnxruntime as ort

VID, OUT, A, Bf, STEP = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
import os
MD = os.environ.get("DSJ_MODELS", "/mnt/user-data/uploads/电影资源/大事件_长镜头拆解/models/")
so = ort.SessionOptions(); so.intra_op_num_threads = int(os.environ.get("DSJ_THREADS", "2"))
det = ort.InferenceSession(MD + "yolox_m.onnx", so, providers=["CPUExecutionProvider"])
din = det.get_inputs()[0]; IN = din.shape[2]
pose = cv.dnn.readNet(MD + "pose_mediapipe.onnx")
KEEP = {0: "person", 2: "car", 5: "bus", 7: "truck", 3: "motorbike", 1: "bicycle"}

def yolox_grids(size):
    grids, strides = [], []
    for s in (8, 16, 32):
        h = w = size // s
        xv, yv = np.meshgrid(np.arange(w), np.arange(h))
        grids.append(np.stack((xv, yv), 2).reshape(-1, 2)); strides.append(np.full((h * w, 1), s))
    return np.concatenate(grids), np.concatenate(strides)
GRID, STR = yolox_grids(IN)

def run_tile(img):
    """img: BGR tile；返回 [x1,y1,x2,y2,score,cls]（tile 坐标）"""
    h, w = img.shape[:2]; r = min(IN / h, IN / w)
    pad = np.full((IN, IN, 3), 114, np.uint8); rs = cv.resize(img, (int(w * r), int(h * r)), interpolation=cv.INTER_LINEAR)
    pad[:rs.shape[0], :rs.shape[1]] = rs
    blob = pad.transpose(2, 0, 1)[None].astype(np.float32)
    out = det.run(None, {din.name: blob})[0][0]
    out[:, :2] = (out[:, :2] + GRID) * STR; out[:, 2:4] = np.exp(out[:, 2:4]) * STR
    cls = out[:, 5:].argmax(1); sc = out[:, 4] * out[:, 5:].max(1)
    m = (sc > 0.30) & np.isin(cls, list(KEEP))
    o = out[m]; cls = cls[m]; sc = sc[m]
    b = np.stack([o[:, 0] - o[:, 2] / 2, o[:, 1] - o[:, 3] / 2, o[:, 0] + o[:, 2] / 2, o[:, 1] + o[:, 3] / 2], 1) / r
    return np.c_[b, sc, cls]

def nms(d, thr=0.5):
    if len(d) == 0: return d
    keep = []
    for c in np.unique(d[:, 5]):
        dc = d[d[:, 5] == c]; boxes = dc[:, :4].tolist(); scores = dc[:, 4].tolist()
        idx = cv.dnn.NMSBoxes([[b[0], b[1], b[2] - b[0], b[3] - b[1]] for b in boxes], scores, 0.3, thr)
        keep += [dc[i] for i in np.array(idx).flatten()]
    return np.array(keep)

def detect(frame):
    H, W = frame.shape[:2]  # 832 x 1920
    dets = [run_tile(frame)]  # 整帧（大目标）
    ts = H  # 方形瓦片，三块覆盖整宽
    for x0 in (0, (W - ts) // 2, W - ts):
        d = run_tile(frame[:, x0:x0 + ts])
        if len(d): d[:, [0, 2]] += x0; dets.append(d)
    d = np.concatenate([x for x in dets if len(x)]) if any(len(x) for x in dets) else np.zeros((0, 6))
    return nms(d, 0.55)

def run_pose(frame, b):
    x1, y1, x2, y2 = b[:4]; h = y2 - y1; cx = (x1 + x2) / 2
    mid = np.array([cx, y1 + 0.55 * h], np.float32); full = np.array([cx, y1 - 0.08 * h], np.float32)
    dist = np.linalg.norm(mid - full)
    fb = np.array([mid - dist, mid + dist], np.int32)
    pb = fb.copy(); pb[:, 0] = np.clip(pb[:, 0], 0, frame.shape[1]); pb[:, 1] = np.clip(pb[:, 1], 0, frame.shape[0])
    crop = frame[pb[0][1]:pb[1][1], pb[0][0]:pb[1][0]]
    if crop.size == 0: return None
    l, t = pb[0] - fb[0]; r_, bt = fb[1] - pb[1]
    crop = cv.copyMakeBorder(crop, int(t), int(bt), int(l), int(r_), cv.BORDER_CONSTANT, None, (0, 0, 0))
    side = crop.shape[0]
    blob = cv.cvtColor(cv.resize(crop, (256, 256), interpolation=cv.INTER_AREA), cv.COLOR_BGR2RGB).astype(np.float32)[None] / 255.0
    pose.setInput(blob)
    lm, conf, mask, heat, lmw = pose.forward(pose.getUnconnectedOutLayersNames())
    c = float(conf[0][0])
    if c < 0.5: return None
    lm = lm[0].reshape(-1, 5)[:33]; vis = 1 / (1 + np.exp(-lm[:, 3]))
    s = side / 256.0; x0, y0 = fb[0]
    px = lm[:, 0] * s + x0; py = lm[:, 1] * s + y0
    w3 = lmw[0].reshape(-1, 3)[:33]
    return {"c": round(c, 3), "p2": np.c_[px, py].round(1).tolist(), "v": vis.round(2).tolist(), "w3": w3.round(3).tolist()}

cap = cv.VideoCapture(VID); cap.set(cv.CAP_PROP_POS_FRAMES, A)
fo = open(OUT, "a")
f = A
while f < Bf:
    ok, frame = cap.read()
    if not ok: break
    if (f - A) % STEP == 0:
        d = detect(frame); rec = {"f": f, "d": []}
        for b in d:
            e = {"k": KEEP[int(b[5])], "b": [round(float(v), 1) for v in b[:4]], "s": round(float(b[4]), 3)}
            if e["k"] == "person" and (b[3] - b[1]) >= 90:
                ps = run_pose(frame, b)
                if ps: e["pose"] = ps
            if e["k"] == "person":
                # 躯干颜色（上身中部）
                x1, y1, x2, y2 = [int(v) for v in b[:4]]; hh = y2 - y1
                roi = frame[max(0, y1 + int(0.25 * hh)):max(1, y1 + int(0.5 * hh)), max(0, x1 + (x2 - x1) // 4):max(1, x2 - (x2 - x1) // 4)]
                if roi.size: e["col"] = [int(v) for v in roi.reshape(-1, 3).mean(0)[::-1]]
            rec["d"].append(e)
        fo.write(json.dumps(rec) + "\n"); fo.flush()
    f += 1
print("done", A, Bf)
