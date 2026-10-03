"""Prepare PSS only from a completed, stationary physical-register core.

The full PLL is unchanged. Reference loading remains an approximation and
other slow controls remain fixed ideal pins. This cannot sign off PLL RMS.
"""
from pathlib import Path
import hashlib,json,re
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
j=ROOT/'research/runs/spectre_cmos_v14_full/coressettle01/core_register_settle_tt'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
v=json.loads((H/'results/core_settle_validation.json').read_text())
assert v['preflight_passed'],'Stationary phase/code screen must pass before PSS'
r=json.loads((j/'result.json').read_text());assert r['ok'] and r['remote_inputs_match']
assert sha(j/'result.json')==v['source_sha256']
assert sha(j/'final.ic')==r['local_outputs_sha256']['final.ic']
available={p.name:p for p in (H.parents[1]/'blocks').glob('*/*') if p.suffix in ('.scs','.va')}
for name,digest in r['inputs_sha256'].items():
 if name in available:assert sha(available[name])==digest,('Core dependency changed',name)
source=(j/'inputs/core_register_settle_tt.scs').read_text()
assert 'ref_load=1.9p' in source and 'maxstep=1p' in source and 'reltol=1e-5' in source
lines=['# Same-core5us final state; excludes TB-only observer state.']
for line in (j/'final.ic').read_text().splitlines():
 if not line.strip() or line.startswith('#'):continue
 node=line.split()[0]
 if node.startswith('XP.') or node=='out':lines.append(line)
ic=H/'state_inputs/core_register_settled_tt.ic';ic.write_text('\n'.join(lines)+'\n')
base=(H/'tb/core_noise_probe_tt.scs').read_text()
base=base.replace('pll_noise_core_v14','pll_noise_register_core_v14').replace('XP (ref out vdd 0) pll_noise_register_core_v14','XP (ref out vdd 0) pll_noise_register_core_v14 ref_load=1.9p')
base=base.replace('closedloop_core_tt.ic',ic.name).replace('tstab=1u','tstab=250n')
assert 'lc_loop_observer' not in base
base+='save XP.b0 XP.b1 XP.b2 XP.b3 XP.b4 XP.b5 XP.b6 XP.b7\n'
for label in ['probe','band']:
 s=base if label=='probe' else base.replace('values=[10k 100k 1M 10M 100M 491.99M]','start=10k stop=492M dec=20')
 (H/'tb'/f'core_register_noise_{label}_tt.scs').write_text(s)
(H/'results/register_noise_protocol.json').write_text(json.dumps(dict(scope=__doc__,source_result=v['source_result'],source_sha256=v['source_sha256'],source_ic_sha256=sha(j/'final.ic'),filtered_ic_sha256=sha(ic),preflight=v,pss_fund_hz=4000000,pss_tstab_ns=250,harmonics=4095,maxsideband=4095,condition='TT27/1.2V/K41/M4/10fF/Q5; coarse23 physical8DFF,additionalref1.9pF. FullDUT equivalence not established.',full_pll_acceptance=False),indent=2)+'\n')
print('Prepared core_register_noise_probe_tt and band. Probe must converge and match operating point before integrating noise.')
