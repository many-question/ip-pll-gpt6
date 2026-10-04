"""One bounded tuning point after the already-running RC calibration releases its slot."""
from pathlib import Path
import datetime,hashlib,json,subprocess,sys,time
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
p=json.loads((H/'results/rt4_code24_tuning_protocol.json').read_text());previous=json.loads((H/'results/core_noise_calibration_protocol.json').read_text())
journal=ROOT/'research/rt4_code24_tuning_pipeline.json';assert not journal.exists() and not (R/p['run']).exists()
def record(state,**extra):
    journal.write_text(json.dumps(dict(state=state,updated=datetime.datetime.now().astimezone().isoformat(),run=p['run'],case=p['case'],threads=1,replacement_run='corecal01',scope='One750ns tuning point only; no automatic further batch.',**extra),indent=2)+'\n')
record('waiting_calibration_collection');deadline=time.monotonic()+10800
while True:
    done=0
    for x in previous['cases']:
        rp=R/previous['run']/x['case']/'result.json'
        if not rp.exists():continue
        try:r=json.loads(rp.read_text())
        except json.JSONDecodeError:continue
        if not r.get('local_outputs_sha256'):continue
        if not r['ok'] or not r.get('remote_inputs_match'):record('stopped_predecessor_failure');raise SystemExit(1)
        done+=1
    if done==2:break
    if time.monotonic()>deadline:record('stopped_wait_timeout');raise SystemExit(1)
    time.sleep(30)
subprocess.run([sys.executable,str(ROOT/'research/snapshot_owned_v14_jobs.py')],check=True,stdout=subprocess.DEVNULL)
s=json.loads((ROOT/'research/v14_owned_jobs_latest.json').read_text())
assert s['requested_threads']+1<=18 and len(s['jobs'])<=4
assert not any('/noise_core_cal_' in x['netlist'] for x in s['jobs'])
assert hashlib.sha256((H/'tb'/(p['case']+'.scs')).read_bytes()).hexdigest()==p['tb_sha256']
record('running',threads_at_dispatch=s['requested_threads']+1)
r=subprocess.run([sys.executable,str(H/'run_spectre.py'),'--run-id',p['run'],'--cases',p['case'],'--mode','ax','--threads','1','--preset-override','all','--timeout','7200'])
if r.returncode:record('stopped_simulation_failure');raise SystemExit(r.returncode)
c=subprocess.run([sys.executable,str(H/'analyze_rt4_code24_tuning.py')])
record('completed_requires_review' if c.returncode==0 else 'stopped_analysis_failure');raise SystemExit(c.returncode)
