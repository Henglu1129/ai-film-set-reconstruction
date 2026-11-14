import pycolmap, os, time
from pathlib import Path
root=Path('sfm'); db=root/'db.db'; out=root/'sparse'; out.mkdir(exist_ok=True)
if db.exists(): db.unlink()
t=time.time()
ro=pycolmap.ImageReaderOptions(); ro.mask_path=str(root/'masks'); ro.camera_model='SIMPLE_RADIAL'
eo=pycolmap.FeatureExtractionOptions(); eo.num_threads=2; eo.sift.max_num_features=6000
pycolmap.extract_features(db, root/'images', camera_mode=pycolmap.CameraMode.PER_IMAGE, reader_options=ro, extraction_options=eo, device=pycolmap.Device.cpu)
print('extract',time.time()-t,flush=True)
mo=pycolmap.FeatureMatchingOptions(); mo.num_threads=2
pycolmap.match_exhaustive(db, matching_options=mo, device=pycolmap.Device.cpu)
print('match',time.time()-t,flush=True)
po=pycolmap.IncrementalPipelineOptions(); po.min_model_size=3
po.mapper.init_min_num_inliers=60
maps=pycolmap.incremental_mapping(db, root/'images', out, options=po)
print('map',time.time()-t,flush=True)
for k,m in maps.items():
    print(k, m.num_reg_images(), m.num_points3D(), sorted(im.name for im in m.images.values()))
