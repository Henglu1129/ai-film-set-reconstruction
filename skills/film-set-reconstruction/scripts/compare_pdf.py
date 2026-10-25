# 第 6 步：把“原片 | 同机位渲染”配成审片 PDF（每页 8 组，每 3 秒一组），给用户逐页指认问题
# 用法：python3 compare_pdf.py take.mp4 qa_dir out.pdf T0 [notes.json]
#   notes.json：{"帧号": "本轮已改：……"}，把上轮反馈的修改写在对应帧旁边，方便用户复核
import sys, os, glob, json, subprocess
from PIL import Image, ImageDraw, ImageFont
take, qa, out, T0 = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4])
notes = json.load(open(sys.argv[5])) if len(sys.argv) > 5 else {}
FB = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", 26, index=2)
FR = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 22, index=2)
fr = sorted(int(os.path.basename(p)[4:9]) for p in glob.glob(qa + "/chk_*.jpg"))
def film(f):
    p = f"/tmp/_film_{f}.jpg"
    if not os.path.exists(p):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", take, "-vf", f"select=eq(n\\,{f}),scale=760:-2", "-frames:v", "1", p])
    return Image.open(p)
pages = []; PW, RH = 1580, 375
for k in range(0, len(fr), 8):
    pg = Image.new("RGB", (PW, 148 + RH * 8), (245, 243, 238)); d = ImageDraw.Draw(pg)
    d.text((30, 30), f"同机位对照（左：原片  右：重建场景按反求机位渲染）  第 {k // 8 + 1} 页", font=FB, fill=(20, 20, 20))
    for i, f in enumerate(fr[k:k + 8]):
        y = 148 + RH * i; t = T0 + f / 24
        d.text((30, y - 30), f"{int(t // 60):02d}:{t % 60:04.1f}  (f{f})", font=FB, fill=(200, 80, 30))
        if str(f) in notes: d.text((820, y - 28), notes[str(f)], font=FR, fill=(90, 90, 90))
        a = film(f).resize((760, 329)); b = Image.open(f"{qa}/chk_{f:05d}.jpg").resize((760, 329))
        pg.paste(a, (30, y)); pg.paste(b, (790, y))
    pages.append(pg)
pages[0].save(out, save_all=True, append_images=pages[1:], resolution=110)
print(out, len(pages), "pages")
