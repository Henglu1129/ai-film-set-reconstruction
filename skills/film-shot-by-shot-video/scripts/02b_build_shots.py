"""把核验后的切点写成 shots.json，并为每镜挂上：采样帧、重叠字幕、声音标签摘要。
用法：python3 02b_build_shots.py WORK_DIR [cuts.json]
cuts.json 默认用 psd_adaptive.json（[[start,end],...]，秒）；人工增删切点后另存一份传进来。
需要 frames/（1fps 截帧）、可选 subs_clean.json、tags.json。同时输出 shots_digest.txt 和 8 镜一页的帧拼图 verify/sheet_*.jpg。"""
import json, collections, os, sys, subprocess, glob
W = sys.argv[1]; CUTS = sys.argv[2] if len(sys.argv) > 2 else os.path.join(W, 'psd_adaptive.json')
d = json.load(open(CUTS))
NF = len(glob.glob(os.path.join(W, 'frames', 'f_*.jpg')))
END = float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', os.path.join(W, 'clip.mp4')]).decode())
d[-1][1] = END
subs = json.load(open(os.path.join(W, 'subs_clean.json'))) if os.path.exists(os.path.join(W, 'subs_clean.json')) else []
tags = json.load(open(os.path.join(W, 'tags.json'))) if os.path.exists(os.path.join(W, 'tags.json')) else []
shots = []
for i, (s, e) in enumerate(d):
    dur = e - s
    fr = sorted(set(max(1, min(NF, int(s + dur * k) + 1)) for k in (0.08, 0.3, 0.5, 0.7, 0.92)))
    ss = [x['t'] for x in subs if x['s'] < e - 0.2 and x['e'] > s + 0.2]
    agg = collections.defaultdict(float); n = 0
    for t in tags:
        if s <= t['t'] + 1.5 < e:
            n += 1
            for nm, p in t['tags']: agg[nm] += p
    top = sorted(agg.items(), key=lambda x: -x[1])[:5]
    shots.append({'n': i + 1, 'start': round(s, 3), 'end': round(e, 3), 'dur': round(dur, 2), 'frames': fr, 'subs': ss,
                  'audio': ', '.join(f'{k}:{v / max(n, 1):.2f}' for k, v in top)})
json.dump(shots, open(os.path.join(W, 'shots.json'), 'w'), ensure_ascii=False, indent=1)
with open(os.path.join(W, 'shots_digest.txt'), 'w') as f:
    for x in shots:
        f.write(f"#{x['n']} {x['start']:.2f}-{x['end']:.2f} ({x['dur']}s) | audio: {x['audio']}\n   subs: {' / '.join(x['subs'])}\n")
os.makedirs(os.path.join(W, 'sheets'), exist_ok=True); os.makedirs(os.path.join(W, 'verify'), exist_ok=True)
for b in range(0, len(shots), 8):
    rows = []
    for x in shots[b:b + 8]:
        fs = [os.path.join(W, 'frames', f'f_{f:05d}.jpg') for f in x['frames']]
        out = os.path.join(W, 'sheets', f"r_{x['n']:03d}.jpg")
        subprocess.run(['montage', *fs, '-tile', f'{len(fs)}x1', '-geometry', '230x+1+1', '-background', 'black', out])
        subprocess.run(['convert', out, '-background', 'black', '-fill', 'yellow', '-pointsize', '22', 'label:' + f"#{x['n']} {x['dur']}s", '+swap', '-gravity', 'west', '+append', out])
        rows.append(out)
    subprocess.run(['montage', *rows, '-tile', '1x', '-geometry', '+0+3', '-background', 'gray30', os.path.join(W, 'verify', f'sheet_{b // 8}.jpg')])
print('shots', len(shots))
