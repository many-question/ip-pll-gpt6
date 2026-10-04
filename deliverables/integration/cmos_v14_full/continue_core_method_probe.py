"""Finite20ns method controls, after both sampler tuning cases release the short slot."""
from pathlib import Path
import datetime,hashlib,json,subprocess,sys,time
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
p=json.loads((H/'results/core_method_probe_protocol.json').read_text());previous=json.loads((H/'results/sampler_tuning_protocol.json').read_text())
journal=ROOT/'research/core_method_probe_pipeline.json';assert not journal.exists() and not (R/p['run']).exists()
def record(state):
    journal.write_text(json.dumps(dict(state=state,updated=datetime.datetime.now().astimezone().isoformat(),run=p['run'],cases=[x['case'] for x in p['cases']],threads=1,replacement_run=previous['run'],scope='Four20ns warm controls after both750ns tuning points; same shortslot. No automatic PSS retry or circuit adoption.'),indent=2)+'\n')
record('waiting_two_tuning_cases');deadline=time.monotonic()+7200
while True:
    complete=[]
    for x in previous['cases']:
        rp=R/previous['run']/x['case']/'result.json'
        if not rp.exists():continue
        try:r=json.loads(rp.read_text())
        except json.JSONDecodeError:continue
        if not r.get('local_outputs_sha256'):continue
        if not r['ok']:
            record('stopped_predecessor_failed');raise SystemExit(1)
        assert r['remote_inputs_match']
        complete.append(x['case'])
    if len(complete)==len(previous['cases']):break
    if time.monotonic()>deadline:
        record('stopped_wait_timeout');raise SystemExit(1)
    time.sleep(30)
for x in p['cases']:
    assert hashlib.sha256((H/'tb'/(x['case']+'.scs')).read_bytes()).hexdigest()==x['tb_sha256']
record('running_four_short_controls')
r=subprocess.run([sys.executable,str(H/'run_spectre.py'),'--run-id',p['run'],'--cases',*[x['case'] for x in p['cases']],
    '--mode','ax','--threads','1','--preset-override','all','--timeout','1800'])
if r.returncode:
    record('stopped_simulation_failure');raise SystemExit(r.returncode)
c=subprocess.run([sys.executable,str(H/'analyze_core_method_probe.py')],stdout=subprocess.DEVNULL)
record('completed_requires_review' if c.returncode==0 else 'stopped_analysis_failed')
raise SystemExit(c.returncode)
