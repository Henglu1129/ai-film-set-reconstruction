# 《周处除三害》灵修堂 —— 拍摄现场还原（俯视方案图）Blender 构建模块
# 用法（Blender 内）：import sys; sys.path.insert(0, SCRIPTS); import lxt_build as L; L.build_all()
import bpy, bmesh, math, json, os
from mathutils import Vector, Matrix

PROJ = os.environ.get("LXT_PROJ", "/path/to/项目")   # 项目根目录（含 work/plan/plan_data.json）
DATA = PROJ + "/work/plan/plan_data.json"
SCN = "灵修堂还原"
D = None

# ---------- 基础工具 ----------
def hex2rgb(h):
    h = h.lstrip('#'); c = [int(h[i:i+2], 16) / 255 for i in (0, 2, 4)]
    return [((v + 0.055) / 1.055) ** 2.4 if v > 0.04045 else v / 12.92 for v in c]

def mat(name, col, emit=0.0, alpha=1.0, rough=0.7, metal=0.0):
    key = "lx_" + name
    m = bpy.data.materials.get(key) or bpy.data.materials.new(key)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    c = hex2rgb(col) if isinstance(col, str) else list(col)
    b.inputs["Base Color"].default_value = (*c, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    b.inputs["Emission Color"].default_value = (*c, 1)
    b.inputs["Emission Strength"].default_value = emit
    b.inputs["Alpha"].default_value = alpha
    try:
        m.surface_render_method = 'BLENDED' if alpha < 1 else 'DITHERED'
    except Exception:
        pass
    m.diffuse_color = (*c, alpha)
    return m

def coll(name, parent=None):
    c = bpy.data.collections.get(name)
    if not c:
        c = bpy.data.collections.new(name)
        (parent or bpy.context.scene.collection).children.link(c)
    return c

def obj_from_bm(name, bm, m, col):
    me = bpy.data.meshes.new("lx_" + name)
    bm.to_mesh(me); bm.free()
    if m: me.materials.append(m)
    o = bpy.data.objects.new(name, me); col.objects.link(o)
    return o

def bm_box(bm, x0, y0, z0, x1, y1, z1):
    M = Matrix.Translation(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)) @ Matrix.Diagonal((abs(x1 - x0), abs(y1 - y0), abs(z1 - z0), 1))
    bmesh.ops.create_cube(bm, size=1.0, matrix=M)

def bm_cyl(bm, x, y, z0, h, r, seg=20, sx=1.0, sy=1.0, r2=None):
    M = Matrix.Translation((x, y, z0 + h / 2)) @ Matrix.Diagonal((sx, sy, 1, 1))
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg, radius1=r, radius2=r if r2 is None else r2, depth=h, matrix=M)

def bm_sph(bm, x, y, z, r, seg=14):
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=max(6, seg // 2), radius=r, matrix=Matrix.Translation((x, y, z)))

def bm_seg(bm, a, b, r, seg=10):
    a = Vector(a); b = Vector(b); d = b - a; L = d.length
    q = d.to_track_quat('Z', 'Y')
    M = Matrix.Translation((a + b) / 2) @ q.to_matrix().to_4x4()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg, radius1=r, radius2=r, depth=L, matrix=M)

def box(name, x0, y0, z0, x1, y1, z1, m, col):
    bm = bmesh.new(); bm_box(bm, x0, y0, z0, x1, y1, z1); return obj_from_bm(name, bm, m, col)

def cyl(name, x, y, z0, h, r, m, col, seg=24, sx=1, sy=1, r2=None):
    bm = bmesh.new(); bm_cyl(bm, x, y, z0, h, r, seg, sx, sy, r2); return obj_from_bm(name, bm, m, col)

