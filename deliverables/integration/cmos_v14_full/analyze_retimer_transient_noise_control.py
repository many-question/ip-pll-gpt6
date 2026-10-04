"""Cross-check native RT4 edge jitter against independently converged PNoise."""
from pathlib import Path
import hashlib, json, re
import numpy as np
from noise_utils import cross, parse, header
from analyze_vco_bias_band import integral

H = Path(__file__).resolve().parent
ROOT = H.parents[3]
R = ROOT/'research/runs/spectre_cmos_v14_full'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def physical(text):
    # Analysis and observation changes cannot alter DUT/source statements.
    return '\n'.join(s for s in text.splitlines() if s and not s.startswith(
        ('pss ', 'pn ', 'edge ', 'tran ', 'save ', 'saveOptions ', 'simulatorOptions '))).strip()


def edge_band_power(residual, fs, lower, upper):
    """One-sided edge-index power, including the single real Nyquist bin."""
    n = len(residual); assert n%2==0 and 0<lower<upper<=fs/2
    f = np.fft.rfftfreq(n, 1/fs); df = fs/n
    select = (f>=lower) & (f<=upper); assert np.any(select)
    indices = np.flatnonzero(select)
    transform = np.fft.rfft(residual)
    power = abs(transform)**2/n**2
    power[1:-1] *= 2
    filtered = np.fft.irfft(np.where(select, transform, 0), n=n)
    return dict(variance=float(np.sum(power[select])), filtered=filtered, df=df,
                lower=f[indices[0]]-df/2, upper=min(fs/2, f[indices[-1]]+df/2))


