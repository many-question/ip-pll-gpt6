from build import *
P=dict(kind='r',core=120e-6,switch=1.2e-6,l=2e-9,unit=4.4e-15)
for corner in ['tt','ss','ff']:
    for code in [8,248]:
        bench(f'noise_proxy_{corner}_c{code}',code=code,corner=corner,proxy=140e-15,analysis='noise',stop=200e-9,step=2e-12,sidebands=63,fund=3.94e9 if code==8 else 2.69e9,**P)

# Autonomous VCO + the actual /4 divider. Sampler and CP are physically
# present but held OFF: this is a loading/back-action check, not PLL noise.
name='noise_divider_tt_c8';bench(name,code=8,m=4,loaded=True,stop=200e-9,**P)
p=H/'tb'/f'{name}.scs';s=p.read_text()
s=re.sub(r'VR \(ref 0\).*\n','VR (ref 0) vsource dc=0\n',s)
s=re.sub(r'VRST \(rst 0\).*\n','VRST (rst 0) vsource type=pwl wave=[0 1.2 20n 1.2 20.02n 0]\n',s)
s=re.sub(r'tran tran .*\n','pss (out 0) pss fund=984M harms=63 tstab=200n maxstep=2p errpreset=conservative saveinit=yes\npn (vp vn) pnoise start=10k stop=500M dec=20 maxsideband=63 noiseout=[usb am pm] sweeptype=relative relharmnum=4\n',s)
p.write_text(s)
