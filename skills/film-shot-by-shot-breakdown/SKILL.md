---
name: "film-shot-by-shot-breakdown"
description: "把电影/剧集自动拆成逐镜拉片报告 HTML/PDF：逐秒截帧+镜头边界检测得真实镜头时长，并行 agent 逐镜读帧/读字幕，产出景别·运动·内容·台词·视听分析表。用户要拉片、逐镜分析、shot-by-shot breakdown 时使用。"
---

# 电影逐镜拉片自动化 SKILL

> 适用场景：用户要对一部电影/剧集做「逐镜分析 / 拉片 / shot-by-shot breakdown」，需要精确的每镜时长（而不是按固定 10 秒切块），并输出带首帧图的 HTML/PDF 报告。面向电影学院教学。

一句话：**逐秒截帧 → 镜头边界检测（得到真实时长）→ 视觉抽检 → 并行 agent 逐镜分析（读帧+读硬字幕）→ 组装 HTML/PDF**。

这套流程已成功跑通多部长片：《安李的遗嘱》(2h16m, 906 镜)、《爱丁顿》(2h22m, 825 镜)、《阿尔及尔之战》(黑白片)、《霸王别姬》(2h51m, 1331 镜)。下面是完整可复用步骤 + 所有脚本 + **踩过的坑**（最值钱的部分，务必先读「七、踩坑清单」）。

> **检测质量三板斧**（吃过亏才总结出来的，按顺序做）：
> ① 基线 `AdaptiveDetector(2.5)` → ② 对长镜用**低阈值自适应 + HashDetector 双跑、只采纳两者一致的切点**（坑 #15/#18）→ ③ 用 `audit_cuts.py` 对**每一个**切点做画面证据核验，删掉两侧几乎相同的伪切点（坑 #19），并对长镜做 montage 目视复核（坑 #3）。
> 三步做完才能说「镜头时长是真的」——这是本 skill 唯一的核心卖点。

---

## 一、核心理念（为什么这么做）

- **不要按固定时长切块**。"每 10 秒一个镜头"是错的——每个镜头长度天差地别（中位 5 秒，但有 1 秒的快切也有 3 分钟的长镜）。必须**真正检测剪辑点**。
- **镜头边界检测 = 逐帧比对相邻画面是否连贯**。这正是用户想要的"判断相邻两帧是否连贯"，但用算法在 24/25fps 帧级做，比人工 1fps 抽样更准。
- **分析靠"看帧 + 读硬字幕"**。很多资源是烧录字幕（burned-in），可直接从画面读台词，无需转录音频。
- **规模靠并行 agent**。几百个镜头 → 切成每批 ~20 镜，fan-out 给几十个 subagent 并行读帧产出结构化 JSON，再组装。

---

## 二、前置依赖

```bash
# macOS (Homebrew)
brew install ffmpeg imagemagick
# 注意 PEP 668：Homebrew 的 python 需要 --break-system-packages
pip3 install --break-system-packages scenedetect opencv-python-headless
# 渲染 PDF 用系统自带 Chrome（headless），无需额外装
```
检查：`which ffmpeg ffprobe montage; python3 -c "import scenedetect; print(scenedetect.__version__)"`（需 0.7+）。

---

## 三、整体流程

```
0. 建工作目录，记录源文件路径
1. ffmpeg 逐秒截帧 (1fps, 640px宽)         → frames/f_00001.jpg ...
2. PySceneDetect 自适应检测镜头边界         → psd_adaptive.csv
3. finalize：清洗+合并极短镜+映射首帧       → shots.json
4. 视觉抽检（长镜/暗场/密集段 contact sheet）→ 确认不漏切不误切；处理片尾字幕
5. 切批                                      → batches/batch_000.json ...
6. 并行 agent 逐镜分析（读帧+读硬字幕）      → analysis/batch_NNN_out.json
7. 校验+修复 JSON+合并                       → all_analysis.json
8. 场景分段（一个 agent 读全片摘要）         → scenes.json
9. 组装 meta+数据 → gen_html → 渲染验证 → PDF → 成稿 HTML
```

