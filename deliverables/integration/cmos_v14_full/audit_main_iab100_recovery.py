"""Audit the completed original-V14 0.25 ps 100 fA quiet record and settling windows."""
from pathlib import Path
import datetime, hashlib, json
import numpy as np
from noise_utils import stream_selected, cross

H = Path(__file__).resolve().parent
ROOT = H.parents[3]

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1048576), b''):
            h.update(b)
    return h.hexdigest()

def main():
    pp = H/'results/full_pll_main_iab100_pair_protocol.json'
    p = json.loads(pp.read_text()); c = p['cases'][0]
    d = ROOT/'research/runs/spectre_cmos_v14_full'/c['run']/c['case']
    rp = d/'result.json'; r = json.loads(rp.read_text())
    vp = H/'results/full_pll_main_iab100_pair_validation.json'
    v = json.loads(vp.read_text()); q = v['cases'][0]
    assert r['ok'] and r['remote_inputs_match'] and r['state_file']['collected']
    assert q['completed'] and q['source_sha256'] == sha(rp) and v['protocol_sha256'] == sha(pp)
    inputs = {k: sha(d/'inputs'/k) for k in r['inputs_sha256']}
    assert inputs == r['inputs_sha256'] == r['remote_inputs_sha256']
    remote_path = ROOT/'research/main_iab100_remote_audit84.json'
    remote = json.loads(remote_path.read_text())
    outputs = {}
    for k, expected in remote['files'].items():
        local = d/('final.ic' if k == 'final_state.ic' else k)
        outputs[k] = dict(bytes=local.stat().st_size, sha256=sha(local))
        assert outputs[k] == expected
    assert inputs == remote['inputs'] and remote['exit_code'] == '0' and not remote['old_pid_exists']
    cache = d/'waveforms.npz'; assert sha(cache) == r['local_outputs_sha256'][cache.name]
    keys = p['observations']
    a, duplicates = stream_selected(d/(c['case']+'.raw/tran.tran.tran'), keys)
    with np.load(cache) as z:
        assert all(len(z[k]) == len(a['time']) for k in a)
        diffs = {k: float(np.max(abs(values-z[k]))) for k, values in a.items()}
    assert not any(diffs.values()) and not duplicates
    assert all(np.all(np.isfinite(x)) for x in a.values())
    t = a['time']; assert abs(t[-1]-p['stop_s']) < 1e-15
    dense = t >= 1e-6
    rf = cross(t[dense], (a['XP.vp']-a['XP.vn'])[dense], 0)
    out = cross(t[dense], a['out'][dense], .6)
    refs = cross(t[dense], a['XP.refb'][dense], .6)
    refs = refs[(refs > max(rf[0], out[0])) & (refs < min(rf[-1], out[-1]))]
    urf = np.interp(refs, rf, np.arange(len(rf)))
    uout = np.interp(refs, out, np.arange(len(out)))
    phase = np.unwrap(2*np.pi*(urf-np.floor(urf)))
    windows = []
    for lo, hi in [(1.0,1.5),(1.2,2.2),(1.5,2.0),(1.7,2.2)]:
        m = (refs >= lo*1e-6) & (refs <= hi*1e-6)
        tr = refs[m]*1e6
        windows.append(dict(window_us=[lo,hi],reference_samples=len(tr),
            phase_pp_rad=float(np.ptp(phase[m])),phase_drift_rad_per_us=float(np.polyfit(tr,phase[m],1)[0]),
            mean_output_mhz=float(np.mean(np.diff(uout[m]))*24),
            control_slope_mv_per_us=float(np.polyfit(tr,np.interp(refs[m],t,a['XP.ctrl'])*1e3,1)[0]),
            filter_slope_mv_per_us=float(np.polyfit(tr,np.interp(refs[m],t,a['XP.vc1'])*1e3,1)[0])))
    m = t >= p['measurement_start_s']
    ranges = {k: dict(min_v=float(a[k][m].min()),max_v=float(a[k][m].max())) for k in keys[4:]}
    state = {}
    for line in (d/'final.ic').read_text().splitlines():
        if line.strip() and not line.startswith('#'):
            fields = line.split()
            assert len(fields) == 2 or fields[2].startswith('#')
            name, value = fields[:2]; state[name] = float(value)
    initial = {s.split()[0] for s in (H/'state_inputs'/p['text_state']).read_text().splitlines()
               if s.strip() and not s.startswith('#')}
    assert set(state) == initial and all(np.isfinite(x) for x in state.values())
    final_diff = {k: abs(float(a[k][-1])-state[k]) for k in keys if k in state}
    assert len(state) > 7800 and max(final_diff.values()) < 1e-9
    log = (d/'spectre.out').read_text()
    result = dict(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),
        run=c['run'],case=c['case'],condition=p['condition'],
        source_result=rp.relative_to(ROOT).as_posix(),source_result_sha256=sha(rp),
        protocol_sha256=sha(pp),validation_at_audit_sha256=sha(vp),
        remote_hash_audit=remote_path.relative_to(ROOT).as_posix(),remote_hash_audit_sha256=sha(remote_path),
        input_count=len(inputs),all_inputs_match=True,outputs=outputs,remote_local_raw_log_state_match=True,
        cache_sha256=sha(cache),independent_parser_samples=len(t),independent_parser_max_differences=diffs,
        duplicate_records=duplicates,measurement_window_ranges=ranges,settling_windows=windows,
        final_state_entries=len(state),all_source_state_keys_preserved=True,final_state_saved_voltage_differences={k:v for k,v in final_diff.items() if ':' not in k},
        final_state_saved_current_differences_a={k:v for k,v in final_diff.items() if ':' in k},
        trapezoidal_ringing_reported='Trapezoidal ringing is detected' in log,
        ringing_nodes=[],quiet_validation=q,recovery_audit_passed=True,
        full_pll_acceptance=False,integrated_10khz_jitter_fs=None,
        limitations=['Recovery audit does not override the quiet stationarity gate.',
            'Shorter settling windows are diagnostic only; the complete last 1us gate remains unchanged.',
            'Trapezoidal ringing notices require numerical convergence checks; absence of Newton/LTE recovery alone is insufficient.',
            'All observations belong to original V14 at the stated condition; they are not RT4 or full PVT/noise acceptance.'])
    dest = H/'results/full_pll_main_iab100_recovery_audit.json'
    dest.write_text(json.dumps(result,indent=2)+'\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2,1,figsize=(8,6),sharex=True)
    axes[0].plot(refs*1e6,phase-phase[0],'.-'); axes[0].set_ylabel('RF phase change (rad)')
    for k in ['XP.ctrl','XP.vc1']:
        axes[1].plot(refs*1e6,np.interp(refs,t,a[k]),'.-',label=k)
    axes[1].set_ylabel('Voltage (V)');axes[1].set_xlabel('Continuation time (us)');axes[1].legend()
    for ax in axes: ax.grid(alpha=.3);ax.axvspan(1.2,2.2,color='grey',alpha=.1)
    fig.suptitle('Original V14 full transistor PLL: quiet settling, TT 27 C\n0.25 ps, iabstol 100 fA, reltol 1e-6; shaded: required last 1 us window')
    fig.tight_layout();fig.savefig(H/'results/figures/main_iab100_quiet_settling.png',dpi=150);plt.close(fig)
    print(json.dumps(dict(quiet=q,windows=windows,samples=len(t),audit_passed=True),indent=2))

if __name__ == '__main__': main()
