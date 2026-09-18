"""Loaded R2 varactor curves at low band, narrow overlap and high band."""
from analyze import H,R
import re,json

cases=[('tt',14,243),('ff',17,101),('ss',41,6)]
controls=[.2,.4,.6,.8,1.0];stage=140e-9
wave=[(0.,controls[0])]
for i,v in enumerate(controls[1:],1):wave.extend([(i*stage,controls[i-1]),(i*stage+5e-9,v)])
for corner,k,code in cases:
    old=f'r2_{corner}_k{k}_c{code}';s=(R/old/old/'inputs'/f'{old}.scs').read_text()
    s=re.sub(r'^VC .*$', 'VC (ctrl 0) vsource type=pwl wave=['+' '.join(f'{t:.14g} {v:g}' for t,v in wave)+']',s,flags=re.M)
    s=re.sub(r'tran tran stop=\S+',f'tran tran stop={len(controls)*stage:.14g}',s)
    s=re.sub(r'^save .*$', 'save vp vn out VDD:p VVCO:p',s,flags=re.M)
    assert 'VC (ctrl 0)' in s
    (H/'tb'/f'fine_curve_{corner}_k{k}.scs').write_text(s)
(H/'results/fine_curve_stimulus.json').write_text(json.dumps(dict(cases=cases,control_v=controls,stage_s=stage,measure_after_s=100e-9),indent=2)+'\n')
