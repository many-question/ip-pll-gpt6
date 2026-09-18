from build import H
from analyze import R
for corner,k,code in [('ff',17,101),('ss',41,6),('tt',14,243)]:
    original=f'r2_{corner}_k{k}_c{code}'
    p=R/original/original/'inputs'/f'{original}.scs'
    s=p.read_text().replace('maxstep=2e-12','maxstep=1e-12')
    import re
    s=re.sub(r'^save .*$', 'save vp vn out VDD:p VVCO:p',s,flags=re.M)
    (H/'tb'/f'precision_{corner}_k{k}.scs').write_text(s)
