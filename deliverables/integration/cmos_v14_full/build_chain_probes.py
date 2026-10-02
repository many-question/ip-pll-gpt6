"""Prepare phase-position and isolated-noise checks at three fixed offsets.

Limited diagnostic spectra, not additional full-band jitter measurements.
Use globalnoiseon_inst: this Spectreversion ignores it on a pnoiseanalysis.
"""
from pathlib import Path
import json,datetime
H=Path(__file__).resolve().parent
base=(H/'tb/chain_noise_coarse_tt.scs').read_text()
base=base.replace('start=10k stop=492M dec=10','values=[1M 100M 492M]')
events=' '.join('edge'+str(i) for i in range(2,7))
s=base.replace('measurement=[edge]','measurement=['+events+']')
original='edge jitterevent trigger=[out] triggerthresh=0.6 triggernum=1 triggerdir=rise target=[out] jittercal=[Jee]'
assert original in s
s=s.replace(original,'\n'.join(f'edge{i} jitterevent trigger=[out] triggerthresh=0.6 triggernum={i} triggerdir=rise target=[out]' for i in range(2,7)))
(H/'tb/chain_edge_probe_tt.scs').write_text(s)
groups={'rt':['XR'],'rx':['XRX'],'divider':['XD'],'aux':['XACQ0','XACQ1','XACB0','XACB1','XCOUNT']}
for name,instances in groups.items():
 s=base.replace('temp=27','temp=27 noiseon_inst=['+' '.join(instances)+'] noiseon_type=all').replace(' jittercal=[Jee]','')
 (H/'tb'/f'chain_gate_{name}_tt.scs').write_text(s)
protocol=dict(created=datetime.datetime.now().astimezone().isoformat(),scope=__doc__,basis='chainnoise02/chain_noise_coarse_tt, identical RF replay and physicalchain',phase_numbers=[2,3,4,5,6],offsets_hz=[1e6,100e6,492e6],isolated_groups=groups,limits=dict(max_phase_psd_delta_db=.1,max_gate_psd_relative_difference=.001,max_excluded_noise_fraction=1e-8),not_full_band=True)
(H/'results/chain_probe_protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
print('Prepared5 diagnostics: five edgepositions and4 isolatednoisegroups,3offsets each')
