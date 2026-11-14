---
name: "film-props-reconstruction"
description: "根据电影原片还原美术道具组的全部工作（服装、实物道具、墙地面做旧）：截图→GPT-image-2 产品图→Rodin 3D，出「原片+三行道具滚动+定格全标注+分类总览」视频和道具清单。"
---

# 电影美术道具组工作还原

产物：横版视频（上：原片片段；下：三行道具卡随原片滚动；每场定格时全部道具同时标注；结尾 75 项分类总览），配原片对白与片尾配乐；另交道具清单 CSV（UTF-8 BOM，含 分类/年代 列）、每场道具标注图、.blend。
来源项目：《布达佩斯大饭店》Zero 与 Gustave 房间、员工食堂等 4 场（原片 15:53–16:42，49 秒），共 75 项（服装 11、实物道具 59、墙地面做旧 5），v1→v4。

## 工作约定（这位用户）
- 全程中文。过程文件放 `项目/work/`，交付放 `项目/输出/`；每版新文件名 _v2、_v3…，不覆盖已交付版本。
- 先给道具清单（分场、分类、年代+名称+依据），用户确认后再做 3D 和视频。
- 用户的 Blender 场景（Scene）不动；项目用独立场景（如 `GBH_Props`），对象前缀 GBR_；结束把窗口切回 Scene。
- Rodin 次数用户说不限时可大方重生成，交付时报用量（GPT 次数、Rodin 次数、没用上的次数）。
- 3D 一律走「原片截图 → GPT-image-2 产品图 → Rodin」。道具有问题（穿模、文字乱码、形状错）就改提示词重出图、重跑 Rodin，不在 Blender 里手工修。
- MuleRouter key 只用环境变量传，不写文件、不进记忆；交付时提醒用户换 key。
- 电脑上不能 rm：作废文件 mv 到 `_to_delete/`。

## 1. 片段与道具清单
1. 用户给时间码 + 截图：先确认实际片段边界（截图可能比时间码早/晚几秒），按镜头切成场（A/B/C/D…），每场记录 原片起止秒。
2. 抽 2880×2160 全分辨率帧（frames/f_*.jpg，按 0.5–1 s 间隔），每场拼联系表通看。
3. 检索幕后资料（美术指导 Adam Stockhausen 访谈、道具/布景报道、剧本），帮助认出道具和推断年代；以原片为准。
4. 清单三类，对应视频下半部三行：
   - C 服装（每个角色一套，同场同款制服合并）
   - P 实物道具（家具、灯具、电气、厨具、餐具、洗漱、书报、陈设…）
   - W 墙面与地面做旧工艺（每场主墙面/地面一项）
5. **命名必须强调年代**，这是震撼感的来源：`【1920年代裸灯泡吊灯：白瓷螺口灯头、扭绞白花线直吊、透明梨形白炽灯泡】`。表里分 era / name / detail 三段（cards3.py：`T[id]=(row, era, name, detail)`）。
6. 每项记：首次出现时间、标注点（帧号, x, y）、参考裁框（ref_crops.json）。

## 2. 参考图裁取
- 在 2000 宽显示图上读坐标，×1.44 换算到 2880 宽原帧裁框；每项 1–3 张（正面、另一角度）。
- 卡片用的缩略图（ref_card/）裁到字幕线以上（显示坐标 y ≤ 1285），否则卡片里带字幕。
- 裁完拼一张总览核对，确认裁的是这件道具。

## 3. GPT-image-2（MuleRouter）出产品图
接口与跑法同 film-costume-reconstruction 第 3A 节：`POST https://api.mulerouter.ai/vendors/openai/v1/gpt-image-2/edit`，Bearer key + `User-Agent: curl/8.7.1`（下载结果图也要带），size 1024x1536，异步轮询 `task_info.status`，并发 ≤16–18（上限 20，超了 429）。在 Mac 上用 Blender `subprocess.Popen([sys.executable, 'gpt_run.py', jobs.json], env={..., 'MR_KEY':key}, start_new_session=True)` 跑，写 gpt_status.json 和 `_GPT_DONE`。jobs 是 `[{id, out, refs:[...], prompt}]`，已存在的 out 跳过，方便补跑。

