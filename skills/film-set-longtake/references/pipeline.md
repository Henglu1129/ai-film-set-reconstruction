# 分步细节：命令、参数、数据格式

坐标和命名约定（全流程统一，换片也照用）：
- **帧号**：take 帧号 f（从 0 开始），对应原片时间 t = T0 + f/24。
  - 检测和 SfM 每 3 帧一个采样：f ∈ {0, 3, 6, …}；文件名为 `f%05d.jpg`。
  - Blender 时间轴的帧号 = f + 1。
- **画面**：
  - 原片去黑边后 1920×832（2.35:1），这次的裁切参数是 `crop=1920:832:0:124`。
  - SfM 和消失点用的图缩到 1280×554：CX=640，CY=277，F = 640 / tan(HFOV/2)。
- **世界坐标**：米制，z 朝上，地面 z=0，街道沿 Y 轴。
  - 偏航 yaw：0 = +Y，顺时针为正。由方向向量 (dx, dy) 求为 θ = atan2(dx, dy)；人物朝向用 atan2(−dx, dy)（这次的实体约定）。
- **机位**：`C`（相机中心），`R`（世界→相机，OpenCV 约定：x 右、y 下、z 前）。
  - Blender 相机矩阵：`M = column_stack([R[0], −R[1], −R[2]])`（Blender 相机看向 −Z、上为 +Y）。

---

## 1. 切镜头、抽帧

1. **找剪辑点**（长镜头的起止点前后通常是硬切）：
   ```
   ffmpeg -i film.mp4 -ss 75 -t 15 -vf "select='gt(scene,0.3)',showinfo" -f null - 2>&1 | grep pts_time
   ```
   在候选点前后逐帧导出图片确认，精确到帧。
2. **切镜头**：`bash scripts/extract_frames.sh film.mp4 T0 T1 3 1920:832:0:124`
   - 精确切割时，`-ss` 放在 `-i` 后面。
   - 后面合成时用 `-ss` 前置做快速定位，再加 `setpts=PTS-STARTPTS`。
3. **段落表**：看接触印样（每 2 秒一张），把整段切成 10–20 个段落。每个段落写：
   - 时间段 + 小标题；
   - 剧情一句；
   - 镜头运动一句；
   - 这一段摄影机会看到、会进入的场景元素（这就是勘景清单）。

   字幕卡、审片、展示图都要用到这张表。

## 2. 检测（人、车、姿态）

- 模型（ONNX，CPU 即可）：`yolox_m.onnx`（COCO 类别）和 `pose_mediapipe.onnx`（MediaPipe Pose 的 ONNX 版本，33 个关键点）。
- 脚本：`scripts/detect_people.py <video> <out.jsonl> <start> <end> <step>`。
  - 环境变量 `DSJ_MODELS` 指向模型目录，`DSJ_THREADS` 设线程数。
  - 整帧跑一次，再分 3 块方形瓦片（边长 = 画面高）覆盖整宽，最后做 NMS。
  - 人物框高 ≥90 px 才跑姿态；同时记录上身中部的平均颜色（后面区分身份时有用）。
- **并行**：把帧区间等分成 4 段，各开一个后台进程，各写一个 jsonl：
  ```
  nohup python3 -I detect_people.py take.mp4 det_0.jsonl 0 2442 3 > d0.log 2>&1 &
  ```
  其余 3 段同理。完成后 `cat det_*.jsonl > det_all.jsonl`。
- **jsonl 每行的格式**：
  ```
  {"f": 帧号, "d": [{"k": "person|car|truck|bus|motorbike|bicycle", "b": [x1,y1,x2,y2](1920×832 坐标), "s": 置信度, "col": [r,g,b], "pose": {"c": 置信度, "p2": [[x,y]×33], "v": [可见度×33], "w3": [[x,y,z]×33](米，髋中心为原点，相机方向)}}]}
  ```
- **检查**：用 `scripts/draw_detections.py 帧号…` 画框和骨骼看效果。
  - 烧录字幕区域、海报上的人像会被误检，后面按位置或尺寸过滤掉。

## 3. 机位

### 3a. 消失点和焦距
- `scripts/vp_focal.py sfm_dir`：
  - LSD 线段检测，RANSAC 找最多 3 个消失点；
  - 用两两正交的有限消失点求焦距。

  取全片的稳健中位数，换算成 HFOV（这次是 42°）。
- **竖直消失点（VVP）**：近竖直线段的交点。每帧存 `[vx, vy, vz, 线段数]`，作为重力先验（`vvp_all.json`）。
- 过滤：线段长度 > 50 px；去掉字幕区域（y > 700，按 1920×832 坐标）；去掉近水平和近竖直的噪声角度。

