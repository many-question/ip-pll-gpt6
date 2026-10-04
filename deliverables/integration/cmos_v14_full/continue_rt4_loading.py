"""Run three reviewed RT4 control points after the old-bank audit releases its slot.

This is a finite dependency pipeline, not a recurring monitor. No candidate
adoption, noise acceptance, additional automatic batch or circuit change.
"""
from pathlib import Path
import datetime,hashlib,json,subprocess,sys,time
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
run='rt4load01';journal=ROOT/'research/rt4_loading_pipeline.json'
assert not journal.exists() and not (R/run).exists()
p=json.loads((H/'results/rt4_loading_protocol.json').read_text());assert p['run']==run
cases=[x['case'] for x in p['cases']]
assert cases==['rt4load_nominal_tt','rt4load_minus100m_tt','rt4load_minus250m_tt']
sha=lambda x:hashlib.sha256(x.read_bytes()).hexdigest()
for x in p['cases']:
    assert sha(H/'tb'/(x['case']+'.scs'))==x['tb_sha256']
    assert sha(H/'state_inputs'/(x['case']+'.ic'))==x['seed_sha256']
loading=json.loads((H/'results/sampler_loading_validation.json').read_text())
actual=json.loads((H/'results/core_noise_candidates_validation.json').read_text())
assert loading['complete'] and len(loading['cases'])==5 and all(x['valid_for_diagnosis'] for x in loading['cases'])
assert len(actual['cases'])==4
def record(state):
    journal.write_text(json.dumps(dict(state=state,updated=datetime.datetime.now().astimezone().isoformat(),run=run,
        cases=cases,threads=1,replacement_run='rt4fineaudit01',
        reviewed_basis='All five baseline loading controls and four actualLC comparisons are recovered. RT4 correct division but ~8MHz RF detuning motivates a measured frequency/control curve.',
        scope='Three pre-existing widened control points in the released one-thread long slot; same4long+1short/17thread maximum. No automatic closed-loop retry or adoption.'),indent=2)+'\n')
record('waiting_old_rt4_audit_completion');deadline=time.monotonic()+7200
while True:
    s=json.loads((ROOT/'research/rt4_fine_audit_pipeline.json').read_text())['state']
    if s.startswith('stopped'):
        record('stopped_predecessor_failed');raise SystemExit(1)
    if s=='completed_requires_review':break
    if time.monotonic()>deadline:
        record('stopped_wait_timeout');raise SystemExit(1)
    time.sleep(30)
check=subprocess.run([sys.executable,str(H/'analyze_rt2_fine_audit.py'),'--factor','4'],stdout=subprocess.DEVNULL)
v=json.loads((H/'results/rt4_fine_audit_validation.json').read_text())
if check.returncode or not v['complete'] or not v['passed']:
    record('stopped_predecessor_validation_failed');raise SystemExit(1)
record('running_rt4_control_curve')
r=subprocess.run([sys.executable,str(H/'run_spectre.py'),'--run-id',run,'--cases',*cases,
    '--mode','ax','--threads','1','--preset-override','all','--timeout','5400'])
if r.returncode:
    record('stopped_simulation_failure');raise SystemExit(r.returncode)
c=subprocess.run([sys.executable,str(H/'analyze_rt4_loading.py')],stdout=subprocess.DEVNULL)
record('completed_requires_review' if c.returncode==0 else 'stopped_analysis_failed')
raise SystemExit(c.returncode)
