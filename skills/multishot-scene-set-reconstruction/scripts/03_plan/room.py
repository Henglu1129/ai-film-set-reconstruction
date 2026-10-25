# Final room model (metres). x east+, y north+, z up. South (door) wall y=0, stage front y=17.8, back wall y=22.6
W=10.4; X0,X1=-5.2,5.2; YS=0.0; YF=17.8; YN=22.6; HS=0.5; HC=4.3
DOOR=dict(xc=0.14,half=1.73,open=0.89,cross=2.35,top=2.9)
AC=dict(x0=2.56,x1=4.24,y0=0.2,y1=0.9,h=2.15)
PORT=dict(xc=-0.34,w=1.46,h=1.95,zb=0.98)
SDOOR_W=(15.74,17.0,2.0); SDOOR_E=(15.98,17.25,2.0)
def segs():
    S=[]
    def box(x0,y0,z0,x1,y1,z1):
        P=[(x,y,z) for x in (x0,x1) for y in (y0,y1) for z in (z0,z1)]
        E=[(0,1),(2,3),(4,5),(6,7),(0,2),(1,3),(4,6),(5,7),(0,4),(1,5),(2,6),(3,7)]
        return [(P[a],P[b]) for a,b in E]
    # floor/wall edges
    for (a,b) in [((X0,YS,0),(X1,YS,0)),((X0,YS,0),(X0,YF,0)),((X1,YS,0),(X1,YF,0)),((X0,YS,HC),(X1,YS,HC)),((X0,YS,0),(X0,YS,HC)),((X1,YS,0),(X1,YS,HC)),
                  ((X0,YF,0),(X1,YF,0)),((X0,YF,HS),(X1,YF,HS)),((X0,YN,HS),(X1,YN,HS)),((X0,YN,HC),(X1,YN,HC)),((X0,YF,HS),(X0,YN,HS)),((X1,YF,HS),(X1,YN,HS)),
                  ((X0,YN,HS),(X0,YN,HC)),((X1,YN,HS),(X1,YN,HC)),((X0,YS,HC),(X0,YN,HC)),((X1,YS,HC),(X1,YN,HC))]: S.append((a,b,'room'))
    d=DOOR; xc=d['xc']
    for x in (xc-d['half'],xc-d['open'],xc+d['open'],xc+d['half']): S.append(((x,YS,0),(x,YS,d['cross']),'door'))
    S+= [((xc-d['half'],YS,d['cross']),(xc+d['half'],YS,d['cross']),'door'),((xc-d['half'],YS,d['top']),(xc+d['half'],YS,d['top']),'door'),
         ((xc-d['half'],YS,d['cross']),(xc-d['half'],YS,d['top']),'door'),((xc+d['half'],YS,d['cross']),(xc+d['half'],YS,d['top']),'door')]
    S+= [(a,b,'ac') for a,b in box(AC['x0'],AC['y0'],0,AC['x1'],AC['y1'],AC['h'])]
    p=PORT; y=YN-0.03
    S+= [((p['xc']-p['w']/2,y,p['zb']),(p['xc']+p['w']/2,y,p['zb']),'port'),((p['xc']-p['w']/2,y,p['zb']+p['h']),(p['xc']+p['w']/2,y,p['zb']+p['h']),'port'),
         ((p['xc']-p['w']/2,y,p['zb']),(p['xc']-p['w']/2,y,p['zb']+p['h']),'port'),((p['xc']+p['w']/2,y,p['zb']),(p['xc']+p['w']/2,y,p['zb']+p['h']),'port')]
    for (y0,y1,h),x in [(SDOOR_W,X0),(SDOOR_E,X1)]:
        S+= [((x,y0,0),(x,y0,h),'sdoor'),((x,y1,0),(x,y1,h),'sdoor'),((x,y0,h),(x,y1,h),'sdoor')]
    # 1.80 m reference poles at Chen station
    return S