### 3b. SfM
- **掩码**：对每张 SfM 图，把人、车的检测框（外扩 10%）和字幕条涂成 0，存为 `masks/f02376.jpg.png`。
- **配对**：顺序匹配（overlap 12），加上远距离配对 `pairs_long.txt`。
  - 生成方法：按段落表找出「机位回到同一地点」的帧段，两两配对，每行写 `fA.jpg fB.jpg`。
  - 这次一共配了约 9000 对。
- 内参固定为 SIMPLE_PINHOLE，焦距不参与优化。
- 有全局式重建（global mapping）就用它，并带上 VVP 重力先验。
- 模板：`scripts/sfm_pycolmap.py`。
- **运行方式**：
  - 在 Mac 上用 Blender 自带的 Python 起子进程，后台跑；
  - 输出导出成 json：`{"models": {k: {"images": {"f00123.jpg": {"C": [...], "R": [[...]], "n3d": N}}}}}`，加上点云 `[x, y, z, model, …, r, g, b]`。
- **预期**：会得到好几个子模型，有的段落根本建不起来（暗的油料铺、楼梯间、快速甩镜）。不要硬调参数，交给 3d 去补。

### 3c. 转到米制世界
1. **重力方向**：每帧 `R^T · vvp` 是世界里的「上」，加权平均后迭代剔除偏差 >8° 的帧，再旋转模型让它朝 +z（`reference/gravity_align.py`）。
2. **比例和地面**：用站着的人求（`scripts/ground_fit.py`）。
   - 未知量：上方向的 2 个自由度、地面偏移、人高（SfM 单位）。
   - 残差用 soft-L1；只用观测 ≥40 次、拟合可信的人。
   - 或者用尺寸已知的静止车辆。
3. **偏航**：`reference/street_compass.py` 和 `yaw_series.py`。
   - 每帧把最强的水平消失点转成世界方向，取 mod 90，得到相对街道轴的偏转。
   - 在初值附近选分支，加权中位数平滑（窗口 240 帧）。
4. **地面原点和街道方向**：选一个显著地标定原点（例如便衣车的车头），让街道沿 +Y。

### 3d. 分段对齐、补洞
- **切段**：相邻采样之间位移异常大（大于局部中位数的 8 倍）或缺帧 >12 个采样，就断开；每段至少 6 个采样。
- **每段求 5 个参数** x = (θ, tx, ty, tz, log s)（`reference/seg_align_5dof.py`）：
  - 用已知位姿的静止车辆的 8 个角点投影出预测框，和检测框比较；
  - 被画面切掉的那条边不参与；
  - 先用初值按 IoU 把预测框和检测框配对并固定，再做优化。
- **静止车辆的位姿**：用 `scripts/carpose.py` 在已知机位下拟合（中心 P、朝向 ψ，车身尺寸已知）。
- **段间和 SfM 失效段**：
  - 用 `scripts/fit_pose_manual.py`：在原片上手工量几个像素特征（车身角点、轮子触地点、门框、窗台），解出 (x, y, z, yaw, pitch)，当关键帧用；
  - 关键帧之间做 Catmull-Rom 插值，朝向用 slerp。
- **局部偏差**：在 `cam(f)` 里叠加分段线性插值的偏航偏移、俯仰修正和高度修正。这次的例子：
  - 03:31–03:38 降低 0.3 m、偏航 +13°；
  - 07:29–07:36（路口俯拍）俯仰固定为 −30°。
- 最终接口：`cam(f) → (C, R)`，任意帧都能取值（`reference/cam_assemble_example.py`）。

### 3e. 线框验收
- `scripts/wire_check.py`：把车、油桶、楼面等关键物体的线框投影到原片帧上，叠成图看。
- 每 2–3 秒查一帧，重点查段落交界、关键帧附近、俯仰大的地方。

## 4. 场景
- 脚本化搭建（`reference/blender_build_example.py`），读一个 `bake.json`：
  - `world`：街道、两侧楼块、劫匪楼、横街、檐篷、远处高楼、油桶组、修路区、货板、轨道、停放车辆……
  - `frames`：每个采样的 cam / 吊臂底座 / 观察机位 / 车 / 人物；
  - `people`、`cars`、`crew`、`segments`。
- **几何**：楼块用 `add_box`；门洞、凹进去的地方用布尔挖洞（`cuts`、`recess`）。
- **立面材质**：
  - 按层高 3.1 m、开间 2.6 m 程序化生成窗户；
  - 加竖向污渍，越往下越脏；
  - 底层是卷闸门。
