"""Recover actual SS RF shape from the already-validated full-DUT near-lock state.

This is a short dense restart at unchanged precision, not a new reset-capture
proof. It lets SS receiver tests use an SS source instead of frequency-scaled TT.
"""
from pathlib import Path
import hashlib,re,json
H=Path(__file__).resolve().parent;ROOT=H.parents[3];D=H.parents[1]
j=ROOT/'research/runs/spectre_cmos_v14_full/completess01/complete_near_ss'
rec=json.loads((j/'result.json').read_text());assert rec['remote_inputs_match']
assert 'spectre completes with 0 errors' in (j/'spectre.out').read_text()
available={p.name:p for p in (D/'blocks').rglob('*') if p.suffix in ['.scs','.va']}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
proof={}
for p in (j/'inputs').iterdir():
 if p.name=='complete_near_ss.scs' or p.suffix=='.ic':continue
 assert p.name in available and sha(p)==sha(available[p.name]),p.name
 proof[p.name]=sha(p)
state=H/'state_inputs/ss_interface_seed.ic';state.write_bytes((j/'final.ic').read_bytes())
s=(j/'inputs/complete_near_ss.scs').read_text()
s=re.sub(r'^tran tran .*$', 'tran tran stop=100n outputstart=50n readic="ss_interface_seed.ic" maxstep=1p method=traponly errpreset=conservative writefinal="__FINAL_STATE__"',s,flags=re.M)
s+='save XP.vp XP.vn XP.refb XP.clk XP.q1 XP.data\n'
(H/'tb/ss_interface_dense.scs').write_text(s)
(H/'results/ss_interface_dense_protocol.json').write_text(json.dumps(dict(scope=__doc__,source_run='completess01/complete_near_ss',source_state_sha256=sha(state),verified_unchanged_dependencies=proof,condition='SS60/1.2V/K41/M4/10fF/Q5;1ps/reltol1e-5.100ns,last50ns dense. Same physical complete_v14,not new capture_v14 reset.'),indent=2)+'\n')
print('Prepared same-DUT SS dense restart; source dependencies unchanged.')
