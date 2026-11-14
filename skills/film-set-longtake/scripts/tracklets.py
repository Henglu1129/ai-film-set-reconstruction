# ==== 《大事件》(2004) 开场长镜头项目里的实际代码，原样保留作参考 ====
# 里面的路径（/tmp/claude-0/...、/mnt/user-data/...）、坐标、车辆尺寸、帧号区间都是那部片子的，换片时逐项改。
# 约定：机位 R 为 世界→相机（OpenCV：x 右 y 下 z 前），C 为相机中心；画面 1280×554 时 CX=640 CY=277、HFOV=42°。
# 试点段：纯图像空间的人物短轨迹（不依赖旧机位）。IoU 关联，宁可断开也不串人
import json, math, collections
import sys
I0, I1 = int(sys.argv[1]), int(sys.argv[2]); PFX = sys.argv[3]
DET = {}
for line in open('/tmp/claude-0/det/all.jsonl'):
    o = json.loads(line); i = o['f'] // 3
    if I0 <= i <= I1:
        DET[i] = [d for d in o['d'] if d['k'] == 'person' and d['s'] >= 0.35 and (d['b'][3] - d['b'][1]) >= 40]
def iou(a, b):
    x0, y0, x1, y1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, x1 - x0) * max(0, y1 - y0); ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0
def coldist(a, b):
    if not a or not b: return 0
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))
active, done = [], []
for i in range(I0, I1 + 1):
    dets = DET.get(i, [])
    cands = []
    for ti, t in enumerate(active):
        last = t['obs'][-1]; gap = i - last['i']
        lb = last['b']
        if len(t['obs']) >= 2 and gap > 1:
            pb = t['obs'][-2]['b']; v = [(lb[k] - pb[k]) for k in range(4)]; lb = [lb[k] + v[k] * (gap - 1) for k in range(4)]
        for di, d in enumerate(dets):
            u = iou(lb, d['b'])
            if u >= 0.3 and coldist(last['d'].get('col'), d.get('col')) < 70: cands.append((u, ti, di))
    cands.sort(reverse=True); ut, ud = set(), set()
    for u, ti, di in cands:
        if ti in ut or di in ud: continue
        ut.add(ti); ud.add(di); active[ti]['obs'].append({'i': i, 'b': dets[di]['b'], 'd': dets[di]})
    for di, d in enumerate(dets):
        if di not in ud: active.append({'obs': [{'i': i, 'b': d['b'], 'd': d}]})
    keep = []
    for t in active:
        if i - t['obs'][-1]['i'] > 2: done.append(t)
        else: keep.append(t)
    active = keep
done += active
done = [t for t in done if len(t['obs']) >= 4]
done.sort(key=lambda t: t['obs'][0]['i'])
out = []
for k, t in enumerate(done):
    out.append({'id': f'{PFX}{k:03d}', 'obs': [{'i': o['i'], 'b': o['b'], 's': o['d']['s'], 'col': o['d'].get('col'), 'pose': o['d'].get('pose')} for o in t['obs']]})
json.dump(out, open(f'tracklets_{PFX}.json', 'w'))
L = [len(t['obs']) for t in out]
print('tracklets', len(out), 'samples', sum(L), 'median len', sorted(L)[len(L)//2])
