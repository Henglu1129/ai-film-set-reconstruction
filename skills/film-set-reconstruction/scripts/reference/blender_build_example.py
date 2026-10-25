# ==== 《大事件》(2004) 开场长镜头项目里的实际代码，原样保留作参考 ====
# 里面的路径（/tmp/claude-0/...、/mnt/user-data/...）、坐标、车辆尺寸、帧号区间都是那部片子的，换片时逐项改。
# 约定：机位 R 为 世界→相机（OpenCV：x 右 y 下 z 前），C 为相机中心；画面 1280×554 时 CX=640 CY=277、HFOV=42°。
# 《大事件》开场长镜头 · 拍摄现场还原 —— Blender 建场景 + 渲染脚本
# 用法：Blender → Scripting 工作区 → 打开本文件 → 点「运行脚本」。
# 脚本会新建一个名为 DSJ_Oner 的场景（不动你已有的场景），读取同目录的 bake.json，
# 建好街道、楼宇、吊臂、摄影机、演员和剧组，保存 dsj_oner.blend，然后开始渲染上层画面。
# 渲染输出：同目录 render_top/00001.jpg … 09768.jpg（1280×544，24fps）
import bpy, bmesh, json, math, os, random
from mathutils import Vector, Matrix, Euler

# ---------------- 路径 ----------------
HERE = os.environ.get("DSJ_DIR") or "/path/to/大事件_长镜头拆解"
BAKE = os.environ.get("DSJ_BAKE") or os.path.join(HERE, "bake_v3.json")
OUT = os.path.join(HERE, "render_v3", "")
RES = (1080, 780)
START_RENDER = os.environ.get("DSJ_NO_RENDER") is None
FRAME_LIMIT = int(os.environ.get("DSJ_FRAMES", "0"))  # 测试用：只建前 N 帧

B = json.load(open(BAKE, encoding="utf-8"))
W = B["world"]
FR = B["frames"]
if FRAME_LIMIT:
    FR = [f for f in FR if f["f"] <= FRAME_LIMIT]
NF = FR[-1]["f"] if FRAME_LIMIT else B["frames_total"]
random.seed(7)

# ---------------- 场景 ----------------
scene = bpy.data.scenes.get("DSJ_Oner") or bpy.data.scenes.new("DSJ_Oner")
for o in list(scene.collection.all_objects):
    bpy.data.objects.remove(o, do_unlink=True)
try:
    bpy.context.window.scene = scene
except Exception:
    pass
scene.frame_start, scene.frame_end = 1, NF
scene.render.fps = 24
scene.render.resolution_x, scene.render.resolution_y = RES
scene.render.resolution_percentage = 100
scene.unit_settings.system = "METRIC"
for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
    try:
        scene.render.engine = eng; break
    except Exception:
        pass
ee = scene.eevee
for k, v in (("taa_render_samples", 16), ("use_gtao", True), ("use_soft_shadows", True), ("use_shadows", True), ("shadow_ray_count", 1), ("use_raytracing", True), ("use_fast_gi", True)):
    try: setattr(ee, k, v)
    except Exception: pass
try:
    scene.view_settings.view_transform = "AgX"; scene.view_settings.look = "AgX - Medium High Contrast"
except Exception:
    try: scene.view_settings.view_transform = "Filmic"
    except Exception: pass
scene.render.image_settings.file_format = "JPEG"
scene.render.image_settings.quality = 90
scene.render.filepath = OUT

COL = bpy.data.collections.new("DSJ_Set"); scene.collection.children.link(COL)

# 世界：阴天
world = bpy.data.worlds.get("DSJ_Overcast") or bpy.data.worlds.new("DSJ_Overcast")
world.use_nodes = True
nt = world.node_tree; nt.nodes.clear()
bg = nt.nodes.new("ShaderNodeBackground"); out = nt.nodes.new("ShaderNodeOutputWorld")
grad = nt.nodes.new("ShaderNodeTexGradient"); tc = nt.nodes.new("ShaderNodeTexCoord"); ramp = nt.nodes.new("ShaderNodeValToRGB")
sep = nt.nodes.new("ShaderNodeSeparateXYZ")
nt.links.new(tc.outputs["Generated"], sep.inputs[0])
ramp.color_ramp.elements[0].position = 0.45; ramp.color_ramp.elements[0].color = (0.50, 0.53, 0.55, 1)
ramp.color_ramp.elements[1].position = 1.0; ramp.color_ramp.elements[1].color = (0.80, 0.85, 0.88, 1)
nt.links.new(sep.outputs["Z"], ramp.inputs[0]); nt.links.new(ramp.outputs[0], bg.inputs["Color"])
bg.inputs["Strength"].default_value = 0.85
nt.links.new(bg.outputs[0], out.inputs[0])
hdr = os.path.join(HERE, "polyhaven", "overcast_industrial_courtyard_2k.hdr")
if os.path.exists(hdr):
    nt.nodes.clear()
    env = nt.nodes.new("ShaderNodeTexEnvironment"); env.image = bpy.data.images.load(hdr, check_existing=True)
    bg = nt.nodes.new("ShaderNodeBackground"); bg.inputs["Strength"].default_value = 1.0
    out = nt.nodes.new("ShaderNodeOutputWorld"); nt.links.new(env.outputs["Color"], bg.inputs["Color"]); nt.links.new(bg.outputs[0], out.inputs[0])
scene.world = world

# ---------------- 材质 ----------------
def _inp(node, *names):
    for n in names:
        if n in node.inputs: return node.inputs[n]
    return None

def mat(name, color, rough=0.7, metal=0.0, emit=None, estr=0.0, alpha=1.0, spec=None):
    m = bpy.data.materials.get(name)
    if m: return m
    m = bpy.data.materials.new(name); m.use_nodes = True
    p = m.node_tree.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value = (*color, 1)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal
    if emit is not None:
        e = _inp(p, "Emission Color", "Emission"); e.default_value = (*emit, 1)
        s = _inp(p, "Emission Strength");
        if s: s.default_value = estr
    if alpha < 1:
        p.inputs["Alpha"].default_value = alpha
        try: m.blend_method = "BLEND"
        except Exception: pass
        try: m.surface_render_method = "BLENDED"
        except Exception: pass
    m.diffuse_color = (*color, alpha)
    return m

def noisy(name, c1, c2, scale=6.0, rough=0.85, bump=0.15):
    """带噪声的表面（沥青、混凝土、旧墙）"""
    m = bpy.data.materials.get(name)
    if m: return m
    m = bpy.data.materials.new(name); m.use_nodes = True
    t = m.node_tree; p = t.nodes.get("Principled BSDF")
    n = t.nodes.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = scale
    try: n.inputs["Detail"].default_value = 8
    except Exception: pass
    r = t.nodes.new("ShaderNodeValToRGB")
    r.color_ramp.elements[0].color = (*c1, 1); r.color_ramp.elements[1].color = (*c2, 1)
    t.links.new(n.outputs["Fac"], r.inputs[0]); t.links.new(r.outputs[0], p.inputs["Base Color"])
    p.inputs["Roughness"].default_value = rough
    bm = t.nodes.new("ShaderNodeBump"); bm.inputs["Strength"].default_value = bump
    t.links.new(n.outputs["Fac"], bm.inputs["Height"]); t.links.new(bm.outputs["Normal"], p.inputs["Normal"])
    m.diffuse_color = (*c1, 1)
    return m

PH = os.path.join(HERE, "polyhaven")
def _img(path, colorspace="sRGB"):
    im = bpy.data.images.load(path, check_existing=True)
    try: im.colorspace_settings.name = colorspace
    except Exception: pass
    return im