# ---------- 场景 ----------
def reset_scene():
    sc = bpy.data.scenes.get(SCN) or bpy.data.scenes.new(SCN)
    bpy.context.window.scene = sc
    root = sc.collection
    for c in list(root.children):
        for o in list(c.all_objects):
            bpy.data.objects.remove(o, do_unlink=True)
        for cc in list(c.children_recursive):
            bpy.data.collections.remove(cc)
        bpy.data.collections.remove(c)
    for o in list(root.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for me in list(bpy.data.meshes):
        if me.name.startswith("lx_") and me.users == 0: bpy.data.meshes.remove(me)
    sc.render.engine = 'BLENDER_EEVEE'
    try: sc.eevee.taa_render_samples = 24
    except Exception: pass
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.look = 'None'
    sc.render.resolution_x, sc.render.resolution_y = 1080, 620
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = True
    w = bpy.data.worlds.get("lx_world") or bpy.data.worlds.new("lx_world")
    w.use_nodes = True
    bg = w.node_tree.nodes.get("Background")
    bg.inputs[0].default_value = (*hex2rgb("#9aa0aa"), 1); bg.inputs[1].default_value = 0.9
    sc.world = w
    sc.unit_settings.system = 'METRIC'
    return sc

def build_hall():
    C = coll("HALL")
    W0, W1, YS, YF, YN, HS = -5.2, 5.2, 0.0, 17.8, 22.6, 0.5
    WALL_H, CUT_E = 3.2, 1.0          # 剖切高度：西/南/北墙 3.2 m，东墙压低到 1.0 m 方便俯视
    floor_m = mat("floor", "#d9d4cf", rough=0.35)
    wall_m = mat("wall", "#e8c9c4", rough=0.8)
    wallcut_m = mat("wallcut", "#5c4a48", rough=0.9)
    wood_m = mat("wood", "#8a5a3c", rough=0.6)
    stage_m = mat("stage", "#9b6b4a", rough=0.6)
    red_m = mat("carpet", "#8f1d24", rough=0.9)
    curt_m = mat("curtain", "#5d1a26", rough=0.95)
    sheer_m = mat("sheer", "#fff4ef", emit=0.6, alpha=0.55)
    glass_m = mat("glass", "#cfe3ea", alpha=0.45, rough=0.2)
    black_m = mat("black", "#141414", rough=1.0)
    white_m = mat("whiteprop", "#f3efe9")
    cush_m = mat("cushion", "#d49a55", rough=0.9)
    port_m = mat("portrait", "#e8d6c0", emit=0.2)
    frame_m = mat("frame", "#b39a62", metal=0.6, rough=0.4)
    # 地面（含门外走廊）与 1 m 地砖缝
    bm = bmesh.new(); bm_box(bm, W0 - 0.3, -6.5, -0.12, W1 + 0.3, YN + 0.3, 0.0); obj_from_bm("floor", bm, floor_m, C)
    grid_m = mat("grid", "#b9b2ab", rough=0.6)
    bm = bmesh.new()
    for x in range(-5, 6): bm_box(bm, x - 0.006, 0.0, 0.0, x + 0.006, YF, 0.004)
    for y in range(1, 18): bm_box(bm, W0, y - 0.006, 0.0, W1, y + 0.006, 0.004)
    obj_from_bm("floor_grid", bm, grid_m, C)
    # 墙
    t = 0.22
    bm = bmesh.new()
    bm_box(bm, W0 - t, -t, 0, W0, YN + t, WALL_H)                       # 西墙
    xc, half = 0.14, 1.73
    bm_box(bm, W0 - t, -t, 0, xc - half, 0, WALL_H)                    # 南墙（门两侧）
    bm_box(bm, xc + half, -t, 0, W1 + t, 0, WALL_H)
    bm_box(bm, xc - half, -t, 2.9, xc + half, 0, WALL_H)               # 门楣
    bm_box(bm, W0 - t, YN, 0, W1 + t, YN + t, WALL_H + 0.6)            # 北墙（台后）
    obj_from_bm("walls", bm, wall_m, C)
    bm = bmesh.new(); bm_box(bm, W1, -t, 0, W1 + t, YN + t, CUT_E); obj_from_bm("wall_east_cut", bm, wall_m, C)
    # 墙体剖切面描边（俯视时看清墙厚）
    bm = bmesh.new()
    bm_box(bm, W0 - t, -t, WALL_H, W0, YN + t, WALL_H + 0.01)
    bm_box(bm, W0 - t, -t, WALL_H, xc - half, 0, WALL_H + 0.01); bm_box(bm, xc + half, -t, WALL_H, W1 + t, 0, WALL_H + 0.01)
    bm_box(bm, W1, -t, CUT_E, W1 + t, YN + t, CUT_E + 0.01)
    obj_from_bm("wall_cap", bm, wallcut_m, C)
    # 门外走廊墙 + 楼梯示意
    bm = bmesh.new()
    bm_box(bm, -2.4, -6.5, 0, -2.2, -t, 2.0); bm_box(bm, 6.0, -6.5, 0, 6.2, -t, 2.0)
    obj_from_bm("corridor_walls", bm, mat("corridor", "#9a9590"), C)
    bm = bmesh.new()
    for i in range(7): bm_box(bm, 2.4, -6.4 + i * 0.32, 0, 5.8, -6.4 + (i + 1) * 0.32, 0.17 * (7 - i))
    obj_from_bm("stairs", bm, mat("stairs", "#8c8580"), C)
    # 侧墙壁柱 + 窗（纱帘发亮）
    piers = [1.6, 4.8, 8.0, 11.2, 14.4]
    bm = bmesh.new()
    for y in piers:
        bm_box(bm, W0, y - 0.35, 0, W0 + 0.28, y + 0.35, WALL_H)
    obj_from_bm("piers_W", bm, wall_m, C)
    bm = bmesh.new()
    for y in piers: bm_box(bm, W1 - 0.28, y - 0.35, 0, W1, y + 0.35, CUT_E + 0.02)
    obj_from_bm("piers_E", bm, wall_m, C)
    bm = bmesh.new()
    for y in (3.2, 6.4, 9.6, 12.8):
        bm_box(bm, W0 + 0.02, y - 1.2, 0.05, W0 + 0.08, y + 1.2, WALL_H - 0.1)
    obj_from_bm("sheers_W", bm, sheer_m, C)
    bm = bmesh.new()
    for y in (3.2, 6.4, 9.6, 12.8):
        bm_box(bm, W1 - 0.08, y - 1.2, 0.05, W1 - 0.02, y + 1.2, CUT_E)
    obj_from_bm("sheers_E", bm, sheer_m, C)
    # 侧门（舞台两侧）
    box("sidedoor_W", W0 - 0.02, 15.74, 0, W0 + 0.05, 17.0, 2.0, wood_m, C)
    box("sidedoor_E", W1 - 0.05, 15.98, 0, W1 + 0.02, 17.25, CUT_E, wood_m, C)
    # 大门：门框、磨砂玻璃侧扇、门洞黑幕
    bm = bmesh.new()
    for x in (xc - half, xc - 0.89, xc + 0.89, xc + half):
        bm_box(bm, x - 0.05, -0.12, 0, x + 0.05, 0.02, 2.9)
    bm_box(bm, xc - half, -0.12, 2.3, xc + half, 0.02, 2.4)
    obj_from_bm("door_frame", bm, wood_m, C)
    bm = bmesh.new(); bm_box(bm, xc - half + 0.05, -0.08, 0.05, xc - 0.94, -0.04, 2.3); bm_box(bm, xc + 0.94, -0.08, 0.05, xc + half - 0.05, -0.04, 2.3)
    obj_from_bm("door_glass", bm, glass_m, C)
    box("door_blackdrape", xc - 1.1, -0.45, 0, xc + 1.1, -0.4, 2.6, black_m, C)
    # 舞台
    box("stage", W0, YF, 0, W1, YN, HS, stage_m, C)
    box("stage_carpet", -2.6, 18.9, HS, 2.0, 22.3, HS + 0.01, red_m, C)
    bm = bmesh.new()
    for r, h in ((1.6, 0.13), (1.2, 0.26), (0.8, 0.39)):
        M = Matrix.Translation((-0.3, YF, h / 2))
        res = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=32, radius1=r, radius2=r, depth=h, matrix=M)
        # 切掉 y>YF 的半边（台口外的半圆台阶）
    for v in bm.verts:
        if v.co.y > YF: v.co.y = YF
    obj_from_bm("stage_steps", bm, wood_m, C)
    # 台后幕布、画像
    bm = bmesh.new()
    for x0, x1 in ((-4.3, -1.7), (1.0, 3.6), (-5.2, -4.9), (4.9, 5.2)):
        bm_box(bm, x0, YN - 0.12, HS, x1, YN - 0.02, 3.6)
    obj_from_bm("stage_curtains", bm, curt_m, C)
    box("portrait_frame", -0.34 - 0.8, YN - 0.08, 0.92, -0.34 + 0.8, YN - 0.03, 3.0, frame_m, C)
    box("portrait", -0.34 - 0.73, YN - 0.1, 0.98, -0.34 + 0.73, YN - 0.07, 2.93, port_m, C)
    # 空调柜、鞋架、供桌
    box("ac_unit", 2.56, 0.2, 0, 4.24, 0.9, 2.15, white_m, C)
    bm = bmesh.new(); bm_box(bm, -4.6, 0.2, 0.0, -1.7, 0.6, 0.45); obj_from_bm("shoe_bench", bm, wood_m, C)
    bm = bmesh.new()
    for (x0, y0, x1, y1) in ((-5.0, 2.2, -4.4, 5.4), (4.4, 2.0, 5.0, 4.6), (-5.0, 13.6, -4.4, 15.4), (4.4, 13.6, 5.0, 15.6)):
        bm_box(bm, x0, y0, 0.0, x1, y1, 0.42)
    obj_from_bm("offering_tables", bm, wood_m, C)
    # 尊者的圈椅、鼓、乐器
    bm = bmesh.new(); bm_cyl(bm, -0.3, 19.05, HS, 0.45, 0.32, 20); obj_from_bm("leader_chair", bm, wood_m, C)
    bm = bmesh.new()
    bm_cyl(bm, 3.05, 21.0, HS, 0.45, 0.28, 20); bm_cyl(bm, 2.7, 21.25, HS, 0.55, 0.16); bm_cyl(bm, 3.4, 21.25, HS, 0.55, 0.16)
    bm_cyl(bm, 2.6, 20.9, HS + 0.9, 0.02, 0.22); bm_cyl(bm, 3.55, 20.9, HS + 0.95, 0.02, 0.22)
    obj_from_bm("drums", bm, mat("drum", "#a33b2b", rough=0.4), C)
    # 坐垫（地面信众）
    bm = bmesh.new()
    for p in D['people']:
        if p['kind'] == 'floor': bm_cyl(bm, p['x'], p['y'], 0.0, 0.07, 0.27, 16)
    obj_from_bm("cushions", bm, cush_m, C)

