import json, numpy as np, glob
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont
R=json.load(open('/home/claude/proj/cuts_raw.json')); D=np.array(R['D'])
P=json.load(open('/home/claude/proj/plan/plan_data.json'))
SH=P['shots']; SET={s['id']:s for s in P['setups']}
fl=json.load(open('/home/claude/proj/shots_v2.json'))['flashes']
t=np.arange(len(D))/24
# 1) cut signal
fig=plt.figure(figsize=(9.6,3.2),dpi=100); ax=fig.add_axes([0.0,0.12,1,0.86]); fig.patch.set_facecolor('#0d1015'); ax.set_facecolor('#0d1015')
ax.plot(t,D,color='#5edce6',lw=0.7,alpha=0.9)
cuts=[s['f0'] for s in SH[1:]]
ax.scatter(np.array(cuts)/24,D[cuts],s=10,color='#ff7a3d',zorder=3,label='剪辑点')
ff=[f for f in fl if f<len(D)]
ax.scatter(np.array(ff)/24,D[ff],s=26,marker='x',color='#ffd43b',zorder=4,label='枪口闪光（排除）')
ax.set_xlim(0,463.5); ax.set_ylim(0,1.0); ax.axis('off')
fig.savefig('src/cut_signal.png',facecolor=fig.get_facecolor()); plt.close(fig)
# 2) shot mosaic colored by setup (138 tiles)
cols=12; tw,th=150,63; pad=4
rows=(len(SH)+cols-1)//cols
M=Image.new('RGB',(cols*(tw+pad)+pad,rows*(th+pad)+pad),(13,16,21))
for i,s in enumerate(SH):
    f=glob.glob(f"/home/claude/proj/frames_mid/s{s['n']:03d}_*.jpg")[0]
    im=Image.open(f).convert('RGB').resize((tw,th),Image.LANCZOS)
    x=pad+(i%cols)*(tw+pad); y=pad+(i//cols)*(th+pad)
    M.paste(im,(x,y))
    c=tuple(int(SET[s['setup']]['color'][j:j+2],16) for j in (1,3,5))
    ImageDraw.Draw(M).rectangle((x,y+th-6,x+tw-1,y+th-1),fill=c)
M.save('src/mosaic.png'); print('mosaic',M.size)
# 3) point cloud (model 3, leveled) dark
SM=json.load(open('/home/claude/proj/sfm_models.json')); G=json.load(open('/home/claude/proj/sfm_grav.json'))
from mpl_toolkits.mplot3d import Axes3D
fig=plt.figure(figsize=(10.8,7.2),dpi=100); fig.patch.set_facecolor('#0d1015')
ax=fig.add_axes([-0.12,-0.12,1.24,1.24],projection='3d'); ax.set_facecolor('#0d1015')
for k in ['3']:
    g=np.array(G[k]['G']); Pp=np.array(SM[k]['points']); good=(Pp[:,6]>=3)&(Pp[:,7]<1.5)
    X=(g@Pp[good,:3].T).T; C=Pp[good,3:6]/255.
    ax.scatter(X[:,0],X[:,1],X[:,2],c=C,s=4,depthshade=False,alpha=0.95)
    for n,dd in SM[k]['images'].items():
        c=g@np.array(dd['C']); R_=np.array(dd['R'])@g.T; fw=R_[2]
        ax.scatter([c[0]],[c[1]],[c[2]],color='#ff7a3d',s=30,depthshade=False)
        ax.plot([c[0],c[0]+fw[0]*1.2],[c[1],c[1]+fw[1]*1.2],[c[2],c[2]+fw[2]*1.2],color='#ff7a3d',lw=1)
ax.view_init(elev=24,azim=-118); ax.set_axis_off()
lim=np.percentile(X,[3,97],axis=0); ax.set_xlim(lim[0][0]-1,lim[1][0]+1); ax.set_ylim(lim[0][1]-1,lim[1][1]+1); ax.set_zlim(lim[0][2]-1,lim[1][2]+1)
fig.savefig('src/pointcloud.png',facecolor=fig.get_facecolor()); plt.close(fig)
print('ok')
