"""（可选）没有硬字幕时的转录：sherpa-onnx whisper turbo + silero VAD，模型都从 GitHub release 下载（HuggingFace 被拦）。
2 核 CPU 约 0.75 倍实时。原文转录后由 Claude 翻译、校对。
用法：MODELS=... LANG_CODE=ko python3 04b_asr_whisper.py WORK_DIR"""
import sherpa_onnx, wave, numpy as np, json, sys, os
WORK = sys.argv[1] if len(sys.argv) > 1 else '.'
MODELS = os.environ.get('MODELS', '/home/claude/models')
LANG = os.environ.get('LANG_CODE', 'ko')
M=os.path.join(MODELS,'sherpa-onnx-whisper-turbo/')
rec=sherpa_onnx.OfflineRecognizer.from_whisper(
    encoder=M+'turbo-encoder.int8.onnx', decoder=M+'turbo-decoder.int8.onnx',
    tokens=M+'turbo-tokens.txt', language=LANG, task='transcribe', num_threads=2)
cfg=sherpa_onnx.VadModelConfig()
cfg.silero_vad.model=os.path.join(MODELS,'silero_vad.onnx')
cfg.silero_vad.min_silence_duration=0.35
cfg.silero_vad.min_speech_duration=0.25
cfg.silero_vad.max_speech_duration=12
cfg.silero_vad.threshold=0.4
cfg.sample_rate=16000
vad=sherpa_onnx.VoiceActivityDetector(cfg, buffer_size_in_seconds=60)
w=wave.open(os.path.join(WORK,'audio16k.wav')); x=np.frombuffer(w.readframes(w.getnframes()),dtype=np.int16).astype(np.float32)/32768
out=[]; ws=512
def flush():
    while not vad.empty():
        seg=vad.front; s=seg.start/16000; samp=np.array(seg.samples,dtype=np.float32)
        st=rec.create_stream(); st.accept_waveform(16000,samp); rec.decode_stream(st)
        t=st.result.text.strip()
        out.append({'s':round(s,2),'e':round(s+len(samp)/16000,2),'t':t})
        print(f"{s:7.2f} {t}",flush=True)
        vad.pop()
for i in range(0,len(x),ws):
    vad.accept_waveform(x[i:i+ws]); flush()
vad.flush(); flush()
json.dump(out,open(os.path.join(WORK,'asr.json'),'w'),ensure_ascii=False,indent=0)
print('DONE',len(out))
