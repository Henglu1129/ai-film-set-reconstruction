# ==== 《大事件》(2004) 开场长镜头项目里的实际代码，原样保留作参考 ====
# 里面的路径（/tmp/claude-0/...、/mnt/user-data/...）、坐标、车辆尺寸、帧号区间都是那部片子的，换片时逐项改。
# 约定：机位 R 为 世界→相机（OpenCV：x 右 y 下 z 前），C 为相机中心；画面 1280×554 时 CX=640 CY=277、HFOV=42°。
# 人物骨骼：为 Rodin 人物网格建立统一比例的骨架与蒙皮权重，并提供姿态求解
# 约定：人物面朝 +Y，Z 向上，原点在脚底中心；解剖学左侧在 -X。
import bpy, math
import numpy as np
from mathutils import Vector, Quaternion, Matrix

# 骨骼：名称 → (头, 尾, 父)，坐标为身高的比例
BONES = {
    "hips":       ((0, 0, 0.53), (0, 0, 0.60), None),
    "spine":      ((0, 0, 0.60), (0, 0, 0.72), "hips"),
    "chest":      ((0, 0, 0.72), (0, 0, 0.835), "spine"),
    "neck":       ((0, 0, 0.835), (0, 0, 0.885), "chest"),
    "head":       ((0, 0, 0.885), (0, 0.01, 1.0), "neck"),
}
for side, sx in (("L", -1), ("R", 1)):
    BONES.update({
        f"shoulder.{side}":  ((0.02 * sx, 0, 0.815), (0.115 * sx, 0, 0.815), "chest"),
        f"upper_arm.{side}": ((0.118 * sx, 0, 0.812), (0.142 * sx, 0, 0.628), f"shoulder.{side}"),
        f"forearm.{side}":   ((0.142 * sx, 0, 0.628), (0.150 * sx, 0.01, 0.475), f"upper_arm.{side}"),
        f"hand.{side}":      ((0.150 * sx, 0.01, 0.475), (0.150 * sx, 0.015, 0.40), f"forearm.{side}"),
        f"thigh.{side}":     ((0.056 * sx, 0, 0.52), (0.058 * sx, 0.005, 0.285), "hips"),
        f"shin.{side}":      ((0.058 * sx, 0.005, 0.285), (0.060 * sx, -0.005, 0.048), f"thigh.{side}"),
        f"foot.{side}":      ((0.060 * sx, -0.005, 0.048), (0.062 * sx, 0.085, 0.01), f"shin.{side}"),
    })
ORDER = ["hips", "spine", "chest", "neck", "head"] + [f"{b}.{s}" for s in "LR" for b in ("shoulder", "upper_arm", "forearm", "hand", "thigh", "shin", "foot")]

def _seg_dist(P, a, b):
    ab = b - a; t = np.clip(((P - a) @ ab) / max(ab @ ab, 1e-9), 0, 1)
    return np.linalg.norm(P - (a + np.outer(t, ab)), axis=1)

