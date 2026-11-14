# 第 6 步：同机位验收图——用“原片机位”（CHK_FilmCam，逐帧动画来自反求结果）渲染指定帧，和原片并排
# 用法：execute_blender_code 执行；FRAMES 选在采样网格上（帧号 % STEP == 0，否则插值机位和检测对不上）
import bpy, os, mathutils
OUT = "/Users/<you>/.../qa_round1"; FRAMES = list(range(0, 9768, 72)); STEP = 3
HIDE_PREFIX = ("RIG_", "E_CREW", "M_CREW", "R_CREW", "R_PP", "FX_paper")   # 吊臂、剧组、站位圈等只属于“身后视角”的东西
s = bpy.context.scene; cam = bpy.data.objects["CHK_FilmCam"]; os.makedirs(OUT, exist_ok=True)
old = (s.camera, s.render.resolution_x, s.render.resolution_y)
s.camera = cam; s.render.resolution_x, s.render.resolution_y = 1280, 554     # 与原片同画幅（含焦距一致）
hidden = [o for o in bpy.data.objects if o.name.startswith(HIDE_PREFIX) and not o.hide_render]
for o in hidden: o.hide_render = True
def inside_car(c):
    # 机位在车里时：隐藏车壳、显示车内（座椅、车门内板、车顶内衬）；否则相反——否则会出现“车没了”
    car = bpy.data.objects.get("CAR_blue"); inner = bpy.data.objects.get("CAR_blue_int")
    if not car or not inner: return
    bb = [car.matrix_world @ mathutils.Vector(v) for v in car.bound_box]
    lo = [min(v[i] for v in bb) for i in range(3)]; hi = [max(v[i] for v in bb) for i in range(3)]
    ins = all(lo[i] <= c[i] <= hi[i] for i in range(3)); car.hide_render = ins; inner.hide_render = not ins
try:
    for f in FRAMES:
        f -= f % STEP; s.frame_set(f); inside_car(cam.matrix_world.translation)
        s.render.filepath = os.path.join(OUT, f"chk_{f:05d}.jpg"); bpy.ops.render.render(write_still=True)
finally:
    for o in hidden: o.hide_render = False
    s.camera, s.render.resolution_x, s.render.resolution_y = old
