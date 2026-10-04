"""Audit the method-only physical-core experiment before any noise interpretation."""
from pathlib import Path
import hashlib,json,re,subprocess,sys
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=json.loads((H/'results/core_gear_trial_protocol.json').read_text());j=R/p['run']/p['case'];rp=j/'result.json'
if not rp.exists():print('pending');raise SystemExit(0)
r=json.loads(rp.read_text())
if not r.get('local_outputs_sha256'):print('pending collection');raise SystemExit(0)
base=R/'coretripquiet01/core_pulsetrip_quiet_noise_tt';old=json.loads((base/'result.json').read_text());assert r['remote_inputs_match']
def canonical(s):
    s=re.sub(r'/home/jielu/TSMC180/MP/IP-PLL-GPT6/simulation/cmos_v14_full/coretrip(?:quiet|gear)01_core_pulsetrip_(?:quiet|gear)_noise_tt','__JOB__',s)
    return s.replace('method=traponly','method=__ONLY_CHANGE__').replace('method=gear2only','method=__ONLY_CHANGE__')
assert canonical((j/'inputs'/(j.name+'.scs')).read_text())==canonical((base/'inputs'/(base.name+'.scs')).read_text())
assert {k:v for k,v in r['inputs_sha256'].items() if k!=j.name+'.scs'}=={k:v for k,v in old['inputs_sha256'].items() if k!=base.name+'.scs'}
log=(j/'spectre.out').read_text();assert sha(j/'spectre.out')==r['local_outputs_sha256']['spectre.out']
methods=re.findall(r'^\s*method\s*=\s*(\S+)\s*$',log,re.M);assert methods and all(x=='gear2only' for x in methods)
out=dict(scope=__doc__,source_result=rp.relative_to(ROOT).as_posix(),source_sha256=sha(rp),only_methods_changed=True,actual_logged_methods=methods,
    convergence_history=re.findall(r'^Conv norm.*$',log,re.M),previous_convergence_history=re.findall(r'^Conv norm.*$',(base/'spectre.out').read_text(),re.M),
    simulator_completed=bool(r['ok'] and 'spectre completes with 0 errors' in log),pss_achieved='The steady-state solution was achieved' in log,
    random_noise_integral_accepted=False,full_pll_acceptance=False,
    interpretation='Changing methods is verified independently of any convergence improvement. Fresh PSS success alone does not prove numerical accuracy, fullband randomRMS, all246edge equivalence or fullPLLcontrol-noise coverage.')
(H/'results/core_gear_trial_audit.json').write_text(json.dumps(out,indent=2)+'\n')
subprocess.run([sys.executable,str(H/'analyze_closedloop_noise.py'),p['run'],'--output','core_gear_noise_validation.json'],check=True)
print(json.dumps(out,indent=2))
