"""Finite method-only PSS trial after the RT4 boundary point releases its long slot."""
from pathlib import Path
import datetime,hashlib,json,subprocess,sys,time
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
p=json.loads((H/'results/core_gear_trial_protocol.json').read_text());journal=ROOT/'research/core_gear_trial_pipeline.json'
assert not journal.exists() and not (R/p['run']).exists()
def record(state,**extra):
    journal.write_text(json.dumps(dict(state=state,updated=datetime.datetime.now().astimezone().isoformat(),run=p['run'],case=p['case'],threads=2,replacement_run='rt4loadlimit01',scope='One method-only diagnostic, fresh PSS and six offsets, no automatic further batch or adoption.',**extra),indent=2)+'\n')
record('waiting_rt4_limit_result');deadline=time.monotonic()+7200
rp=R/'rt4loadlimit01/rt4load_v200_tt/result.json'
while True:
    if rp.exists():
        try:r=json.loads(rp.read_text())
        except json.JSONDecodeError:r={}
        if r.get('local_outputs_sha256'):
            if not r['ok'] or not r.get('remote_inputs_match'):
                record('stopped_predecessor_failure');raise SystemExit(1)
            break
    if time.monotonic()>deadline:record('stopped_wait_timeout');raise SystemExit(1)
    time.sleep(30)
subprocess.run([sys.executable,str(ROOT/'research/snapshot_owned_v14_jobs.py')],check=True,stdout=subprocess.DEVNULL)
jobs=json.loads((ROOT/'research/v14_owned_jobs_latest.json').read_text())
assert jobs['requested_threads']+2<=18 and len(jobs['jobs'])<=4
assert not any('/rt4load_v200_tt.scs' in x['netlist'] for x in jobs['jobs'])
assert hashlib.sha256((H/'tb'/(p['case']+'.scs')).read_bytes()).hexdigest()==p['tb_sha256']
record('running',threads_at_dispatch=jobs['requested_threads']+2)
r=subprocess.run([sys.executable,str(H/'run_spectre.py'),'--run-id',p['run'],'--cases',p['case'],'--mode','ax','--threads','2','--preset-override','all','--timeout','43200'])
record('completed_requires_review' if r.returncode==0 else 'stopped_simulation_failure')
raise SystemExit(r.returncode)