def ph_nodes(t, tid, scale, tint=(1, 1, 1), coord="Object"):
    """在节点树 t 里搭 Poly Haven 贴图（盒投影），返回 (颜色输出, 粗糙度输出, 法线输出)；缺文件时返回 None"""
    d = os.path.join(PH, f"{tid}_diff.jpg")
    if not os.path.exists(d): return None
    N, L = t.nodes, t.links
    tc = N.new("ShaderNodeTexCoord"); mp = N.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (1 / scale, 1 / scale, 1 / scale)
    L.new(tc.outputs[coord], mp.inputs[0])
    def tex(path, cs):
        n = N.new("ShaderNodeTexImage"); n.image = _img(path, cs); n.projection = "BOX"; n.projection_blend = 0.25; L.new(mp.outputs[0], n.inputs[0]); return n
    dn = tex(d, "sRGB")
    tn = N.new("ShaderNodeMix"); tn.data_type = "RGBA"; tn.blend_type = "MULTIPLY"; tn.inputs[0].default_value = 1.0
    L.new(dn.outputs["Color"], tn.inputs[6]); tn.inputs[7].default_value = (*tint, 1)
    r = os.path.join(PH, f"{tid}_rough.jpg"); rn = tex(r, "Non-Color").outputs["Color"] if os.path.exists(r) else None
    nn = None; n_ = os.path.join(PH, f"{tid}_nor.jpg")
    if os.path.exists(n_):
        ni = tex(n_, "Non-Color"); nm = N.new("ShaderNodeNormalMap"); nm.inputs["Strength"].default_value = 0.8; L.new(ni.outputs["Color"], nm.inputs["Color"]); nn = nm.outputs["Normal"]
    return tn.outputs[2], rn, nn

def pbr(name, tid, scale, fallback, tint=(1, 1, 1), coord="Object"):
    m = bpy.data.materials.get(name)
    if m: return m
    m = bpy.data.materials.new(name); m.use_nodes = True; t = m.node_tree; p = t.nodes.get("Principled BSDF")
    r = ph_nodes(t, tid, scale, tint, coord)
    if r is None:
        bpy.data.materials.remove(m); return fallback
    c, ro, no = r
    t.links.new(c, p.inputs["Base Color"])
    if ro: t.links.new(ro, p.inputs["Roughness"])
    if no: t.links.new(no, p.inputs["Normal"])
    m.diffuse_color = (*tint, 1)
    return m

WALL_TEX = ["painted_plaster_wall", "grey_plaster_03", "concrete_wall_006", "damaged_plaster"]
def facade(name, wall, glass=(0.06, 0.08, 0.09), shop=(0.13, 0.13, 0.12), floor_h=3.1, bay=2.6, tex_wall=True):
    """唐楼立面：物体坐标里的窗格 + 底层铺位卷闸"""
    m = bpy.data.materials.get(name)
    if m: return m
    m = bpy.data.materials.new(name); m.use_nodes = True
    t = m.node_tree; N = t.nodes; L = t.links; p = N.get("Principled BSDF")
    tc = N.new("ShaderNodeTexCoord"); sx = N.new("ShaderNodeSeparateXYZ"); L.new(tc.outputs["Object"], sx.inputs[0])
    geo = N.new("ShaderNodeNewGeometry"); sn = N.new("ShaderNodeSeparateXYZ"); L.new(geo.outputs["True Normal"], sn.inputs[0])
    def math_(op, a, b=None, v=None):
        n = N.new("ShaderNodeMath"); n.operation = op
        if isinstance(a, float): n.inputs[0].default_value = a
        else: L.new(a, n.inputs[0])
        if b is not None:
            if isinstance(b, float): n.inputs[1].default_value = b
            else: L.new(b, n.inputs[1])
        return n.outputs[0]
    # 沿立面方向的坐标：|nx| 大用 y，|ny| 大用 x
    ax = math_("ABSOLUTE", sn.outputs["X"]); ay = math_("ABSOLUTE", sn.outputs["Y"])
    along = math_("ADD", math_("MULTIPLY", sx.outputs["Y"], ax), math_("MULTIPLY", sx.outputs["X"], ay))
    u = math_("FRACT", math_("DIVIDE", along, bay)); v = math_("FRACT", math_("DIVIDE", sx.outputs["Z"], floor_h))
    win_u = math_("MULTIPLY", math_("GREATER_THAN", u, 0.30), math_("LESS_THAN", u, 0.70))
    win_v = math_("MULTIPLY", math_("GREATER_THAN", v, 0.33), math_("LESS_THAN", v, 0.78))
    fr_u = math_("MULTIPLY", math_("GREATER_THAN", u, 0.285), math_("LESS_THAN", u, 0.715))
    fr_v = math_("MULTIPLY", math_("GREATER_THAN", v, 0.315), math_("LESS_THAN", v, 0.795))
    upper = math_("GREATER_THAN", sx.outputs["Z"], floor_h)  # 物体原点在地面
    side = math_("LESS_THAN", math_("ABSOLUTE", sn.outputs["Z"]), 0.5)
    win = math_("MULTIPLY", math_("MULTIPLY", math_("MULTIPLY", win_u, win_v), upper), side)
    ground = math_("MULTIPLY", math_("LESS_THAN", sx.outputs["Z"], floor_h * 0.95), side)
    frame = math_("MULTIPLY", math_("MULTIPLY", math_("MULTIPLY", fr_u, fr_v), upper), side)
    # 墙面污渍：竖向拉长的噪声 + 越往下越脏
    mp = N.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (1.0, 1.0, 0.12); L.new(tc.outputs["Object"], mp.inputs[0])
    nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 2.2; L.new(mp.outputs[0], nz.inputs["Vector"])
    try: nz.inputs["Detail"].default_value = 6
    except Exception: pass
    wr = N.new("ShaderNodeValToRGB"); wr.color_ramp.elements[0].position = 0.35; wr.color_ramp.elements[0].color = (*[c * 0.55 for c in wall], 1); wr.color_ramp.elements[1].position = 0.7; wr.color_ramp.elements[1].color = (*wall, 1)
    L.new(nz.outputs["Fac"], wr.inputs[0])
    wall_col = wr.outputs[0]
    ph = ph_nodes(t, WALL_TEX[len([x for x in bpy.data.materials if x.name.startswith("dsj_facade_")]) % 4], 2.5, tint=wall) if tex_wall else None
    if ph:
        g2 = N.new("ShaderNodeMix"); g2.data_type = "RGBA"; g2.blend_type = "MULTIPLY"; g2.inputs[0].default_value = 0.85
        L.new(ph[0], g2.inputs[6]); L.new(wr.outputs[0], g2.inputs[7]); wall_col = g2.outputs[2]
        if ph[2]: L.new(ph[2], p.inputs["Normal"])
    mf = N.new("ShaderNodeMix"); mf.data_type = "RGBA"; L.new(frame, mf.inputs[0]); L.new(wall_col, mf.inputs[6]); mf.inputs[7].default_value = (0.22, 0.22, 0.21, 1)
    m1 = N.new("ShaderNodeMix"); m1.data_type = "RGBA"; L.new(win, m1.inputs[0]); L.new(mf.outputs[2], m1.inputs[6]); m1.inputs[7].default_value = (*glass, 1)
    m2 = N.new("ShaderNodeMix"); m2.data_type = "RGBA"; L.new(ground, m2.inputs[0]); L.new(m1.outputs[2], m2.inputs[6]); m2.inputs[7].default_value = (*shop, 1)
    L.new(m2.outputs[2], p.inputs["Base Color"])
    rr = math_("ADD", math_("MULTIPLY", win, -0.75), 0.9); L.new(rr, p.inputs["Roughness"])
    m.diffuse_color = (*wall, 1)
    return m

