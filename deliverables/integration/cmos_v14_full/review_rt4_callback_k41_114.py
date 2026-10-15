"""Review two same-code K41 VCO tuning points with stable independent terminal proofs."""
from pathlib import Path
import datetime
import json
import sys
import numpy as np
from review_pdk_callback110 import ROOT, H, sha, clock, stats


def main():
    ap, bp, out = map(Path, sys.argv[1:])
    assert not out.exists()
    aa = [json.loads(p.read_text()) for p in (ap, bp)]
    gap = (datetime.datetime.fromisoformat(aa[1]['time']) -
           datetime.datetime.fromisoformat(aa[0]['time'])).total_seconds()
    assert gap >= 60
    pp = H / 'results/rt4_callback_k41_114_protocol.json'
    protocol = json.loads(pp.read_text())
    c = protocol['cases'][0]
    work = ROOT / 'research/runs/spectre_cmos_v14_full' / c['run'] / c['case']
    r = json.loads((work / 'result.json').read_text())
    assert r['ok'] and not r['errors'] and r['remote_inputs_match']
    raw = work / (c['case'] + '.raw/tran.tran.tran')
    for a in aa:
        assert a['transport_identity'] == dict(hostname='thu-xia', user='jielu', uid=528)
        j = next(x for x in a['jobs'] if x['case'] == c['case'])
        assert not j['alive'] and j['exit_marker'] == '0' and j['raw_end']
        assert j['remote_inputs_match'] and j['inputs'] == r['inputs_sha256']
        assert j['final_state_sha256'] == sha(work / 'final.ic')
        assert j['completed_output_hashes'][c['case'] + '.raw/tran.tran.tran'] == sha(raw)
        assert j['completed_output_hashes']['spectre.out'] == sha(work / 'spectre.out')
        assert j['effective']['method'] == 'traponly' and j['effective']['maxstep'] == 8e-12
        assert j['effective']['reltol'] == .001
    assert 'spectre completes with 0 errors' in (work / 'spectre.out').read_text()
    with raw.open('rb') as f:
        f.seek(-128, 2)
        assert f.read().rstrip().endswith(b'END')
    with np.load(work / 'waveforms.npz') as z:
        d = {k: z[k] for k in z.files if k != 'units'}
    t = d['time']
    assert len(t) == c['expected_points'] and abs(t[0]) < 1e-18
    assert abs(t[-1] - c['stop_s']) < 1e-16 and np.all(np.diff(t) > 0)
    assert all(len(v) == len(t) and np.isfinite(v).all() for v in d.values())
    rows = []
    for s in protocol['segments']:
        lo, hi = s['window_s']
        rf = clock(t, d['vp'] - d['vn'], lo, hi, 0.)
        output = clock(t, d['out'], lo, hi)
        subwindows = [clock(t, d['vp'] - d['vn'], lo + i * 100e-9, lo + (i+1) * 100e-9, 0.)['frequency_Hz'] for i in range(3)]
        mask = (t >= lo) & (t <= hi)
        assert np.allclose(d['ctrl'][mask], s['control_V'], atol=1e-6)
        for bit in range(8):
            assert np.allclose(d['b'+str(bit)][mask], 1.2 if (s['coarse'] >> bit) & 1 else 0, atol=1e-6)
        rows.append(dict(**s, rf=rf, output=output, rf_100ns_means_Hz=subwindows,
                         divide4_observed=abs(rf['frequency_Hz'] / output['frequency_Hz'] - 4) < .004,
                         ctrl=stats(t, d['ctrl'], lo, hi),
                         signed_target_error_MHz=rf['frequency_Hz']/1e6-s['target_MHz'],
                         nfilt=stats(t, d['XV.XL.nfilt'], lo, hi),
                         nfilt_linear_drift_V_per_us=float(np.polyfit((t[mask] - lo)*1e6, d['XV.XL.nfilt'][mask], 1)[0]),
                         rf_first_to_last_100ns_drift_MHz=(subwindows[-1] - subwindows[0]) / 1e6))
    low_max = max(rows[0]['rf_100ns_means_Hz']) / 1e6
    high_min = min(rows[1]['rf_100ns_means_Hz']) / 1e6
    data = dict(time=datetime.datetime.now().astimezone().isoformat(),
                protocol_sha256=sha(pp), script_sha256=sha(Path(__file__).resolve()),
                terminal=dict(exit_code=0, errors=0, stable_interval_s=gap, psf_end=True,
                              raw_sha256=sha(raw), final_ic_sha256=sha(work / 'final.ic'),
                              log_sha256=sha(work / 'spectre.out'), inputs_sha256=r['inputs_sha256']),
                audits=[dict(path=p.as_posix(), sha256=sha(p)) for p in (ap, bp)],
                points=len(t), finite_physical_waveforms=True, units_metadata_excluded=True,
                waveforms_sha256=sha(work / 'waveforms.npz'), segments=rows,
                worst_100ns_window_endpoint_MHz=dict(low_max=low_max, high_min=high_min),
                conditional_k41_bracketed=low_max <= 3936 and high_min >= 3936,
                boundary=protocol['evidence_boundary'])
    out.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(points=len(t), stable_interval_s=gap,
                         conditional_k41_bracketed=data['conditional_k41_bracketed'],
                         worst_100ns_window_endpoint_MHz=data['worst_100ns_window_endpoint_MHz'],
                         segments=[{k: x[k] for k in ['coarse', 'control_V', 'rf_100ns_means_Hz', 'nfilt', 'nfilt_linear_drift_V_per_us', 'divide4_observed']} for x in rows]), indent=2))


if __name__ == '__main__':
    main()