def skin_weights(mesh, H):
    """为网格写入按骨骼命名的顶点组（最近骨段 + 解剖区域约束）"""
    n = len(mesh.vertices); co = np.empty(n * 3, np.float32); mesh.vertices.foreach_get("co", co); P = co.reshape(-1, 3).astype(np.float64)
    x, y, z = P[:, 0] / H, P[:, 1] / H, P[:, 2] / H
    D = {}
    for b, (h, t, _) in BONES.items():
        D[b] = _seg_dist(P, np.array(h) * H, np.array(t) * H) / H
    # 区域约束：手臂只取躯干外侧、腿只取胯下，左右分开
    big = 9.0
    for s, sg in (("L", -1), ("R", 1)):
        side_ok = (sg * x) > 0.0
        thr = np.where(z > 0.62, 0.110, np.where(z < 0.54, 0.128, 0.128 - (z - 0.54) / 0.08 * 0.018))
        arm_zone = ((sg * x) > thr) & (z > 0.36) & (z < 0.86)
        for b in ("upper_arm", "forearm", "hand"):
            D[f"{b}.{s}"] = np.where(arm_zone & side_ok, D[f"{b}.{s}"], big)
        sh = (sg * x > 0.03) & (z > 0.74) & (z < 0.9)
        D[f"shoulder.{s}"] = np.where(sh, D[f"shoulder.{s}"], big)
        leg_zone = (z < 0.56) & ((sg * x) > -0.012) & ~arm_zone
        for b in ("thigh", "shin", "foot"):
            D[f"{b}.{s}"] = np.where(leg_zone, D[f"{b}.{s}"], big)
    for b in ("hips", "spine", "chest", "neck", "head"):
        armish = ((np.abs(x) > 0.125) & (z > 0.38) & (z < 0.80))
        D[b] = np.where(armish, D[b] + 0.05, D[b])
    # 手掌附近的顶点只跟手走
    for s, sg in (("L", -1), ("R", 1)):
        hd = _seg_dist(P, np.array(BONES[f"hand.{s}"][0]) * H, np.array(BONES[f"hand.{s}"][1]) * H) / H
        near = (hd < 0.05) & ((sg * x) > 0.10)
        for b in list(D):
            if b != f"hand.{s}" and b != f"forearm.{s}": D[b] = np.where(near, 9.0, D[b])
    names = list(BONES); M = np.stack([D[b] for b in names], 1)
    W = 1.0 / np.maximum(M, 0.004) ** 8
    W[M > 5] = 0
    # 只保留每个顶点权重最大的 2 个
    idx = np.argsort(-W, 1)[:, :2]; Wk = np.take_along_axis(W, idx, 1); Wk /= Wk.sum(1, keepdims=True) + 1e-12
    for vg in list(mesh.vertices[0:0]): pass
    return names, idx, Wk

ARM_SET = {f"{b}.{s}" for b in ("upper_arm", "forearm", "hand") for s in "LR"}
BODY_SET = {"hips", "spine"} | {f"{b}.{s}" for b in ("thigh", "shin", "foot") for s in "LR"}
def cut_bridges(mesh, names, idx):
    """删除同时连到手臂和躯干/腿的面（Rodin 网格里手贴着大腿处常被缝在一起）"""
    import bmesh
    dom = idx[:, 0]; arm_ids = {i for i, n in enumerate(names) if n in ARM_SET}; body_ids = {i for i, n in enumerate(names) if n in BODY_SET}
    bm = bmesh.new(); bm.from_mesh(mesh); bm.verts.ensure_lookup_table()
    bad = []
    for f in bm.faces:
        ds = {int(dom[v.index]) for v in f.verts}
        if ds & arm_ids and ds & body_ids: bad.append(f)
        else:
            # 拉得很长的面（手和腿之间的长三角）
            vs = [v.co for v in f.verts]; L = max((vs[i] - vs[i - 1]).length for i in range(len(vs)))
            if L > 0.09 and ds & arm_ids: bad.append(f)
    bmesh.ops.delete(bm, geom=bad, context="FACES_ONLY")
    bm.to_mesh(mesh); bm.free()
    return len(bad)

def apply_weights(obj, H):
    names, idx, Wk = skin_weights(obj.data, H)
    obj["cut_faces"] = cut_bridges(obj.data, names, idx)
    obj.vertex_groups.clear()
    vgs = [obj.vertex_groups.new(name=nm) for nm in names]
    for bi, vg in enumerate(vgs):
        sel = np.where((idx == bi) & (Wk > 0.01))
        for v, k in zip(*sel):
            vg.add([int(v)], float(Wk[v, k]), "REPLACE")

