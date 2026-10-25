# 多镜头群戏拍摄现场还原 · 脚本索引

来源项目：《周处除三害》灵修堂（1:45:06.6–1:52:50.1，138 个镜头 → 25 个机位、9 组光源）。

- `SKILL.md`：skill 正文，先读这个。
- `scripts/`：这次实际跑过的脚本，按流程分组。路径、时间码、房间尺寸、机位参数都是这部片子的，换片时要逐项改。

| 目录 | 内容 | 在哪跑 |
|---|---|---|
| 01_cuts | 找剪辑点（含枪口闪光排除）、合并误切、镜头运动统计、中间帧抽取。**脚本暂未收录**，算法和参数写在 `SKILL.md` 第 2、3 步 | 用户电脑（shell） |
| 02_geometry | SfM（pycolmap）、标定点观测 `obs_v4.json`、联合 BA / 多起点、逐机位 PnP、SfM 对齐到世界；`room_final.json` 是解出的房间参数 | 云端容器 |
| 03_plan | 房间模型与线框验收、机位表 → `plan_data.json`、群演座位与命运；`plan_data.example.json` 是这部片子的实际数据，可以当格式参考 | 云端容器 |
| 04_blender | `lxt_build.py`：Blender 构建 + 每镜头俯视渲染 + 锚点 + 同机位验收渲染 | Blender（Blender MCP 的 execute_blender_code） |
| 05_video | `compose_panels.py` / `compose_panels_en.py`：1080×1560 面板合成（中文 / 英文）；`encode_seg.py`：分段编码并烧英文字幕 | 用户电脑（shell） |
| 06_subtitles | 字幕带 OCR、字幕事件检测与分组、英文字幕 cues（公开版只留写法示例，不含对白译文） | 云端容器 |
| 07_showcase | 总图与分段方案图、9 张中文 / 英文展示卡、片头片尾卡 | 云端容器 |

`04_blender/lxt_build.py` 和 `05_video/` 下的脚本，是云端留存的版本，比项目最后一版略早，主要差别是读的数据文件名（`plan_data.json` 对应后来的 `plan_data_v5.json`）。

在 Blender 里加载构建模块：

```python
import importlib.util, sys, os
os.environ["LXT_PROJ"] = "/path/to/项目"   # 里面要有 work/plan/plan_data.json
spec = importlib.util.spec_from_file_location("lxt_build", "/path/to/scripts/04_blender/lxt_build.py")
L = importlib.util.module_from_spec(spec); sys.modules["lxt_build"] = L; spec.loader.exec_module(L)
L.build_all()                                # 搭场景
L.start_top_renders("/path/to/render_top")   # 每个镜头一张俯视图 + anchors.json
```