提示词模板（英文效果最好）：
- **实物道具**：`The reference images are stills from a 1930s-set Wes Anderson film showing the same prop; they are dim, partly blurred, have a warm pink colour cast and may contain burned-in subtitles or people - ignore those. Create a clean e-commerce studio product photograph of exactly this prop: {年代+材质+形状+细节}. Show the single object complete and uncropped, centered, three-quarter front view from slightly above eye level, on a seamless light grey background, soft neutral daylight, true neutral colours with the film's warm pink cast removed. Faithfully keep the shape, proportions, materials, colours, wear and details seen in the reference. No people, no hands, no subtitles, no watermark, no added objects.`
- **服装**：同开头，换成 `headless beige linen dress form mannequin on a dark wooden stand, full length, front view`；背面另出一张 `back view, seen from directly behind; infer the back of the garment consistently with the front`；`ignore the actor's face`。
- **墙地面做旧**：画成美术师的 60×60 cm 样板，正面平拍，**竖分四条展示工序**（如 1 石灰底 → 2 土黄/赭石淡彩 → 3 水渍流痕 → 4 污渍做旧完成）。卡片上把四步写成 ①②③④。

易错点（v4 实测）：
- **组合道具会穿模**（牙刷穿过漱口杯）：写死空间关系 `the brush handle goes down into the cup and stays fully inside the cup walls … must never pass through the glass wall or bottom`，杯子改 FROSTED 半透明；出正面 + 纯侧面两张给 Rodin。
- **道具上的文字会乱码**（LOBBY BOY 帽）：字要大、分行、粗体、居中：`LOBBY above BOY, large, bold, perfectly legible block capitals`；出一张正对平视（文字展平）+ 一张 3/4；Rodin 用 high。小字母仍可能变形（L 像 U），交付时说明。
- **安全拦截**：内衣类被拒，改写成 `loungewear set`，只留一张参考图。
- 修订版用新文件名（A14v2_front.png），Rodin 输入文件夹也新建（rodin_img/A14v2/）。

## 4. Rodin 图生 3D
- 每项建 `rodin_img/<id>/`（0_front.png、1_back/side.png），`generate_3d(image=文件夹, provider='hyper3d')`，`wait_seconds=3` 拿句柄存 rodin_jobs.txt，2–3 分钟后逐个 `job=…` 续等导入。几十项可一次全发。
- 有文字、细结构、组合关系的道具用 `quality='high'`。
- 新场景要先把 HY_Qipao 等旧场景的 `blendermcp_*` 场景属性拷过来（use_hyper3d=True），否则报 hyper3d not enabled。偶发 SSL EOF：重发即可。
- 导入前把窗口场景切到项目场景。

## 5. 归一化、调色、渲染
- 把 matrix_basis 烘进网格，rotation_mode='XYZ'（导入是四元数，不改不转），按最大边缩放到 1 m，XY 居中，最低点 z=0。
- Rodin 颜色发灰/发白：Base Color 前插 Gamma 1.25 + HueSaturation（sat 1.15, val 0.95），材质打标记 `m['gb_fix']` 防重复插。顶面发白部分是 Rodin 贴图问题，压主光、相机仰角 8° 能缓解。
- 相机正交 ortho_scale 1.45、仰角 8°、距离 6；三灯 Key(-2.6,-3.0,1.6) 240W / Fill(2.8,-2.2,0.8) 110W / Rim(0.6,2.8,1.8) 220W，World 0.45；EEVEE 440×440 透明底，AgX Medium High Contrast。
- 72 帧转台（每 5°），用 `bpy.app.timers` 渲染器（render_job.py：start(job, tag, per_tick, rot_off)），只显示当前 GBR_ 对象，写 `_PROGRESS_tag`/`_DONE_tag`，避开工具超时。
- 替换模型：旧对象改名 GBX_<id>_v1 并隐藏，新模型改名 GBR_<id>；旧渲染目录挪到 render_old/。
- 保存：`bpy.data.libraries.write(path, {scene}, fake_user=True)`，交付时拷一份到 输出/。

## 6. 原片素材
- 片子是 2.39/1.37 混合画幅时先找有效画面区域（本片 crop=2748:2090:542:42），缩放到 868×660，24000/1001 fps，按场导出 film/<场>/%05d.jpg，记 _counts.txt。
- 片头若有淡入，跳过黑帧（FILM_OFF A=18）。
- 场尾若落在甩镜/转场上，用拉普拉斯清晰度逐帧查，截到甩镜前一帧（B 场限 395 帧），否则定格帧是糊的还带下一场字幕。
- 音频：抽片段 audio.wav；片尾配乐（片尾字幕段）抽成 bed.wav 作背景乐。

