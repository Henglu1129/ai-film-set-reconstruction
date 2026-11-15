"""三种检测器各跑一遍：AdaptiveDetector(2.5) 基线、低阈值(1.8) 补漏、HashDetector 交叉验证。
只采纳基线切点，再对三者分歧的地方逐个 montage 目视核验（见 SKILL.md 第 3 步）。
用法：python3 02_detect_cuts.py WORK_DIR"""
from scenedetect import detect, AdaptiveDetector, HashDetector
import json, os, sys
WORK = sys.argv[1] if len(sys.argv) > 1 else '.'
V=os.path.join(WORK,'clip.mp4')
a=detect(V, AdaptiveDetector(adaptive_threshold=2.5, min_scene_len=14), show_progress=False)
json.dump([[s.seconds,e.seconds] for s,e in a],open(os.path.join(WORK,'psd_adaptive.json'),'w'))
print('adaptive',len(a),flush=True)
a2=detect(V, AdaptiveDetector(adaptive_threshold=1.8, min_content_val=10, min_scene_len=14), show_progress=False)
json.dump([[s.seconds,e.seconds] for s,e in a2],open(os.path.join(WORK,'psd_adaptive_low.json'),'w'))
print('adaptive_low',len(a2),flush=True)
h=detect(V, HashDetector(min_scene_len=14), show_progress=False)
json.dump([[s.seconds,e.seconds] for s,e in h],open(os.path.join(WORK,'psd_hash.json'),'w'))
print('hash',len(h),flush=True)
