from build import *
name='r2_noise_divider'
bench(name,kind='r',core=120e-6,switch=1.2e-6,l=2e-9,unit=4.4e-15,fixed=10e-15,fine=4.5e-6,code=6,m=4,loaded=True,stop=200e-9)
p=H/'tb'/f'{name}.scs';s=p.read_text()
s=s.replace('temp=27','temp=27 gmin=1n')
s=re.sub(r'VR \(ref 0\).*\n','VR (ref 0) vsource dc=0\n',s)
s=re.sub(r'VRST \(rst 0\).*\n','VRST (rst 0) vsource type=pwl wave=[0 1.2 20n 1.2 20.02n 0]\n',s)
s=re.sub(r'tran tran .*\n',f'pss (out 0) pss fund=984M harms=63 tstab=400n method=traponly maxstep=2p errpreset=conservative saveinit=yes writepss="{name}.raw/steady_state.bin"\npn (vp vn) pnoise start=10k stop=500M dec=20 maxsideband=63 noiseout=[usb am pm] sweeptype=relative relharmnum=4\n',s)
s=re.sub(r'^save .*$', 'save vp vn out VDD:p VVCO:p',s,flags=re.M)
p.write_text(s)
