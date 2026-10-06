"""Compare original V14 noiseless trajectories at 0.5 ps and 0.25 ps.

Edge differences are deterministic numerical sensitivity, never random jitter.
No fit, trend subtraction, or spur notch is applied to the edge differences.
"""
from pathlib import Path
import datetime, hashlib, json
import numpy as np
from noise_utils import cross

H = Path(__file__).resolve().parent
ROOT = H.parents[3]


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1048576), b''):
            h.update(b)
    return h.hexdigest()


def trajectory(protocol):
    c = protocol['cases'][0]
    d = ROOT/'research/runs/spectre_cmos_v14_full'/c['run']/c['case']
    rp = d/'result.json'; r = json.loads(rp.read_text())
    assert r['ok'] and r['remote_inputs_match'] and r['state_file']['collected']
    cache = d/'waveforms.npz'
    assert sha(cache) == r['local_outputs_sha256'][cache.name]
    with np.load(cache) as z:
        t = z['time']; dense = t >= 1e-6
        rf = cross(t[dense], (z['XP.vp']-z['XP.vn'])[dense], 0)
        out = cross(t[dense], z['out'][dense], .6)
        refs = cross(t[dense], z['XP.refb'][dense], .6)
        refs = refs[(refs > max(rf[0],out[0])) & (refs < min(rf[-1],out[-1]))]
        cyc = np.interp(refs, rf, np.arange(len(rf)))
        phase = np.unwrap(2*np.pi*(cyc-np.floor(cyc)))
        controls = {k: np.interp(refs,t,z[k]) for k in ['XP.ctrl','XP.vc1']}
    edges = out[out >= protocol['measurement_start_s']][:protocol['edge_count']]
    assert len(edges) == protocol['edge_count']
    assert np.max(abs(np.diff(edges)*protocol['output_hz']-1)) < .2
    return dict(source_result=rp.relative_to(ROOT).as_posix(), source_result_sha256=sha(rp),
                cache_sha256=sha(cache), refs=refs, phase=phase, controls=controls, edges=edges)


