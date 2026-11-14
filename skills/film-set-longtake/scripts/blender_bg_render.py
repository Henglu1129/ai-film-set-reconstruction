# 第 7 步：在用户已打开的 Blender 里后台逐帧渲染（不重启、不阻塞界面、单次 MCP 调用不会超时）
# 用法：通过 Blender MCP 的 execute_blender_code 执行本文件内容，改好 OUT / F0 / F1 / CAM。
# 原理：bpy.app.timers 每次 tick 渲染 TICK 帧然后让出控制权；已存在的帧跳过（可断点续渲）；全部完成写 _DONE。
# 《大事件》：EEVEE、1080×780、约 57 帧/分钟（M 系列 Mac），9768 帧约 3 小时。
import bpy, os, time
OUT = "/Users/<you>/.../render_full"; F0, F1 = 1, 9768; TICK = 12; CAM = "TopCam"
os.makedirs(OUT, exist_ok=True); s = bpy.context.scene
s.render.image_settings.file_format = "JPEG"; s.render.image_settings.quality = 92
state = {"f": F0, "t0": time.time()}
def _tick():
    s.camera = bpy.data.objects[CAM]; n = 0
    while state["f"] <= F1 and n < TICK:
        f = state["f"]; p = os.path.join(OUT, f"{f:05d}.jpg")
        if not os.path.exists(p):
            s.frame_set(f); s.render.filepath = p; bpy.ops.render.render(write_still=True); n += 1
        state["f"] += 1
    if state["f"] > F1:
        open(os.path.join(OUT, "_DONE"), "w").write(f"{time.time() - state['t0']:.0f}s"); return None
    return 0.05
bpy.app.timers.register(_tick, first_interval=0.5)
print("render started", F0, F1)
# 查看进度：device_bash 里 ls render_full | wc -l；停止：bpy.app.timers.unregister(_tick)（需在同一会话里拿到函数引用）
