"""每 2 秒做一次 AudioSet 声音事件分类（sherpa-onnx CED，模型在 GitHub release 上），
用来判断哪里有配乐、哪里只是环境声（虫鸣、海浪、车噪、缝纫机……）。AI 听不到声音，「声音」一栏只写这里能确认的东西。
用法：MODELS=/path/to/models python3 04_audio_tags.py WORK_DIR"""
import sherpa_onnx, wave, numpy as np, json, os, sys
WORK = sys.argv[1] if len(sys.argv) > 1 else '.'
MODELS = os.environ.get('MODELS', '/home/claude/models')
M=os.path.join(MODELS,'sherpa-onnx-ced-base-audio-tagging-2024-04-19/')
cfg=sherpa_onnx.AudioTaggingConfig(model=sherpa_onnx.AudioTaggingModelConfig(ced=M+'model.int8.onnx',num_threads=2),labels=M+'class_labels_indices.csv',top_k=8)
at=sherpa_onnx.AudioTagging(cfg)
w=wave.open(os.path.join(WORK,'audio16k.wav')); x=np.frombuffer(w.readframes(w.getnframes()),dtype=np.int16).astype(np.float32)/32768
res=[]
for t in np.arange(0,len(x)/16000-1,2.0):
    seg=x[int(t*16000):int((t+3)*16000)]
    st=at.create_stream(); st.accept_waveform(16000,seg)
    ev=at.compute(st)
    res.append({'t':float(t),'tags':[(e.name,round(e.prob,3)) for e in ev]})
json.dump(res,open(os.path.join(WORK,'tags.json'),'w'),ensure_ascii=False)
print('done',len(res))
