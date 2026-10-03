"""Finite fresh-PSS controls for the MOS noise discrepancy after readpss.

Wait for the existing five isolated cases to release their single thread, then
run all noise and FF-only noise from a fresh PSS. Change only frequency grid and
the explicit global noise switch. Keep writepss/finite-difference behavior.
"""
from pathlib import Path
import datetime, hashlib, json, re, subprocess, sys, time

H = Path(__file__).resolve().parent
ROOT = H.parents[3]
R = ROOT / 'research/runs/spectre_cmos_v14_full'
J = R / 'chainrtscale01/chain_rtscale2_tt'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
rec = json.loads((J / 'result.json').read_text())
assert rec['ok'] and rec['remote_inputs_match']
available = {p.name: p for p in (H.parents[1] / 'blocks').glob('*/*')
             if p.suffix in ('.scs', '.va')}
for name, digest in rec['inputs_sha256'].items():
    if name != J.name + '.scs':
        assert name in available and sha(available[name]) == digest, name
base = (J / 'inputs' / (J.name + '.scs')).read_text()
base = re.sub(r'writefinal="[^"]+"', 'writefinal="__FINAL_STATE__"', base)
base = re.sub(r'writepss="[^"]+"', 'writepss="__PERIODIC_STATE__"', base)
assert 'readpss=' not in base and 'writepss=' in base
base = base.replace('start=10k stop=492M dec=20', 'values=[1M 10M 100M]')
cases = ['chain_rt2_fresh_control_tt', 'chain_rt2_fresh_ff_tt']
for case in cases:
    s = base
    if case.endswith('_ff_tt'):
        s = re.sub(r'^(simulatorOptions options .*)$',
                   lambda m: m[0] + ' noiseon_inst=[XR.XFF] noiseon_type=all',
                   s, flags=re.M)
    p = H / 'tb' / (case + '.scs')
    assert not p.exists(), p
    p.write_text(s)
journal = ROOT / 'research/rt2_fresh_pipeline.json'
def record(state, **kwargs):
    journal.write_text(json.dumps(dict(updated=datetime.datetime.now().astimezone().isoformat(),
        state=state, run='rtfresh01', cases=cases, threads=1,
        full_pll_acceptance=False, **kwargs), indent=2) + '\n')
record('waiting_for_existing_gates_to_release_thread')
deadline = time.monotonic() + 1800
while True:
    gate = json.loads((H / 'results/rt_noise_gate2_validation.json').read_text())
    if gate['completed']:
        break
    if time.monotonic() > deadline:
        record('stopped_gate_completion_timeout')
        raise SystemExit('No fresh controls launched: existing gates not complete')
    time.sleep(20)
record('fresh_controls_running')
p = subprocess.run([sys.executable, str(H / 'run_spectre.py'), '--run-id', 'rtfresh01',
    '--cases', *cases, '--mode', 'ax', '--threads', '1', '--preset-override', 'all',
    '--timeout', '3600'])
record('simulations_finished' if p.returncode == 0 else 'stopped_simulation_failure',
       returncode=p.returncode)
raise SystemExit(p.returncode)
