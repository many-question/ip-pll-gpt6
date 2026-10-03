"""Finite updated-divider noise probes in the released RT2 audit slot."""
from pathlib import Path
import datetime,json,subprocess,sys,time
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
p=json.loads((H/'results/rt_pulsetrip_noise_protocol.json').read_text())
cases=[x['case'] for x in p['cases'] if x['grade']=='probe'];run='rtpulsetripprobe01'
journal=ROOT/'research/rt_pulsetrip_noise_pipeline.json'
assert len(cases)==2 and not (R/run).exists() and not journal.exists()
def record(state):
    journal.write_text(json.dumps(dict(state=state,updated=datetime.datetime.now().astimezone().isoformat(),
        run=run,cases=cases,threads=1,replacement_run='rt2fineaudit01',
        scope='Two freshPSS six-offset local-chain probes with updated divider. Same one-thread long slot; no automatic full-band job or main-DUT adoption.'),indent=2)+'\n')
record('waiting_rt2_audit_completion');deadline=time.monotonic()+7200
while True:
    state=json.loads((ROOT/'research/rt2_fine_audit_pipeline.json').read_text())['state']
    if state.startswith('stopped'):
        record('stopped_predecessor_failed');raise SystemExit(1)
    if state=='completed_requires_review':break
    if time.monotonic()>deadline:
        record('stopped_wait_timeout');raise SystemExit(1)
    time.sleep(30)
record('validating_completed_predecessor')
check=subprocess.run([sys.executable,str(H/'analyze_rt2_fine_audit.py')],stdout=subprocess.DEVNULL)
if check.returncode:
    record('stopped_predecessor_analysis_failed');raise SystemExit(1)
v=json.loads((H/'results/rt2_fine_audit_validation.json').read_text())
if not v['complete'] or not v['passed']:
    record('stopped_predecessor_gate_failed');raise SystemExit(1)
# Completed audit's analyzer checks local results, fresh-state provenance,
# zero-error logs, six edges, branch ratios, all five groups and excluded noise.
record('running_repaired_divider_probes')
res=subprocess.run([sys.executable,str(H/'run_spectre.py'),'--run-id',run,'--cases',*cases,
    '--mode','ax','--threads','1','--preset-override','all','--timeout','5400'])
if res.returncode:
    record('stopped_simulation_failure');raise SystemExit(res.returncode)
check=subprocess.run([sys.executable,str(H/'analyze_rt_pulsetrip_noise.py')],stdout=subprocess.DEVNULL)
record('completed_requires_review' if check.returncode==0 else 'stopped_analysis_failed')
raise SystemExit(check.returncode)