def main():
    files = [H/'results/full_pll_main_settled_ssd_cwd_pair_protocol.json',
             H/'results/full_pll_main_quarter_pair_protocol.json']
    p = [json.loads(x.read_text()) for x in files]
    assert p[1]['parent_protocol_sha256'] == sha(files[0])
    for k in ['text_state_sha256','physical_dependency_hashes','ref_hz','output_hz',
              'measurement_start_s','edge_count','reltol','vabstol','iabstol','stop_s']:
        assert p[0][k] == p[1][k], k
    tb = [(H/'tb'/(q['cases'][0]['case']+'.scs')) for q in p]
    assert all(sha(f) == q['cases'][0]['tb_sha256'] for f,q in zip(tb,p))
    assert tb[0].read_text().replace('maxstep=.5p ','maxstep=.25p ') == tb[1].read_text()
    auditfile = H/'results/full_pll_main_quarter_recovery_audit.json'
    a = json.loads(auditfile.read_text()); assert a['recovery_audit_passed']
    data = [trajectory(q) for q in p]
    difference = data[1]['edges']-data[0]['edges']
    assert np.max(abs(difference))*p[0]['output_hz'] < .25
    residual = difference-difference.mean()
    n = len(residual); f = np.fft.fftfreq(n,d=1/p[0]['output_hz'])
    power = abs(np.fft.fft(residual)/n)**2
    band = (abs(f)>=p[0]['band_hz'][0]) & (abs(f)<=p[0]['band_hz'][1])
    parseval = abs(power.sum()/np.mean(residual**2)-1)
    assert parseval < 1e-12
    diagnostics = dict(edge_count=n, edge_threshold_v=.6,
        difference_order='0.25 ps minus 0.5 ps, matched rising-edge ordinal',
        mean_edge_difference_ps=float(difference.mean()*1e12),
        peak_to_peak_difference_ps=float(np.ptp(difference)*1e12),
        maximum_absolute_difference_ps=float(np.max(abs(difference))*1e12),
        mean_removed_difference_rms_fs=float(np.std(difference)*1e15),
        fft_bin_width_hz=p[0]['output_hz']/n,
        selected_bin_centers_hz=[float(abs(f[band]).min()),float(abs(f[band]).max())],
        effective_bin_coverage_hz=[float(abs(f[band]).min()-p[0]['output_hz']/n/2),p[0]['output_hz']/2],
        band_limited_deterministic_difference_rms_fs=float(np.sqrt(power[band].sum())*1e15),
        parseval_relative_error=float(parseval),random_jitter=False)
    baseline_v = json.loads((H/'results/full_pll_main_settled_ssd_cwd_pair_validation.json').read_text())
    evidence = dict(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),
        condition=p[1]['condition'],protocol_sha256=[sha(x) for x in files],
        same_dut_state_reference_and_tolerances=True,source_tb_diff_only_maxstep=True,
        baseline=dict(**{k:v for k,v in data[0].items() if k.startswith('source_') or k=='cache_sha256'},
                      stationarity=baseline_v['cases'][0]['stationarity']),
        refined=dict(**{k:v for k,v in data[1].items() if k.startswith('source_') or k=='cache_sha256'},
                     stationarity=a['quiet_validation']['stationarity']),
        recovery_audit_sha256=sha(auditfile),deterministic_edge_sensitivity=diagnostics,
        numerical_convergence_established=False,full_pll_acceptance=False,
        integrated_10khz_jitter_fs=None,
        limitations=['Both quiet records pass their complete last 1 us stationarity gates; this does not establish numerical convergence.',
          'The 0.25 ps log contains internal trapezoidal ringing; integration-method and tolerance checks remain open.',
          'Quiet-quiet differences include deterministic settling and numerical changes. They are not noise-on/quiet differences or a measured noise floor.',
          'Effective band denotes selected-bin edges, consistent with the existing protocol; the first selected bin center is 5.765625 MHz, not a directly resolved 5 MHz sample.',
          'The 0.25 ps noise run must be paired with its own quiet record. Same seed does not ensure the same adaptive stochastic realization.',
          'No full-band jitter, independent-seed, noise-bandwidth, PVT or duration acceptance follows from this comparison.'])
    (H/'results/full_pll_main_quiet_timestep_comparison.json').write_text(json.dumps(evidence,indent=2)+'\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(3,1,figsize=(8.5,8))
    for d,label in zip(data,['0.5 ps','0.25 ps']):
        axes[0].plot(d['refs']*1e6,d['phase']-d['phase'][0],'.-',label=label)
        axes[1].plot(d['refs']*1e6,d['controls']['XP.ctrl']*1e3,'.-',label=label)
    axes[0].set_ylabel('RF phase change (rad)');axes[0].legend()
    axes[1].set_ylabel('Control voltage (mV)');axes[1].set_xlabel('Continuation time (us)')
    for ax in axes[:2]: ax.axvspan(1.2,2.2,color='grey',alpha=.1)
    axes[2].plot((data[0]['edges']-data[0]['edges'][0])*1e6,residual*1e12,lw=.8)
    axes[2].set_ylabel('Quiet edge difference (ps)');axes[2].set_xlabel('Time since first measured edge (us)')
    axes[2].set_title('0.25 ps minus 0.5 ps; mean removed only; deterministic sensitivity',fontsize=10)
    for ax in axes:ax.grid(alpha=.3)
    fig.suptitle('Original V14 full PLL, TT 27 C: timestep comparison\nSame devices, initial state and tolerances; no random-noise result')
    fig.tight_layout();fig.savefig(H/'results/figures/main_quiet_timestep_comparison.png',dpi=150);plt.close(fig)
    print(json.dumps(diagnostics,indent=2))


if __name__ == '__main__':main()
