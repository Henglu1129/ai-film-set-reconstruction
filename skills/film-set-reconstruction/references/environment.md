# 运行环境与工具用法

## 三个地方
1. **用户的 Mac**：片源、项目文件夹、开着的 Blender。
   - `device_bash`：Mac 上的 Linux 虚拟机，项目文件夹挂载在 `$HOME/mnt/<文件夹名>`。里面有 python3、ffmpeg，可以用 pip 装 onnxruntime、opencv。
   - Blender MCP：`execute_blender_code`（跑 bpy）、`get_scene_info`、`look`（看视口）、`generate_3d`（Hyper3D Rodin 生成网格）、`search_assets` / `import_asset`（素材库）。
   - 文件互传：`device_stage_files`（Mac → 容器 `/mnt/user-data/uploads/…`）、`device_commit_files`（容器 `/mnt/user-data/outputs/…` → Mac）。
2. **云端容器**（Bash）：
   - 看图：Read 能直接看 jpg/png；
   - 做 PDF、字幕卡、展示图；
   - 跑纯 numpy 的拟合脚本。
3. **用户**：审片、确认计划。

## 哪些事放哪里做
- 跟视频直接打交道的（抽帧、检测、合成）在 Mac 上做，避免来回传几个 GB 的素材。
- 拟合和数据处理在哪边都行：数据量小就 stage 到容器里做，改代码方便。
- SfM：
  - 在 Mac 上用 Blender 自带的 Python（macOS 原生、arm64，比虚拟机快）；
  - 先 `pip install --target <项目>/pylib_colmap pycolmap`；
  - 再在 `execute_blender_code` 里用 `subprocess.Popen([sys.executable, "sfm_pycolmap.py", root], env={…, "PYTHONPATH": pylib_colmap})` 后台启动，日志写到文件，之后定期读日志。
- 渲染：只在用户开着的 Blender 里做，用 timer 分批。

## 长任务的固定套路
1. 后台启动（`nohup … &`、`Popen`、`bpy.app.timers`）。
2. 每个任务写日志，结束时写完成标记（`_DONE`）。
3. 能断点续跑：输出已存在就跳过。
4. 用 `send_later` 约好时间回来查看。如果用户人不在，查完后用推送告诉他结果。
5. 查看时汇报进度、速度、预计还要多久。

## 实测耗时（M 系列 Mac，《大事件》9768 帧）
- 正式渲染：EEVEE 1080×780，约 57 帧/分钟，整片约 3 小时。
- 合成：每 1200 帧约 40 秒，整片 9 段约 6 分钟；concat 只要几秒。
- 审片 PDF：每 3 秒一帧，一共 136 组、17 页。每轮反馈从修改到重新出 PDF，大约 1–2 小时。

## 和用户协作的约定
- 用中文；先说要做什么，再动手；重活先给计划和预计耗时。
- 不重启、不关闭用户的 Blender；临时改动的场景设置要恢复；不保存用户的 .blend（除非用户要求）。
- 不替用户输入 API Key 或其他凭据。
- 交付时说清楚：文件在哪、规格、哪些地方还没对上（具体到时间码）。