M = {
    "asphalt": noisy("dsj_asphalt", (0.10, 0.10, 0.10), (0.17, 0.17, 0.16), 14, 0.9, 0.08),
    "walk": noisy("dsj_walk", (0.36, 0.35, 0.33), (0.47, 0.46, 0.43), 5, 0.9, 0.05),
    "curb": mat("dsj_curb", (0.55, 0.54, 0.5), 0.8),
    "paint": mat("dsj_roadpaint", (0.85, 0.85, 0.82), 0.6),
    "yellow": mat("dsj_yellowline", (0.82, 0.62, 0.08), 0.6),
    "shutter": noisy("dsj_shutter", (0.18, 0.19, 0.2), (0.32, 0.33, 0.33), 40, 0.5, 0.3),
    "canopy": noisy("dsj_canopy", (0.25, 0.21, 0.17), (0.42, 0.38, 0.33), 3, 0.7, 0.4),
    "barrel": mat("dsj_barrel", (0.05, 0.16, 0.42), 0.45),
    "drum_white": mat("dsj_drum_white", (0.75, 0.75, 0.72), 0.5),
    "wrap": mat("dsj_wrap", (0.82, 0.84, 0.85), 0.25),
    "carton": noisy("dsj_carton", (0.45, 0.33, 0.2), (0.6, 0.47, 0.3), 9, 0.9, 0.1),
    "rubber": mat("dsj_rubber", (0.03, 0.03, 0.03), 0.8),
    "chrome": mat("dsj_chrome", (0.8, 0.8, 0.8), 0.2, 1.0),
    "glass": mat("dsj_glass", (0.05, 0.07, 0.08), 0.05, 0.0, alpha=0.55),
    "darkglass": mat("dsj_darkglass", (0.03, 0.04, 0.05), 0.08),
    "steel": mat("dsj_steel", (0.32, 0.33, 0.35), 0.35, 0.9),
    "rail": mat("dsj_rail", (0.42, 0.43, 0.45), 0.3, 1.0),
    "sleeper": mat("dsj_sleeper", (0.26, 0.18, 0.11), 0.9),
    "crane": mat("dsj_crane", (0.12, 0.12, 0.13), 0.45, 0.6),
    "crane_y": mat("dsj_crane_yellow", (0.85, 0.62, 0.05), 0.5),
    "camera": mat("dsj_camera", (0.04, 0.04, 0.045), 0.4, 0.3),
    "lens": mat("dsj_lens", (0.01, 0.01, 0.01), 0.15, 0.5),
    "monitor": mat("dsj_monitor", (0.2, 0.3, 0.35), 0.3, emit=(0.45, 0.6, 0.7), estr=2.5),
    "cable": mat("dsj_cable", (0.02, 0.02, 0.02), 0.6),
    "orange_fence": mat("dsj_orange_fence", (0.95, 0.32, 0.05), 0.6),
    "redwhite": mat("dsj_redwhite", (0.8, 0.12, 0.1), 0.5),
    "white": mat("dsj_white", (0.85, 0.86, 0.86), 0.4),
    "van_red": mat("dsj_van_red", (0.7, 0.05, 0.05), 0.4),
    "tent": mat("dsj_tent", (0.1, 0.1, 0.12), 0.8),
    "paper": mat("dsj_paper", (0.85, 0.84, 0.78), 0.8),
    "flash": mat("dsj_flash", (1.0, 0.7, 0.3), 0.5, emit=(1.0, 0.65, 0.25), estr=60),
    "smoke": mat("dsj_smoke", (0.7, 0.7, 0.7), 1.0, alpha=0.28),
    "lamp": mat("dsj_lamp", (0.9, 0.85, 0.7), 0.3, emit=(1, 0.9, 0.7), estr=6),
}
M["asphalt"] = pbr("dsj_ph_asphalt", "asphalt_02", 4.0, M["asphalt"], tint=(0.75, 0.75, 0.75))
M["walk"] = pbr("dsj_ph_walk", "concrete_pavement", 3.0, M["walk"])
M["canopy"] = pbr("dsj_ph_canopy", "rusty_corrugated_iron", 2.0, M["canopy"])
M["shutter"] = pbr("dsj_ph_shutter", "rusty_metal_shutter", 2.5, M["shutter"], tint=(0.8, 0.8, 0.8))
WALLS = [(0.62, 0.6, 0.55), (0.55, 0.57, 0.56), (0.66, 0.62, 0.52), (0.5, 0.52, 0.55), (0.6, 0.55, 0.5), (0.7, 0.68, 0.6)]
FAC = [facade(f"dsj_facade_{i}", c) for i, c in enumerate(WALLS)]
TOWER = facade("dsj_tower", (0.78, 0.8, 0.82), glass=(0.25, 0.32, 0.38), shop=(0.6, 0.62, 0.64), floor_h=2.9, bay=2.2, tex_wall=False)
ROLE = {"robber": (0.75, 0.12, 0.1), "cop": (0.15, 0.35, 0.8), "patrol": (0.05, 0.55, 0.5), "crew": (0.5, 0.3, 0.75), "extra": None}
RING = {k: mat(f"dsj_ring_{k}", v, 0.5, emit=v, estr=1.5, alpha=0.75) for k, v in ROLE.items() if v}

# ---------------- 几何工具 ----------------
def new_obj(name, bm, mats, parent=None, loc=(0, 0, 0), col=COL):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for m_ in mats: me.materials.append(m_)
    o = bpy.data.objects.new(name, me); o.location = loc
    col.objects.link(o)
    if parent: o.parent = parent
    return o

def add_box(bm, x0, x1, y0, y1, z0, z1, mi=0):
    r = bmesh.ops.create_cube(bm, size=1.0)
    vs = r["verts"]
    bmesh.ops.scale(bm, vec=(x1 - x0, y1 - y0, z1 - z0), verts=vs)
    bmesh.ops.translate(bm, vec=((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), verts=vs)
    for f in {f for v in vs for f in v.link_faces}: f.material_index = mi
    return vs

def add_cyl(bm, r1, r2, depth, loc, rot=(0, 0, 0), seg=16, mi=0):
    res = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg, radius1=r1, radius2=r2, depth=depth)
    vs = res["verts"]
    bmesh.ops.rotate(bm, verts=vs, cent=(0, 0, 0), matrix=Euler(rot).to_matrix())
    bmesh.ops.translate(bm, vec=loc, verts=vs)
    for f in {f for v in vs for f in v.link_faces}: f.material_index = mi
    return vs

