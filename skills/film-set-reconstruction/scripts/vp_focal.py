# ==== 《大事件》(2004) 开场长镜头项目里的实际代码，原样保留作参考 ====
# 里面的路径（/tmp/claude-0/...、/mnt/user-data/...）、坐标、车辆尺寸、帧号区间都是那部片子的，换片时逐项改。
# 约定：机位 R 为 世界→相机（OpenCV：x 右 y 下 z 前），C 为相机中心；画面 1280×554 时 CX=640 CY=277、HFOV=42°。
# 由消失点估计焦距：图像空间里先找消失点（与焦距无关），再用两两正交的有限消失点算 f² = -(va-p)·(vb-p)
import cv2, numpy as np, glob, json, sys
rng = np.random.default_rng(1)
lsd = cv2.createLineSegmentDetector(cv2.LSD_REFINE_STD)
cx, cy = 640.0, 277.0
def vps(L, ln, k=3, iters=2500, thr=np.radians(1.2)):
    mid = (L[:, :2] + L[:, 2:]) / 2; d = L[:, 2:] - L[:, :2]; d /= np.linalg.norm(d, axis=1)[:, None]
    hom = np.cross(np.c_[L[:, :2], np.ones(len(L))], np.c_[L[:, 2:], np.ones(len(L))])
    alive = np.ones(len(L), bool); out = []
    for _ in range(k):
        idx = np.where(alive)[0]
        if len(idx) < 10: break
        best = None
        for it in range(iters):
            i, j = rng.choice(idx, 2, replace=False)
            v = np.cross(hom[i], hom[j])
            if abs(v[2]) < 1e-9 * np.linalg.norm(v):
                dirv = v[:2] / np.linalg.norm(v[:2]); cosang = np.abs(d @ dirv)
            else:
                p = v[:2] / v[2]; w = p - mid; w /= np.linalg.norm(w, axis=1)[:, None] + 1e-12; cosang = np.abs((d * w).sum(1))
            inl = alive & (cosang > np.cos(thr)); s = ln[inl].sum()
            if best is None or s > best[0]: best = (s, v, inl)
        s, v, inl = best
        A = hom[inl] / np.linalg.norm(hom[inl][:, :2], axis=1)[:, None]
        _, _, vt = np.linalg.svd(A * ln[inl][:, None]); v = vt[2]
        out.append((float(s), v, int(inl.sum()))); alive &= ~inl
    return out
R = {}
files = sorted(glob.glob(sys.argv[1] + "/f*.jpg"))
for fn in files:
    g = cv2.imread(fn, 0); L = lsd.detect(g)[0]
    if L is None: continue
    L = L.reshape(-1, 4).astype(float); ln = np.hypot(L[:, 2] - L[:, 0], L[:, 3] - L[:, 1]); m = ln > 30; L, ln = L[m], ln[m]
    if len(L) < 30: continue
    V = vps(L, ln)
    fs = []; info = []
    for a in range(len(V)):
        va = V[a][1]
        info.append((round(V[a][0]), V[a][2], (va[:2] / va[2]).round(0).tolist() if abs(va[2]) > 1e-6 * np.linalg.norm(va) else "inf"))
        for b in range(a + 1, len(V)):
            vb = V[b][1]
            if abs(va[2]) < 1e-6 * np.linalg.norm(va) or abs(vb[2]) < 1e-6 * np.linalg.norm(vb): continue
            pa = va[:2] / va[2] - [cx, cy]; pb = vb[:2] / vb[2] - [cx, cy]
            f2 = -(pa @ pb)
            if f2 > 0 and min(V[a][2], V[b][2]) >= 8:
                f = np.sqrt(f2); fs.append((round(float(np.degrees(2 * np.arctan(cx / f))), 1), a, b))
    name = fn.split("/")[-1]
    R[name] = {"vps": info, "hfov": fs}
    print(name, info, fs, flush=True)
json.dump(R, open(sys.argv[2], "w"))
