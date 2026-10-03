"""PSS convergence diagnostic; same circuit, longer settling and Gear2.

The previous 5us transient's text state is only a seed. Its PSS restart
showed a decaying phase transient, and the Newton iterations then diverged.
This experiment does not relax periodic residual tolerances or change the DUT.
The failed periodic.state must NOT be reused.
"""
from pathlib import Path
import hashlib,json
H=Path(__file__).resolve().parent; ROOT=H.parents[3]
J=ROOT/'research/runs/spectre_cmos_v14_full/coreregisterprobe01/core_register_noise_probe_tt'
rec=json.loads((J/'result.json').read_text())
assert not rec['ok'] and rec['remote_inputs_match']
source=J/'inputs/core_register_noise_probe_tt.scs'
s=source.read_text()
# Frozen runner inputs contain remote substitutions for state paths.
import re
s=re.sub(r'readic="[^"]+"','readic="core_register_settled_tt.ic"',s)
s=re.sub(r'writefinal="[^"]+"','writefinal="__FINAL_STATE__"',s)
s=re.sub(r'writepss="[^"]+"','writepss="__PERIODIC_STATE__"',s)
assert 'tstab=250n' in s and 'method=traponly' in s
s=s.replace('tstab=250n','tstab=2u').replace('method=traponly','method=gear2only tstabmethod=gear2only')
s=s.replace('maxperiods=12','maxperiods=20')
s+='save XP.XD.XRL.a XP.XD.XRL.b XP.XD.load XP.XD.loadb XP.XD.XD12.X0.XM.fb XP.XD.ck\n'
dest=H/'tb/core_register_noise_gear_tt.scs';dest.write_text(s)
available={p.name:p for p in (H.parents[1]/'blocks').glob('*/*') if p.suffix in ('.scs','.va')}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for name,digest in rec['inputs_sha256'].items():
 if name in available:assert sha(available[name])==digest,name
assert sha(H/'state_inputs/core_register_settled_tt.ic')==rec['inputs_sha256']['core_register_settled_tt.ic']
(H/'results/noise_recovery_protocol.json').write_text(json.dumps(dict(
 scope=__doc__,source_result=(J/'result.json').relative_to(ROOT).as_posix(),
 source_sha256=sha(J/'result.json'),changes=['tstab250ns->2us','traponly->gear2only for both tstab and shooting','maxperiods12->20','observe inactive reset latch and div12 internal state'],
 physical_dependencies_unchanged=True,relaxed_residual_tolerance=False,
 previous_periodic_state_valid=False,full_pll_acceptance=False,
 case=dest.stem,netlist_sha256=sha(dest)),indent=2)+'\n')
print(dest.stem)
