# ==== 《大事件》(2004) 开场长镜头项目里的实际代码，原样保留作参考 ====
# 里面的路径（/tmp/claude-0/...、/mnt/user-data/...）、坐标、车辆尺寸、帧号区间都是那部片子的，换片时逐项改。
# 约定：机位 R 为 世界→相机（OpenCV：x 右 y 下 z 前），C 为相机中心；画面 1280×554 时 CX=640 CY=277、HFOV=42°。
# globF → 重力对齐坐标（z 上），每帧 C、R（世界→相机 cv）
import json, numpy as np, math
E = json.load(open("/tmp/claude-0/full/globF_export.json"))["models"]; V = json.load(open("/tmp/claude-0/full/vvp_all.json"))
def up_of(m):
    names = sorted(m["images"]); U = []; W = []
    for n in names:
        if n in V and V[n][3] >= 12: U.append(np.array(m["images"][n]["R"]).T @ np.array(V[n][:3])); W.append(V[n][3])
    U = np.array(U); W = np.array(W, float); u = (U * W[:, None]).sum(0); u /= np.linalg.norm(u)
    for _ in range(5):
        dev = np.degrees(np.arccos(np.clip(U @ u, -1, 1))); w = W * (dev < 8); u = (U * w[:, None]).sum(0); u /= np.linalg.norm(u)
    return u      # R^T·vvp = 世界里的"上"
CAMS = {}
for k, m in E.items():
    u = up_of(m); z = u
    x = np.cross([0, 0, 1.0], z) if abs(z[2]) < 0.9 else np.cross([1.0, 0, 0], z); x /= np.linalg.norm(x); y = np.cross(z, x)
    G = np.array([x, y, z])        # 旧 → 新（行）
    for n, c in m["images"].items():
        C = G @ np.array(c["C"]); R = np.array(c["R"]) @ G.T
        CAMS[n] = (int(k), C, R, c["n3d"])
def yaw_of(R): return math.degrees(math.atan2(R[2][0], R[2][1]))
def pitch_of(R): return math.degrees(math.asin(max(-1, min(1, R[2][2]))))
