"""Prepare six-edge and five isolated-noise checks; each solves PSS fresh.

Launch only after the matched-offset numerical screen passes. These sparse
points check measurement consistency and attribution, not integrated RMS.
"""
from pathlib import Path
import json

H=Path(__file__).resolve().parent
groups=json.loads((H/'results/rt_noise_gate2_validation.json').read_text())['groups']
base=(H/'tb/chain_rt2_precision_fine_tt.scs').read_text()
base=base.replace('values=[10k 100k 1M 10M 100M 491.99M]','values=[1M 100M 491.99M]')
line=next(x for x in base.splitlines() if x.startswith('edge jitterevent'))
edges=base.replace('measurement=[edge]','measurement=['+' '.join(f'edge{i}' for i in range(1,7))+']')
edges=edges.replace(line,'\n'.join(line.replace('edge jitterevent',f'edge{i} jitterevent').replace('triggernum=1',f'triggernum={i}') for i in range(1,7)))
cases=['chain_rt2_fine_edges_tt']+[f'chain_rt2_fine_only_{g}_tt' for g in groups]
for case,body in [(cases[0],edges)]+[(case,base.replace('temp=27','temp=27 noiseon_inst=['+' '.join(groups[g])+'] noiseon_type=all')) for case,g in zip(cases[1:],groups)]:
    p=H/'tb'/(case+'.scs'); assert not p.exists(); p.write_text(body)
    assert 'readpss=' not in body and 'writepss=' in body
out=dict(scope=__doc__,run='rt2fineaudit01',cases=cases,groups=groups,offsets_hz=[1e6,1e8,491.99e6],
         launch_gate='rt2_precision_validation.json passed=true; no overlapping replacement of its single thread.',
         noise_gate_relative_limit=.001,edge_spread_limit_db=.2,
         condition='Same TT27/1.2V/984MHz/10fF local-chain candidate, 0.5ps/767sidebands/maxacfreq504GHz.',
         full_band_integral=False,full_pll_acceptance=False,main_dut_modified=False)
(H/'results/rt2_fine_audit_protocol.json').write_text(json.dumps(out,indent=2)+'\n')
print(' '.join(cases))