def build_armature(name, H, scene):
    arm = bpy.data.armatures.get(name)
    if arm: return arm
    arm = bpy.data.armatures.new(name)
    ob = bpy.data.objects.new("_tmp_" + name, arm); scene.collection.objects.link(ob)
    vl = bpy.context.view_layer
    prev = vl.objects.active
    vl.objects.active = ob; ob.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    for b in ORDER:
        h, t, p = BONES[b]
        eb = arm.edit_bones.new(b); eb.head = Vector(h) * H; eb.tail = Vector(t) * H
        if p: eb.parent = arm.edit_bones[p]; eb.use_connect = False
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.data.objects.remove(ob, do_unlink=True)
    vl.objects.active = prev
    arm.use_fake_user = True
    return arm

# ---------------- 姿态 ----------------
REST = {b: (Vector(BONES[b][1]) - Vector(BONES[b][0])).normalized() for b in BONES}

def rot_between(a, b):
    a = a.normalized(); b = b.normalized(); c = a.cross(b); d = a.dot(b)
    if d < -0.9999:
        ax = a.orthogonal().normalized(); return Quaternion(ax, math.pi)
    q = Quaternion((1 + d, c.x, c.y, c.z)); q.normalize(); return q

class Solver:
    """把目标骨骼方向（物体局部空间）转换为各骨骼的 pose 四元数"""
    def __init__(self, arm):
        self.rest = {b.name: b.matrix_local.to_quaternion() for b in arm.bones}
        self.parent = {b.name: (b.parent.name if b.parent else None) for b in arm.bones}
    def solve(self, targets):
        posed = {}; out = {}
        for b in ORDER:
            p = self.parent[b]
            Rr_b = self.rest[b]
            if p is None:
                C = Rr_b
            else:
                C = posed[p] @ self.rest[p].inverted() @ Rr_b
            cur = C @ Vector((0, 1, 0))
            D = rot_between(cur, targets[b]) if b in targets else Quaternion()
            posed[b] = D @ C
            out[b] = C.inverted() @ D @ C
        return out

def default_dirs():
    return {b: REST[b].copy() for b in BONES}

def proc_pose(kind, phase=0.0, amp=1.0):
    """程序化姿态：stand / walk / run / crouch / kneel / sit / lie / aim / aim2 / raise / jump"""
    d = default_dirs()
    def rx(v, deg):  # 绕 X 轴旋转（前后摆）
        return Quaternion((1, 0, 0), math.radians(deg)) @ v
    s = math.sin(phase)
    if kind in ("walk", "run"):
        A = (24 if kind == "walk" else 42) * amp
        for side, sg in (("L", 1), ("R", -1)):
            d[f"thigh.{side}"] = rx(REST[f"thigh.{side}"], -A * s * sg)
            knee = max(0, (A * 1.1) * math.sin(phase + (0.9 if sg > 0 else 0.9 + math.pi)))
            d[f"shin.{side}"] = rx(d[f"thigh.{side}"], -knee)
            d[f"upper_arm.{side}"] = rx(REST[f"upper_arm.{side}"], A * 0.6 * s * sg)
            d[f"forearm.{side}"] = rx(d[f"upper_arm.{side}"], (20 if kind == "walk" else 70))
        if kind == "run":
            d["spine"] = rx(REST["spine"], -12); d["chest"] = rx(REST["chest"], -8)
    elif kind in ("crouch", "kneel"):
        d["spine"] = rx(REST["spine"], -25); d["chest"] = rx(REST["chest"], -10)
        if kind == "crouch":
            for side in "LR":
                d[f"thigh.{side}"] = rx(REST[f"thigh.{side}"], 100); d[f"shin.{side}"] = rx(REST[f"shin.{side}"], -20)
        else:
            d["thigh.R"] = rx(REST["thigh.R"], 90); d["shin.R"] = rx(REST["shin.R"], 5)
            d["thigh.L"] = rx(REST["thigh.L"], 5); d["shin.L"] = rx(REST["shin.L"], -90)
    elif kind == "sit":
        for side in "LR":
            d[f"thigh.{side}"] = rx(REST[f"thigh.{side}"], 88); d[f"shin.{side}"] = rx(REST[f"shin.{side}"], 5)
            d[f"upper_arm.{side}"] = rx(REST[f"upper_arm.{side}"], 35); d[f"forearm.{side}"] = rx(REST[f"forearm.{side}"], 75)
    elif kind == "jump":
        for side in "LR":
            d[f"thigh.{side}"] = rx(REST[f"thigh.{side}"], 55); d[f"shin.{side}"] = rx(d[f"thigh.{side}"], -80)
            d[f"upper_arm.{side}"] = rx(REST[f"upper_arm.{side}"], 110)
    if kind in ("aim", "aim2"):  # 双手持枪平举 / 单手
        fwd = Vector((0, 1, -0.05)).normalized()
        d["upper_arm.R"] = (fwd + Vector((-0.12, 0, 0))).normalized(); d["forearm.R"] = (fwd + Vector((-0.2, 0, 0))).normalized()
        if kind == "aim":
            d["upper_arm.L"] = (fwd + Vector((0.25, 0, -0.1))).normalized(); d["forearm.L"] = (fwd + Vector((0.45, 0, 0))).normalized()
    if kind == "raise":
        for side, sx in (("L", -1), ("R", 1)):
            d[f"upper_arm.{side}"] = Vector((0.35 * sx, 0.1, 0.93)).normalized(); d[f"forearm.{side}"] = Vector((0.15 * sx, 0.05, 1)).normalized()
    if kind == "lie":
        pass  # 整体由物体旋转实现
    return d