---

## 四、分阶段操作（含确切命令）

> 下面把工作目录记作 `$OUT`，源视频记作 `$M`。

### 阶段 0–1：建目录 + 截帧（后台）
```bash
OUT="$HOME/Downloads/Claudecode/拉片报告/<片名>逐镜分析"
M="/path/to/movie.mp4"
mkdir -p "$OUT/frames" "$OUT/batches" "$OUT/analysis" "$OUT/verify"
echo "$M" > "$OUT/source.txt"
cd "$OUT"
# 1fps，缩到 640 宽（足够看清画面与字幕，文件小）。后台跑。
nohup ffmpeg -y -i "$M" -vf "fps=1,scale=640:-1" -q:v 4 "frames/f_%05d.jpg" > frames_extract.log 2>&1 &
# 看进度： ls frames | wc -l ；典型 35-80x 实时速度
```
先 `ffprobe -v error -show_entries format=duration:stream=codec_type,r_frame_rate,width,height "$M"` 拿到时长/帧率/分辨率。

**确认有没有字幕**：看一帧 `frames/f_03000.jpg`。若底部有烧录字幕（硬字幕）→ 后面直接读；若没有，且无外挂/内嵌字幕轨 → 台词列只能写"对白/旁白"类型或另行转录（whisper）。
> ⚠️ 没有独立字幕轨 ≠ 没字幕。中文资源常是"中英双字"烧录版，一定要看帧确认。

### 阶段 2：镜头边界检测（后台，关键）
```bash
cd "$OUT"
nohup python3 -c "
from scenedetect import detect, AdaptiveDetector
import csv
# min_scene_len 单位是帧：24fps→17, 25fps→18 (约0.7s)，避免把烛光/噪点闪烁当成切点
scenes=detect('$M', AdaptiveDetector(adaptive_threshold=2.5, min_scene_len=18), show_progress=False)
with open('psd_adaptive.csv','w',newline='') as f:
    w=csv.writer(f); w.writerow(['n','start_s','end_s','dur_s'])
    for i,(s,e) in enumerate(scenes):
        w.writerow([i+1, round(s.seconds,3), round(e.seconds,3), round(e.seconds-s.seconds,3)])
print('scenes:', len(scenes))
" > psd.log 2>&1 &
# 2h+ 影片全帧解码约 15-20 分钟，耐心等。等待： grep -q scenes psd.log
```
> **为什么用 PySceneDetect 的 AdaptiveDetector 而不是 ffmpeg `select=gt(scene,X)`？** 见「七、踩坑清单 #1」——ffmpeg 的亮度差检测在暗场/烛光戏会**灾难性漏切**。

### 阶段 3：清洗 + 映射首帧 → `shots.json`
把下面存成 `$OUT/finalize_shots.py` 并运行（已**自动读取帧数和时长**，避免硬编码踩坑）：
```python
import csv, json, os, glob, subprocess
WORK=os.path.dirname(os.path.abspath(__file__))
NF=len(glob.glob(os.path.join(WORK,'frames','f_*.jpg')))           # 自动帧数
SRC=open(os.path.join(WORK,'source.txt')).read().strip()
DUR=float(subprocess.check_output(['ffprobe','-v','error','-show_entries',
     'format=duration','-of','default=nw=1:nk=1',SRC]).decode().strip())
rows=[(float(x['start_s']),float(x['end_s'])) for x in csv.DictReader(open(os.path.join(WORK,'psd_adaptive.csv')))]
# 合并 <1.0s 的极短镜（多为误检/闪帧）到前一镜
merged=[]
for s,e in rows:
    if merged and (e-s)<1.0: merged[-1][1]=e
    else: merged.append([s,e])
def fidx(t): return max(1, min(NF, int(round(t))+1))   # 1fps: f_00001≈第0秒；★必须 clamp 到真实帧数 NF
out=[]
for i,(s,e) in enumerate(merged):
    d=e-s; first=fidx(s+0.4)
    samples=sorted(set([first]+[fidx(s+d*k) for k in (.25,.5,.75)]+[fidx(e-0.6)]))
    samples=[f for f in samples if f>=first]
    out.append({"n":i+1,"start":round(s,2),"end":round(e,2),"dur":round(d,2),
                "frame":f"f_{first:05d}.jpg","fidx":first,
                "samples":[f"f_{f:05d}.jpg" for f in samples]})
json.dump(out, open(os.path.join(WORK,'shots.json'),'w'), ensure_ascii=False, indent=0)
print("shots:",len(out),"| frames:",NF,"| dur:",round(DUR))
```

