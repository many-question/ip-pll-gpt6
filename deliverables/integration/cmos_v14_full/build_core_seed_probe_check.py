"""Isolate missing voltage-probe supply IC nodes with matched short transients.

The settled source transient did not save supply probe currents. Those zero-V
probe supply nodes are absent in its IC file, but the PSS fixture preserves
them when currents are saved. Both tests have identical observation topology;
only three derived 1.2 V IC entries differ. This is not a PSS/noise result.
"""
from pathlib import Path
import hashlib,json,re
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
source=H/'state_inputs/core_pulsetrip_settled_tt.ic'
nodes={x.split()[0] for x in source.read_text().splitlines() if x.strip() and not x.startswith('#')}
names=['XP.vco_vdd','XP.rx_vdd','XP.rt_vdd'];assert not set(names)&nodes
core=(H.parents[1]/'blocks/cmos_v14_full/pll_noise_pulsetrip_core_v14.scs').read_text()
for inst,node in [('VVCO','vco_vdd'),('VRX','rx_vdd'),('VRT','rt_vdd')]:
    assert f'{inst} ({node} vdd) vsource dc=0' in core
assert 'vdd\t1.2' in source.read_text()
dest=H/'state_inputs/core_pulsetrip_supply_seed_tt.ic';assert not dest.exists()
dest.write_text(source.read_text()+'\n# Exact zero-volt-probe constraints, no circuit change.\n'+''.join(k+'\t1.2\n' for k in names))
base=(H/'tb/core_pulsetrip_noise_probe_tt.scs').read_text()
base=re.sub(r'^(pss |pn |edge ).*\n','',base,flags=re.M)
base+='\nsave XP.vco_vdd XP.rx_vdd XP.rt_vdd XP.XR.qb XP.XR.ob\n'
cases=[]
for kind,seed in [('original',source),('complete',dest)]:
    case=f'core_seed_{kind}_tt';cases.append(case)
    tb=base+f'tran tran stop=10n readic="{seed.name}" skipdc=yes maxstep=1p method=traponly errpreset=conservative\n'
    p=H/'tb'/(case+'.scs');assert not p.exists();p.write_text(tb)
out=dict(scope=__doc__,run='coreseedcheck01',cases=cases,
    source_seed_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),complete_seed_sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),
    added_nodes=names,added_voltage_v=1.2,condition='Same TT27/1.2V/realLC core and current probes,10ns/1ps,skipdc; time0 equivalent to settled3us reference phase.',
    hypothesis='Unseeded retained supply nodes default to0 and cause initialization impulses. The test can isolate the impulse, but not prove it caused PSS failure.',
    full_pll_acceptance=False,noise_acceptance=False,main_dut_modified=False)
(H/'results/core_seed_probe_protocol.json').write_text(json.dumps(out,indent=2)+'\n')
print(' '.join(cases))