def dirs_from_mediapipe(w3, vis, basis, fallback):
    """w3：33×3 世界关键点（相机轴：x 右、y 下、z 远离相机）；basis：(r,u,f) 世界向量；
    返回 (方向字典[世界空间], 朝向向量)"""
    r, u, f = basis
    P = [r * p[0] - u * p[1] + f * p[2] for p in w3]
    V = vis
    def ok(*ids): return all(V[i] > 0.55 for i in ids)
    out = {}
    hipL, hipR, shL, shR = P[23], P[24], P[11], P[12]
    hc = (hipL + hipR) / 2; sc = (shL + shR) / 2
    if ok(11, 12, 23, 24):
        up = (sc - hc).normalized(); out["spine"] = up; out["chest"] = up
    if ok(0, 11, 12): out["neck"] = (P[0] - sc).normalized(); out["head"] = out["neck"]
    for side, (s, e, w, h, k, a) in (("L", (11, 13, 15, 23, 25, 27)), ("R", (12, 14, 16, 24, 26, 28))):
        if ok(s, e): out[f"upper_arm.{side}"] = (P[e] - P[s]).normalized()
        if ok(e, w): out[f"forearm.{side}"] = (P[w] - P[e]).normalized()
        if ok(h, k): out[f"thigh.{side}"] = (P[k] - P[h]).normalized()
        if ok(k, a): out[f"shin.{side}"] = (P[a] - P[k]).normalized()
    facing = None
    rr = hipR - hipL if ok(23, 24) else (shR - shL if ok(11, 12) else None)
    if rr is not None:
        rr.z = 0
        if rr.length > 1e-4: facing = Vector((0, 0, 1)).cross(rr.normalized()).normalized()
    return out, facing

LEN = {"thigh": 0.235, "shin": 0.237}
def ground_drop(d, H, kind=None):
    """按腿部方向计算脚/膝着地需要的下沉量（米，负数为下沉）"""
    lows = []
    for side in "LR":
        t = d.get(f"thigh.{side}", REST[f"thigh.{side}"]); sh = d.get(f"shin.{side}", REST[f"shin.{side}"])
        knee = 0.52 + LEN["thigh"] * t.z; ank = knee + LEN["shin"] * sh.z
        lows += [ank - 0.045, knee - 0.035]
    return -min(lows) * H
