"""Two settled fine-control points in one run, under the actual selected divider."""
from build import *
P=dict(kind='r',core=120e-6,switch=1.2e-6,l=2e-9,unit=4.4e-15)
def channel(name,code,m,corner='tt',settled=False,**kwargs):
    bench(name,code=code,m=m,corner=corner,loaded=True,stop=(280e-9 if settled else 200e-9),**(P|kwargs))
    p=H/'tb'/f'{name}.scs';s=p.read_text()
    wave='0 0.2 160n 0.2 165n 1.0' if settled else '0 0.2 100n 0.2 105n 1.0'
    s=s.replace('VC (ctrl 0) vsource dc=0.6',f'VC (ctrl 0) vsource type=pwl wave=[{wave}]')
    # Frequency coverage needs tank voltages, divided edges and both measured
    # supply currents. Do not store unused internal waveforms for every channel.
    s=re.sub(r'^save .*$', 'save vp vn out VDD:p VVCO:p',s,flags=re.M)
    p.write_text(s)
    meta=H/'cases'/f'{name}.json';d=json.loads(meta.read_text());d['fine_endpoint_windows_s']=([[110e-9,150e-9],[240e-9,280e-9]] if settled else [[50e-9,90e-9],[160e-9,200e-9]]);d['fine_controls_v']=[.2,1.0];meta.write_text(json.dumps(d,indent=2)+'\n')
    return name
if __name__=='__main__':
    for c in ['tt','ss','ff']:
        for code in [8,9,10]:channel(f'hi_{c}_c{code}',code,4,c)
