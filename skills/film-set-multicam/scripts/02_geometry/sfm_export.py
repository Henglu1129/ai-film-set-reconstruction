import pycolmap, numpy as np, json
out={}
for k in [0,2,3,4,5]:
    r=pycolmap.Reconstruction(f'sfm/sparse/{k}')
    ims={}
    for iid,im in r.images.items():
        cam=r.cameras[im.camera_id]
        T=im.cam_from_world() if callable(im.cam_from_world) else im.cam_from_world
        R=np.array(T.rotation.matrix()); t=np.array(T.translation)
        C=-R.T@t
        ims[im.name]=dict(C=C.tolist(),R=R.tolist(),f=float(cam.params[0]),k=float(cam.params[3]) if len(cam.params)>3 else 0,n=int(im.num_points3D))
    pts=[]
    for pid,p in r.points3D.items():
        pts.append(list(map(float,p.xyz))+list(map(int,p.color))+[int(p.track.length()),float(p.error)])
    out[k]=dict(images=ims,points=pts)
    print(k,len(ims),len(pts))
json.dump(out,open('sfm_models.json','w'))
