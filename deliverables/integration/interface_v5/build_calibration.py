"""Create clamped-control calibration; all physical loading is retained."""
from pathlib import Path
import re
H=Path(__file__).resolve().parent
s=(H/'tb/timing_both.scs').read_text()
for label,levels in [('fine',[.65,.75,.85,.95]),('local',[.80,.82,.84,.86])]:
    pairs=['0 '+str(levels[0])]
    for i,v in enumerate(levels[1:],1):
        pairs.extend([f'{i*180}n {levels[i-1]}',f'{i*180+5}n {v}'])
    t=re.sub(r'VC .*', 'VC (ctrl 0) vsource type=pwl wave=['+' '.join(pairs)+']',s)
    t=re.sub(r'tran tran .*','tran tran stop=720n maxstep=2p errpreset=conservative',t)
    t=t.replace('save vp vn out','save ctrl pulse refb vp vn out')
    (H/'tb'/f'cal_{label}.scs').write_text(t)
print('Built fine and local calibration fixtures')
