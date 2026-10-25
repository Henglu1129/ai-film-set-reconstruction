# ==== 《大事件》(2004) 开场长镜头项目里的实际代码，原样保留作参考 ====
# 里面的路径（/tmp/claude-0/...、/mnt/user-data/...）、坐标、车辆尺寸、帧号区间都是那部片子的，换片时逐项改。
# 约定：机位 R 为 世界→相机（OpenCV：x 右 y 下 z 前），C 为相机中心；画面 1280×554 时 CX=640 CY=277、HFOV=42°。
# 全片机位（旧场景坐标，米）：cam(f) → (C, R_cv)。f 为原片 take 帧号（0..9767，步长 3 的网格上有值，其余插值）
import sys, json, math, numpy as np
sys.path.insert(0, "/tmp/claude-0/full"); sys.path.insert(0, "/tmp/claude-0/pilot/s3"); sys.path.insert(0, "/tmp/claude-0/pilot/s2")
from gfr import CAMS, yaw_of, pitch_of
from xf import Rz_cw
import cam2
S = json.load(open("/tmp/claude-0/full/segF.json")); XA1 = S["A1"]["x"]; PIVA1 = np.array(S["A1"]["piv"])
def catmull(ks, ps, f):
    ks = np.array(ks, float); ps = np.array(ps, float)
    if f <= ks[0]: return ps[0].copy()
    if f >= ks[-1]: return ps[-1].copy()
    k = int(np.clip(np.searchsorted(ks, f) - 1, 0, len(ks) - 2)); t0, t1 = ks[k], ks[k + 1]; u = (f - t0) / (t1 - t0)
    p0 = ps[max(k - 1, 0)]; p1 = ps[k]; p2 = ps[k + 1]; p3 = ps[min(k + 2, len(ps) - 1)]
    m1 = (p2 - p0) / max(ks[k + 1] - ks[max(k - 1, 0)], 1) * (t1 - t0); m2 = (p3 - p1) / max(ks[min(k + 2, len(ks) - 1)] - ks[k], 1) * (t1 - t0)
    h00 = 2 * u ** 3 - 3 * u ** 2 + 1; h10 = u ** 3 - 2 * u ** 2 + u; h01 = -2 * u ** 3 + 3 * u ** 2; h11 = u ** 3 - u ** 2
    return h00 * p1 + h10 * m1 + h01 * p2 + h11 * m2
def quat(R):
    m = R; t = np.trace(m)
    if t > 0: s = 0.5 / math.sqrt(t + 1); q = [0.25 / s, (m[2][1] - m[1][2]) * s, (m[0][2] - m[2][0]) * s, (m[1][0] - m[0][1]) * s]
    else:
        i = int(np.argmax([m[0][0], m[1][1], m[2][2]]))
        if i == 0: s = 2 * math.sqrt(1 + m[0][0] - m[1][1] - m[2][2]); q = [(m[2][1] - m[1][2]) / s, 0.25 * s, (m[0][1] + m[1][0]) / s, (m[0][2] + m[2][0]) / s]
        elif i == 1: s = 2 * math.sqrt(1 + m[1][1] - m[0][0] - m[2][2]); q = [(m[0][2] - m[2][0]) / s, (m[0][1] + m[1][0]) / s, 0.25 * s, (m[1][2] + m[2][1]) / s]
        else: s = 2 * math.sqrt(1 + m[2][2] - m[0][0] - m[1][1]); q = [(m[1][0] - m[0][1]) / s, (m[0][2] + m[2][0]) / s, (m[1][2] + m[2][1]) / s, 0.25 * s]
    q = np.array(q); return q / np.linalg.norm(q)
