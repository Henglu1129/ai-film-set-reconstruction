import math, numpy as np
def Rmat(yaw,pitch,roll=0.0):
    y,p,r=map(math.radians,(yaw,pitch,roll))
    f=np.array([math.sin(y)*math.cos(p),math.cos(y)*math.cos(p),math.sin(p)])
    r0=np.array([math.cos(y),-math.sin(y),0.0]); u0=np.cross(r0,f)
    rr=r0*math.cos(r)+u0*math.sin(r); uu=-r0*math.sin(r)+u0*math.cos(r)
    return np.vstack([rr,-uu,f])
