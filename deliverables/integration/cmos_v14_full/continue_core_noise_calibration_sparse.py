"""Two analytic-RC controls after the single physical RT4 tuning point."""
from pathlib import Path
import datetime,hashlib,json,subprocess,sys,time
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
p=json.loads((H/'results/core_noise_calibration_sparse_protocol.json').read_text());previous=json.loads((H/'results/rt4_code24_tuning_protocol.json').read_text())
journal=ROOT/'research/core_noise_calibration_sparse_pipeline.json';assert not journal.exists() and not (R/p['run']).exists()
def record(state):
    journal.write_text(json.dumps(dict(state=state,updated=datetime.datetime.now().astimezone().isoformat(),run=p['run'],cases=[x['case'] for x in p['cases']],threads=1,replacement_run=previous['run'],scope='Two six-frequency analyticRC calibration cases only; fresh PSS; no further batch.'),indent=2)+'\n')
record('waiting_rt4_tuning_collection');deadline=time.monotonic()+10800
rp=R/previous['run']/previous['case']/'result.json'
while True:
    if rp.exists():
        try:r=json.loads(rp.read_text())
        except json.JSONDecodeError:r={}
        if r.get('local_outputs_sha256'):
            if not r['ok'] or not r.get('remote_inputs_match'):record('stopped_predecessor_failure');raise SystemExit(1)
            break
    if time.monotonic()>deadline:record('stopped_wait_timeout');raise SystemExit(1)
    time.sleep(30)
subprocess.run([sys.executable,str(ROOT/'research/snapshot_owned_v14_jobs.py')],check=True,stdout=subprocess.DEVNULL)
s=json.loads((ROOT/'research/v14_owned_jobs_latest.json').read_text());assert s['requested_threads']+1<=18 and len(s['jobs'])<=4
assert not any('/'+previous['case']+'.scs' in x['netlist'] for x in s['jobs'])
for x in p['cases']:assert hashlib.sha256((H/'tb'/(x['case']+'.scs')).read_bytes()).hexdigest()==x['tb_sha256']
record('running')
r=subprocess.run([sys.executable,str(H/'run_spectre.py'),'--run-id',p['run'],'--cases',*[x['case'] for x in p['cases']],'--mode','ax','--threads','1','--preset-override','all','--timeout','7200'])
if r.returncode:record('stopped_simulation_failure');raise SystemExit(r.returncode)
c=subprocess.run([sys.executable,str(H/'analyze_core_noise_calibration.py'),'--protocol','core_noise_calibration_sparse_protocol.json'])
record('completed_requires_review' if c.returncode==0 else 'stopped_analysis_failure');raise SystemExit(c.returncode)