# ---------- 人物 ----------
def person_mesh(kind):
    key = "lx_m_" + kind
    if key in bpy.data.meshes: return bpy.data.meshes[key]
    bm = bmesh.new()
    if kind == 'seat':
        bm_cyl(bm, 0, 0.12, 0.0, 0.14, 0.3, 16, 1.3, 0.9)
        bm_cyl(bm, 0, -0.04, 0.12, 0.5, 0.16, 16, 1.25, 0.8)
        bm_sph(bm, 0, -0.03, 0.75, 0.105); bm_sph(bm, 0, 0.07, 0.76, 0.03)
    elif kind in ('stand', 'aim', 'crew'):
        for sx in (-0.09, 0.09): bm_cyl(bm, sx, 0, 0.0, 0.86, 0.075, 10)
        bm_cyl(bm, 0, 0, 0.85, 0.62, 0.17, 16, 1.3, 0.8)
        bm_sph(bm, 0, 0, 1.62, 0.11); bm_sph(bm, 0, 0.1, 1.63, 0.03)
        bm_seg(bm, (-0.25, 0, 1.42), (-0.27, 0.02, 0.92), 0.045)
        if kind == 'aim':
            bm_seg(bm, (0.24, 0, 1.40), (0.26, 0.66, 1.42), 0.045)
            bm_box(bm, 0.22, 0.66, 1.40, 0.30, 0.86, 1.50)
        else:
            bm_seg(bm, (0.25, 0, 1.42), (0.27, 0.02, 0.92), 0.045)
    elif kind == 'lie':
        bm_seg(bm, (0, -0.32, 0.14), (0, 0.32, 0.14), 0.15, 14)
        bm_sph(bm, 0, 0.5, 0.12, 0.11)
        for sx in (-0.09, 0.09): bm_seg(bm, (sx, -0.34, 0.08), (sx * 1.6, -1.15, 0.08), 0.075)
    me = bpy.data.meshes.new(key); bm.to_mesh(me); bm.free()
    me.materials.append(mat("skin_dummy", "#cccccc"))
    return me

