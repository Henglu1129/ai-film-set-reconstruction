import json, random, math
random.seed(7)
D=json.load(open('plan_data.json'))
P=[]
def add(**k): P.append(k)
# floor crowd: seated on cushions, rows facing north (stage)
rows=[]
y=6.1
while y<16.7:
    rows.append(y); y+=0.86
for yi,y in enumerate(rows):
    x=-4.55+(0.38 if yi%2 else 0)
    while x<4.6:
        if not (abs(x+0.3)<1.2 and y>15.6) and not (-1.2<x<0.6):   # keep platform steps + central aisle clear
            add(kind='floor',x=round(x+random.uniform(-0.12,0.12),2),y=round(y+random.uniform(-0.12,0.12),2),yaw=round(random.uniform(-28,28),1))
        x+=0.84
# side groups flanking Chen near the door (seen in s004/s049)
for y in (3.6,4.45,5.3):
    for x in (-4.5,-3.7,-2.9,-2.1, 1.5,2.3,3.1,3.9,4.6):
        if x>2.4 and y<4.0: continue   # AC / table zone
        add(kind='floor',x=round(x+random.uniform(-0.1,0.1),2),y=round(y+random.uniform(-0.1,0.1),2),yaw=round(random.uniform(-40,40)+(25 if x<0 else -25),1))
nfloor=len(P)
# stage believers (west part of stage), facing south
for y in (19.4,20.25,21.1,21.9):
    for x in (-4.6,-3.85,-3.1,-2.35):
        add(kind='stage',x=round(x+random.uniform(-0.08,0.08),2),y=round(y+random.uniform(-0.08,0.08),2),yaw=180+round(random.uniform(-15,15),1))
for x,y in ((1.0,21.9),(4.4,21.6),(4.6,20.4)):
    add(kind='stage',x=x,y=y,yaw=180)
# band
add(kind='band',role='吉他手(男)',x=-1.6,y=20.4,yaw=180)
add(kind='band',role='吉他手(女)',x=0.9,y=20.5,yaw=185)
add(kind='band',role='贝斯',x=1.55,y=20.9,yaw=190)
add(kind='band',role='大提琴',x=2.05,y=20.6,yaw=195)
add(kind='band',role='鼓手',x=3.05,y=21.5,yaw=185)
add(kind='singer',role='主唱吉他手',x=-0.3,y=21.75,yaw=180)
add(kind='leader',role='尊者',x=-0.3,y=18.95,yaw=180)
# fates
for p in P:
    if p['kind']=='floor':
        dd=math.hypot(p['x']-0.1,p['y']-0.3)
        if random.random()<0.55:
            p['fate']='flee'; p['t_up']=277+random.uniform(0,6); p['t_leave']=round(281+ (dd/17.0)*33+random.uniform(-3,3),1)
        else:
            p['fate']='stay'; p['stand']=random.random()<0.55
            p['t_kill']=round(321+ (p['y']-3.5)/(16.8-3.5)*74+random.uniform(-6,6),1)
    elif p['kind']=='stage': p['fate']='stay'; p['t_kill']=round(random.uniform(398,424),1)
    elif p['kind']=='band': p['fate']='stay'; p['t_kill']=round(random.uniform(426,446),1)
    elif p['kind']=='singer': p['fate']='stay'; p['t_kill']=446.0; p['t_stand']=330.0
    elif p['kind']=='leader': p['fate']='stay'; p['t_kill']=219.3
# early victims near the door (bodies visible in #49/#56)
add(kind='floor',x=0.95,y=3.5,yaw=60,fate='stay',stand=False,t_kill=52.0)
add(kind='floor',x=-1.05,y=3.0,yaw=-40,fate='stay',stand=False,t_kill=150.0)
for i,p in enumerate(P): p['id']=i
D['people']=P
json.dump(D,open('plan_data.json','w'),ensure_ascii=False,indent=1)
from collections import Counter
print(len(P),Counter(p['kind'] for p in P),Counter(p.get('fate') for p in P if p['kind']=='floor'))