### 阶段 4：视觉抽检（必做，别跳）
对**长镜**和**密集快剪段**做 contact sheet 复核，确认边界质量。ImageMagick `montage`：
```bash
cd "$OUT"
# 列出可疑长镜（>75s 的镜头容易藏漏切）
python3 -c "import json;[print(x['n'],x['frame'],x['dur']) for x in json.load(open('shots.json')) if x['dur']>75]"
# 给某长镜（首帧号 A 到末帧号 B）抽 12 帧拼图：
A=1499; B=1616; files=(); step=$(( (B-A)/11 )); for ((f=A;f<=B;f+=step)); do files+=("frames/f_$(printf %05d $f).jpg"); done
montage "${files[@]}" -tile 4x -geometry 210x+2+2 -background black verify/check.jpg
# 密集段：连续帧逐一拼（看每秒是否在切）
files=(); for ((f=2353;f<=2400;f++)); do files+=("frames/f_$(printf %05d $f).jpg"); done
montage "${files[@]}" -tile 8x -geometry 130x+1+1 -background black verify/dense.jpg
```
然后用 Read 看这些 `verify/*.jpg`：
- 拼图里**画面构图/主体明显跳变** = 真的是多个镜头被并成一镜（漏切）→ 若大量漏切，调低 `adaptive_threshold`（如 2.0）重跑阶段 2。
- 拼图里**只是同一机位里人物在动/字幕在变** = 一个长镜，正确。
- **片尾字幕**：常是"暗夜地景 + 滚动字幕"，检测器会按字幕变化切成几十个碎镜 → **手动合并成 1 个 credits 镜**：
```bash
python3 -c "
import json; s=json.load(open('shots.json'))
CUT=825   # ← 改成片尾第一个镜号（从抽检确定）
keep=[x for x in s if x['n']<CUT]; tail=[x for x in s if x['n']>=CUT]
keep.append({'n':CUT,'start':tail[0]['start'],'end':tail[-1]['end'],
 'dur':round(tail[-1]['end']-tail[0]['start'],2),'frame':tail[0]['frame'],
 'fidx':tail[0]['fidx'],'samples':[tail[0]['frame']]})
json.dump(keep,open('shots.json','w'),ensure_ascii=False,indent=0); print('shots:',len(keep))
"
```

### 阶段 5：切批
```bash
cd "$OUT"; python3 -c "
import json
s=json.load(open('shots.json')); B=20
mmss=lambda t:f'{int(t//60):02d}:{int(t%60):02d}'
for i in range(0,len(s),B):
    rows=[{'n':x['n'],'tc':mmss(x['start']),'dur':round(x['dur'],1),'samples':x['samples']} for x in s[i:i+B]]
    json.dump(rows,open(f'batches/batch_{i//B:03d}.json','w'),ensure_ascii=False)
print('batches:', -(-len(s)//B))
"
```

### 阶段 6：并行 agent 逐镜分析
先写 `$OUT/BRIEFING.md`（见「五、模板」）。然后**分波**派发 subagent，每波 ~12-14 个，每个处理一批。**用 Agent 工具并行**（一条消息里放多个 Agent 调用）。Agent prompt 模板：
```
你是电影拉片分析师。先用 Read 读取简报 <OUT>/BRIEFING.md，再读取批次 <OUT>/batches/batch_<NNN>.json。
按简报对该批每个镜头读取其 samples 帧（frames/ 目录），逐镜产出六字段 JSON（n/size/move/content/sound/analysis），
sound 必须逐字引用画面底部中文硬字幕。JSON 字符串内部只用中文全角引号，绝不用半角双引号。
把 JSON 数组用 Write 写到 <OUT>/analysis/batch_<NNN>_out.json。完成回复 DONE。
```
> ★ **务必加"只用全角引号，绝不用半角双引号"**——见踩坑 #6。加了这句后第二部片 0 个 JSON 报错；没加的第一部片 6 个文件需修复。

