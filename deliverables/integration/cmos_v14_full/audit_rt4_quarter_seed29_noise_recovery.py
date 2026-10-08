"""Independently audit the RT4 candidate SSD noise pair; no full-band acceptance."""
from pathlib import Path
import datetime, hashlib, json
import numpy as np
from noise_utils import stream_selected, cross

H = Path(__file__).resolve().parent
ROOT = H.parents[3]
R = ROOT/'research/runs/spectre_cmos_v14_full'


def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1048576), b''):
            h.update(b)
    return h.hexdigest()


def main():
    pp = H/'results/full_pll_rt4_quarter_seed29_pair_protocol.json'
    vp = H/'results/full_pll_rt4_quarter_seed29_pair_validation.json'
    p = json.loads(pp.read_text()); v = json.loads(vp.read_text())
    assert v['complete'] and v['protocol_sha256'] == sha(pp)
    c = p['cases'][1]; d = R/c['run']/c['case']; rp = d/'result.json'
    r = json.loads(rp.read_text())
    assert r['ok'] and r['remote_inputs_match'] and r['state_file']['collected']
    assert v['cases'][1]['source_sha256'] == sha(rp)
    inputs = {k: sha(d/'inputs'/k) for k in r['inputs_sha256']}
    assert inputs == r['inputs_sha256'] == r['remote_inputs_sha256']
    ap = ROOT/'research/rt4_quarter_seed29_noise_remote_audit81.json'
    remote = json.loads(ap.read_text()); outputs = {}
    assert not remote['old_pid_exists'] and remote['exit_code']=='0'
    for k, expected in remote['files'].items():
        local = d/('final.ic' if k == 'final_state.ic' else k)
        outputs[k] = dict(bytes=local.stat().st_size, sha256=sha(local))
        assert all(outputs[k][x] == expected[x] for x in outputs[k])
        assert expected['realpath'].startswith('/server_local_ssd/jielu/IP-PLL-GPT6/')
    print('Input and raw/log/full-state hashes match.', flush=True)
    cache = d/'waveforms.npz'
    assert sha(cache) == r['local_outputs_sha256'][cache.name]
    keys = ['out','XP.vp','XP.vn','XP.refb','qualified','XP.XC.acquired',
            'XP.XC.phase_held','XP.restart','XP.ctrl','XP.vc1']
    a, duplicates = stream_selected(d/(c['case']+'.raw/tran.tran.tran'), p['observations'])
    with np.load(cache) as z:
        assert all(len(z[k]) == len(a['time']) for k in a)
        diffs = {k: float(np.max(abs(values-z[k]))) for k, values in a.items()}
    assert not any(diffs.values()) and not duplicates
    print('Independent raw parser matches cache.', flush=True)
    state = {}
    for line in (d/'final.ic').read_text().splitlines():
        if line.strip() and not line.startswith('#'):
            fields = line.split(); state[fields[0]] = float(fields[1])
    initial = {s.split()[0] for s in (H/'state_inputs'/p['text_state']).read_text().splitlines()
               if s.strip() and not s.startswith('#')}
    assert set(state) == initial and all(np.isfinite(x) for x in state.values())
    final_diff = {k: abs(float(a[k][-1])-state[k]) for k in keys if k in state}
    assert len(state) > 7800 and max(final_diff.values()) < 1e-9
    t = a['time']; sel = t >= p['measurement_start_s']
    ranges = {k: dict(min_v=float(a[k][sel].min()),max_v=float(a[k][sel].max())) for k in keys[4:]}
    quiet_case = p['cases'][0]
    quiet_cache = R/quiet_case['run']/quiet_case['case']/'waveforms.npz'
    with np.load(quiet_cache) as z:
        tq = z['time']; oq = z['out']
    # Independent full complex FFT and explicit positive/negative frequency mask.
    edges = []
    for tt, yy in [(tq,oq),(t,a['out'])]:
        e = cross(tt,yy,.6); e = e[e >= p['measurement_start_s']][:p['edge_count']]
        assert len(e) == p['edge_count']; edges.append(e)
    raw_residual = edges[1]-edges[0]; residual = raw_residual-np.mean(raw_residual)
    n = len(residual); fs = p['output_hz']; f = np.fft.fftfreq(n,1/fs)
    spectrum = np.fft.fft(residual); mask = (abs(f) >= p['band_hz'][0]) & (abs(f) <= p['band_hz'][1])
    variance = float(np.sum(abs(spectrum[mask])**2)/n**2)
    filtered = np.fft.ifft(spectrum*mask).real
    assert np.isclose(np.mean(filtered**2),variance,rtol=1e-12,atol=0)
    rms = float(np.sqrt(variance)*1e15)
    assert np.isclose(rms,v['diagnostic_band_rms_fs'],rtol=1e-12)
    block_rms = (np.sqrt(np.mean(filtered.reshape(16,-1)**2,axis=1))*1e15).tolist()
    qfreq = 1/np.mean(np.diff(edges[0])); nfreq = 1/np.mean(np.diff(edges[1]))
    log = (d/'spectre.out').read_text()
    out = dict(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),
        source_result=rp.relative_to(ROOT).as_posix(),source_result_sha256=sha(rp),
        protocol_sha256=sha(pp),validation_sha256=sha(vp),
        remote_hash_audit=ap.relative_to(ROOT).as_posix(),remote_hash_audit_sha256=sha(ap),
        input_count=len(inputs),all_inputs_match=True,outputs=outputs,remote_local_raw_log_state_match=True,
        cache_sha256=sha(cache),independent_parser_samples=len(t),independent_parser_max_differences=diffs,
        duplicate_records=duplicates,measurement_window_ranges=ranges,
        final_state_entries=len(state),all_source_state_keys_preserved=True,final_state_saved_voltage_differences=final_diff,
        independent_fft_band_rms_fs=rms,fft_parseval_relative_error=float(abs(np.mean(filtered**2)/variance-1)),
        measured_edge_times_s=[[float(e[0]),float(e[-1])] for e in edges],
        quiet_noisy_mean_output_hz=[float(qfreq),float(nfreq)],paired_edge_max_abs_difference_ps=float(max(abs(raw_residual))*1e12),
        mean_removed_residual_rms_fs=float(np.std(residual)*1e15),band_block_rms_fs=block_rms,
        trapezoidal_ringing_reported='Trapezoidal ringing is detected' in log,
        pair_validation=v,recovery_audit_passed=True,full_pll_acceptance=False,integrated_10khz_jitter_fs=None,
        limitations=['Single TT warm continuation, seed 29, ideal external supply/reference.',
            '1024 edges and 5.28515625-492MHz are a high-offset diagnostic only.',
            'Mean removal and matched quiet subtraction only; no trend fit, amplitude scaling or spectral notches.',
            'Quiet subtraction removes repeatable deterministic response but does not establish a complete discrete-spur classification.',
            'Numerical, bandwidth, seed and duration convergence remain open; no 10kHz full-band value is inferred.'])
    (H/'results/full_pll_rt4_quarter_seed29_noise_recovery_audit.json').write_text(json.dumps(out,indent=2)+'\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2,1,figsize=(9,6))
    axes[0].plot((edges[0]-edges[0][0])*1e6,residual*1e12,lw=.8)
    axes[0].set(xlabel='Time from first paired edge (us)',ylabel='Noisy minus quiet (ps)')
    ff = np.fft.rfftfreq(n,1/fs); power = abs(np.fft.rfft(residual))**2/n**2
    power[1:-1] *= 2
    axes[1].semilogx(ff[1:]/1e6,10*np.log10(np.maximum(power[1:]*1e30,1e-30)),lw=.8)
    axes[1].axvline(v['effective_band_hz'][0]/1e6,color='grey',ls='--')
    axes[1].set(xlabel='Offset (MHz)',ylabel='Edge variance per bin (dB fs²)')
    for ax in axes: ax.grid(alpha=.3)
    fig.suptitle(f'RT4 full transistor candidate: 0.25 ps, seed 29, TT 27 C\nHigh-offset diagnostic {rms:.2f} fs; full-band acceptance remains unknown')
    fig.tight_layout(); fig.savefig(H/'results/figures/rt4_quarter_seed29_noise_pair.png',dpi=150);plt.close(fig)
    print(json.dumps(dict(audit_passed=True,samples=len(t),diagnostic_valid=v['high_offset_diagnostic_valid'],rms_fs=rms,ranges=ranges),indent=2))


if __name__ == '__main__': main()