- **贴图**：Poly Haven 贴图加阴天 HDRI，原片是阴天、软光。
- **吊臂和摄影机**：
  - 吊臂车放在轨道上，底座沿街跟着机位移动；
  - 吊臂臂杆指向摄影机头；
  - 遥控云台加胶片摄影机；
  - 半透明橙色线框取景锥，深 6 米。
- **上层渲染相机（TopCam）**：
  - 位置在摄影机后方 2.4 m、上方 1.15 m、右侧 0.7 m，看向摄影机前方 6 m 处；
  - 位置用 σ=8 个采样的高斯平滑；
  - 不能进楼：x 夹在街道范围内；落到车顶上方时抬高到 2.4 m 以上。

## 5. 人物
1. **短轨迹**：`scripts/tracklets.py I0 I1 前缀`（I = 帧号/3）。
   - 只用 s ≥0.35、框高 ≥40 px 的检测；IoU 关联，缺帧时用速度外推；颜色差太大就断开。
2. **身份表**：`reference/id_sheets.py`，每条轨迹 3 张截图，附时间段和观测数，每页 4×N 格。
   - Claude 逐页看完，在 `labels.py` 里用 `put("身份码", "A002 A062 …")` 标注；
   - 不确定的标 `extra`，误检标 `drop`。
3. **投到地面**：`reference/people_to_world.py`。
   - 脚点射线和地面（或室内地板）求交；
   - 脚被切掉（框的下沿贴近画面底边）时，用头顶高度推距离；
   - 落在楼里或车里的点沿视线滑出来。
4. **合并、平滑、补洞、去重、朝向**：`reference/entities_staging.py`。
   - 采样间隔 DT = 0.125 s；
   - 首尾各原地保持 2.5 s；
   - 空档 ≤4 s 的直线补；
   - 位置权重：脚 1.0、躯干 0.45、框 0.2；
   - 车里的人用 `SEATS` 固定座位。
5. **人工补位**：用户指出的段落写成 `drop(f0, f1, 条件)`、`path(f0, f1, 路点, 动作, yaw)`、`put(身份, 行)`，每条注释写明对应的原片时间和画面内容。
6. **组装**：`reference/pieces_assemble.py` 输出 `pieces.json`，合并进 `bake.json`，再重跑 Blender 构建脚本。

## 6. 审片
- `scripts/blender_qa_render.py`：用 `CHK_FilmCam` 每 72 帧（3 秒）渲染一张。
  - 渲染时隐藏吊臂、剧组、站位圈；
  - 处理好机位在车里时的显示切换。
- `scripts/compare_pdf.py take.mp4 qa_dir out.pdf T0 notes.json` 生成 PDF，每页 8 组，17 页左右。
- 用户反馈 → 逐条落实 → 下一版 PDF 标注「本轮已改」。

## 7. 渲染
- 用 `scripts/blender_bg_render.py`：在用户的 Blender 里用 timer 分批渲染，可以断点续渲，完成后写 `_DONE`。
- 进度：`ls render_full | wc -l`。速度约 57 帧/分钟，按这个估算剩余时间告诉用户，再用 `send_later` 约好回来查看的时间。
- 渲染期间可以并行做字幕卡、合成脚本，并合成已经渲染完的段落。

## 8. 合成
- 字幕卡：`scripts/make_captions.py` 按段落表生成 1080×140 的 PNG 和 `times.json`。
- 合成：`bash scripts/compose_part.sh 输出.mp4 起始帧 帧数`，在项目根目录运行；每 1200 帧一段，两三段放一次 `device_bash` 调用（每段约 40 秒）。
  - 字幕卡用 concat demuxer 按时长排；最后一张要重复写一次。
- 拼接：
  ```
  for i in 1..9: echo "file 'p0$i.mp4'"  > listF.txt
  ffmpeg -f concat -safe 0 -i listF.txt -c copy 成片.mp4
  ```
- 检查：`ffprobe` 看帧数和时长；在每段交界前后各抽一帧，拼成接触印样看。

## 9. 交付
- 成片往往有 180 MB 以上：
  1. Mac 上运行 `split -b 45m 成片.mp4 part_`；
  2. 分两批 stage 到容器；
  3. 在容器里 `cat` 拼回，对 md5；
  4. 用 `SendUserFile` 发出。
- 告诉用户：文件在 Mac 上的位置、时长、帧数，以及还没对上的地方（要具体到时间码）。