### 阶段 7：校验 + 修复 + 合并
```bash
cd "$OUT"; python3 -c "
import json,glob
allrows=[]; bad=[]
for f in sorted(glob.glob('analysis/batch_*_out.json')):
    try:
        d=json.load(open(f))
        for x in d: assert all(k in x for k in ('n','size','move','content','sound','analysis'))
        allrows+=d
    except Exception as e: bad.append((f,str(e)[:60]))
ns=sorted(x['n'] for x in allrows)
print('rows:',len(allrows),'| missing:',sorted(set(range(1,max(ns)+1))-set(ns)),'| bad:',bad)
if not bad:
    allrows.sort(key=lambda x:x['n'])
    json.dump(allrows,open('all_analysis.json','w'),ensure_ascii=False,indent=0); print('merged OK')
"
```
若有 `bad`（JSON 解析失败，几乎都是字符串里混入半角双引号），用这个**逐行修复**脚本（文件是每字段一行的 pretty JSON，所以按行转义内部引号很稳）：
```python
import re,json
def repair(path):
    pat=re.compile(r'^(\s*"(?:n|size|move|content|sound|analysis)":\s*)"(.*)"(,?)\s*$')
    out=[]
    for ln in open(path,encoding='utf-8').read().split('\n'):
        m=pat.match(ln)
        if m:
            pre,val,comma=m.groups()
            val=val.replace('\\"','"').replace('"','\\"')   # 先去已转义再统一转义内部 "
            out.append(f'{pre}"{val}"{comma}')
        else: out.append(ln)
    txt='\n'.join(out); json.loads(txt)   # 校验
    open(path,'w',encoding='utf-8').write(txt)
for b in ['007','013','022']:   # ← 填 bad 文件的批号
    repair(f'analysis/batch_{b}_out.json'); print('fixed',b)
```

### 阶段 8：场景分段（一个 agent 读全片摘要）
先生成摘要 `digest.tsv`：
```bash
cd "$OUT"; python3 -c "
import json
d=json.load(open('all_analysis.json')); s={x['n']:x for x in json.load(open('shots.json'))}
mmss=lambda t:f'{int(t//60):02d}:{int(t%60):02d}'
open('digest.tsv','w').write('\n'.join(
 f\"{x['n']}\t{mmss(s[x['n']]['start'])}\t{s[x['n']]['dur']:.0f}s\t{x['size']}\t{x['content']}\t<sub>{x['sound']}\" for x in d))
"
```
派一个 agent：读 `digest.tsv`，按叙事节拍/地点时间/章节卡把全部镜号**无缝连续**切成 24–32 个场景，每个给 `{title(含时间码范围), start_n, end_n, note}`，写到 `scenes.json`。强调：前一场 end_n+1 = 后一场 start_n，第一场 start_n=1，最后一场 end_n=末镜，片尾字幕单独成场。

### 阶段 9：组装 + 生成 + 验证
- 写 `assemble.py`（见模板）填好 `meta`（片名/主创/概述/总结/封面帧/输出文件名），它把 `scenes.json`+`all_analysis.json`+`shots.json` 合成 `shots_analysis.json`。
- `gen_html.py` + `report.css`（见模板）→ 生成 HTML。
- **联网核实主创**（导演/摄影/配乐/主演/首映），别瞎编 credits。
- 渲染验证（headless Chrome 截图）+ 出 PDF：
```bash
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
cd "$OUT"
python3 assemble.py && python3 gen_html.py
# 截一张封面 + 一段镜头表，用 Read 看，确认排版/图片/字幕都对
"$CHROME" --headless --disable-gpu --hide-scrollbars --window-size=1280,1400 --screenshot="verify/cover.png" "file://$OUT/<输出>.html"
# 出 PDF
"$CHROME" --headless --disable-gpu --no-pdf-header-footer --print-to-pdf="<输出>.pdf" "file://$OUT/<输出>.html"
```
> 校验要点：`所有 frame 都存在`、`镜号 1..N 无缺无重`、`<strong> 标签数 > 0`、`scene-section 数 = 场景数`。