## 7. 版面与时间轴（用户最终选定，v4）
画面 1080 宽竖屏布局：
- **顶栏**：左上「布达佩斯大饭店 · AI 还原出道具组惊人工作量」，副标题「拍 49 秒镜头，需 75 项复古道具」，右上累计计数「N / 75 项」。不要片头黑底介绍页（直接从电影开始），不要「原片时间码」「A场」「流程说明」这类行。
- **原片区**：(106,84) 起 868×660。随播放在道具首次出现时打标注：圆点 + 标签「年代（金色）+ 名称（白色）」，格式与下半部卡片标题一致。坐标换算：out = FILM_X + (fx−62)·660/2090，FILM_Y + (fy−42)·660/2090。
- **下半部三行**（y=772 服装 / 1030 实物道具 / 1288 墙地面做旧），每行有类别小标题；颜色：服装淡紫、道具金、做旧青。
  - 卡片 232×232、间距 244，从右往左匀速滚动 165 px/s（慢到能看清）；场与场之间留 660 px 空档，避免下一场道具混进来。
  - 服装每场静态排开（一般 1–4 套），标注圆点在它们之间轮换。
  - 卡片：3D 转台（或做旧样板）+ 左上原片小图 + 「年代+名称」+ 细节一两行。不要黄框高亮移动卡片，不要「GPT-image-2→Rodin」流程注释。
- **每场末尾定格**：最后一帧定格，画面缓推到 1.10；定格最后 3.5 秒把本场所有道具同时标注（圆点和标签错开依次出现，标签用贪心布局避免重叠，左上角药丸「这一场共 N 项道具与工艺」），同时画面拉回 1.0。最后一帧看不到的道具标在画面边缘。
- **结尾总览 10 秒**（240 帧，原 5 秒用户要求加倍）：标题「拍 49 秒镜头，需 75 项复古道具」，分三块依次淡入：服装（11 列）、实物道具（10 列）、墙面与地面做旧工艺（5 列），同类放一起，每项缩略图 + 年代名称；底部美术组致谢。
- 合成脚本（compose_vN.py）逐帧生成，记录 timeline_vN.json（`scenes: {场: [起帧, 止帧, 原片帧数, 总帧数]}`）；转台缓存 tt() 先清再插。模式：`run a b outdir`（分批，单次 device_bash ≤180 s）、`test`（抽几帧拼图审）。

## 8. 混音
- 按 timeline 把每场原片音频放回对应位置（两端 30–40 ms 渐变）；原片对白归一到 −22 dBFS RMS。
- bed 归一到 −20 dBFS，循环铺满；包络：有原片声时压 −16 dB，定格/总览时 0 dB，0.5 s 平滑；结尾 2 s 淡出；峰值 >0.95 用 tanh 软限幅。写 mix_vN.wav。

## 9. 编码与验收
- 在 Mac 上经 Blender Popen 跑：`/opt/homebrew/bin/ffmpeg -y -framerate 24000/1001 -i frames_vN/%05d.jpg -i mix_vN.wav -c:v libx264 -preset slow -crf 18 -pix_fmt yuv420p -c:a aac -b:a 192k -shortest -movflags +faststart 输出/..._vN.mp4 && echo ok > _ENC_DONE`。先把旧 `_ENC_DONE` 改名。
- 验收：ffprobe `-count_packets` 视频包数 = 总帧数；抽 4 场全标注帧 + 结尾总览拼一张图看。
- 交付：stage → SendUserFile 发 mp4；说明改了什么、剩余瑕疵、用量，提醒换 key。

## 10. 踩过的坑
1. 下半部太快看不清：分三行、降速到 165 px/s，每场的服装静态展示。
2. 下一场道具混进本场：场间加大空档（GAP 660）。
3. 片头淡入导致开头几帧黑：跳过 18 帧。
4. 定格帧落在甩镜上（糊 + 下一场字幕）：拉普拉斯查甩镜起点，截短该场。
5. 卡片缩略图带字幕：参考裁框限制在字幕线以上。
6. 组合道具穿模、道具文字乱码：改 GPT 提示词写死空间关系/放大文字，出正面 + 侧面，Rodin high。
7. 新场景 hyper3d 未启用：拷 blendermcp_* 场景属性。
8. Rodin 颜色发灰、顶面发白：Gamma+HSV 节点、降主光、相机仰角 8°。
9. VM 里 nohup 后台进程会随调用结束被杀：长任务（GPT、ffmpeg）一律在 Mac 上用 Blender Popen 跑，写标记文件。
10. device_commit_files 有时不覆盖同名文件（即使 force）：用新文件名提交（compose_v4b.py），再 grep 核对。
11. 转台缓存清空后 KeyError：先清再插。
12. 设备掉线：重连后立刻保存 .blend；长任务用一次性 send_later 提醒续传，完成后删提醒。
13. 第一次跑坏的帧目录挪到 _to_delete/ 再重跑，不要在旧目录上「跳过已存在」。