def qmat(q):
    w, x, y, z = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)], [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)], [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
def slerp(Ra, Rb, u):
    qa, qb = quat(Ra), quat(Rb)
    if qa @ qb < 0: qb = -qb
    d = min(1.0, float(qa @ qb)); om = math.acos(d)
    if om < 1e-6: return Ra
    q = (math.sin((1 - u) * om) * qa + math.sin(u * om) * qb) / math.sin(om); return qmat(q / np.linalg.norm(q))
def raw(f, model):
    """该模型里 f 附近的 SfM 位姿（缺帧时插值）"""
    n = f"f{f:05d}.jpg"
    if n in CAMS and CAMS[n][0] == model: return CAMS[n][1], CAMS[n][2]
    ks = [int(k[1:6]) for k in CAMS if CAMS[k][0] == model]; ks.sort()
    i = np.searchsorted(ks, f); a = ks[max(i - 1, 0)]; b = ks[min(i, len(ks) - 1)]
    Ca, Ra = CAMS[f"f{a:05d}.jpg"][1:3]; Cb, Rb = CAMS[f"f{b:05d}.jpg"][1:3]
    u = 0 if b == a else (f - a) / (b - a)
    return Ca + (Cb - Ca) * u, slerp(Ra, Rb, u)
# ---------------- 开场 A ----------------
def A1(f):
    th, tx, ty, tz, ls = XA1; C, R = raw(f, 0)
    return math.exp(ls) * (Rz_cw(th) @ (C - PIVA1)) + np.array([tx, ty, tz]), R @ Rz_cw(th).T
REF3 = CAMS["f02373.jpg"][1]; OLD3 = np.array(cam2.cam(2376)[0])
def A3(f):
    C, R = raw(f, 0); thp = XA1[0]
    thr = float(np.interp(f, [2250, 2373], [XA1[0], 45.0]))
    return OLD3 + 3.24 * (Rz_cw(thp) @ (C - REF3)), R @ Rz_cw(thr).T
STAIR = [(1248, None), (1296, (-3.0, -18.9, 1.7)), (1344, (-3.3, -19.6, 2.3)), (1368, (-3.4, -20.0, 3.4)), (1440, (-3.4, -21.2, 6.2)), (1512, (-3.6, -22.0, 7.8)), (1536, (-4.15, -22.1, 8.45)), (1566, None)]
def A(f):
    if f < 336: C, _ = A1(336); _, R = A1(f); return C, R
    if f <= 1248:
        C, R = A1(f); C = C + np.array([0.0, float(np.interp(f, [1056, 1152], [0.0, 2.0])), 0.0])
        return C, R @ Rz_cw(float(np.interp(f, [1100, 1152, 1176, 1200, 1248], [0, 12, 0, -10, -5]))).T
    if f < 1566:
        ks = [k for k, p in STAIR]; ps = [np.array(p) if p is not None else (A1(k)[0] + np.array([0, 2.0, 0]) if k == 1248 else A3(k)[0]) for k, p in STAIR]
        R = A1(f)[1] @ Rz_cw(float(np.interp(f, [1248, 1296, 1344, 1400, 1440], [-5, 10, 15, 8, 0]))).T; return catmull(ks, ps, f), R
    C, R = A3(f); C = C.copy(); C[2] -= 0.3 * float(np.interp(f, [1960, 1990, 2050, 2080], [0, 1, 1, 0])); return C, R
# ---------------- 05:30 以后 C ----------------
TH1 = [(5991, 54), (6380, 57), (6408, 40), (6480, 45), (6552, 79), (6624, 76), (6696, 60), (6768, 60), (6840, 78), (6880, 40), (6900, 23), (6960, 0), (6990, -8), (7056, -20), (7128, -16), (7200, -4), (7260, 3), (7359, 24)]
TH0 = [(7362, 38), (7650, 38), (7899, 45), (8100, 65), (8150, 80), (8360, 82), (8500, 78), (8900, 78), (9200, 70), (9768, 70)]
def thC(f):
    T = TH1 if f <= 7360 else TH0; return float(np.interp(f, [a for a, b in T], [b for a, b in T]))
POSK = [(5991, None), (6150, (5.27, -9.0, 1.7)), (6258, (1.2, -8.9, 1.5)), (6339, (1.0, -8.4, 1.4)), (6420, (3.6, -7.0, 1.5)), (6498, (4.6, -6.0, 0.75)),
        (6579, (5.0, -8.2, 1.3)), (6660, (4.6, -12.5, 1.3)), (6738, (4.3, -15.2, 1.3)), (6819, (2.7, -18.2, 1.45)), (6900, (2.0, -19.0, 1.6)),
        (6990, (0.0, -17.0, 1.4)), (7056, (-0.2, -16.7, 1.4)), (7128, (-0.4, -16.3, 1.45)), (7200, (-0.3, -15.8, 1.5)), (7260, (0.9, -11.6, 1.6)), (7350, (1.0, -11.2, 1.6)),
        (7440, (0.3, -8.7, 1.5)), (7530, (0.4, -6.4, 1.3)), (7620, (0.4, 3.5, 1.4)), (7710, (0.6, 5.0, 1.4)), (7800, (-0.5, 1.4, 1.5)),
        (7899, (-1.6, -5.5, 6.0)), (7989, (-2.4, -10.5, 8.3)), (8100, (-2.4, -14.5, 9.6)), (8199, (-2.8, -16.8, 9.9)), (8298, (-3.1, -18.4, 9.5)),
        (8400, (-2.4, -24.0, 5.0)), (8499, (-1.5, -28.5, 2.6)), (8598, (-1.3, -29.0, 1.7)), (8800, (-1.4, -29.3, 1.8)), (8856, (-1.6, -27.4, 5.6)), (8900, (-1.6, -27.0, 6.0)), (9000, (-1.8, -27.2, 6.0)), (9072, (-2.5, -28.4, 5.2)), (9144, (-2.7, -27.6, 4.9)),
        (9234, (-2.8, -24.0, 4.5)), (9342, (-2.6, -13.5, 4.0)), (9447, (-1.5, 0.3, 1.35)), (9543, (-1.52, 0.53, 1.14)), (9732, (-1.2, -1.8, 1.4)), (9765, (-1.2, -2.2, 1.4))]
def _posC(f):
    return catmull([k for k, p in POSK], [np.array(p) if p is not None else np.array(cam2.cam(5988)[0]) for k, p in POSK], f)
def C_part(f):
    model = 1 if f <= 7359 else 0
    if f > 9732: model = 0
    _, R = raw(min(f, 9732), model)
    return _posC(f), R @ Rz_cw(thC(f)).T
PITCH = [(8790, None), (8840, -30.0), (9010, -30.0), (9072, -25.0), (9144, -22.0), (9220, None)]
def _pitch_fix(f, R):
    ks = [k for k, p in PITCH]
    if not (ks[0] < f < ks[-1]): return R
    cur = pitch_of(R)
    vals = [cur if p is None else p for k, p in PITCH]
    d = math.radians(float(np.interp(f, ks, vals)) - cur)
    c_, s_ = math.cos(d), math.sin(d); Rx = np.array([[1, 0, 0], [0, c_, s_], [0, -s_, c_]])
    R2 = Rx @ R
    if abs(pitch_of(R2) - float(np.interp(f, ks, vals))) > abs(pitch_of(Rx.T @ R) - float(np.interp(f, ks, vals))): R2 = Rx.T @ R
    return R2
def cam(f):
    if 8790 < f < 9220:
        C, R = C_part(f); return C, _pitch_fix(f, R)
    if f <= 2373: return A(f)
    if 3300 < f < 3340:            # seg2 → 参照段交接处高度跳变：高度线性过渡（03:38.6 机位已在车厢里）
        C, R = cam2.cam(f); C = np.array(C, float)
        za = cam2.cam(3300)[0][2]; zb = cam2.cam(3340)[0][2]; C[2] = float(np.interp(f, [3300, 3312, 3340], [za, min(za, 1.15), zb])); return C, R
    if 3140 <= f <= 3306:          # 03:31–03:38 机位低一点、略向西：车顶在画面下方（原片）
        C, R = cam2.cam(f); C = np.array(C, float); w = float(np.interp(f, [3140, 3160, 3290, 3306], [0, 1, 1, 0]))
        C[2] -= 0.3 * w; return C, R @ Rz_cw(13 * w).T
    if f <= 5988: C, R = cam2.cam(f); return np.array(C, float), R
    return C_part(f)
def M_from_cv(R): return np.column_stack([R[0], -R[1], -R[2]])