---

## 五、模板文件

### BRIEFING.md（发给分析 agent 的简报，按片替换占位）
```markdown
# 拉片分析任务简报（《<片名>》）
## 影片背景（让分析有据可依）
- 片名/年份/导演/摄影/配乐/类型；一句话剧情；主要人物与演员；
- 视觉风格要点（画幅、光线、机位习惯、剪辑特征、母题）。  ← 越具体，分析越准
## 字幕说明
画面底部通常有中英双语硬字幕（上中下英）。sound 字段逐字引用中文原文；歌唱段标 ♪。
## 你的工作
拿到 batch JSON（每镜含 n/tc/dur/samples）。帧目录：<OUT>/frames/
对每镜：Read 其 samples 帧（短镜读首帧；多帧用于判断镜头运动与动作变化，并确认确属同一镜），产出一个 JSON 对象。
## 输出字段（严格 schema）
- n: 镜号(整数,照抄)
- size: 景别 [大远景/远景/全景/中全景/中景/中近景/近景/特写/大特写/空镜/插入(屏幕)]
- move: 镜头运动+视角 [固定/手持微晃/肩扛跟拍/推/拉/横摇/直摇/移/跟/升降/甩 · 俯/仰/平/过肩]
- content: 画面内容与人物动作，1-2句，具体（谁/在哪/做什么/光线构图景深要点）
- sound: 声音/字幕。优先逐字引用中文硬字幕；注类型（对白/旁白/环境音/音乐/屏幕文字/静默）
- analysis: 面向电影学院学生的视听语言分析，1-2句，点出技巧与意图，关键术语用 <strong>…</strong>
## 输出方式
JSON 数组 Write 到 <OUT>/analysis/batch_<NNN>_out.json。
★字符串内部只用中文全角引号「」""，绝不用半角双引号 "（否则破坏 JSON）。只写 JSON。完成回复 DONE。
```

### report.css + gen_html.py + assemble.py
> 这三个文件已存在于两个成片目录里，**直接复制复用**即可：
> `~/Downloads/Claudecode/拉片报告/Eddington逐镜分析/{report.css,gen_html.py,assemble.py}`
>
> 复用 `gen_html.py` 时**只需改一处**：顶部 `BASE="file://…/<片名>逐镜分析/frames/"` 指向新片 frames 目录。
> 表格列：截图｜镜号｜时间码(含时长副行)｜景别｜镜头运动｜画面内容/人物动作｜声音/字幕｜分析注释。
> `analysis` 字段按原始 HTML 注入（保留 <strong>）；其余字段做 HTML 转义。
> `assemble.py` 里手写 `meta`（标题/副标/tagline/封面帧/credits/overview 三段/overview_facts/summary 六节/outfile）。

---

## 六、可调参数速查

| 参数 | 默认 | 调整方向 |
|---|---|---|
| 截帧分辨率 | `scale=640:-1` | 字幕太小看不清→提到 854 或 960 |
| `adaptive_threshold` | 2.5 | 漏切多→调低(2.0)；碎镜多→调高(3.0) |
| `min_scene_len`(帧) | 24fps=17 / 25fps=18 | 闪烁误切多→加大；快剪被吞→减小 |
| 合并极短镜阈值 | `<1.0s` | 视片子快剪程度 0.7–1.5s |
| 每批镜头数 | 20 | agent 太慢→减到 12–15 |
| 每波 agent 数 | 12–14 | 并发上限默认 20，边完成边补派 |
| 场景数 | 24–32 | 按片长与叙事（2h50m 长片可到 34） |
| 伪切点判据 | `corr>0.975 & mad<4.5` | 见坑 #19，**别放宽**（0.95 会误伤正反打） |