CROWD_COLS = ["#efe6d8", "#e6d8c3", "#f4efe6", "#d9c7ad", "#ece2d2"]
def build_people():
    C = coll("PEOPLE")
    for k in ('seat', 'stand', 'lie', 'aim', 'crew'): person_mesh(k)
    for p in D['people']:
        o = bpy.data.objects.new("P%03d" % p['id'], person_mesh('seat')); C.objects.link(o)
        o.location = (p['x'], p['y'], 0.5 if p['kind'] in ('stage', 'band', 'singer', 'leader') else 0.0)
        o.rotation_euler = (0, 0, -math.radians(p['yaw']))
        col = CROWD_COLS[p['id'] % len(CROWD_COLS)]
        if p['kind'] == 'leader': col = "#fbf7ef"
        if p['kind'] == 'singer': col = "#ffffff"
        o.material_slots[0].link = 'OBJECT'; o.material_slots[0].material = mat("crowd_" + col, col, rough=0.8)
    ch = bpy.data.objects.new("CHEN", person_mesh('stand')); C.objects.link(ch)
    ch.material_slots[0].link = 'OBJECT'; ch.material_slots[0].material = mat("chen", "#1d2a3c", rough=0.6)
    ring = cyl("CHEN_ring", 0, 0, 0.005, 0.01, 0.55, mat("chen_ring", "#ff3b30", emit=2.0), C, 32)
    ring.parent = ch
    lr = cyl("LEADER_ring", 0, 0, 0.005, 0.01, 0.5, mat("leader_ring", "#f6c343", emit=1.5), C, 32)
    lr.parent = bpy.data.objects["P%03d" % [p for p in D['people'] if p['kind'] == 'leader'][0]['id']]

def lerp_path(t):
    K = D['chen']
    if t <= K[0][0]: return K[0][1]
    for (ta, pa), (tb, pb) in zip(K[:-1], K[1:]):
        if ta <= t <= tb:
            u = (t - ta) / max(1e-6, tb - ta); return (pa[0] + (pb[0] - pa[0]) * u, pa[1] + (pb[1] - pa[1]) * u)
    return K[-1][1]

def chen_facing(t, xy):
    # 进门/对峙：面向舞台(北)；倒数：面向北（背对门）；处决：面向前进方向；台上终章：面向南
    if t >= 417: return 180.0
    if 233 <= t < 253: return 30.0
    return 0.0

def set_people(t, setup_id=None):
    for p in D['people']:
        o = bpy.data.objects["P%03d" % p['id']]
        vis = True; kind = 'seat'
        if p['kind'] == 'floor':
            if p['fate'] == 'flee':
                if t >= p['t_leave']: vis = False
                elif t >= p['t_up']: kind = 'stand'
            else:
                if t >= p['t_kill']: kind = 'lie'
                elif t >= 318 and p.get('stand'): kind = 'stand'
        elif p['kind'] == 'singer':
            if t >= p['t_kill']: kind = 'lie'
            elif t >= p['t_stand']: kind = 'stand'
        else:
            if t >= p['t_kill']: kind = 'lie'
        o.data = person_mesh(kind)
        o.hide_render = not vis; o.hide_viewport = not vis
    xy = lerp_path(t)
    ch = bpy.data.objects["CHEN"]
    ch.location = (xy[0], xy[1], 0.5 if xy[1] > 17.8 else (0.2 if xy[1] > 17.0 else 0.0))
    ch.rotation_euler = (0, 0, -math.radians(chen_facing(t, xy)))
    aiming = (t > 150 and t < 233) or (t >= 319)
    ch.data = person_mesh('aim' if aiming else 'stand')
    return xy

# ---------- 摄影机 ----------
def cam_rot(yaw, pitch):
    y, p = math.radians(yaw), math.radians(pitch)
    f = Vector((math.sin(y) * math.cos(p), math.cos(y) * math.cos(p), math.sin(p)))
    return f.to_track_quat('-Z', 'Y').to_matrix().to_4x4()

