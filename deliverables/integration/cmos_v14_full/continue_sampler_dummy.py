"""Finite three-case MOS compensation test after reviewed loading controls.

The clocked/track/hold results have been reviewed. Wait for both remaining
KVCO probes to finish and pass, then reuse exactly the same one-thread slot.
No periodic scheduling, no main-DUT changes and no automatic follow-on batch.
"""
from pathlib import Path
import datetime,json,subprocess,sys,time
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
R=ROOT/'research/runs/spectre_cmos_v14_full';journal=ROOT/'research/sampler_dummy_pipeline.json'
source=json.loads((H/'results/sampler_loading_protocol.json').read_text())
protocol=json.loads((H/'results/sampler_dummy_protocol.json').read_text())
observed=json.loads((H/'results/sampler_loading_validation.json').read_text())
reviewed={x['case']:x for x in observed['cases'] if x['valid_for_diagnosis']}
assert all('samplerload_'+x+'_tt' in reviewed for x in ['clocked','track','hold'])
assert observed['comparison']['hold_minus_track_rf_hz']>9e6
assert observed['clocked_clamp_comparison']['output24_pm_ratio_clamped_to_unclamped']>.9
assert not (R/protocol['run']).exists() and not journal.exists()
cases=[x['case'] for x in protocol['cases']]
def record(state,**kw):
    journal.write_text(json.dumps(dict(state=state,updated=datetime.datetime.now().astimezone().isoformat(),
        run=protocol['run'],cases=cases,threads=1,release_run=source['run'],
        reviewed_basis='Clocked/control-clamped reference PM persists; measured DC hold-track frequency split9.531425MHz. Three diagnostic controls reviewed before this finite dispatch.',
        scope='Same released short slot; bounded40/80/120fF MOS dummy comparison. No PLL jitter/closed-loop acceptance or automatic adoption.',**kw),indent=2)+'\n')
record('waiting_existing_loading_batch_release');deadline=time.monotonic()+7200
while True:
    state=json.loads((ROOT/'research/sampler_loading_pipeline.json').read_text())['state']
    if state.startswith('stopped'):
        record('stopped_predecessor_failure');raise SystemExit(1)
    if state=='completed_requires_review':break
    if time.monotonic()>deadline:
        record('stopped_wait_timeout');raise SystemExit(1)
    time.sleep(30)
for case in source['cases']:
    j=R/source['run']/case['case'];r=json.loads((j/'result.json').read_text())
    assert r['ok'] and r['remote_inputs_match'] and r.get('local_outputs_sha256')
    assert 'spectre completes with 0 errors' in (j/'spectre.out').read_text()
subprocess.run([sys.executable,str(H/'analyze_sampler_loading.py')],check=True,stdout=subprocess.DEVNULL)
observed=json.loads((H/'results/sampler_loading_validation.json').read_text())
if not observed['complete'] or not all(x['valid_for_diagnosis'] for x in observed['cases']):
    record('stopped_loading_diagnostic_gate_failed');raise SystemExit(1)
record('running_three_dummy_controls',loading_comparison=observed['comparison'])
p=subprocess.run([sys.executable,str(H/'run_spectre.py'),'--run-id',protocol['run'],'--cases',*cases,
    '--mode','ax','--threads','1','--preset-override','all','--timeout','5400'])
if p.returncode==0:
    subprocess.run([sys.executable,str(H/'analyze_sampler_dummy.py')],check=True,stdout=subprocess.DEVNULL)
record('completed_requires_review' if p.returncode==0 else 'stopped_simulation_failure')