---

## 七、踩坑清单（最值钱，务必读）

1. **暗场/烛光戏会被亮度检测灾难性漏切** ★最大的坑。
   ffmpeg `select='gt(scene,0.25)'` 在近黑画面里相邻帧亮度差极小，硬切检测不到——曾把一段 8 分钟"镜头"当成 1 个，实则是 36 个镜头。
   → **改用 PySceneDetect `AdaptiveDetector`**（滚动均值，对暗场鲁棒）。亮度法只在明亮戏里准。

2. **千万别按固定时长切块**。这是用户明确反对的旧做法。镜头时长必须来自真实剪辑点检测。

3. **长镜必须人工抽检**。检测器既可能漏切（暗场）也可能误切（大幅运镜/运动）。对 >75–90s 的镜头和快剪密集段做 contact sheet 用眼睛核对，再信任结果。

4. **片尾字幕会被切成几十个碎镜**。"暗夜地景+滚动字幕"里字幕在变，检测器疯狂切点。→ 手动把片尾合并成 1 个 credits 镜（阶段 4 脚本）。

5. **跨片复用脚本的硬编码 clamp / 时长 bug**。`finalize_shots.py` 里若残留上一部片的 `min(8203, …)` 帧数上限或 `DUR=8203` 常量，新片所有超过旧上限的帧会被错误钳到最后一帧。→ 本 skill 的 finalize 已改为**自动读帧数 NF 和 ffprobe 时长**，别再硬编码。

6. **agent 写中文时用半角双引号 `"` 会破坏 JSON** ★高频坑。
   如 `"信仰与肉身"`、`"震教"` 直接写进 JSON 字符串值里→解析失败。
   → 两道防线：(a) 简报+prompt 里明确"字符串内部只用全角引号「」""，绝不用半角 `"`"；(b) 阶段 7 的逐行修复脚本兜底。加了 (a) 后第二部片 0 报错。

7. **"没字幕轨"不等于"没字幕"**。`ffprobe` 看不到 subtitle 流，但画面可能是烧录硬字幕（尤其中文"双字"资源）。→ 先 Read 一帧确认；有硬字幕就能直接读台词，省掉音频转录。

8. **检测器会把交叉剪辑/正反打的对侧机位个别帧并入一镜**。生/死并置蒙太奇、快速正反打处常见。→ 在简报里告诉 agent："按该镜主导内容描述并注明镜末切换"，不必强行当成单一机位。

9. **PySceneDetect 慢**。2h+ 影片全帧 opencv 解码约 15–20 分钟。→ 后台跑，期间去写 BRIEFING / 联网查主创 / 准备脚本。

10. **macOS Homebrew Python 装包要 `--break-system-packages`**（PEP 668），否则 pip 报错。

11. **1fps 帧号 ↔ 秒的映射**：`f_NNNNN` ≈ 第 (N-1) 秒；某时刻 t 的首帧号 = `round(t)+1`，且必须 clamp 到真实帧数。

12. **frames/ 不能删/移**。HTML 用绝对 `file://` 路径引用首帧图，成稿依赖 frames 目录。清理中间产物时只能删 `batches/ analysis/ verify/ *.log`，保留 `frames/` 和成稿。

13. **封面帧要挑**。从 overview 抽检里选一张有代表性、构图好的帧作 `cover_frame`，别用第一帧（常是厂标/黑场）。

14. **务必渲染验证**。生成 HTML 后用 headless Chrome 截图，Read 看封面+一段表格，确认图片显示、字幕可读、列对齐、<strong> 生效——再交付。