def main():
    pp = H/'results/retimer_transient_noise_protocol.json'
    p = json.loads(pp.read_text())
    proof = H/'results'/p['source_validation']; assert sha(proof)==p['source_validation_sha256']
    src = ROOT/p['source_result']; assert sha(src)==p['source_sha256']
    reference = (src.parent/'inputs'/(src.parent.name+'.scs')).read_text()
    noise = src.parent/(src.parent.name+'.raw')/'pnMedge.0.sample.pnoise'
    assert sha(noise)==p['source_noise_sha256']
    pn = parse(noise); frequency = pn['freq']; timing_psd = pn['out']**2/header(noise, 'slew rate event_1')**2
    rows, edge_sets = [], {}
    for c in p['cases']:
        j = R/c['run']/c['case']; rp = j/'result.json'
        row = dict(run=c['run'], completed=False); rows.append(row)
        if not rp.exists():
            continue
        r = json.loads(rp.read_text())
        if not r.get('local_outputs_sha256'):
            continue
        assert r['ok'] and r['remote_inputs_match'] and 'spectre completes with 0 errors' in (j/'spectre.out').read_text()
        assert all(sha(j/'inputs'/k)==v for k, v in r['inputs_sha256'].items())
        assert {k:v for k,v in r['inputs_sha256'].items() if k!=c['case']+'.scs'}==p['dependencies_sha256']
        body = (j/'inputs'/(c['case']+'.scs')).read_text(); assert physical(body)==physical(reference)
        expected_options = next(s for s in reference.splitlines() if s.startswith('simulatorOptions ')).replace(
            'reltol=1e-5 vabstol=1e-7 iabstol=1e-13', 'reltol=1e-6 vabstol=1e-9 iabstol=1e-15')
        assert next(s for s in body.splitlines() if s.startswith('simulatorOptions '))==expected_options
        assert r['transient_noise_overrides']=={k:c[k] for k in ('noisefmax', 'noisefmin', 'noiseseed')}
        assert r['numerical_overrides']['maxstep']==c['maxstep']
        native = r['native_state']; assert native['remote_hash_match'] and native['source_snapshot']==p['seed_run']
        assert sha(ROOT/native['local'])==native['sha256']
        cache = j/'waveforms.npz'; assert sha(cache)==r['local_outputs_sha256'][cache.name]
        with np.load(cache) as z:
            t, y = z['time'], z['out']
        assert abs(t[0]-p['seed_time_s'])<1e-12 and t[-1]>=2.3e-6-1e-15
        e = cross(t, y, p['edge_threshold_v'])
        assert len(e)>p['edge_count'] and np.all(np.diff(e)>.8/p['output_hz']) and np.all(np.diff(e)<1.2/p['output_hz'])
        edge_sets[c['run']] = e
        row.update(completed=True, source_result=rp.relative_to(ROOT).as_posix(), source_sha256=sha(rp),
                   raw_cache_sha256=sha(cache), source_bandwidth_hz=c['noisefmax'], maxstep=c['maxstep'],
                   seed=c['noiseseed'], native_sha256=native['sha256'])
    complete = all(c['completed'] for c in rows)
    out = dict(scope=__doc__, protocol_sha256=sha(pp), condition=p['condition'], cases=rows, complete=complete,
               passed=False, full_pll_acceptance=False, main_dut_modified=False, limitations=p['limitations'])
    base_name = 'rttrannoiseoff025'
    if base_name in edge_sets:
        base = edge_sets[base_name]; base = base[base>=p['measurement_start_s']][:p['edge_count']]
        n = len(base); assert n==p['edge_count']
        fs = p['output_hz']; grid = edge_band_power(np.zeros(n), fs, *p['comparison_band_hz'])
        df, actual_lo, actual_hi = grid['df'], grid['lower'], grid['upper']
        expected = integral(frequency, timing_psd, actual_lo, actual_hi)
        out.update(fft_bin_hz=df, effective_comparison_band_hz=[actual_lo, actual_hi],
                   pnoise_expected_rms_fs=float(np.sqrt(expected)*1e15), measurement_edges=n)
        for row in rows:
            if not row['completed']:
                continue
            e = edge_sets[row['run']]; start = int(np.argmin(abs(e-base[0])))
            e = e[start:start+n]; assert len(e)==n and max(abs(e-base))<.25/fs
            residual = e-base; residual -= np.mean(residual)
            measured = edge_band_power(residual, fs, *p['comparison_band_hz'])
            variance, filtered = measured['variance'], measured['filtered']
            assert abs(np.mean(filtered**2)-variance) < max(1e-40, variance*1e-10)
            block_power = np.mean(filtered.reshape(16, n//16)**2, axis=1)
            se = float(np.std(block_power, ddof=1)/4)
            own = e-e[0]-np.arange(n)/fs; own -= np.mean(own)
            row.update(paired_edges=n, residual_mean_removed=True, band_variance_s2=variance,
                band_rms_fs=float(np.sqrt(variance)*1e15), block_variance_standard_error_s2=se,
                rms_relative_to_pnoise=float(np.sqrt(variance/expected)-1),
                noiseless_schedule_rms_fs=float(np.std(own)*1e15) if row['source_bandwidth_hz']==0 else None)
        if complete:
            assert len({r['native_sha256'] for r in rows})==1
            byrun = {r['run']:r for r in rows}
            rms = lambda name:byrun['rttrannoise'+name]['band_rms_fs']
            changes = dict(bandwidth_160g_vs_80g=rms('160g05')/rms('80g05')-1,
                step_025_vs_05_at_160g=rms('160g025')/rms('160g05')-1,
                seed29_vs_11=rms('160g025s29')/rms('160g025')-1)
            checks = dict(noiseless_schedule=all(r['noiseless_schedule_rms_fs']<p['gate']['noiseless_edge_rms_fs'] for r in rows[:2]),
                deterministic_step_floor=rms('off05')<p['gate']['noiseless_step_difference_rms_fs'],
                finer_seed11=abs(byrun['rttrannoise160g025']['rms_relative_to_pnoise'])<p['gate']['noise_rms_relative_pnoise_error'],
                finer_seed29=abs(byrun['rttrannoise160g025s29']['rms_relative_to_pnoise'])<p['gate']['noise_rms_relative_pnoise_error'],
                bandwidth=abs(changes['bandwidth_160g_vs_80g'])<p['gate']['refined_rms_relative_change'],
                step=abs(changes['step_025_vs_05_at_160g'])<p['gate']['refined_rms_relative_change'])
            out.update(comparisons=changes, checks=checks, passed=all(checks.values()))
    (H/'results/retimer_transient_noise_validation.json').write_text(json.dumps(out, indent=2)+'\n')
    print(json.dumps(out, indent=2))


if __name__ == '__main__':
    main()
