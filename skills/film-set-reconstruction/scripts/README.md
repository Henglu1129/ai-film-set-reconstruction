# 脚本索引

## 可以直接改着用（scripts/）
| 文件 | 步骤 | 作用 |
|---|---|---|
| extract_frames.sh | 1 | 切镜头、去黑边、每 3 帧抽一张 SfM 图、接触印样 |
| detect_people.py | 2 | YOLOX-m（整帧 + 3 块瓦片）+ MediaPipe Pose → jsonl |
| draw_detections.py | 2 | 在原片帧上画检测框和骨骼，用来检查效果或做展示图 |
| vp_focal.py | 3a | LSD 线段 → 消失点 → 焦距 |
| sfm_pycolmap.py | 3b | pycolmap 重建模板（API 以安装的版本为准） |
| ground_fit.py | 3c | 用站着的人同时求地面和比例；里面带一个通用的 soft-L1 LM 求解器 `least_squares` |
| carpose.py | 3d | 已知机位下拟合静止车辆的位姿（车身角点投影对检测框） |
| fit_pose_manual.py | 3d | 手工像素特征 → 解相机 (x, y, z, yaw, pitch)，给 SfM 失效段做关键帧 |
| wire_check.py | 3e | 关键物体线框投影到原片帧上，快速检查机位对位 |
| tracklets.py | 5 | 图像空间的人物短轨迹（宁断不串） |
| dsj_rig.py | 5 | Rodin 人物网格自动绑骨架、蒙皮，MediaPipe 驱动姿态（在 Blender 里 import） |
| blender_qa_render.py | 6 | 用原片机位渲染验收帧（处理车内显示切换、恢复场景设置） |
| compare_pdf.py | 6 | 「原片｜渲染」审片 PDF，每页 8 组，可以附上本轮修改说明 |
| blender_bg_render.py | 7 | 在用户开着的 Blender 里用 timer 后台逐帧渲染，可断点续渲，完成后写 _DONE |
| make_captions.py | 8 | 段落字幕卡（标题 + 剧情一句 + 镜头一句）+ times.json |
| compose_part.sh | 8 | 分段合成 1080×1488 成片（上：拍摄现场 / 中：原片 / 下：字幕条） |
| showcase_cards.py | 9 | 1080×1440 展示卡片的版式工具（card / paste / chip / footer） |

## 《大事件》原样代码（scripts/reference/，参数全部要换）
| 文件 | 作用 |
|---|---|
| gravity_align.py | 用竖直消失点求「上」方向，把 SfM 各子模型转正 |
| street_compass.py / yaw_series.py | 水平消失点做罗盘（mod 90），逐段算偏航修正 |
| seg_align_5dof.py | 每段 SfM → 世界的 5 自由度相似变换（拟合静止车辆检测框） |
| integrate_motion.py | 按时变的偏航和比例累加 SfM 位移（适合比例或朝向缓慢漂移的段） |
| cam_assemble_example.py | 全片 `cam(f)`：各段变换 + 手工关键帧 Catmull-Rom + 偏航俯仰偏移，组装成一个函数 |
| cars_world.py | 车辆检测框底边 → 地面位置 → 短轨迹 |
| id_sheets.py / labels_example.py | 身份表生成，以及人工身份标注的写法 |
| people_to_world.py | 人物检测 → 地面位置（含脚被切掉、室内地板、滑出墙体、姿态朝向） |
| entities_staging.py | 合并、平滑、补洞、去重、朝向规则，以及 drop / path / put / PAIRS 人工补位 |
| pieces_assemble.py | 组装 bake 片段：逐采样机位、吊臂底座、观察机位、车、人、剧组 |
| blender_build_example.py | 整个场景的 Blender 构建脚本（楼、立面材质、道具、吊臂、人物绑定与动作、车、灯光、渲染相机） |