15. **极暗/低反差黑白片：连 AdaptiveDetector 都漏切** ★（来自《阿尔及尔之战》1966 黑白片）。
    全片粗颗粒黑白时，`AdaptiveDetector(threshold=2.5)` 仍把暗夜对话长段严重漏切（170 秒"一镜"实为 ~18 镜）。
    → 两步：(a) 整片把 `adaptive_threshold` 降到 ~1.5、`min_content_val` 降到 ~8 重跑（612→891 镜）；(b) 对仍漏的**近黑夜戏**，ffmpeg/AdaptiveDetector/ContentDetector 全失效，唯独 **`HashDetector`（感知哈希，亮度无关）** 能切——用它对该时间段 `open_video()+v.seek(start)+detect_scenes(end_time=…)` 局部补切，再把切点 splice 回 shots.json 并重新编号（见 `splice480.py`）。**记住：HashDetector 是暗场补切的杀手锏。**

16. **软字幕（ASS/SRT 字幕轨）：不要烧录，按时间码挂到镜头上**（来自本片，与硬字幕片不同）。
    本片字幕是独立 ASS 轨（且只有中文、分简/繁两条），不在画面里。烧录会遇到字体/转义麻烦。
    → 更稳的做法：`ffmpeg -map 0:s:0 subs.ass` 抽出 → 解析成 `[{s,e,t}]` 时间轴（过滤压制组水印行）→ **构建 batch 时把与每镜 [start,end] 时间重叠的字幕行放进该镜 `subs` 字段**，简报告诉 agent「台词在 subs 字段里、画面上没有字幕」。比烧录精确，且零字体问题。截帧用**干净视频**（无字幕），scene 检测也跑干净视频。

17. **你自己写的 `assemble.py` meta 里也别用半角双引号**（坑 #6 会反咬一口）。
    在 Python 字符串里写 `"阿尔及尔城战"` 这种内部 ASCII 引号 → Python `SyntaxError`（字符串提前终止，常误报成 em-dash 错误）。→ meta 概述/总结里所有内部引号一律用全角「」“”；overview 段落会被 HTML 转义，**别在 overview 文本里放 `<strong>`**（会显示成字面标签），要加粗就放进 analysis 字段或改 gen_html 不转义。

18. **低阈值 AdaptiveDetector 会在静止长镜里吐出「每隔恰好 10.0 秒」的伪切点** ★（来自《霸王别姬》1993）。
    降阈值补漏切（坑 #15）是有代价的：`adaptive_threshold=2.0` 那一轮在**机位不动、只有轻微表演**的长镜里会周期性误触发，切点间隔**恰好 10.01 秒**。全片 1408 个切点里有 148 个这种间隔，而 HashDetector 的 1254 个切点里只有 3 个——**两个算法的分歧本身就是警报**。
    征兆：`collections.Counter(round(x['dur'],1) for x in shots)` 里某个时长值异常高频（本片 10.0 秒出现 126 次，第二名才 31 次）。**每次 finalize 后都跑一下这个 Counter。**
    → 别靠「是否 ~10 秒」来删（本片 128 个 10 秒镜里仍有 ~87 个是真的，10 秒本来就是常见镜长）。用下面的**画面证据核验**，对全部切点一视同仁地判。

19. **切点画面证据核验（通用质检，建议固化成必跑步骤）** ★★
    真剪辑点两侧画面必然跳变；伪切点两侧几乎逐像素相同。用已有的 1fps 帧就能对**每一个**切点打分，几十秒跑完全片：
