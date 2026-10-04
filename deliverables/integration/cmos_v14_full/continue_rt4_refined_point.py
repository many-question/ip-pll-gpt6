"""One physical RT4 refinement after the long-period RC measurement control."""
from pathlib import Path
import datetime,hashlib,json,subprocess,sys,time
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
p=json.loads((H/'results/rt4_refined_point_protocol.json').read_text());prior=json.loads((H/'results/noise_correlation_long_protocol.json').read_text())
journal=ROOT/'research/rt4_refined_point_pipeline.json';assert not journal.exists() and not (R/p['run']).exists()
def record(state):
    journal.write_text(json.dumps(dict(state=state,updated=datetime.datetime.now().astimezone().isoformat(),run=p['run'],case=p['case'],threads=1,replacement_run=prior['run'],scope='One3us RT4 clamped refinement only. No automatic clamp release or PSS retry.'),indent=2)+'\n')
record('waiting_rc_collection');deadline=time.monotonic()+10800
rp=R/prior['run']/prior['case']/'result.json'
while True:
    if rp.exists():
        try:r=json.loads(rp.read_text())
        except json.JSONDecodeError:r={}
        if r.get('local_outputs_sha256'):
            if not r['ok'] or not r.get('remote_inputs_match'):record('stopped_predecessor_failure');raise SystemExit(1)
            break
    if time.monotonic()>deadline:record('stopped_wait_timeout');raise SystemExit(1)
    time.sleep(30)
c=subprocess.run([sys.executable,str(H/'analyze_noise_correlation_long_control.py')])
if c.returncode:record('stopped_predecessor_analysis_failure');raise SystemExit(c.returncode)
# The diagnostic RC PSD pass/fail is reviewed separately; it cannot change this
# physical tuning point. Resource ownership and successful collection are required.
subprocess.run([sys.executable,str(ROOT/'research/snapshot_owned_v14_jobs.py')],check=True,stdout=subprocess.DEVNULL)
s=json.loads((ROOT/'research/v14_owned_jobs_latest.json').read_text());assert s['requested_threads']+1<=18 and len(s['jobs'])<=4
assert not any('/'+prior['case']+'.scs' in x['netlist'] for x in s['jobs'])
assert hashlib.sha256((H/'tb'/(p['case']+'.scs')).read_bytes()).hexdigest()==p['tb_sha256']
record('running')
ret=subprocess.run([sys.executable,str(H/'run_spectre.py'),'--run-id',p['run'],'--cases',p['case'],'--mode','ax','--threads','1','--preset-override','all','--timeout','21600'])
if ret.returncode:record('stopped_simulation_failure');raise SystemExit(ret.returncode)
c=subprocess.run([sys.executable,str(H/'analyze_rt4_matched_point.py'),'--protocol','rt4_refined_point_protocol.json','--output','rt4_refined_point_validation.json'])
record('completed_requires_review' if c.returncode==0 else 'stopped_analysis_failure');raise SystemExit(c.returncode)
