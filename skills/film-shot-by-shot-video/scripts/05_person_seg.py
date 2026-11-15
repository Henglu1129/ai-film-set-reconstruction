"""逐帧人像分割（YOLOv8n-seg，权重从 ultralytics 的 GitHub release 下载）。
结果用于：①画人物轮廓（景别）②标签避让（人物 mask 并集 + 脸部加权）③判断景别标签贴在谁旁边。
2 核 CPU、imgsz=512 约 20 帧/秒，16 分钟片段约 20 分钟，后台跑。
用法：python3 05_person_seg.py WORK_DIR [STEP=1] [LIMIT]"""
import cv2, numpy as np, pickle, time, sys, os
WORK = sys.argv[1] if len(sys.argv) > 1 else '.'
MODELS = os.environ.get('MODELS', '/home/claude/models')
from ultralytics import YOLO
m = YOLO(os.path.join(MODELS,'yolo','yolov8n-seg.pt'))
cap = cv2.VideoCapture(os.path.join(WORK,'clip.mp4'))
fps = cap.get(cv2.CAP_PROP_FPS)
STEP = int(sys.argv[2]) if len(sys.argv) > 2 else 1
LIMIT = int(sys.argv[3]) if len(sys.argv) > 3 else 10**9
out = {}; i = 0; t0 = time.time()
while i < LIMIT:
    if not cap.grab(): break
    if i % STEP == 0:
        _, fr = cap.retrieve()
        r = m.predict(fr, imgsz=512, classes=[0], conf=0.35, verbose=False, retina_masks=False)[0]
        people = []
        if r.masks is not None:
            for poly, box, cf in zip(r.masks.xyn, r.boxes.xyxyn.numpy(), r.boxes.conf.numpy()):
                if len(poly) < 3: continue
                people.append({'poly': poly.astype(np.float32), 'box': box.astype(np.float32), 'conf': float(cf)})
        out[i] = people
        if i % 960 == 0: print(i, round(time.time() - t0, 1), flush=True)
    i += 1
pickle.dump({'step': STEP, 'fps': fps, 'n': i, 'frames': out}, open(os.path.join(WORK,'seg.pkl'), 'wb'))
print('DONE', i, round(time.time() - t0, 1), flush=True)
