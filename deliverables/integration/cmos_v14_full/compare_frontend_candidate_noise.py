"""Compare measured current noise using each physical candidate's measured PAC gain."""
from pathlib import Path
import argparse, hashlib, json
import numpy as np

H = Path(__file__).resolve().parent
ROOT = H.parents[3]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def load_pair(noise_name, pac_name):
    npth, apth = H/'results'/noise_name, H/'results'/pac_name
    n, a = json.loads(npth.read_text()), json.loads(apth.read_text())
    assert n['noise_valid'] and a['transfer_valid']
    assert n['balanced_center_verified'] and a['balanced_center_verified']
    assert n['condition'] == a['condition'] and n['periodic']['phase_deg'] == a['periodic']['phase_deg']
    assert n['kphi_magnitude_a_per_rf_rad'] == abs(a['signed_static_gain_a_per_rf_rad'])
    for v in [n, a]:
        assert sha(ROOT/v['periodic']['source_result']) == v['periodic']['source_sha256']
    return n, a, dict(noise=npth.name, noise_sha256=sha(npth), pac=apth.name, pac_sha256=sha(apth))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--round', type=int, choices=[1, 2, 3], required=True)
    choice = ap.add_mutually_exclusive_group(required=True)
    choice.add_argument('--reference-candidate', action='store_true')
    choice.add_argument('--cp-variant', choices=['fasttail', 'mid70'])
    args = ap.parse_args()
    label = 'reference_frontend' if args.reference_candidate else 'cp_' + args.cp_variant
    candidate_names = [f'{label}_noise_r{args.round}_all_validation.json',
                       f'{label}_phase_transfer_r{args.round}_validation.json']
    assert all((H/'results'/s).exists() for s in candidate_names), 'Candidate noise/PAC results pending.'
    b, bp, bs = load_pair('frontend_noise_r2_all_validation.json', 'frontend_phase_transfer_validation.json')
    c, cp, cs = load_pair(*candidate_names)
    assert b['offsets_hz'] == c['offsets_hz']
    rows = []
    frf = 3.936e9
    for i, f in enumerate(b['offsets_hz']):
        values = []
        for noise, pac in [(b, bp), (c, cp)]:
            indexes = [k for k, hz in enumerate(pac['offsets_hz']) if abs(hz/f-1) < 1e-12]
            assert len(indexes) == 1
            gain = pac['magnitude_a_per_rad'][indexes[0]]
            psd = noise['current_psd_a2_per_hz'][i] / gain**2
            groups = {k: v[i]/gain**2 for k, v in noise['group_psd_a2_per_hz'].items()}
            assert abs(sum(groups.values())/psd-1) < 1e-7
            values.append(dict(gain_a_per_rf_rad=gain, current_psd_a2_per_hz=noise['current_psd_a2_per_hz'][i],
                               input_equivalent_phase_psd_rad2_per_hz=psd,
                               input_equivalent_timing_asd_fs_per_sqrt_hz=float(np.sqrt(psd)/(2*np.pi*frf)*1e15),
                               input_equivalent_group_phase_psd_rad2_per_hz=groups))
        old, new = values
        ratio = new['input_equivalent_phase_psd_rad2_per_hz']/old['input_equivalent_phase_psd_rad2_per_hz']
        rows.append(dict(offset_hz=f, baseline=old, candidate=new,
                         equivalent_noise_psd_change_db=float(10*np.log10(ratio)),
                         equivalent_noise_asd_relative_change=float(np.sqrt(ratio)-1),
                         current_noise_psd_change_db=float(10*np.log10(new['current_psd_a2_per_hz']/old['current_psd_a2_per_hz'])),
                         group_equivalent_psd_change_db={g: float(10*np.log10(v/old['input_equivalent_group_phase_psd_rad2_per_hz'][g]))
                            if v > 0 and old['input_equivalent_group_phase_psd_rad2_per_hz'][g] > 0 else None
                            for g, v in new['input_equivalent_group_phase_psd_rad2_per_hz'].items()}))
    out = dict(scope=__doc__, baseline_sources=bs, candidate_sources=cs, baseline_condition=b['condition'],
               candidate_condition=c['condition'], rf_hz=frf, points=rows, main_dut_modified=False,
               full_pll_acceptance=False, integrated_jitter_fs=None,
               limitations=['Each frequency uses its own measured PAC response with no interpolation.',
                   'Ideal RF replay and control clamp exclude noisy LC, loop filtering and full PLL dynamics.',
                   'Three noise frequencies are diagnostic points; no RMS integration or band-wide gain claim.',
                   'Per-group independent noise-on, numerical convergence and PVT require separate evidence.'])
    dst = H/'results'/f'{label}_noise_r{args.round}_comparison.json'
    assert not dst.exists(), 'Preserve the previously frozen comparison.'
    dst.write_text(json.dumps(out, indent=2)+'\n')
    print(json.dumps(rows, indent=2))


if __name__ == '__main__':
    main()