def add_sph(bm, r, loc, mi=0, seg=12, squash=1.0):
    res = bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=max(6, seg // 2), radius=r)
    vs = res["verts"]
    if squash != 1.0: bmesh.ops.scale(bm, vec=(1, 1, squash), verts=vs)
    bmesh.ops.translate(bm, vec=loc, verts=vs)
    for f in {f for v in vs for f in v.link_faces}: f.material_index = mi
    return vs

def box_obj(name, x0, x1, y0, y1, z0, z1, m_, bevel=0.0):
    bm = bmesh.new(); add_box(bm, x0, x1, y0, y1, z0, z1)
    o = new_obj(name, bm, [m_])
    if bevel:
        md = o.modifiers.new("bevel", "BEVEL"); md.width = bevel; md.segments = 2
    return o

# ---------------- 动画工具（批量写关键帧） ----------------
def _fcurves(obj):
    ad = obj.animation_data; act = ad.action
    try:
        return act.fcurves
    except AttributeError:
        from bpy_extras import anim_utils
        return anim_utils.action_get_channelbag_for_slot(act, ad.action_slot).fcurves

def bake_channel(obj, path, index, frames, values, interp=1):
    obj.keyframe_insert(data_path=path, index=index, frame=frames[0])
    fcs = _fcurves(obj)
    fc = next(f for f in fcs if f.data_path == path and f.array_index == max(index, 0))
    fc.keyframe_points.clear()
    fc.keyframe_points.add(len(frames))
    co = [0.0] * (2 * len(frames))
    co[0::2] = frames; co[1::2] = values
    fc.keyframe_points.foreach_set("co", co)
    fc.keyframe_points.foreach_set("interpolation", [interp] * len(frames))
    fc.update()

def bake_loc(obj, frames, xyz):
    for i in range(3): bake_channel(obj, "location", i, frames, [p[i] for p in xyz])

def bake_rot(obj, frames, eul, axes=(0, 1, 2)):
    for i in axes: bake_channel(obj, "rotation_euler", i, frames, [e[i] for e in eul])

def bake_scale(obj, frames, sc, axes=(0, 1, 2)):
    for i in axes: bake_channel(obj, "scale", i, frames, [s[i] for s in sc])

def bake_vis(obj, frames, vis):
    vals = [0.0 if v else 1.0 for v in vis]
    bake_channel(obj, "hide_render", -1, frames, vals, interp=0)
    bake_channel(obj, "hide_viewport", -1, frames, vals, interp=0)
    for c in obj.children_recursive:
        bake_channel(c, "hide_render", -1, frames, vals, interp=0)
        bake_channel(c, "hide_viewport", -1, frames, vals, interp=0)

def unwrap(angles):
    out = []; prev = None
    for a in angles:
        if prev is not None:
            while a - prev > math.pi: a -= 2 * math.pi
            while a - prev < -math.pi: a += 2 * math.pi
        out.append(a); prev = a
    return out

FRAMES = [float(f["f"]) for f in FR]

# ---------------- 地面、街道 ----------------
st = W["street"]; Y0, Y1 = -75.0, 60.0
cs = W.get("crossStreet", [-57, -49])
box_obj("ground_far", -60, 60, -110, 170, -0.3, -0.1, M["walk"])
box_obj("road_main", st["road"][0], st["road"][1], Y0, Y1, -0.12, 0.0, M["asphalt"])
box_obj("road_cross", -60, 60, cs[0], cs[1], -0.12, 0.0, M["asphalt"])
for side, (a, b) in (("W", (st["x"][0], st["road"][0])), ("E", (st["road"][1], st["x"][1]))):
    for (ya, yb) in ((Y0, cs[0]), (cs[1], Y1)):
        box_obj(f"walk_{side}_{ya}", a, b, ya, yb, -0.12, 0.15, M["walk"])
        cx = st["road"][0] if side == "W" else st["road"][1]
        box_obj(f"curb_{side}_{ya}", cx - 0.08, cx + 0.08, ya, yb, -0.12, 0.16, M["curb"])
# 路面标线：中线虚线、停止线、黄色禁停线
bm = bmesh.new()
y = Y0
while y < Y1:
    if not (cs[0] - 1 < y < cs[1] + 1): add_box(bm, -0.06, 0.06, y, y + 1.5, 0.0, 0.012)
    y += 4.0
add_box(bm, st["road"][0], st["road"][1], cs[1] + 1.0, cs[1] + 1.3, 0.0, 0.012)
for x in (st["road"][0] + 0.25, st["road"][1] - 0.25):
    add_box(bm, x - 0.05, x + 0.05, cs[1] + 2, Y1, 0.0, 0.012, mi=1)
new_obj("road_marks", bm, [M["paint"], M["yellow"]])

# ---------------- 楼宇 ----------------
rb = W["robberBldg"]
def building(name, x0, x1, y0, y1, h, mi):
    o = box_obj(name, x0, x1, y0, y1, 0, h, FAC[mi % len(FAC)])
    o.data.update()
    # 立面细节：空调机、招牌、天台水箱
    bm = bmesh.new()
    face_x = x1 if x0 < 0 else x0; out = 1 if x0 < 0 else -1
    yy = y0 + 1.2
    while yy < y1 - 1.0:
        for fl in range(1, int(h / 3.1)):
            if random.random() < 0.35:
                z = fl * 3.1 + 0.6
                add_box(bm, face_x if out > 0 else face_x - 0.55, face_x + 0.55 if out > 0 else face_x, yy, yy + 0.8, z, z + 0.5, mi=0)
        if random.random() < 0.18:  # 窗外铁笼（唐楼常见）
            fl = random.randint(1, max(1, int(h / 3.1) - 1)); z = fl * 3.1 + 0.95
            add_box(bm, face_x if out > 0 else face_x - 0.45, face_x + 0.45 if out > 0 else face_x, yy + 0.6, yy + 1.9, z, z + 1.5, mi=0)
        if random.random() < 0.14:  # 竖招牌
            add_box(bm, face_x + (0.1 if out > 0 else -1.1), face_x + (1.1 if out > 0 else -0.1), yy, yy + 0.12, 3.6, 3.6 + random.uniform(1.5, 3.5), mi=1 + random.randint(0, 2))
        yy += random.uniform(2.6, 4.2)
    add_box(bm, (x0 + x1) / 2 - 1, (x0 + x1) / 2 + 1, (y0 + y1) / 2 - 1, (y0 + y1) / 2 + 1, h, h + 1.6, mi=4)
    sign_cols = [mat(f"dsj_sign_{i}", c, 0.5) for i, c in enumerate([(0.28, 0.08, 0.06), (0.38, 0.33, 0.16), (0.1, 0.15, 0.22)])]
    new_obj(name + "_details", bm, [M["steel"], *sign_cols, M["white"]])
    # 底层卷闸
    box_obj(name + "_shutters", face_x - 0.03 * out if out > 0 else face_x - 0.02, face_x + 0.03 if out > 0 else face_x + 0.03, y0 + 0.3, y1 - 0.3, 0.15, 2.8, M["shutter"])
    return o

i = 0
for (a, b, h) in W["blocksW"]:
    building(f"bldgW_{i}", -14, -4.6, a, b, h, i); i += 1
for (a, b, h) in W["blocksE"]:
    building(f"bldgE_{i}", 4.6, 14, a, b, h, i); i += 1
# 劫匪楼：底层（门洞）、上层、一楼房间与窗口
fm = FAC[2]
box_obj("robber_g1", -14, -4.6, rb["y"][0], rb["door"]["y"][0], 0, rb["floorZ"], fm)
box_obj("robber_g2", -14, -4.6, rb["door"]["y"][1], rb["y"][1], 0, rb["floorZ"], fm)
box_obj("robber_stair", -14, -7.5, rb["door"]["y"][0], rb["door"]["y"][1], 0, rb["floorZ"], fm)
box_obj("robber_upper", -14, -4.6, rb["y"][0], rb["y"][1], rb["ceilZ"], rb["h"], fm)
rm = rb["room"]; room_m = noisy("dsj_room", (0.35, 0.37, 0.33), (0.45, 0.47, 0.42), 3)
box_obj("room_back", -14, rm["x"][0], rb["y"][0], rb["y"][1], rb["floorZ"], rb["ceilZ"], room_m)
box_obj("room_s", rm["x"][0], -4.6, rb["y"][0], rm["y"][0], rb["floorZ"], rb["ceilZ"], room_m)
box_obj("room_n", rm["x"][0], -4.6, rm["y"][1], rb["y"][1], rb["floorZ"], rb["ceilZ"], room_m)
wn = rb["win"]
box_obj("room_fa1", rm["x"][1], -4.6, rm["y"][0], wn["y"][0], rb["floorZ"], rb["ceilZ"], fm)
box_obj("room_fa2", rm["x"][1], -4.6, wn["y"][1], rm["y"][1], rb["floorZ"], rb["ceilZ"], fm)
box_obj("room_sill", rm["x"][1], -4.6, wn["y"][0], wn["y"][1], rb["floorZ"], wn["z"][0], fm)
box_obj("room_lintel", rm["x"][1], -4.6, wn["y"][0], wn["y"][1], wn["z"][1], rb["ceilZ"], fm)
box_obj("room_door", -9.05, -8.95, -30.4, -29.4, rb["floorZ"], rb["floorZ"] + 2.1, mat("dsj_door", (0.45, 0.3, 0.18), 0.6))
lp = bpy.data.lights.new("room_window_light", "AREA"); lp.energy = 220; lp.size = 1.5; lp.color = (0.85, 0.9, 1.0)
lo = bpy.data.objects.new("room_window_light", lp); lo.location = (-7.0, -29.3, 5.4); lo.rotation_euler = (math.radians(90), 0, 0); COL.objects.link(lo)
# 远处新楼
for j, (x, y, s, h) in enumerate(W["towers"]):
    box_obj(f"tower_{j}", x - s / 2, x + s / 2, y - s / 2, y + s / 2, 0, h, TOWER)
# 檐篷
for j, (a, b) in enumerate(W["canopies"]):
    o = box_obj(f"canopy_{j}", -4.6, -3.1, a, b, 3.0, 3.08, M["canopy"])
    o.rotation_euler = (0, math.radians(-6), 0)
    for yy in range(int(a) + 1, int(b), 4):
        box_obj(f"canopy_post_{j}_{yy}", -3.2, -3.12, yy, yy + 0.08, 0.15, 3.0, M["steel"])

# ---------------- 街道道具 ----------------
bm = bmesh.new(); drum = bpy.data.meshes.get("RODIN_mesh_drum")
DRUMS = bpy.data.collections.new("DSJ_Drums"); COL.children.link(DRUMS)
for r in W["barrels"]:
    x = r["x"][0] + 0.3
    while x < r["x"][1]:
        y = r["y"][0] + 0.3
        while y < r["y"][1]:
            stack = 2 if random.random() < 0.45 else 1
            for k in range(stack):
                white = random.random() >= 0.8
                if drum and not white:
                    d_ = bpy.data.objects.new("drum", drum); DRUMS.objects.link(d_)
                    d_.location = (x, y, 0.15 + k * 0.9); d_.rotation_euler = (0, 0, random.uniform(0, 6.28))
                else:
                    add_cyl(bm, 0.29, 0.29, 0.88, (x, y, 0.15 + 0.44 + k * 0.9), mi=0 if not white else 1, seg=14)
            y += 0.62
        x += 0.62
new_obj("barrels", bm, [M["barrel"], M["drum_white"]])
pa = W["pallets"]; box_obj("pallets", pa["x"][0], pa["x"][1], pa["y"][0], pa["y"][1], 0.15, 1.6, M["wrap"], 0.05)
sg = W["sign24"]
box_obj("sign24", sg["x"] - 0.3, sg["x"] + 0.3, sg["y"] - 0.04, sg["y"] + 0.04, 0.3, 1.8, mat("dsj_sign24", (0.12, 0.3, 0.7), 0.5))
if W.get("stall"):
    s_ = W["stall"]; box_obj("stall", s_["x"][0], s_["x"][1], s_["y"][0], s_["y"][1], 0.15, 1.5, mat("dsj_stall", (0.35, 0.55, 0.45), 0.6), 0.03)
if W.get("roadworks"):
    rw = W["roadworks"]; bm = bmesh.new()
    x0, x1, y0, y1 = rw["x"][0], rw["x"][1], rw["y"][0], rw["y"][1]
    for (a, b, c, d) in ((x0, x0 + 0.05, y0, y1), (x1 - 0.05, x1, y0, y1), (x0, x1, y0, y0 + 0.05), (x0, x1, y1 - 0.05, y1)):
        add_box(bm, a, b, c, d, 0.05, 1.05)
    new_obj("roadworks_fence", bm, [M["orange_fence"]])
    bm = bmesh.new()
    for k in range(4):
        add_cyl(bm, 0.38, 0.38, 0.28, (x0 + 0.6, y0 + 2.0, 0.14 + k * 0.29), seg=18)
    new_obj("tires", bm, [M["rubber"]])
    box_obj("road_dig", x0 + 0.2, x1 - 0.2, y0 + 3, y0 + 7, -0.1, 0.02, noisy("dsj_dirt", (0.2, 0.16, 0.12), (0.32, 0.27, 0.2), 8))
# 路口让路牌、路灯
bm = bmesh.new()
for (x, y) in ((-4.0, cs[1] + 0.8), (4.0, cs[0] - 0.8), (-4.0, cs[0] - 0.8)):
    add_cyl(bm, 0.04, 0.04, 2.6, (x, y, 1.3), seg=8)
for yy in range(-60, 50, 22):
    add_cyl(bm, 0.07, 0.07, 7.0, (4.2, yy, 3.5), seg=8)
new_obj("poles", bm, [M["steel"]])
# 报纸钢丝
npd = B["newspaper"]
o = bpy.data.objects.new("wire", bpy.data.meshes.new("wire")); COL.objects.link(o)
bm = bmesh.new(); add_cyl(bm, 0.01, 0.01, 9.2, (0, npd["wireY"], npd["wireZ"]), rot=(0, math.radians(90), 0), seg=6); bm.to_mesh(o.data); bm.free(); o.data.materials.append(M["steel"])

# ---------------- 路轨 ----------------
tr = W["track"]; tl = tr["y"][1] - tr["y"][0] + 4
bm = bmesh.new()
for dx in (-0.62, 0.62):
    add_box(bm, tr["x"] + dx - 0.04, tr["x"] + dx + 0.04, tr["y"][0] - 2, tr["y"][1] + 2, 0.0, 0.1)
new_obj("track_rails", bm, [M["rail"]])
bm = bmesh.new(); add_box(bm, tr["x"] - 0.85, tr["x"] + 0.85, -0.09, 0.09, -0.02, 0.05)
sl = new_obj("track_sleepers", bm, [M["sleeper"]], loc=(0, tr["y"][0] - 2, 0))
ar = sl.modifiers.new("arr", "ARRAY"); ar.count = int(tl / 0.6); ar.relative_offset_displace = (0, 0, 0); ar.use_relative_offset = False; ar.use_constant_offset = True; ar.constant_offset_displace = (0, 0.6, 0)
# 监视器区（帐篷）
dir_ = next((c for c in B["crew"] if c["id"] == "dir"), None)
bm = bmesh.new()
vx, vy = 9.0, -53.0
add_box(bm, vx - 1.6, vx + 1.6, vy - 1.6, vy + 1.6, 2.4, 2.5, mi=0)
for (dx, dy) in ((-1.5, -1.5), (1.5, -1.5), (-1.5, 1.5), (1.5, 1.5)): add_cyl(bm, 0.03, 0.03, 2.4, (vx + dx, vy + dy, 1.2), seg=6, mi=1)
add_box(bm, vx - 0.9, vx + 0.9, vy - 0.3, vy + 0.3, 0.75, 0.8, mi=1)
new_obj("video_village", bm, [M["tent"], M["steel"]])
bm = bmesh.new(); add_box(bm, vx - 0.7, vx - 0.1, vy + 0.0, vy + 0.05, 0.85, 1.25); add_box(bm, vx + 0.1, vx + 0.7, vy + 0.0, vy + 0.05, 0.85, 1.25)
new_obj("village_monitors", bm, [M["monitor"]])
# 线缆（东侧人行道 → 横街）
cu = bpy.data.curves.new("cable_main", "CURVE"); cu.dimensions = "3D"; cu.bevel_depth = 0.025
spl = cu.splines.new("POLY"); pts = [(4.4, tr["y"][1] + 1, 0.18), (4.4, cs[1], 0.18), (8.0, -52.0, 0.02)]
spl.points.add(len(pts) - 1)
for p_, (x, y, z) in zip(spl.points, pts): p_.co = (x, y, z, 1)
co = bpy.data.objects.new("cable_main", cu); co.data.materials.append(M["cable"]); COL.objects.link(co)

# ---------------- 人物（Rodin 模型 + 骨骼，逐采样还原动作） ----------------
import sys, importlib
if HERE not in sys.path: sys.path.insert(0, HERE)
import dsj_rig as RG; importlib.reload(RG)
from mathutils import Quaternion
RIG_VER = 3
PEOPLE = bpy.data.collections.new("DSJ_People"); COL.children.link(PEOPLE)
TEMPLATES = {}
def template(key):
    if key in TEMPLATES: return TEMPLATES[key]
    src = bpy.data.meshes.get("RODIN_mesh_" + key) or bpy.data.meshes.get("RODIN_mesh_extra")
    H = max(v.co.z for v in src.vertices)
    rm = bpy.data.meshes.get("RIGGED_" + key)
    if rm is None or rm.get("rig_ver") != RIG_VER:
        if rm is not None: rm.name = "RIGGED_old_" + key
        rm = src.copy(); rm.name = "RIGGED_" + key
        tmp = bpy.data.objects.new("_w_" + key, rm); COL.objects.link(tmp)
        RG.apply_weights(tmp, H); bpy.data.objects.remove(tmp, do_unlink=True)
        rm["rig_ver"] = RIG_VER; rm.use_fake_user = True
    arm = bpy.data.armatures.get("RIGT_" + key)
    if arm is None or arm.get("rig_ver") != RIG_VER:
        if arm is not None: arm.name = "RIGT_old_" + key
        arm = RG.build_armature("RIGT_" + key, H, scene); arm["rig_ver"] = RIG_VER
    TEMPLATES[key] = (rm, arm, H, RG.Solver(arm))
    return TEMPLATES[key]

def pose_dirs(kind, phase, mp):
    legs = kind.replace("_aim", "")
    d = RG.proc_pose(legs if legs in ("walk", "run", "crouch", "kneel", "sit", "jump") else "stand", phase)
    if kind.endswith("_aim") or kind in ("aim", "aim2"):
        arms = RG.proc_pose("aim" if kind in ("aim", "kneel_aim", "crouch_aim") else "aim2")
        for b in ("upper_arm.L", "forearm.L", "upper_arm.R", "forearm.R"): d[b] = arms[b]
    if kind == "raise":
        r = RG.proc_pose("raise")
        for b in ("upper_arm.L", "forearm.L", "upper_arm.R", "forearm.R"): d[b] = r[b]
    if mp:
        for b, v in mp.items():
            if b in d: d[b] = Vector(v)
        # 脚：跟随小腿
        for side in "LR":
            sh = d[f"shin.{side}"]; d[f"foot.{side}"] = (Vector((0, 1, 0)) + sh * 0.3).normalized()
    return d

BONE_PATHS = [f'pose.bones["{b}"].rotation_quaternion' for b in RG.ORDER]
def bake_entity(ao, rows, H, S, holder_name):
    fr_, locs, rots = [], [], []
    quats = {b: [] for b in RG.ORDER}; prevq = {}
    for (i, x, y, z, yaw, kind, phase, mp) in rows:
        f = float(FR[i]["f"]); fr_.append(f)
        d = pose_dirs(kind, phase, mp)
        lie = kind == "lie"
        drop = 0.0 if lie else RG.ground_drop(d, H)
        curb = 0.15 if (3.0 < abs(x) < 4.6 and z < 0.5) else 0.0
        locs.append((x, y, z + curb + drop + (0.22 if lie else 0.0)))
        rots.append((math.radians(-86) if lie else 0.0, yaw))
        q = S.solve(d)
        for b in RG.ORDER:
            qq = q.get(b, Quaternion())
            if b in prevq and prevq[b].dot(qq) < 0: qq = -qq
            prevq[b] = qq; quats[b].append(qq)
    # 动作切换处做 ±0.4 秒的姿势过渡（骨骼四元数加权平均），避免一帧内突变
    kinds_ = [r[5] for r in rows]; mps_ = [r[7] is not None for r in rows]
    chg = [k for k in range(1, len(rows)) if kinds_[k] != kinds_[k - 1] or mps_[k] != mps_[k - 1]]
    if chg:
        W_ = [0.15, 0.5, 1.0, 0.5, 0.15]; zone = set()
        for c in chg: zone.update(range(max(0, c - 3), min(len(rows), c + 3)))
        for b in RG.ORDER:
            src = quats[b]; out = list(src)
            for k in zone:
                acc = Quaternion((0, 0, 0, 0)); wsum = 0.0
                for t, w in zip(range(-2, 3), W_):
                    j = k + t
                    if 0 <= j < len(src):
                        q = src[j] if src[j].dot(src[k]) >= 0 else -src[j]
                        acc = Quaternion((acc[0] + q[0] * w, acc[1] + q[1] * w, acc[2] + q[2] * w, acc[3] + q[3] * w)); wsum += w
                acc.normalize(); out[k] = acc
            quats[b] = out
        zl = [l[2] for l in locs]
        for k in zone:
            ws = [(zl[k + t], w) for t, w in zip(range(-2, 3), W_) if 0 <= k + t < len(zl)]
            locs[k] = (locs[k][0], locs[k][1], sum(z * w for z, w in ws) / sum(w for _, w in ws))
        rx = [r[0] for r in rots]
        for k in zone:
            ws = [(rx[k + t], w) for t, w in zip(range(-2, 3), W_) if 0 <= k + t < len(rx)]
            rots[k] = (sum(z * w for z, w in ws) / sum(w for _, w in ws), rots[k][1])
    bake_loc(ao, fr_, locs)
    bake_channel(ao, "rotation_euler", 0, fr_, [r[0] for r in rots]); bake_channel(ao, "rotation_euler", 2, fr_, unwrap([r[1] for r in rots]))
    for b, path in zip(RG.ORDER, BONE_PATHS):
        ao.pose.bones[b].rotation_mode = "QUATERNION"
        for k in range(4): bake_channel(ao, path, k, fr_, [q[k] for q in quats[b]])
    # 可见性：连续采样段可见，段间与前后隐藏
    vf, vv = [], []
    runs = []; st = rows[0][0]; pv = rows[0][0]
    for r in rows[1:]:
        if r[0] - pv > 2: runs.append((st, pv)); st = r[0]
        pv = r[0]
    runs.append((st, pv))
    if runs[0][0] > 0: vf.append(1.0); vv.append(False)
    for a_, b_ in runs:
        vf.append(float(FR[a_]["f"])); vv.append(True)
        if b_ + 1 < len(FR): vf.append(float(FR[b_]["f"]) + 1); vv.append(False)
    order = sorted(range(len(vf)), key=lambda k: vf[k]); vf = [vf[k] for k in order]; vv = [vv[k] for k in order]
    bake_vis(ao, vf, vv)
    return vf, vv

PROP_MESH = {"rifle": bpy.data.meshes.get("RODIN_mesh_rifle"), "pistol": bpy.data.meshes.get("RODIN_mesh_pistol")}
ENT_OBJ = {}
for e in B["entities"]:
    rm, arm, H, S = template(e["tpl"])
    ao = bpy.data.objects.new("E_" + e["id"], arm); PEOPLE.objects.link(ao)
    mo = bpy.data.objects.new("M_" + e["id"], rm); PEOPLE.objects.link(mo); mo.parent = ao
    md = mo.modifiers.new("arm", "ARMATURE"); md.object = ao
    view_layer = bpy.context.view_layer
    scene.view_layers[0].update()
    if e["main"] and e["role"] in RING:
        rb_ = bmesh.new(); add_cyl(rb_, 0.4, 0.4, 0.012, (0, 0, 0.02), seg=28)
        new_obj("R_" + e["id"], rb_, [RING[e["role"]]], parent=ao, col=PEOPLE)
    vf, vv = bake_entity(ao, e["s"], H, S, e["id"])
    for c in ao.children: bake_vis(c, vf, vv)
    if e.get("prop") and PROP_MESH.get(e["prop"]):
        po = bpy.data.objects.new("G_" + e["id"], PROP_MESH[e["prop"]]); PEOPLE.objects.link(po)
        po.parent = ao; po.parent_type = "BONE"; po.parent_bone = "hand.R"
        po.location = (0, -0.05 if e["prop"] == "pistol" else 0.18, 0); po.rotation_euler = (0, 0, 0)
        # 枪只在枪战段出现
        pf = [1.0, float(int((330 - B["t0"]) * 24)), float(B["frames_total"])]
        bake_vis(po, [1.0, float(int((330 - B["t0"]) * 24))], [False, True])
    ENT_OBJ[e["id"]] = ao
print("[DSJ] people", len(ENT_OBJ), "templates", list(TEMPLATES))

# ---------------- 车辆 ----------------
PAINT = {"blue": (0.03, 0.06, 0.16), "silver": (0.55, 0.56, 0.57), "grey": (0.32, 0.33, 0.34), "teal": (0.08, 0.32, 0.32)}
def car(name, paint, glass=True):
    bm = bmesh.new()
    add_box(bm, -0.86, 0.86, -2.2, 2.2, 0.32, 0.98, mi=0)
    add_box(bm, -0.78, 0.78, -0.95, 1.05, 0.98, 1.44, mi=1)
    add_box(bm, -0.74, 0.74, -0.85, 0.95, 1.43, 1.47, mi=0)
    for (x, y) in ((-0.82, 1.35), (0.82, 1.35), (-0.82, -1.35), (0.82, -1.35)):
        add_cyl(bm, 0.31, 0.31, 0.2, (x, y, 0.31), rot=(0, math.radians(90), 0), seg=16, mi=2)
    add_box(bm, -0.7, -0.45, 2.19, 2.22, 0.72, 0.84, mi=3); add_box(bm, 0.45, 0.7, 2.19, 2.22, 0.72, 0.84, mi=3)
    add_box(bm, -0.75, -0.5, -2.22, -2.19, 0.75, 0.88, mi=4); add_box(bm, 0.5, 0.75, -2.22, -2.19, 0.75, 0.88, mi=4)
    o = new_obj(name, bm, [mat(f"dsj_paint_{name}", paint, 0.25, 0.3), M["glass"] if glass else M["darkglass"], M["rubber"], M["lamp"], M["redwhite"]])
    md = o.modifiers.new("bevel", "BEVEL"); md.width = 0.05; md.segments = 2
    return o

def van(name):
    bm = bmesh.new()
    add_box(bm, -1.0, 1.0, -2.7, 2.7, 0.35, 2.4, mi=0)
    add_box(bm, -1.01, 1.01, -2.71, 2.71, 1.0, 1.25, mi=1)
    add_box(bm, -1.02, 1.02, -1.5, 2.2, 1.55, 2.1, mi=2)
    add_box(bm, -0.6, 0.6, 1.5, 2.0, 2.4, 2.55, mi=3)
    for (x, y) in ((-0.95, 1.8), (0.95, 1.8), (-0.95, -1.8), (0.95, -1.8)):
        add_cyl(bm, 0.36, 0.36, 0.24, (x, y, 0.36), rot=(0, math.radians(90), 0), seg=16, mi=4)
    o = new_obj(name, bm, [M["white"], M["van_red"], M["darkglass"], mat("dsj_lightbar", (0.1, 0.2, 0.9), 0.3, emit=(0.2, 0.3, 1.0), estr=3), M["rubber"]])
    md = o.modifiers.new("bevel", "BEVEL"); md.width = 0.06; md.segments = 2
    return o

def rodin_car(o, key):
    me = bpy.data.meshes.get(f"RODIN_mesh_{key}")
    if me:
        o.data = me
        for md in list(o.modifiers): o.modifiers.remove(md)
    return o
for c2 in B.get("cars2", []):
    key = c2["tpl"]
    if "static" in c2:
        x, y, yaw = c2["static"]
        o = car("PK_" + c2["id"], (0.5, 0.5, 0.5), glass=False); rodin_car(o, key)
        o.location = (x, y, 0); o.rotation_euler = (0, 0, -math.radians(yaw))
    else:
        rows = c2["rows"]; o = car("MV_" + c2["id"], (0.5, 0.5, 0.5), glass=False); rodin_car(o, key)
        fr_ = [float(FR[r[0]]["f"]) for r in rows]
        bake_loc(o, fr_, [(r[1], r[2], 0) for r in rows]); bake_channel(o, "rotation_euler", 2, fr_, unwrap([-math.radians(r[3]) for r in rows]))
        vf = [1.0, fr_[0], fr_[-1] + 1] if fr_[0] > 1 else [fr_[0], fr_[-1] + 1]; vv = [False, True, False] if fr_[0] > 1 else [True, False]
        bake_vis(o, vf, vv)
for ci, c in enumerate(B["cars"]):
    o = van("CAR_" + c["id"]) if c["id"] == "van" else car("CAR_" + c["id"], PAINT.get(c["id"], (0.4, 0.4, 0.4)))
    rodin_car(o, {"van": "van", "blue": "car_navy"}.get(c["id"], "car_silver"))
    ser = [fr["cars"][ci] for fr in FR]; last = next(s for s in ser if s)
    locs, rots, vis = [], [], []
    for s in ser:
        if s: last = s
        locs.append((last[0], last[1], 0)); rots.append((0, 0, -math.radians(last[2]))); vis.append(bool(s))
    bake_loc(o, FRAMES, locs); bake_rot(o, FRAMES, [(0, 0, r) for r in unwrap([r[2] for r in rots])], axes=(2,)); bake_vis(o, FRAMES, vis)

# ---------------- 吊臂与摄影机 ----------------
def build_crane():
    bm = bmesh.new()
    add_box(bm, -0.75, 0.75, -1.35, 1.35, 0.18, 0.62, mi=1)
    for (x, y) in ((-0.62, 1.0), (0.62, 1.0), (-0.62, -1.0), (0.62, -1.0)):
        add_cyl(bm, 0.14, 0.14, 0.12, (x, y, 0.17), rot=(0, math.radians(90), 0), seg=12, mi=2)
    add_cyl(bm, 0.24, 0.3, 1.1, (0, 0, 1.15), seg=16, mi=0)
    add_box(bm, -0.45, 0.45, -1.3, -0.6, 0.62, 1.0, mi=0)
    dolly = new_obj("RIG_dolly", bm, [M["crane"], M["crane_y"], M["rubber"]])
    pivot = bpy.data.objects.new("RIG_pivot", None); COL.objects.link(pivot); pivot.parent = dolly; pivot.location = (0, 0, 1.7)
    bm = bmesh.new()
    add_box(bm, -3.3, 3.6, -0.11, 0.11, -0.13, 0.13, mi=0)
    add_box(bm, -3.4, -2.5, -0.35, 0.35, -0.45, 0.35, mi=1)
    add_box(bm, -0.25, 0.25, -0.3, 0.3, -0.3, 0.3, mi=1)
    arm1 = new_obj("RIG_arm1", bm, [M["crane"], M["steel"]], parent=pivot)
    bm = bmesh.new(); add_box(bm, 0, 1, -0.085, 0.085, -0.1, 0.1)
    arm2 = new_obj("RIG_arm2", bm, [M["crane"]], parent=pivot, loc=(3.4, 0, 0))
    bm = bmesh.new(); add_box(bm, 0, 1, -0.065, 0.065, -0.075, 0.075)
    arm3 = new_obj("RIG_arm3", bm, [M["crane"]], parent=pivot, loc=(5.0, 0, 0))
    # 遥控云台 + 胶片摄影机
    head = bpy.data.objects.new("RIG_head", None); COL.objects.link(head)
    bm = bmesh.new()
    add_cyl(bm, 0.05, 0.05, 0.5, (0, 0, 0.3), seg=10)
    add_box(bm, -0.32, 0.32, -0.05, 0.05, 0.02, 0.08); add_box(bm, -0.32, -0.27, -0.05, 0.05, -0.2, 0.05); add_box(bm, 0.27, 0.32, -0.05, 0.05, -0.2, 0.05)
    yoke = new_obj("RIG_yoke", bm, [M["crane"]], parent=head)
    bm = bmesh.new()
    add_box(bm, -0.12, 0.12, -0.25, 0.2, -0.15, 0.13, mi=0)
    add_cyl(bm, 0.15, 0.15, 0.1, (0, -0.08, 0.27), rot=(0, math.radians(90), 0), seg=18, mi=0)
    add_cyl(bm, 0.15, 0.15, 0.1, (0, 0.16, 0.27), rot=(0, math.radians(90), 0), seg=18, mi=0)
    add_cyl(bm, 0.065, 0.075, 0.26, (0, 0.33, -0.01), rot=(math.radians(90), 0, 0), seg=16, mi=1)
    add_box(bm, -0.15, 0.15, 0.46, 0.5, -0.12, 0.1, mi=0)
    add_box(bm, 0.12, 0.2, -0.25, -0.1, -0.02, 0.06, mi=0)
    filmcam = new_obj("RIG_filmcam", bm, [M["camera"], M["lens"]], parent=head)
    if bpy.data.meshes.get("RODIN_mesh_filmcam"):
        filmcam.data = bpy.data.meshes["RODIN_mesh_filmcam"]
    return dolly, pivot, arm1, arm2, arm3, head, filmcam, yoke

dolly, pivot, arm1, arm2, arm3, head, filmcam, yoke = build_crane()
# 摄影机取景范围（半透明橙色线框，6 米深）
_L, _th = 6.0, math.tan(math.radians(23))
bm = bmesh.new()
_o = Vector((0, 0.3, 0)); _cs = [Vector((sx * _L * _th, 0.3 + _L, sz * _L * _th / 2.35)) for sx, sz in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
def _tube(bm, p, q, r=0.008):
    d = q - p; ln = d.length; mid = (p + q) / 2
    res = bmesh.ops.create_cone(bm, cap_ends=False, segments=6, radius1=r, radius2=r, depth=ln)
    bmesh.ops.rotate(bm, verts=res["verts"], cent=(0, 0, 0), matrix=Vector((0, 0, 1)).rotation_difference(d.normalized()).to_matrix())
    bmesh.ops.translate(bm, vec=mid, verts=res["verts"])
for k_ in range(4): _tube(bm, _o, _cs[k_]); _tube(bm, _cs[k_], _cs[(k_ + 1) % 4])
fru = new_obj("RIG_frustum", bm, [mat("dsj_frustum", (1.0, 0.45, 0.15), 0.5, emit=(1.0, 0.45, 0.15), estr=4.0, alpha=0.6)], parent=filmcam)

# 吊臂车上的线缆到人行道
bm = bmesh.new(); add_cyl(bm, 0.025, 0.025, 2.2, (1.1, 0, 0.2), rot=(0, math.radians(90), 0), seg=6)
new_obj("RIG_cable_stub", bm, [M["cable"]], parent=dolly)
# 跟焦员旁的监视器推车
bm = bmesh.new(); add_box(bm, -0.35, 0.35, -0.25, 0.25, 0.1, 0.9, mi=0); add_box(bm, -0.3, 0.3, -0.02, 0.02, 0.95, 1.35, mi=1)
cart = new_obj("RIG_monitor_cart", bm, [M["steel"], M["monitor"]], parent=dolly, loc=(1.6, 1.4, 0))

dl, pr, a2l, a2s, a3l, a3s, hl, hr = [], [], [], [], [], [], [], []
for fr in FR:
    cx, cy, cz, yaw, pitch, _ = fr["cam"]; bx, by = fr["base"]
    tip = Vector((cx, cy, cz + 0.55)); piv = Vector((bx, by, 1.7))
    d = tip - piv; L = d.length
    ayaw = math.atan2(d.y, d.x); apitch = math.atan2(d.z, math.hypot(d.x, d.y))
    dl.append((bx, by, 0.1)); pr.append((0, -apitch, ayaw))
    ext = max(L - 3.4, 0.4)
    a2l.append((3.4, 0, 0)); a2s.append((ext * 0.6, 1, 1)); a3l.append((3.4 + ext * 0.5, 0, 0)); a3s.append((ext * 0.5, 1, 1))
    hl.append((cx, cy, cz)); hr.append((math.radians(pitch), 0, -math.radians(yaw)))
bake_loc(dolly, FRAMES, dl)
pz = unwrap([p[2] for p in pr]); bake_rot(pivot, FRAMES, [(0, p[1], z) for p, z in zip(pr, pz)], axes=(1, 2))
bake_loc(arm2, FRAMES, a2l); bake_scale(arm2, FRAMES, a2s, axes=(0,)); bake_loc(arm3, FRAMES, a3l); bake_scale(arm3, FRAMES, a3s, axes=(0,))
bake_loc(head, FRAMES, hl)
yz = unwrap([h[2] for h in hr]); bake_rot(filmcam, FRAMES, [(h[0], 0, z) for h, z in zip(hr, yz)], axes=(0, 2))
bake_rot(yoke, FRAMES, [(0, 0, z) for z in yz], axes=(2,))

# ---------------- 报纸、枪火、烟 ----------------
bm = bmesh.new(); add_box(bm, -0.28, 0.28, -0.2, 0.2, 0, 0.005)
paper = new_obj("FX_paper", bm, [M["paper"]])
locs, vis = [], []
for fr in FR:
    p = fr.get("paper"); vis.append(bool(p)); locs.append(tuple(p) if p else (-2, -4.7, 1.25))
bake_loc(paper, FRAMES, locs); bake_vis(paper, FRAMES, vis)

shooters = sorted({s for fr in FR for s in fr.get("flash", [])})
for sid in shooters:
    gun = bpy.data.objects.get("G_P_" + sid); holder = gun or ENT_OBJ.get("P_" + sid)
    if holder is None: continue
    bm = bmesh.new(); add_cyl(bm, 0.0, 0.14, 0.4, (0, 0.2, 0), rot=(math.radians(-90), 0, 0), seg=8)
    fl = new_obj("FX_flash_" + sid, bm, [M["flash"]], col=PEOPLE)
    fl.parent = holder
    fl.location = (0, 0.5, 0.02) if gun and "rifle" in gun.data.name else (0, 0.14, 0.02)
    vf, vv = [], []; last = None
    for fr in FR:
        v = sid in fr.get("flash", [])
        if v != last: vf.append(float(fr["f"])); vv.append(v); last = v
    bake_vis(fl, vf, vv)

def smoke(name, center, t0, t1, rmax):
    bm = bmesh.new()
    for k in range(7):
        add_sph(bm, random.uniform(0.5, 1.0), (random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(0.3, 1.6)), seg=10)
    o = new_obj(name, bm, [M["smoke"]], loc=center)
    sc, vis = [], []
    for fr in FR:
        f_ = (fr["t"] - t0) / (t1 - t0)
        on = 0 <= f_ <= 1.25; s = max(0.05, min(1.0, f_ * 1.5)) * rmax
        sc.append((s, s, s)); vis.append(on)
    bake_scale(o, FRAMES, sc); bake_vis(o, FRAMES, vis)
smoke("FX_smoke_barrels", (-3.6, -16.0, 0), 365.0, 386.0, 1.6)
smoke("FX_smoke_junction", (-1.0, -48.0, 0), 462.0, 487.75, 3.0)
smoke("FX_smoke_end", (-0.5, -12.0, 0), 478.0, 487.75, 2.2)

# ---------------- 观察机位遮挡：挡住观察者视线的车辆、烟团在该时段隐藏 ----------------
for name, idx in B.get("occl", {}).items():
    o = bpy.data.objects.get(name)
    if o is None: continue
    hid = set(idx); fc = None
    if o.animation_data and o.animation_data.action:
        fc = next((f for f in _fcurves(o) if f.data_path == "hide_render"), None)
    vis = [(fc.evaluate(f) < 0.5 if fc else True) and (k not in hid) for k, f in enumerate(FRAMES)]
    ch = [0] + [k for k in range(1, len(vis)) if vis[k] != vis[k - 1]]
    bake_vis(o, [FRAMES[k] for k in ch], [vis[k] for k in ch])

# ---------------- 灯光 ----------------
sun = bpy.data.lights.new("DSJ_sun", "SUN"); sun.energy = 3.2; sun.angle = math.radians(12); sun.color = (0.95, 0.96, 1.0)
so = bpy.data.objects.new("DSJ_sun", sun); so.rotation_euler = (math.radians(38), math.radians(12), math.radians(-35)); COL.objects.link(so)

# ---------------- 渲染机位（上层：现场近景跟拍） ----------------
cam_data = bpy.data.cameras.new("TopCam"); cam_data.lens = 21; cam_data.sensor_width = 36; cam_data.clip_end = 600
tc = bpy.data.objects.new("TopCam", cam_data); COL.objects.link(tc); scene.camera = tc
locs, rots = [], []
for fr in FR:
    px, py, pz, tx, ty, tz = fr["near"]
    p = Vector((px, py, pz)); t = Vector((tx, ty, tz))
    q = (t - p).to_track_quat("-Z", "Y"); e = q.to_euler()
    locs.append((px, py, pz)); rots.append((e.x, e.y, e.z))
bake_loc(tc, FRAMES, locs)
rz = unwrap([r[2] for r in rots]); bake_rot(tc, FRAMES, [(r[0], r[1], z) for r, z in zip(rots, rz)])

# ---------------- 保存并渲染 ----------------
os.makedirs(OUT, exist_ok=True)
blend = os.path.join(HERE, "dsj_oner.blend")
try:
    bpy.ops.wm.save_as_mainfile(filepath=blend)
except Exception as ex:
    print("save failed:", ex)
print(f"[DSJ] scene built: {len(scene.collection.all_objects)} objects, frames 1–{NF}")
if START_RENDER and not bpy.app.background:
    scene.render.use_overwrite = False   # 中断后重跑会跳过已渲染的帧
    scene.render.use_placeholder = True
    bpy.ops.render.render("INVOKE_DEFAULT", animation=True)
