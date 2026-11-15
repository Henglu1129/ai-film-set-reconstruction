# 字幕校对：T = {字幕段编号: 校对后的文字}，两行字幕用 " / " 连接；没有字幕的误检段不写（会被丢掉）。
import json, sys, os
W = sys.argv[1] if len(sys.argv) > 1 else '.'
T = {
    # 5: '……',
}
d = json.load(open(os.path.join(W, 'subseg.json')))
out = [{'k': x['k'], 's': x['s'], 'e': x['e'], 't': T[x['k']]} for x in d if x['k'] in T]
json.dump(out, open(os.path.join(W, 'subs_clean.json'), 'w'), ensure_ascii=False, indent=0)
print(len(out))
