"""Same-DUT numerical/retention checks initialized from the actual cold result.

This imports terminal voltages/currents, not a native continuation. Do not join
these trajectories to the cold run or claim uninterrupted observer history.
"""
from pathlib import Path
import hashlib,json,re
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
source=ROOT/'research/runs/spectre_cmos_v14_full/repaircold01/repair_capture_tt/final.ic'
result=json.loads((H/'results/capture_repaircold01.json').read_text())
assert result['functional_capture_screen_passed']
removed=[];lines=[]
for line in source.read_text().splitlines():
 if not line or line.startswith('#'):continue
 node=line.split()[0]
 if node.startswith(('XOBS.','XE.')) or node in ['energy_nj','power_mw','obsphase','obscycles','obsctrl','obsdivcycles']:
  removed.append(node)
 else:lines.append(line)
dest=H/'state_inputs/repair_actual64_tt.ic'
dest.write_text('# Actual repaircold01 64us terminal state; observers reinitialized, not native continuation.\n'+'\n'.join(lines)+'\n')
s=(H/'tb/repair_capture_tt.scs').read_text()
s=re.sub(r'^VRST .*$', 'VRST (reset 0) vsource dc=0',s,flags=re.M)
s=re.sub(r'^VAP .*$', 'VAP (apply 0) vsource dc=0',s,flags=re.M)
s=re.sub(r'^ic .*\n','',s,flags=re.M)
instrument=(H/'tb/complete_strict_tt.scs').read_text().split('ahdl_include "tb_edge_observer.va"',1)[1]
s+='\nahdl_include "tb_edge_observer.va"'+instrument
for label,stop,step,tol in [('strict',4,1,'1e-5'),('retain',36,4,'1e-4')]:
 tb=s.replace('stop=64u',f'stop={stop}u readic="repair_actual64_tt.ic"').replace('maxstep=4p',f'maxstep={step}p').replace('reltol=1e-4',f'reltol={tol}')
 if label=='strict':tb=tb.replace('vabstol=1e-6','vabstol=1e-7').replace('iabstol=1e-12','iabstol=1e-13')
 (H/'tb'/f'repair_{label}_tt.scs').write_text(tb)
proof=dict(scope=__doc__,source=source.relative_to(ROOT).as_posix(),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
 state_sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),removed_observer_nodes=removed,
 changed_DUT_initial_values=[],reference_phase='64us is exactly1536 reference periods; retain1ns reference delay in the new time origin.',
 acceptance='Last1us existing stationarity criteria, qualified/frequency_good high, range_error low, no restart. Retention36us covers at least one32us control/divider period after initialization.',
 power='Internal-timestep supply/branch energy integration; average8..36us plus full4..36us32us cycle for retention, not sparse RF current averaging.')
(H/'results/repair_retention_protocol.json').write_text(json.dumps(proof,indent=2)+'\n')
print('Built strict4us and retention36us tests from actual terminal state; no DUT changes.')
