# 第 3b 步：pycolmap 重建（模板——pycolmap 版本不同 API 会变，先 help(pycolmap) 核对函数名）
# 《大事件》里实际做法：在 Mac 上用 Blender 自带的 Python 跑（pip install --target pylib_colmap pycolmap，
# 再用 subprocess 以 PYTHONPATH=pylib_colmap 启动 Blender 的 python），后台运行、写日志，定时查看。
# 输入：sfm/f*.jpg（每 3 帧一张）、masks/（COLMAP 掩码：文件名 = 图片名 + .png，0 = 忽略，遮掉人、车、字幕）、
#       pairs_long.txt（可选：机位回到同一地方时的远距离配对，每行 "imgA imgB"）
# 输出：sparse/<k>/（多个子模型很正常——暗处、快速移动、进屋都会断开）
import sys, os, pycolmap
from pathlib import Path
root = Path(sys.argv[1]); img = root / "sfm"; db = root / "db.db"; out = root / "sparse"; out.mkdir(exist_ok=True)
HFOV = float(os.environ.get("HFOV", "42"))          # 由 vp_focal.py 求得；全片定焦时固定内参
W, H = 1280, int(os.environ.get("IMG_H", "554")); import math
f = (W / 2) / math.tan(math.radians(HFOV / 2))
cam = pycolmap.Camera(model="SIMPLE_PINHOLE", width=W, height=H, params=[f, W / 2, H / 2])
ro = pycolmap.ImageReaderOptions(); ro.mask_path = str(root / "masks") if (root / "masks").exists() else ""
pycolmap.extract_features(db, img, camera_mode=pycolmap.CameraMode.SINGLE, camera_model="SIMPLE_PINHOLE", reader_options=ro)
# 只做顺序匹配会漏掉“绕回来”的闭环；长镜头一定要补远距离配对
sm = pycolmap.SequentialMatchingOptions(); sm.overlap = 12; sm.loop_detection = False
pycolmap.match_sequential(db, matching_options=sm)
if (root / "pairs_long.txt").exists():
    # 对应 COLMAP 命令行的 matches_importer --match_list_path；pycolmap 里的名字随版本变，逐个试
    fn = next((getattr(pycolmap, n) for n in ("match_image_pairs", "match_imported_pairs") if hasattr(pycolmap, n)), None)
    if fn is None: print("WARN: 这个 pycolmap 没有按列表配对的接口，改用 colmap 命令行 matches_importer")
    else: fn(db, str(root / "pairs_long.txt"))   # 签名以 help(fn) 为准
mo = pycolmap.IncrementalPipelineOptions(); mo.ba_refine_focal_length = False; mo.ba_refine_extra_params = False
maps = pycolmap.incremental_mapping(db, img, out, options=mo)
for k, m in maps.items(): print(k, m.summary())
# 《大事件》最终用的是“全局式重建 + 重力先验”（每帧竖直消失点给出重力方向），比增量式稳得多；
# 若装的 pycolmap 有 global_mapping（GLOMAP 合入版），优先用它并传入重力先验。
