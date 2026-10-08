"""Compare RT4 candidate independent seeds 11 and 29 at fixed 0.25 ps."""
from pathlib import Path
import datetime, hashlib, json
import numpy as np
from noise_utils import cross

H = Path(__file__).resolve().parent
ROOT = H.parents[3]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    names = ['full_pll_rt4_quarter_pair', 'full_pll_rt4_quarter_seed29_pair']
    protocols = [json.loads((H/'results'/(n+'_protocol.json')).read_text()) for n in names]
    validations = [json.loads((H/'results'/(n+'_validation.json')).read_text()) for n in names]
    assert protocols[1]['parent_protocol_sha256'] == sha(H/'results'/(names[0]+'_protocol.json'))
    invariant = ['physical_dependency_hashes', 'text_state_sha256', 'output_hz', 'ref_hz',
                 'stop_s', 'noise_start_s', 'measurement_start_s', 'edge_count', 'band_hz',
                 'reltol', 'vabstol', 'iabstol', 'noisefmax_hz', 'noisefmin_hz', 'maxstep_s', 'reference_phase_preservation']
    assert all(protocols[0][k] == protocols[1][k] for k in invariant)
    for old, new in zip(protocols[0]['cases'], protocols[1]['cases']):
        a = H/'tb'/(old['case']+'.scs'); b = H/'tb'/(new['case']+'.scs')
        assert sha(a) == old['tb_sha256'] and sha(b) == new['tb_sha256']
        assert (a.read_text().replace('noiseseed=11 ', 'noiseseed=29 ') if old['noise_enabled'] else a.read_text()) == b.read_text()
    rows = []; spectra = []
    for name, p, v in zip(names, protocols, validations):
        assert v['complete'] and v['high_offset_diagnostic_valid']
        assert v['protocol_sha256'] == sha(H/'results'/(name+'_protocol.json'))
        edges = []
        for c in p['cases']:
            d = ROOT/'research/runs/spectre_cmos_v14_full'/c['run']/c['case']
            with np.load(d/'waveforms.npz') as z:
                e = cross(z['time'], z['out'], .6)
            edges.append(e[e >= p['measurement_start_s']][:p['edge_count']])
        residual = edges[1]-edges[0]; residual -= residual.mean(); n = len(residual)
        f = np.fft.rfftfreq(n, 1/p['output_hz'])
        power = abs(np.fft.rfft(residual))**2/n**2; power[1:-1] *= 2
        select = (f >= p['band_hz'][0]) & (f <= p['band_hz'][1])
        variance = float(power[select].sum()); rms = np.sqrt(variance)*1e15
        assert np.isclose(rms, v['diagnostic_band_rms_fs'], rtol=1e-12)
        bands = []
        for lo, hi in [(5e6,20e6),(20e6,100e6),(100e6,492e6)]:
            mask = (f >= lo) & ((f < hi) if hi < 492e6 else (f <= hi))
            bands.append(dict(center_selection_hz=[lo,hi],rms_fs=float(np.sqrt(power[mask].sum())*1e15)))
        rows.append(dict(maxstep_ps=p['maxstep_s']*1e12,seed=p['seed'],
            protocol_sha256=v['protocol_sha256'],validation_sha256=sha(H/'results'/(name+'_validation.json')),
            band_rms_fs=float(rms),band_variance_s2=variance,
            block_variance_standard_error_s2=v['block_variance_standard_error_s2'],subbands=bands))
        spectra.append(power)
    delta = rows[1]['band_variance_s2']-rows[0]['band_variance_s2']
    se = np.hypot(*[r['block_variance_standard_error_s2'] for r in rows])
    out = dict(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),
        physical_inputs_and_initial_state_match=True,testbench_change='noise seed only: 11 to 29; exact quiet case reused',records=rows,
        rms_relative_change_percent=100*(rows[1]['band_rms_fs']/rows[0]['band_rms_fs']-1),
        variance_difference_s2=delta,block_se_quadrature_s2=float(se),
        descriptive_variance_difference_over_block_se=float(delta/se),
        effective_band_hz=validations[1]['effective_band_hz'],numerical_convergence_established=False,statistical_convergence_established=False,
        full_pll_acceptance=False,integrated_10khz_jitter_fs=None,
        limitations=['Two independent seeds at one timestep characterize initial realization spread, not a population confidence interval or numerical convergence.',
          'The variance difference divided by block SE is descriptive, not a significance test or confidence interval; blocks may be correlated.',
          'The 0.25 ps quiet and both noisy records report no trapezoidal ringing; absence of a notice is not proof of convergence.',
          'Do not subtract the two random noise traces and label the difference a numerical error floor.',
          'Retain both preregistered rectangular results. Seed, tolerance, integration method, bandwidth and duration convergence remain open.',
          'No result includes 10 kHz to 5.28515625 MHz or constitutes full-band acceptance.'])
    (H/'results/full_pll_rt4_quarter_seed_comparison.json').write_text(json.dumps(out,indent=2)+'\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2,1,figsize=(9,6))
    for row, power in zip(rows, spectra):
        label = f"Seed {row['seed']}: {row['band_rms_fs']:.2f} fs"
        axes[0].semilogx(f[1:]/1e6,10*np.log10(np.maximum(power[1:]*1e30,1e-30)),label=label,alpha=.75)
        select = f >= protocols[0]['band_hz'][0]
        axes[1].semilogx(f[select]/1e6,np.sqrt(np.cumsum(power[select]))*1e15,label=label)
    axes[0].set(ylabel='Edge variance / bin (dB fs²)')
    axes[1].set(xlabel='Offset (MHz)',ylabel='Cumulative diagnostic RMS (fs)')
    for ax in axes: ax.grid(alpha=.3); ax.legend()
    fig.suptitle('RT4 candidate, TT 27 C, 0.25 ps, independent seeds 11 and 29\nSame matched quiet subtraction; convergence and full-band acceptance remain open')
    fig.tight_layout();fig.savefig(H/'results/figures/rt4_quarter_seed_comparison.png',dpi=150);plt.close(fig)
    print(json.dumps(out,indent=2))


if __name__ == '__main__': main()
