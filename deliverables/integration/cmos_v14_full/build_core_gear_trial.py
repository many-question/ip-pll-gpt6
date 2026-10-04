"""Prepare one method-only fresh-PSS trial after four measured method/mesh controls."""
from pathlib import Path
import datetime,hashlib,json
H=Path(__file__).resolve().parent;ROOT=H.parents[3];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
v=json.loads((H/'results/core_method_probe_validation.json').read_text())
assert v['complete'] and len(v['cases'])==4 and all(x['simulation_completed'] for x in v['cases'])
q=json.loads((H/'results/core_quiet_trial_audit.json').read_text());assert not q['periodic_state_valid'] and q['only_tstab_changed']
src=H/'tb/core_pulsetrip_quiet_noise_tt.scs';body=src.read_text()
assert body.count('method=traponly')==2 and 'maxstep=1p' in body
body=body.replace('method=traponly','method=gear2only')
target=H/'tb/core_pulsetrip_gear_noise_tt.scs';assert not target.exists();target.write_text(body)
out=dict(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),status='prepared_not_run',run='coretripgear01',case=target.stem,
    source_tb_sha256=sha(src),tb_sha256=sha(target),method_probe_result_sha256=sha(H/'results/core_method_probe_validation.json'),
    quiet_trial_audit_sha256=sha(H/'results/core_quiet_trial_audit.json'),
    only_change='Both tstabmethod and shooting method traponly to gear2only. Same1ps,1e-5/1e-7/1e-13,250ns,tstab1.134023us,actual late seed,physical circuit and six PNoise offsets.',
    hypothesis='Current highband peak follows inverse step (~505GHz at1ps,~997GHz at.5ps), whereas Gear2 lacks that component. This supports trapezoidal numerical ringing; its role in PSS failure still needs the method-only trial.',
    primary_tool_documentation=dict(path='research/spectre_help/pss.txt',sha256=sha(ROOT/'research/spectre_help/pss.txt'),lines=[214,223,888,903],
        note='Installed Spectre help permits gear2only and warns both of trapezoidal point-to-point ringing and artificial damping from Gear. No tolerances are relaxed.'),
    launch_gate='Reuse rt4loadlimit01 completed one-thread long slot, with2threads using existing spare budget; verify <=18 total and no extra long job. Finite single trial, no automatic retries.',
    acceptance='Fresh PSS achieved plus periodic branch/edge/endpoint and device-PSD checks; six points never integrated as fullband RMS. Follow with independent mesh/noise validation before acceptance.',
    limitations=['Twenty ns method controls are not loop stationarity or random noise.','Changing method may alter frequency/amplitude and produce artificial damping; convergence alone is not validation.','Core uses static slow controls; not the complete PLL or all frequency/PVT coverage.'],main_dut_modified=False,full_pll_acceptance=False)
(H/'results/core_gear_trial_protocol.json').write_text(json.dumps(out,indent=2)+'\n');print(target.stem)
