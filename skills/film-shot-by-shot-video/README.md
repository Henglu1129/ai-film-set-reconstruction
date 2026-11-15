# 视频拉片 · 脚本索引

来源项目：李沧东《可能的爱》（2026）1:39:24–1:55:52，16分28秒，56 个镜头。

- `SKILL.md`：skill 正文，先读这个。
- `scripts/`：这次实际跑过的脚本，已经改成从工作目录 `WORK_DIR` 读写、从 `config.json` 读片名和时间码偏移。模型目录用环境变量 `MODELS` 指定。
- `examples/possible-love/`：这部片子的 `analysis.py`（56 镜 × 8 字段 + 场景分段）、`anchors.py`（光源 / 主色锚点）、`config.json`，以及公开版拉片笔记（不含台词）。

| 脚本 | 做什么 | 在哪跑 |
|---|---|---|
| `01_device_encode.sh` | 4K 片源分块转 720p（每块 240.24 秒，一次 device_bash 调用一块）、单独导音频、拼接 | 用户电脑 |
| `02_detect_cuts.py` | Adaptive 2.5 / Adaptive 1.8 / Hash 三路镜头检测 | 云端 |
| `02b_build_shots.py` | 核验后的切点 → `shots.json`；每镜采样帧、重叠字幕、声音标签；8 镜一页的帧拼图 | 云端 |
| `03_subtitle_segments.py` | 硬字幕分段（白字黑边 mask + IoU）+ 每段 OCR + 字幕带存图 | 云端 |
| `03b_subtitle_sheets.sh` | 字幕带拼成校对页，人工逐条校对 | 云端 |
| `04_audio_tags.py` | 每 2 秒做一次 AudioSet 声音事件分类（配乐 / 环境声） | 云端 |
| `04b_asr_whisper.py` | （可选）没有硬字幕时用 whisper 转录 | 云端 |
| `05_person_seg.py` | YOLOv8n-seg 逐帧人像分割 → `seg.pkl` | 云端（后台） |
| `06_anchor_grid.py` | 10×6 网格三联帧，读光源 / 主色坐标 | 云端 |
| `07_render_video.py` | 逐帧合成（人物轮廓 + 自动避让的画面标注 + 面板 + 时间轴）并编码 | 云端（后台） |
| `08_export_notes.py` | 导出 Markdown 拉片笔记（可选附台词） | 云端 |
| `templates/` | `config.example.json`、`analysis_template.py`、`anchors_template.py`、`fixsubs_template.py` | — |

依赖：`ffmpeg`、ImageMagick（`montage`）、`scenedetect`、`opencv-python-headless`、`numpy`、`Pillow`、`rapidocr_onnxruntime`、`sherpa-onnx`、`ultralytics`，字体用 [霞鹜文楷](https://github.com/lxgw/LxgwWenKai) Light。

公开版不包含影片对白。`subs_clean.json`（校对后的台词）只留在本地工作目录。
