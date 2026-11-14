import json
from PIL import ImageFont, Image, ImageDraw
E=json.load(open('events_v2.json'))
def span(ids): return (E[ids[0]]['t0'], E[ids[-1]]['t1'])
H1="♪ (the hymn begins) ♪"
HC="♪ (the hymn continues) ♪"
C=[]
def add(ids_or_span, text, kind='d'):
    a,b = span(ids_or_span) if isinstance(ids_or_span,list) else ids_or_span
    C.append(dict(t0=round(a,2),t1=round(b,2),en=text,kind=kind))
# ↓ 在这里逐条写译文：事件编号来自 events_v2.json（字幕事件检测 + OCR 的结果）。
#   原项目这里是这场戏完整的英文对白译文；为尊重原片版权，公开仓库里只留写法示例。
#   kind：'d' 对白（默认）、'n' 人名/字卡、'h' 歌曲（只写“♪ … ♪”，不转写歌词）
add([0,1],"<Character name>",'n')
add([62],"<line 1 of dialogue>")
add([65,66],"<a line that spans two subtitle events>")
add([129,130,131],H1,'h')
# 歌曲段：把连续的字幕事件合并成几段，统一写 HC（下面按事件编号区间自动生成）
ly=[i for i in range(223,283) if E[i]['conf']>0 and E[i]['zh']]
runs=[]; cur=None
for i in ly:
    if cur and E[i]['t0']-E[cur[-1]]['t1']<1.2: cur.append(i)
    else:
        if cur: runs.append(cur)
        cur=[i]
runs.append(cur)
for r in runs: add(r,HC,'h')
C.sort(key=lambda c:c['t0'])
# fit font sizes for one line in 1040 px
FB='/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'
d=ImageDraw.Draw(Image.new('RGB',(10,10)))
for c in C:
    fs=27
    while fs>18 and d.textlength(c['en'],font=ImageFont.truetype(FB,fs,index=2))>1030: fs-=1
    c['fs']=fs
json.dump(C,open('cues_en.json','w'),ensure_ascii=False,indent=0)
for c in C: print(f"{c['t0']:7.2f} {c['t1']:7.2f} {c['kind']} {c['fs']} {c['en']}")
print(len(C))