def frustum_bm(hfov, L, aspect=2.39):
    bm = bmesh.new()
    hw = L * math.tan(math.radians(hfov / 2)); hh = hw / aspect
    v0 = bm.verts.new((0, 0, 0))
    q = [bm.verts.new((sx * hw, sy * hh, -L)) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    for i in range(4): bm.faces.new((v0, q[i], q[(i + 1) % 4]))
    bm.faces.new(q)
    return bm

def frustum_len(hfov):
    return max(3.2, min(13.0, 5.0 * math.sqrt(50.0 / hfov)))

def build_cams():
    C = coll("CAMS")
    for s in D['setups']:
        col = s['color']; k = s['id']
        on = mat("cam_on_" + k, col, emit=1.2, rough=0.4)
        grp = bpy.data.objects.new("CAM_" + k, None); C.objects.link(grp)
        grp.location = s['C']; grp.matrix_world = Matrix.Translation(s['C']) @ cam_rot(s['yaw'], s['pitch'])
        bm = bmesh.new()
        bm_box(bm, -0.11, -0.09, -0.05, 0.11, 0.09, 0.24)        # 机身（沿 -Z 为镜头方向）
        M = Matrix.Translation((0, 0, -0.14)) @ Matrix.Rotation(0, 4, 'X')
        bmesh.ops.create_cone(bm, cap_ends=True, segments=14, radius1=0.055, radius2=0.065, depth=0.2, matrix=M)
        bm_box(bm, -0.13, -0.08, -0.30, 0.13, 0.08, -0.25)        # 遮光斗
        b = obj_from_bm("CAMBODY_" + k, bm, on, C); b.parent = grp
        # 视锥（面 + 描边）
        hf = s['hfov'][0]
        fr = obj_from_bm("FRUST_" + k, frustum_bm(hf, frustum_len(hf)), mat("fr_" + k, col, emit=1.5, alpha=0.16), C); fr.parent = grp
        fe = obj_from_bm("FRUSTE_" + k, frustum_bm(hf, frustum_len(hf)), mat("fre_" + k, col, emit=3.0), C); fe.parent = grp
        mod = fe.modifiers.new("wf", 'WIREFRAME'); mod.thickness = 0.03; mod.use_replace = True
        if len(s['hfov']) > 1:
            hf2 = s['hfov'][1]
            fr2 = obj_from_bm("FRUST2_" + k, frustum_bm(hf2, frustum_len(hf2)), mat("fr2_" + k, col, emit=1.5, alpha=0.10), C); fr2.parent = grp
            fe2 = obj_from_bm("FRUSTE2_" + k, frustum_bm(hf2, frustum_len(hf2)), mat("fre2_" + k, col, emit=2.0), C); fe2.parent = grp
            m2 = fe2.modifiers.new("wf", 'WIREFRAME'); m2.thickness = 0.02; m2.use_replace = True
        # 支架：三脚架 / 手持操作员 / 高脚架 / 顶拍臂
        x, y, z = s['C']
        rig = s['rig']
        bm = bmesh.new()
        if '手持' in rig or '斯坦尼康' in rig:
            pass
        elif rig == '顶拍架':
            bm_seg(bm, (x, y, z), (x + 1.6, y, z), 0.03); bm_seg(bm, (x + 1.6, y, z), (x + 1.6, y, 0.5), 0.04)
        else:
            for a in (0, 120, 240):
                r = 0.35 if z > 0.8 else 0.25
                fx, fy = x + r * math.cos(math.radians(a)), y + r * math.sin(math.radians(a))
                fz = 0.5 if (y > 17.8 and abs(x) < 5.2 and y < 22.6) else 0.0
                bm_seg(bm, (x, y, z - 0.08), (fx, fy, fz), 0.018, 6)
        if len(bm.verts):
            obj_from_bm("RIG_" + k, bm, mat("rig", "#2b2b2b", rough=0.5), C)
        else:
            bm.free()
        if '手持' in rig or '斯坦尼康' in rig:
            # 操作员：站在机身后 0.35 m
            yv = math.radians(s['yaw'])
            ox, oy = x - 0.35 * math.sin(yv), y - 0.35 * math.cos(yv)
            op = bpy.data.objects.new("OP_" + k, person_mesh('crew')); C.objects.link(op)
            op.location = (ox, oy, 0.5 if (17.8 < oy < 22.6) else 0.0)
            op.rotation_euler = (0, 0, -yv)
            op.scale = (1, 1, max(0.35, min(1.0, (z + 0.25) / 1.62)))
            op.material_slots[0].link = 'OBJECT'; op.material_slots[0].material = mat("crew", "#5f6b7a")
        # 地面光圈（激活时显示）
        g = cyl("GLOW_" + k, x, y, 0.012 + (0.5 if 17.8 < y < 22.6 else 0), 0.01, 0.7, mat("glow_" + k, col, emit=2.5, alpha=0.5), C, 32)

def style_cams(active=None, phase_setups=None):
    for s in D['setups']:
        k = s['id']; is_on = (k == active); show = is_on or (phase_setups is None) or (k in phase_setups)
        for pre in ("CAMBODY_", "RIG_", "OP_"):
            o = bpy.data.objects.get(pre + k)
            if o: o.hide_render = not show
        b = bpy.data.objects.get("CAMBODY_" + k)
        if b:
            b.material_slots[0].link = 'OBJECT'
            b.material_slots[0].material = mat("cam_on_" + k, s['color'], emit=1.2) if (is_on or active is None) else mat("cam_dim", "#7d838c", emit=0.0)
        for pre in ("FRUST_", "FRUSTE_", "FRUST2_", "FRUSTE2_"):
            o = bpy.data.objects.get(pre + k)
            if o: o.hide_render = not (is_on or active == '__ALL__')
        g = bpy.data.objects.get("GLOW_" + k)
        if g: g.hide_render = not is_on

def set_zoom(k, hfov):
    """把激活机位的视锥改成本镜头的实际视角"""
    s = [x for x in D['setups'] if x['id'] == k][0]
    for pre, a in (("FRUST_", 0.16), ("FRUSTE_", None)):
        o = bpy.data.objects.get(pre + k)
        bm = frustum_bm(hfov, frustum_len(hfov)); me = o.data; bm.to_mesh(me); bm.free()

# ---------- 灯光（方案示意 + 实际照明） ----------
def build_lights():
    C = coll("LIGHTS")
    win = mat("L_window", "#fff1c1", emit=2.2)
    ray = mat("L_ray", "#ffe8a3", emit=1.0, alpha=0.10)
    for side, xo, sgn in (("W", -6.3, 1), ("E", 6.3, -1)):
        for i, y in enumerate((3.2, 6.4, 9.6, 12.8)):
            bm = bmesh.new(); bm_box(bm, xo - 0.05, y - 0.8, 1.2, xo + 0.05, y + 0.8, 2.6)
            obj_from_bm(f"L{1 if side=='W' else 2}_panel{i}", bm, win, C)
            bm = bmesh.new()
            v = [bm.verts.new(p) for p in ((xo, y - 1.0, 2.8), (xo, y + 1.0, 2.8), (xo, y + 1.0, 1.0), (xo, y - 1.0, 1.0),
                                             (xo + sgn * 4.2, y - 1.5, 0.0), (xo + sgn * 4.2, y + 1.5, 0.0))]
            bm.faces.new((v[0], v[1], v[5], v[4])); bm.faces.new((v[3], v[2], v[5], v[4]))
            obj_from_bm(f"L{1 if side=='W' else 2}_ray{i}", bm, ray, C)
            # 真实照明：面光
            ld = bpy.data.lights.new(f"lx_win_{side}{i}", 'AREA'); ld.shape = 'RECTANGLE'; ld.size = 2.0; ld.size_y = 1.8
            ld.energy = 900; ld.color = (1.0, 0.95, 0.88)
            lo = bpy.data.objects.new(f"LGT_win_{side}{i}", ld); C.objects.link(lo)
            lo.location = (xo + sgn * 0.8, y, 1.9); lo.rotation_euler = (0, math.radians(90 * sgn), 0)
    # 天花灯盘
    cm = mat("L_ceiling", "#dff3ff", emit=3.0, alpha=0.9)
    bm = bmesh.new()
    for x, y in [(x, y) for x in (-3.0, 0.0, 3.0) for y in (3.5, 7.5, 11.5, 15.5)]:
        bm_box(bm, x - 0.3, y - 0.6, 4.22, x + 0.3, y + 0.6, 4.25)
    o3 = obj_from_bm("L3_ceiling", bm, cm, C)
    w3 = o3.modifiers.new("wf", 'WIREFRAME'); w3.thickness = 0.04; w3.use_replace = True
    # 壁灯
    sm = mat("L_sconce", "#ffd8a8", emit=8.0)
    bm = bmesh.new()
    for x in (0.14 - 2.0, 0.14 + 2.0): bm_sph(bm, x, 0.25, 2.43, 0.11)
    for y in (1.6, 4.8, 8.0, 11.2, 14.4): bm_sph(bm, -5.2 + 0.42, y, 2.05, 0.1); bm_sph(bm, 5.2 - 0.42, y, 2.05, 0.1)
    for x in (-4.6, 4.6): bm_sph(bm, x, 22.3, 2.4, 0.1)
    obj_from_bm("L4_sconces", bm, sm, C)
    # 画像光晕
    hm = mat("L_halo", "#ffbf73", emit=6.0, alpha=0.8)
    bm = bmesh.new()
    x0, x1, z0, z1, y = -0.34 - 0.86, -0.34 + 0.86, 0.86, 3.06, 22.6 - 0.04
    for a, b in (((x0, z0), (x1, z0 + 0.04)), ((x0, z1 - 0.04), (x1, z1)), ((x0, z0), (x0 + 0.04, z1)), ((x1 - 0.04, z0), (x1, z1))):
        bm_box(bm, a[0], y - 0.02, a[1], b[0], y, b[1])
    obj_from_bm("L5_halo", bm, hm, C)
    # 发光石雕
    stm = mat("L_statue", "#fff6dc", emit=3.0)
    bm = bmesh.new()
    for (x, y), z in (((-0.45, 0.7), 0.0), ((0.75, 0.7), 0.0), ((-2.4, 20.3), 0.5), ((2.5, 20.4), 0.5)):
        bm_cyl(bm, x, y, z, 1.25, 0.2, 10, 1.0, 1.0, 0.13)
    obj_from_bm("L6_statues", bm, stm, C)
    # 门外走廊光（灯头 + 光束）
    bm = bmesh.new(); bm_cyl(bm, 0.1, -2.4, 0, 2.2, 0.03, 8); bm_box(bm, -0.15, -2.55, 2.2, 0.35, -2.25, 2.55)
    obj_from_bm("L7_corridor_lamp", bm, mat("lampbody", "#333333"), C)
    bm = bmesh.new()
    v = [bm.verts.new(p) for p in ((0.1, -2.2, 2.4), (-0.9, 0.6, 0.0), (1.1, 0.6, 0.0), (0.1, 0.6, 2.6))]
    bm.faces.new((v[0], v[1], v[2])); bm.faces.new((v[0], v[2], v[3])); bm.faces.new((v[0], v[3], v[1]))
    obj_from_bm("L7_corridor_ray", bm, mat("L_ray7", "#ffe066", emit=1.5, alpha=0.18), C)
    # 布幔上方顶部柔光（推测）
    tm = mat("L_topsoft", "#ffb86b", emit=3.0, alpha=0.9)
    bm = bmesh.new()
    for y in (6.5, 12.5): bm_box(bm, -1.2, y - 1.2, 3.95, 1.2, y + 1.2, 4.0)
    o8 = obj_from_bm("L8_topsoft", bm, tm, C)
    w8 = o8.modifiers.new("wf", 'WIREFRAME'); w8.thickness = 0.05; w8.use_replace = True
    # 补一点整体照明（只为渲染可读）
    sd = bpy.data.lights.new("lx_sun", 'SUN'); sd.energy = 3.0; sd.angle = math.radians(25)
    so = bpy.data.objects.new("LGT_sun", sd); C.objects.link(so); so.rotation_euler = (math.radians(35), math.radians(-25), math.radians(20))

# ---------- 俯视摄影机 ----------
TOP = dict(target=(0.4, 8.4, 0.0), dist=42.0, pitch=58.0, yaw=-90.0, lens=50.0)
def build_topcam(target=None, dist=None, pitch=None, lens=None):
    p = dict(TOP)
    if target: p['target'] = target
    if dist: p['dist'] = dist
    if pitch: p['pitch'] = pitch
    if lens: p['lens'] = lens
    C = coll("TOPCAM")
    cd = bpy.data.cameras.get("lx_topcam") or bpy.data.cameras.new("lx_topcam")
    cd.lens = p['lens']; cd.sensor_width = 36.0; cd.sensor_fit = 'HORIZONTAL'; cd.clip_end = 300
    o = bpy.data.objects.get("TOPCAM") or bpy.data.objects.new("TOPCAM", cd)
    if o.name not in C.objects: C.objects.link(o)
    # 从东侧上方看向西：画面右 = 北（舞台），画面左 = 南（门）
    pt = math.radians(p['pitch'])
    look = Vector((-math.cos(pt), 0, -math.sin(pt)))
    loc = Vector(p['target']) - look * p['dist']
    z = -look.normalized(); up = Vector((0, 0, 1))
    y = (up - z * up.dot(z)).normalized(); x = y.cross(z)
    M = Matrix((x, y, z)).transposed().to_4x4(); M.translation = loc
    o.matrix_world = M
    bpy.context.scene.camera = o
    return o

def project(points):
    from bpy_extras.object_utils import world_to_camera_view
    sc = bpy.context.scene; cam = sc.camera
    W, H = sc.render.resolution_x, sc.render.resolution_y
    out = []
    for p in points:
        v = world_to_camera_view(sc, cam, Vector(p))
        out.append((round(v.x * W, 1), round((1 - v.y) * H, 1), round(v.z, 2)))
    return out

NOSHADOW = ("FRUST", "GLOW_", "L1_", "L2_", "L3_", "L5_", "L7_corridor_ray", "L8_", "sheers_", "door_glass", "CHEN_ring", "LEADER_ring")
def fix_shadows():
    for o in bpy.context.scene.objects:
        if o.name.startswith(NOSHADOW):
            try: o.visible_shadow = False
            except Exception: pass

def build_all():
    global D
    D = json.load(open(DATA))
    reset_scene(); build_hall(); build_people(); build_cams(); build_lights(); build_topcam(); fix_shadows()
    set_people(0.0); style_cams(None)
    return "ok"

def load():
    global D
    D = json.load(open(DATA)); return len(D['shots'])


# ---------- 渲染驱动 ----------
STATE = {}
def phase_sets():
    ph = {}
    for sh in D['shots']: ph.setdefault(sh['phase'], set()).add(sh['setup'])
    return ph

def anchors(t):
    pts = []; keys = []
    for s in D['setups']:
        x, y, z = s['C']; pts.append((x, y, z + 0.25)); keys.append('cam:' + s['id'])
    ch = bpy.data.objects['CHEN'].location; pts.append((ch.x, ch.y, ch.z + 1.9)); keys.append('chen')
    ld = [p for p in D['people'] if p['kind'] == 'leader'][0]; pts.append((ld['x'], ld['y'], 0.5 + 1.0)); keys.append('leader')
    LA = {'L1': (-6.3, 1.4, 2.7), 'L2': (6.3, 1.4, 2.2), 'L3': (3.0, 15.5, 4.25), 'L4': (-4.78, 11.2, 2.05), 'L5': (-0.34, 22.55, 3.1),
          'L6': (-0.45, 0.7, 1.3), 'L7': (0.1, -2.4, 2.6), 'L8': (1.2, 12.5, 4.0), 'L9': (0.14, -0.45, 2.6)}
    for k, p in LA.items(): pts.append(p); keys.append('light:' + k)
    for k, p in {'door': (0.14, -0.3, 0.0), 'stage': (2.0, 20.0, 0.5), 'portrait': (-0.34, 22.6, 2.0), 'ac': (3.4, 0.55, 2.15), 'stairs': (4.1, -5.0, 1.0)}.items():
        pts.append(p); keys.append('ref:' + k)
    pr = project(pts)
    return {k: v for k, v in zip(keys, pr)}

def prep_shot(sh):
    t = (sh['t0'] + sh['t1']) / 2.0
    set_people(t)
    ph = phase_sets()[sh['phase']]
    style_cams(sh['setup'], ph)
    set_zoom(sh['setup'], sh['hfov'])
    return t

def start_top_renders(out_dir, only=None, tick=3):
    os.makedirs(out_dir, exist_ok=True)
    sc = bpy.context.scene; sc.camera = bpy.data.objects['TOPCAM']
    sc.render.resolution_x, sc.render.resolution_y = 1080, 620
    sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGBA'
    todo = [sh for sh in D['shots'] if (only is None or sh['n'] in only)]
    STATE.update(todo=todo, i=0, out=out_dir, anchors={}, t0=__import__('time').time(), tick=tick)
    def _tick():
        n = 0
        while STATE['i'] < len(STATE['todo']) and n < STATE['tick']:
            sh = STATE['todo'][STATE['i']]; STATE['i'] += 1
            p = os.path.join(STATE['out'], "shot_%03d.png" % sh['n'])
            t = prep_shot(sh)
            STATE['anchors'][sh['n']] = anchors(t)
            if not os.path.exists(p):
                sc.render.filepath = p; bpy.ops.render.render(write_still=True); n += 1
        if STATE['i'] >= len(STATE['todo']):
            json.dump(STATE['anchors'], open(os.path.join(STATE['out'], 'anchors.json'), 'w'))
            open(os.path.join(STATE['out'], '_DONE'), 'w').write('%.0f' % (__import__('time').time() - STATE['t0']))
            return None
        return 0.05
    bpy.app.timers.register(_tick, first_interval=0.3)
    return len(todo)

def chk_camera(s, hfov=None):
    cd = bpy.data.cameras.get("lx_chk") or bpy.data.cameras.new("lx_chk")
    o = bpy.data.objects.get("CHK_FilmCam") or bpy.data.objects.new("CHK_FilmCam", cd)
    if o.name not in coll("TOPCAM").objects: coll("TOPCAM").objects.link(o)
    cd.sensor_fit = 'HORIZONTAL'; cd.sensor_width = 36.0
    h = hfov or s['hfov'][0]
    cd.lens = 18.0 / math.tan(math.radians(h / 2)); cd.clip_start = 0.05
    o.matrix_world = Matrix.Translation(s['C']) @ cam_rot(s['yaw'], s['pitch'])
    return o

GLYPHS = ("FRUST", "GLOW_", "L1_", "L2_", "L3_", "L5_", "L7_", "L8_", "CAMBODY_", "RIG_", "OP_", "CHEN_ring", "LEADER_ring", "floor_grid")
def start_qa_renders(out_dir, pairs, tick=2):
    """pairs: [(setup_id, shot_n)]"""
    os.makedirs(out_dir, exist_ok=True)
    sc = bpy.context.scene
    STATE.update(q=list(pairs), qi=0, qout=out_dir, qt0=__import__('time').time())
    def _tick():
        n = 0
        while STATE['qi'] < len(STATE['q']) and n < tick:
            k, sn = STATE['q'][STATE['qi']]; STATE['qi'] += 1
            s = [x for x in D['setups'] if x['id'] == k][0]; sh = [x for x in D['shots'] if x['n'] == sn][0]
            set_people((sh['t0'] + sh['t1']) / 2.0)
            hidden = [o for o in sc.objects if o.name.startswith(GLYPHS) and not o.hide_render]
            for o in hidden: o.hide_render = True
            old = (sc.camera, sc.render.resolution_x, sc.render.resolution_y, sc.render.film_transparent)
            try:
                sc.camera = chk_camera(s, sh.get('hfov')); sc.render.resolution_x, sc.render.resolution_y = 1280, 536
                sc.render.film_transparent = False
                sc.render.image_settings.file_format = 'JPEG'; sc.render.image_settings.quality = 90
                sc.render.filepath = os.path.join(STATE['qout'], "qa_%s_s%03d.jpg" % (k, sn)); bpy.ops.render.render(write_still=True)
            finally:
                for o in hidden: o.hide_render = False
                sc.camera, sc.render.resolution_x, sc.render.resolution_y, sc.render.film_transparent = old
                sc.render.image_settings.file_format = 'PNG'
            n += 1
        if STATE['qi'] >= len(STATE['q']):
            open(os.path.join(STATE['qout'], '_DONE'), 'w').write('%.0f' % (__import__('time').time() - STATE['qt0'])); return None
        return 0.05
    bpy.app.timers.register(_tick, first_interval=0.3)
    return len(pairs)
