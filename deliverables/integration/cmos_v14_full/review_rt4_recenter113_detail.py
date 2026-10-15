"""Independent terminal and state review; never launches a simulation.

Usage: python review_rt4_recenter113_detail.py AUDIT_A AUDIT_B NEW_OUTPUT
"""
from pathlib import Path
import datetime
import json
import sys
import numpy as np
from analyze_rt4_fast_range import H, ROOT, sha


def main():
    a_path, b_path, out = map(Path, sys.argv[1:])
    assert not out.exists()
    audits = [json.loads(p.read_text()) for p in (a_path, b_path)]
    gap = (datetime.datetime.fromisoformat(audits[1]['time']) -
           datetime.datetime.fromisoformat(audits[0]['time'])).total_seconds()
    assert gap >= 60
    prior = H / 'results/rt4_recenter109_review113.json'
    r = json.loads(prior.read_text())['result']
    assert r['state'] == 'completed'
    work = ROOT / Path(r['source_result']).parent
    result = json.loads((work / 'result.json').read_text())
    assert result['ok'] and not result['errors'] and result['metadata']['returncode'] == 0
    log = (work / 'spectre.out').read_text()
    assert 'spectre completes with 0 errors' in log
    for a in audits:
        assert a['transport_identity'] == dict(hostname='thu-xia', user='jielu', uid=528)
        j = a['jobs'][0]
        assert j['case'] == r['case'] and not j['alive']
        assert j['exit_marker'] == '0' and j['raw_end'] and j['remote_inputs_match']
        assert j['final_state_sha256'] == sha(work / 'final.ic')
        for n, v in j['completed_output_hashes'].items():
            assert sha(work / n) == v
    a, b = [v['jobs'][0] for v in audits]
    assert a['completed_output_hashes'] == b['completed_output_hashes']
    assert a['inputs'] == b['inputs'] == result['inputs_sha256']
    assert a['final_state_sha256'] == b['final_state_sha256']
    with np.load(work / 'waveforms.npz') as z:
        d = {k: z[k] for k in z.files if k != 'units'}
    t = d['time']
    assert len(t) == 60001 and abs(t[0]) < 1e-18 and abs(t[-1] - 120e-6) < 1e-16
    assert np.all(np.diff(t) > 0)
    assert all(len(v) == len(t) and np.isfinite(v).all() for v in d.values())
    bits = lambda prefix, n: sum((d[prefix + str(i)] > .6).astype(int) * (1 << i) for i in range(n))
    state, coarse, dac = bits('XP.XC.state', 3), bits('XP.b', 8), bits('XP.XC.d', 6)
    transitions = {}
    for name in ['qualified', 'frequency_good', 'phase_good', 'amp_good', 'range_error',
                 'XP.en', 'XP.restart', 'XP.XC.acquired']:
        high = d[name] > .6
        ix = np.flatnonzero(high[1:] != high[:-1]) + 1
        transitions[name] = [dict(time_s=float(t[i]), high=bool(high[i])) for i in ix]
    snapshots = r['eval_snapshots']
    # This record has the original endpoint + 8 coarse + 6 fine SAR trials.
    # Check that protocol segmentation is consistent with observed timing.
    assert len(snapshots) >= 17 and snapshots[14]['time_s'] < 53e-6
    checks = snapshots[15:]
    assert 0 < len(checks) <= 8 and checks[0]['dac'] == 32
    assert checks[0]['time_s'] > 59e-6
    target = 5248
    for c in checks:
        c['signed_count_error'] = c['measured_count'] - target
    coarse_changes = [(x, y) for x, y in zip(checks, checks[1:]) if x['coarse'] != y['coarse']]
    assert len(coarse_changes) <= 1
    for x, y in coarse_changes:
        direction = 1 if x['dac'] <= 15 and x['signed_count_error'] > 0 else -1
        assert (direction == 1 or (x['dac'] >= 49 and x['signed_count_error'] < 0))
        assert y['coarse'] == x['coarse'] + direction and y['dac'] == 32
    paired = checks[-2:]
    accepted_pair = (len(paired) == 2 and
                     paired[0]['coarse'] == paired[1]['coarse'] and
                     paired[0]['dac'] == paired[1]['dac'] and
                     all(abs(x['signed_count_error']) <= 1 for x in paired))
    if np.any(state == 4):
        assert accepted_pair
    q = d['qualified'] > .6
    start = int(np.flatnonzero(~q)[-1]) + 1 if (~q).any() else 0
    change = np.r_[False, (np.diff(d['obsphase']) != 0) |
                   (np.diff(d['obscycles']) != 0) | (np.diff(d['obsdivcycles']) != 0)]

    def stats(mask):
        f = d['obsdivcycles'][mask & change] * 24
        assert len(f) > 10
        return dict(start_s=float(t[np.flatnonzero(mask)[0]]), end_s=float(t[np.flatnonzero(mask)[-1]]),
                    observer_samples=len(f), output_min_mean_max_mhz=[float(f.min()), float(f.mean()), float(f.max())],
                    worst_abs_frequency_error_ppm=float(np.max(abs(f / 984 - 1)) * 1e6),
                    qualified_fraction=float(np.mean(q[mask])),
                    frequency_good_fraction=float(np.mean(d['frequency_good'][mask] > .6)),
                    control_v_min_max=[float(d['XP.ctrl'][mask].min()), float(d['XP.ctrl'][mask].max())],
                    range_error_max_v=float(d['range_error'][mask].max()))

    windows = dict(last_1us=stats(t >= 119e-6), pll_enabled=stats(d['XP.en'] > .6))
    if start < len(t):
        windows['continuous_qualified'] = stats(np.arange(len(t)) >= start)
    data = dict(time=datetime.datetime.now().astimezone().isoformat(),
                review_sha256=sha(prior), script_sha256=sha(Path(__file__).resolve()),
                audits=[dict(path=p.as_posix(), sha256=sha(p)) for p in (a_path, b_path)],
                stable_terminal_interval_s=gap, physical_points=len(t), finite_physical_waveforms=True,
                units_metadata_excluded=True, physical_fields=len(d)-1,
                terminal=dict(exit_code=0, errors=0, remote_process_absent=True, raw_end=True,
                              completed_output_hashes=b['completed_output_hashes'], final_ic_sha256=b['final_state_sha256']),
                fresh_checks=checks, fresh_checks_used=len(checks), shared_budget=8,
                coarse_correction_count=len(coarse_changes), accepted_same_code_pair=accepted_pair,
                state_transitions=transitions,
                controller_state_transitions=[dict(time_s=float(t[i]), state=int(state[i])) for i in
                                              np.r_[0, np.flatnonzero(state[1:] != state[:-1]) + 1]],
                handoff_first_s=float(t[np.flatnonzero(state == 4)[0]]) if np.any(state == 4) else None,
                final_coarse=int(coarse[-1]), final_dac=int(dac[-1]), final_state=int(state[-1]),
                range_error_observed=bool(np.any(d['range_error'] > .6)),
                restart_observed=bool(np.any(d['XP.restart'] > .6)),
                continuous_qualified_start_s=float(t[start]) if start < len(t) else None,
                windows=windows, fast_capture_passed=r['fast_functional_screen_passed'],
                interpretation='Original109 passes this sparse TT capture. SAR chose20 before fresh recheck; no new coarse-correction branch was exercised. This does not isolate the cause of the prior SAR/code discrepancy.',
                boundary='Old assumed240nm geometry, independent4.8fF/controller109 only. No callback110, all-frequency, PVT, jitter or adoption inference. Frequency error is not jitter.')
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: data[k] for k in ['stable_terminal_interval_s', 'fresh_checks_used',
          'coarse_correction_count', 'accepted_same_code_pair', 'handoff_first_s',
          'range_error_observed', 'restart_observed', 'continuous_qualified_start_s', 'windows']}, indent=2))


if __name__ == '__main__':
    main()
