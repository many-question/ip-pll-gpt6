"""Separate fresh/reused PSS and noise-on contributions at three offsets.

These points diagnose the measurement flow. They are never a jitter integral.
Keep the original failed gate results; this audit adds an independent control.
"""
from pathlib import Path
import hashlib, json
import numpy as np
from noise_utils import parse, header, devices

H = Path(__file__).resolve().parent
ROOT = H.parents[3]
R = ROOT / 'research/runs/spectre_cmos_v14_full'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
freq = np.array([1e6, 1e7, 1e8])
groups = json.loads((H / 'results/rt_noise_gate2_validation.json').read_text())['groups']

def read(run, case):
    j = R / run / case
    if not (j / 'result.json').exists():
        return None
    rec = json.loads((j / 'result.json').read_text())
    if not rec.get('local_outputs_sha256'):
        return None
    assert rec['ok'] and rec['remote_inputs_match']
    assert 'spectre completes with 0 errors' in (j / 'spectre.out').read_text()
    p = j / (case + '.raw') / 'pnMedge.0.sample.pnoise'
    d = parse(p)
    slew = header(p, 'slew rate event_1')
    dev = devices(p, len(d['freq']))
    sv = d['out'] ** 2
    assert max(abs(sum(dev.values()) / sv - 1)) < 1e-7
    # All requested offsets lie on the source logarithmic grid (roundoff only).
    assert all(min(abs(d['freq'] / f - 1)) < 1e-10 for f in freq)
    psd = np.interp(freq, d['freq'], sv / slew ** 2)
    grouped = {group: np.interp(freq, d['freq'],
        sum(v for k, v in dev.items() if any(k.startswith(n + '.') for n in names))
        / slew ** 2).tolist() for group, names in groups.items()}
    return dict(run=run, case=case, source_result=(j / 'result.json').relative_to(ROOT).as_posix(),
        source_sha256=sha(j / 'result.json'), pnoise_sha256=sha(p),
        slew_v_per_s=slew, event_time_s=header(p, 'jittereventtime'),
        timing_psd_s2_per_hz=psd.tolist(), group_timing_psd=grouped,
        physical_inputs={k: v for k, v in rec['inputs_sha256'].items()
                         if k != case + '.scs'}, pss_reused=bool(rec.get('periodic_state')))

base = read('chainrtscale01', 'chain_rtscale2_tt')
reuse = read('rtcontrolreuse01', 'chain_rt2_control_tt')
assert base and reuse and base['physical_inputs'] == reuse['physical_inputs']
fresh = read('rtfresh01', 'chain_rt2_fresh_control_tt')
freshff = read('rtfresh01', 'chain_rt2_fresh_ff_tt')
gate_rows = []
for group in groups:
    row = read('rtgates2_01_' + group, 'chain_rt2_only_' + group + '_tt')
    if row is None:
        continue
    assert row['physical_inputs'] == base['physical_inputs']
    diff = np.array(row['timing_psd_s2_per_hz']) / reuse['group_timing_psd'][group] - 1
    gate_rows.append(dict(group=group, max_relative_difference_to_reused_all=float(max(abs(diff))),
                         passed=bool(max(abs(diff)) < .001), evidence=row))
out = dict(scope=__doc__, offsets_hz=freq.tolist(), fresh_fullband_source=base,
    reused_all_noise=reuse, reused_to_fresh_psd_ratio=(np.array(reuse['timing_psd_s2_per_hz'])
        / base['timing_psd_s2_per_hz']).tolist(), reused_isolated_controls=gate_rows,
    fresh_three_point_control=fresh, fresh_ff_only=freshff,
    observations=['All-noise reuse itself disagrees with the fresh full-band source.',
        'The original RC reuse calibration does not establish MOS reuse validity.',
        'Do not use reused-state MOS noise for performance acceptance until resolved.'],
    fresh_control_passed=None, fresh_ff_gate_passed=None,
    full_band_integral=False, full_pll_acceptance=False)
for key, row, reference in [('fresh_control_passed', fresh, base['timing_psd_s2_per_hz']),
                           ('fresh_ff_gate_passed', freshff, base['group_timing_psd']['ff'])]:
    if row:
        assert row['physical_inputs'] == base['physical_inputs']
        err = float(max(abs(np.array(row['timing_psd_s2_per_hz']) / reference - 1)))
        out[key] = err < .001
        out[key + '_max_relative_error'] = err
(H / 'results/rt_noise_controls.json').write_text(json.dumps(out, indent=2) + '\n')
print(json.dumps({k: v for k, v in out.items() if k in ['reused_to_fresh_psd_ratio',
    'fresh_control_passed', 'fresh_ff_gate_passed', 'fresh_control_passed_max_relative_error',
    'fresh_ff_gate_passed_max_relative_error']}, indent=2))
print('reused gate controls', [(r['group'], r['passed']) for r in gate_rows])
