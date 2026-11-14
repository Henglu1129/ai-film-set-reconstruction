# ==== 《大事件》(2004) 开场长镜头项目里的实际代码，原样保留作参考 ====
# 里面的路径（/tmp/claude-0/...、/mnt/user-data/...）、坐标、车辆尺寸、帧号区间都是那部片子的，换片时逐项改。
# 约定：机位 R 为 世界→相机（OpenCV：x 右 y 下 z 前），C 为相机中心；画面 1280×554 时 CX=640 CY=277、HFOV=42°。
# 每帧：用 SfM 旋转把最强的水平消失点转成世界方向；返回 (方向 mod 90) —— 街道/楼面应该是 0 或 90
import json, math, glob, numpy as np, sys
sys.path.insert(0, "/tmp/claude-0/full")
from gfr import CAMS, yaw_of
VP = {}
for f in glob.glob("/tmp/claude-0/full/vp/vp_*.json"): VP.update(json.load(open(f)))
CX, CY = 640.0, 277.0; F = CX / math.tan(math.radians(21))
def comp(n):
    if n not in VP or n not in CAMS: return None
    R = CAMS[n][2]; best = None
    for s, cnt, p in VP[n]["vps"]:
        if cnt < 20: continue
        if p == "inf": continue
        v = np.array([(p[0] - CX) / F, (p[1] - CY) / F, 1.0]); w = R.T @ v; w /= np.linalg.norm(w)
        if abs(w[2]) > 0.35: continue
        a = math.degrees(math.atan2(w[0], w[1]))
        if best is None or cnt > best[1]: best = (a, cnt)
    return best