```python
# audit_cuts.py —— 对 shots.json 每个镜头起点做画面证据核验
import json, cv2, numpy as np, os
shots=json.load(open('shots.json')); NF=len([f for f in os.listdir('frames') if f.startswith('f_')])
def load(n):
    p=f'frames/f_{n:05d}.jpg'; return cv2.imread(p) if os.path.exists(p) else None
def hist(img):
    h=cv2.calcHist([cv2.cvtColor(img,cv2.COLOR_BGR2HSV)],[0,1,2],None,[16,8,8],[0,180,0,256,0,256])
    return cv2.normalize(h,h).flatten()
rows=[]
for x in shots[1:]:
    t=x['start']; a=max(1,int(round(t))); b=min(NF,int(round(t))+2)   # 切点前后各约1秒
    ia,ib=load(a),load(b)
    if ia is None or ib is None: continue
    corr=cv2.compareHist(hist(ia),hist(ib),cv2.HISTCMP_CORREL)
    ga=cv2.cvtColor(cv2.resize(ia,(96,54)),cv2.COLOR_BGR2GRAY).astype(float)
    gb=cv2.cvtColor(cv2.resize(ib,(96,54)),cv2.COLOR_BGR2GRAY).astype(float)
    rows.append({'n':x['n'],'start':t,'dur':x['dur'],'corr':round(float(corr),4),
                 'mad':round(float(np.abs(ga-gb).mean()),2)})
json.dump(rows,open('cut_audit.json','w'),indent=0)
susp=[r for r in rows if r['corr']>0.975 and r['mad']<4.5]
print('切点',len(rows),'| 可疑(两侧几乎相同)',len(susp))
```
    **判据 `corr>0.975 且 mad<4.5` = 伪切点**：灰度均差 <4.5/255 意味着两帧平均差异不到 2%，**同场景正反打也做不到**，所以误伤风险极低。放宽到 0.95 就会开始吃到真的反打，别放宽。
    本片：1383 个切点里 96% 画面明显跳变（检测整体可信），53 个被判伪切点，**逐对拼成 montage 目视复核后全部确认**——一定要看一眼再删。

20. **修伪切点不用重跑 agent：合并镜头的同时合并分析行** ★（省下几十个 agent 的关键手法）。
    合并会导致**全片重新编号**，看似要作废所有 batch 分析——其实不用。拿老编号的 `all_analysis.json`，按合并分组同步合并即可：
    `size` 取首段；`move` 用 ` → ` 串联去重；`content` 用 `；` 串联去重；`sound` 用 ` / ` 串联去重（**字幕最不能丢**）；`analysis` 取最长的一条。
    合并后的行**比拆开时更完整**——content 自然变成「长镜内部的推进描述」，sound 变成完整的台词序列。校验：合并前后 `sum(dur)` 必须分毫不差，编号必须连续。
    ⚠️ 顺序：**等全部 batch 落盘、merge 出 all_analysis.json 之后再动手**。agent 还在跑时改 shots.json，会让它们写回的镜号对不上。

---

## 八、产物结构

```
<片名>逐镜分析/
├── <片名>逐镜拉片分析.html   ← 主交付物
├── <片名>逐镜拉片分析.pdf    ← headless Chrome 打印
├── frames/  f_00001.jpg…     ← 1fps 帧，HTML 依赖，勿删
├── shots.json                ← 镜头边界(真实时长)+采样帧
├── all_analysis.json         ← 906/825 镜逐镜六字段
├── scenes.json               ← 场景分段
├── shots_analysis.json       ← 组装后喂给 gen_html
├── BRIEFING.md / batches/ / analysis/ / verify/  ← 过程文件
└── finalize_shots.py / assemble.py / gen_html.py / report.css
```

---

## 九、一句话复用清单
1. 改 `$OUT`、`$M` → 跑阶段 0-3（截帧+检测+finalize，自动化）。**先看一帧确认有没有硬字幕**（坑 #7）。
2. 阶段 4 抽检长镜、合并片尾字幕、裁掉片头发行方 logo。
3. **跑一次时长 Counter + `audit_cuts.py`**（坑 #18/#19），确认没有周期性伪切点、记下可疑切点清单。
4. 写 BRIEFING（填影片背景）→ 切批 → 分波派 agent。
5. 全部落盘后校验/修复/合并 → **按 #20 合并伪切点镜头并同步合并分析行** → 场景分段 agent。
6. 填 meta（联网核实主创）→ assemble → gen_html → 渲染验证 → PDF。

> **并发与限额**：Agent 并发上限默认 20（`CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`）。长片 60-70 批时要**边完成边补派**。撞上 session 限额时 agent 会在「写文件」那一步挂掉，但**有一部分其实已经落盘**——重置后先 `ls analysis/` 对账，只补跑真正缺的批号，别整批重来。