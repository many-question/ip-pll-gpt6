"""Longer, fixed-window SS validation of the isolated PB1 threshold candidate.

The original120-200ns M6 acceptance failed. A diagnostic window sensitivity
check found correct output after140ns, unlike the old failed clock trees.
Preserve that failure and run new independent600ns tests, last200ns, for all
six modes at their highest planned RF frequency. No hindsight window trimming
is allowed for acceptance of this new run.
"""
from pathlib import Path
import json,re,hashlib

H=Path(__file__).resolve().parent
base=H/'tb/bankpulsetrip_m6_ss.scs'
s=base.read_text();cases=[]
for index,(m,rf) in enumerate([(4,3936),(6,3888),(8,3456),(10,3120),(12,3168),(14,3024)]):
    case=f'banktripsettled_m{m}_ss';cases.append(case)
    tb=s.replace('frequency=3888M',f'frequency={rf}M')
    tb=tb.replace('stop=200n outputstart=120n','stop=600n outputstart=400n')
    for i in range(6):
        tb=re.sub(r'(VS'+str(i)+r' .*dc=)[^\n]+',lambda match:match[1]+('1.2' if i==index else '0'),tb)
    p=H/'tb'/(case+'.scs');assert not p.exists();p.write_text(tb)
(H/'results/ss_settled_pulse_protocol.json').write_text(json.dumps(dict(scope=__doc__,
    source_tb_sha256=hashlib.sha256(base.read_bytes()).hexdigest(),cases=cases,
    run='banktripsettled01',condition='SS60/1.2V/10fF, actual MOS RX, measuredSS RF waveform replay,600ns/fixedlast200ns,1ps/reltol1e-5',
    main_dut_modified=False,prior_failure_not_reclassified=True,
    gates=['Nominal output and every-cycle period/range','RF/2 ratio and every-cycle swing',
           'No isolated late-window substitution for failing last200ns'],
    remaining=['TT/FF and temperature matrix','plannedRF low/intermediate endpoints','reset/mode changes','actualLC loading','noise/fullPLL']),indent=2)+'\n')
print(' '.join(cases))
