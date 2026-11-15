# -*- coding: utf-8 -*-
"""导出「视频拉片笔记」Markdown。
用法：python3 08_export_notes.py WORK_DIR [--with-dialogue] [-o 输出.md]
读取 WORK_DIR 下的 config.json / shots.json / analysis.py（以及可选的 subs_clean.json）。
--with-dialogue 会把每镜对应的字幕台词也写进笔记（仅供个人学习，公开发布时去掉）。
"""
import json, sys, os, argparse, importlib.util

ap = argparse.ArgumentParser()
ap.add_argument('work'); ap.add_argument('--with-dialogue', action='store_true'); ap.add_argument('-o', default=None)
a = ap.parse_args()
W = a.work
cfg = json.load(open(os.path.join(W, 'config.json')))
shots = json.load(open(os.path.join(W, 'shots.json')))
spec = importlib.util.spec_from_file_location('analysis', os.path.join(W, 'analysis.py'))
an = importlib.util.module_from_spec(spec); spec.loader.exec_module(an)
A, SCENES = an.A, an.SCENES
SPK = getattr(an, 'SPK', {})
subs = json.load(open(os.path.join(W, 'subs_clean.json'))) if a.with_dialogue and os.path.exists(os.path.join(W, 'subs_clean.json')) else []
OFF = cfg['offset_seconds']

def tc(t):
    g = OFF + t
    return f"{int(g // 3600)}:{int(g % 3600 // 60):02d}:{int(g % 60):02d}"

total = shots[-1]['end'] - shots[0]['start']
out = []
out.append(f"# {cfg['film_title']}（{cfg.get('film_title_en', '')}）视频拉片笔记\n")
out.append(f"- 导演：{cfg.get('director', '')}　年份：{cfg.get('year', '')}")
out.append(f"- 片段：{tc(shots[0]['start'])} – {tc(shots[-1]['end'])}，时长 {int(total // 60)}分{int(total % 60)}秒，共 {len(shots)} 个镜头")
durs = sorted(x['dur'] for x in shots)
out.append(f"- 平均镜长 {total / len(shots):.1f} 秒，中位 {durs[len(durs) // 2]:.1f} 秒，最长 {durs[-1]:.1f} 秒（镜头边界来自自动检测 + 人工复核）\n")

out.append("## 场景结构\n")
out.append("| 场 | 名称 | 镜号 | 时间码 | 时长 |")
out.append("|---|---|---|---|---|")
for i, (s, e, lab) in enumerate(SCENES):
    st, en = shots[s - 1]['start'], shots[e - 1]['end']
    out.append(f"| {i + 1} | {lab} | {s}–{e} | {tc(st)} – {tc(en)} | {en - st:.0f}s |")
out.append("")

out.append("## 镜头总表\n")
out.append("| 镜号 | 时间码 | 时长 | 景别 | 镜头运动 |")
out.append("|---|---|---|---|---|")
for x in shots:
    v = A[x['n']]
    out.append(f"| {x['n']} | {tc(x['start'])} | {x['dur']:.1f}s | {v[0]} | {v[1]} |")
out.append("")

out.append("## 逐镜笔记\n")
for si, (s, e, lab) in enumerate(SCENES):
    out.append(f"### 第{si + 1}场 · {lab}\n")
    for n in range(s, e + 1):
        x = shots[n - 1]; size, move, light, color, plot, perf, sound, note = A[n]
        out.append(f"#### 镜号 {n:02d} · {tc(x['start'])} → {tc(x['end'])}（{x['dur']:.1f} 秒）\n")
        out.append(f"- **景别**：{size}")
        out.append(f"- **镜头运动**：{move}")
        out.append(f"- **布光**：{light}")
        out.append(f"- **色调**：{color}")
        out.append(f"- **剧情**：{plot}")
        out.append(f"- **表演**：{perf}")
        out.append(f"- **声音**：{sound}")
        if subs:
            ls = [((SPK.get(q['k'], '') + '：') if SPK.get(q['k']) else '') + q['t'].replace(' / ', ' ')
                  for q in subs if q['e'] > x['start'] + 0.2 and q['s'] < x['end'] - 0.2]
            if ls: out.append("- **台词**：" + ' ／ '.join(ls))
        out.append(f"- **分析注释**：{note}\n")

path = a.o or os.path.join(W, f"{cfg['film_title']}_视频拉片笔记.md")
open(path, 'w', encoding='utf-8').write('\n'.join(out))
print('wrote', path)
