"""Review one completed range48 capture; no simulation launch or noise claim.

Usage: python review_rt4_range48_capture.py CASE OUTPUT_JSON
OUTPUT_JSON must not already exist. The 2 ns strobed RF/output voltages are
not used to count GHz edges; the internal per-reference observers are used.
"""
import datetime
import json
import sys
from pathlib import Path

import numpy as np

from analyze_rt4_fast_range import H, R, ROOT, analyze, sha


def review(case_name):
    protocol_path = H / 'results/rt4_range48_repair_protocol.json'
    protocol = json.loads(protocol_path.read_text())
    case = next(c for c in protocol['cases'] if c['case'] == case_name)
    assert case['kind'] == 'capture'
    result = analyze(case, protocol)
    assert result['state'] == 'completed'
    wave = R / case['run'] / case_name / 'waveforms.npz'
    with np.load(wave) as z:
        d = {k: z[k] for k in z.files if k != 'units'}
    t = d['time']
    assert len(t) == 32001 and abs(t[0]) < 1e-15
    assert np.all(np.diff(t) > 0)
    assert all(np.all(np.isfinite(v)) for v in d.values())
    change = np.r_[False, (np.diff(d['obsphase']) != 0)
                   | (np.diff(d['obscycles']) != 0)
                   | (np.diff(d['obsdivcycles']) != 0)]
    transitions = {}
    for name in ['qualified', 'frequency_good', 'XP.XC.acquired', 'range_error']:
        high = d[name] > .6
        indices = np.flatnonzero(np.diff(high.astype(int)) != 0) + 1
        transitions[name] = [{'time_s': float(t[i]), 'high': bool(high[i])}
                             for i in indices]
    qlow = np.flatnonzero(d['qualified'] <= .6)
    last_low = int(qlow[-1]) if len(qlow) else -1
    qstart = float(t[last_low + 1]) if last_low + 1 < len(t) else None
    windows = {}
    starts = {'last_1us': float(t[-1] - 1e-6),
              'last_4us': float(t[-1] - 4e-6)}
    if qstart is not None:
        starts['continuous_qualified_interval'] = qstart
    for label, start in starts.items():
        mask = t >= start
        f = d['obsdivcycles'][mask & change] * 24
        assert len(f) > 10
        target = case['target_out_mhz']
        windows[label] = {
            'start_s': start, 'end_s': float(t[-1]),
            'observer_samples': len(f),
            'output_mhz_min_mean_max': [float(np.min(f)), float(np.mean(f)), float(np.max(f))],
            'max_absolute_frequency_error_ppm': float(np.max(np.abs(f / target - 1)) * 1e6),
            'mean_frequency_error_ppm': float((np.mean(f) / target - 1) * 1e6),
            'qualified_fraction': float(np.mean(d['qualified'][mask] > .6)),
            'frequency_good_fraction': float(np.mean(d['frequency_good'][mask] > .6)),
            'range_error_max_v': float(np.max(d['range_error'][mask])),
            'control_v_min_max': [float(np.min(d['XP.ctrl'][mask])), float(np.max(d['XP.ctrl'][mask]))],
        }
    return {
        'time': datetime.datetime.now().astimezone().isoformat(),
        'protocol': protocol_path.relative_to(ROOT).as_posix(),
        'protocol_sha256': sha(protocol_path),
        'candidate_sha256': protocol['candidate_sha256'],
        'waveforms_path': wave.relative_to(ROOT).as_posix(),
        'waveforms_sha256': sha(wave),
        'analysis_script_sha256': sha(Path(__file__).resolve()),
        'result': result, 'finite_physical_waveforms': True,
        'points': len(t), 'transitions': transitions,
        'continuous_qualified_start_s': qstart, 'windows': windows,
        'boundary': 'One TT AX functional capture. Frequency observations are not jitter. No full-band noise, PVT, all-code overlap, other-frequency pass or candidate adoption inferred.',
    }


if __name__ == '__main__':
    output = Path(sys.argv[2])
    assert not output.exists(), 'Existing evidence must not be overwritten'
    data = review(sys.argv[1])
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'case': sys.argv[1], 'passed': data['result']['fast_functional_screen_passed'],
                      'windows': data['windows']}, ensure_ascii=False))
