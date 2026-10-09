"""Audit the original V14 two-timestep/two-seed high-offset diagnostic matrix."""
from pathlib import Path
import datetime, hashlib, json
import numpy as np
from noise_utils import cross

H=Path(__file__).resolve().parent
ROOT=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    names=['full_pll_main_settled_ssd_cwd_pair','full_pll_main_half_seed29_pair',
           'full_pll_main_quarter_pair','full_pll_main_quarter_seed29_pair']
    protocols=[json.loads((H/'results'/(n+'_protocol.json')).read_text()) for n in names]
    invariant=['physical_dependency_hashes','text_state_sha256','output_hz','ref_hz','stop_s',
               'noise_start_s','measurement_start_s','edge_count','band_hz','reltol','vabstol',
               'iabstol','noisefmax_hz','noisefmin_hz','reference_phase_preservation']
    assert all(all(p[k]==protocols[0][k] for k in invariant) for p in protocols)
    def normalize(body):
        return body.replace('maxstep=.25p ','maxstep=.5p ').replace('noiseseed=29 ','noiseseed=11 ')
    reference=[normalize((H/'tb'/(c['case']+'.scs')).read_text()) for c in protocols[0]['cases']]
    rows=[]; spectra=[]
    for name,p in zip(names,protocols):
        vp=H/'results'/(name+'_validation.json');v=json.loads(vp.read_text())
        assert v['complete'] and v['high_offset_diagnostic_valid']
        assert v['protocol_sha256']==sha(H/'results'/(name+'_protocol.json'))
        edges=[]
        for i,c in enumerate(p['cases']):
            tb=H/'tb'/(c['case']+'.scs')
            assert sha(tb)==c['tb_sha256'] and normalize(tb.read_text())==reference[i]
            d=ROOT/'research/runs/spectre_cmos_v14_full'/c['run']/c['case']
            assert sha(d/'result.json')==v['cases'][i]['source_sha256']
            assert sha(d/'waveforms.npz')==v['cases'][i]['cache_sha256']
            with np.load(d/'waveforms.npz') as z: e=cross(z['time'],z['out'],.6)
            edges.append(e[e>=p['measurement_start_s']][:p['edge_count']])
        residual=edges[1]-edges[0];residual-=residual.mean();n=len(residual)
        f=np.fft.rfftfreq(n,1/p['output_hz']);power=abs(np.fft.rfft(residual))**2/n**2;power[1:-1]*=2
        selected=(f>=p['band_hz'][0])&(f<=p['band_hz'][1])
        variance=float(power[selected].sum());rms=float(np.sqrt(variance)*1e15)
        assert np.isclose(rms,v['diagnostic_band_rms_fs'],rtol=1e-12)
        subbands=[]
        for lo,hi in [(5e6,20e6),(20e6,100e6),(100e6,492e6)]:
            mask=(f>=lo)&((f<hi) if hi<492e6 else (f<=hi))
            subbands.append(dict(center_selection_hz=[lo,hi],rms_fs=float(np.sqrt(power[mask].sum())*1e15)))
        rows.append(dict(maxstep_ps=p['maxstep_s']*1e12,seed=p['seed'],protocol_sha256=v['protocol_sha256'],
            validation_sha256=sha(vp),band_rms_fs=rms,band_variance_s2=variance,subbands=subbands,
            block_variance_standard_error_s2=v['block_variance_standard_error_s2']))
        spectra.append(power)
    def compare(a,b,label):
        x,y=rows[a],rows[b];delta=y['band_variance_s2']-x['band_variance_s2']
        se=float(np.hypot(x['block_variance_standard_error_s2'],y['block_variance_standard_error_s2']))
        return dict(comparison=label,from_record=a,to_record=b,rms_relative_change_percent=100*(y['band_rms_fs']/x['band_rms_fs']-1),
                    variance_difference_s2=delta,block_se_quadrature_s2=se,descriptive_variance_difference_over_block_se=delta/se)
    comparisons=[compare(0,1,'seed 11 to 29 at 0.5 ps'),compare(2,3,'seed 11 to 29 at 0.25 ps'),
                 compare(0,2,'0.5 to 0.25 ps at seed 11'),compare(1,3,'0.5 to 0.25 ps at seed 29')]
    pooled=[dict(maxstep_ps=step,seeds=[11,29],equal_record_mean_variance_s2=float(np.mean([r['band_variance_s2'] for r in rows if r['maxstep_ps']==step])),
                 equal_record_variance_rms_fs=float(np.sqrt(np.mean([r['band_variance_s2'] for r in rows if r['maxstep_ps']==step]))*1e15)) for step in [.5,.25]]
    out=dict(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),physical_inputs_and_initial_state_match=True,
        only_changed_parameters=['maxstep','noiseseed'],records=rows,comparisons=comparisons,equal_record_summaries=pooled,
        equal_record_rms_step_change_percent=100*(pooled[1]['equal_record_variance_rms_fs']/pooled[0]['equal_record_variance_rms_fs']-1),
        effective_band_hz=v['effective_band_hz'],numerical_convergence_established=False,statistical_convergence_established=False,
        full_pll_acceptance=False,integrated_10khz_jitter_fs=None,
        limitations=['Two seeds per timestep cannot identify a small timestep bias with a reliable population confidence interval.',
          'Same seed at different adaptive timesteps does not imply identical random waveforms; differences are not numerical error floors.',
          'Equal-record variance summaries are descriptive, not a replacement for any preregistered individual result or an acceptance metric.',
          'Block SE comparisons are descriptive only; blocks can be correlated.',
          'The quarter-ps quiet record contains two internal trapezoidal-ringing notices; all noisy traces and the half-ps quiet have none.',
          'Tolerance, integration method, bandwidth, record length and low-offset coverage remain open.',
          'Quiet subtraction does not establish complete discrete-spur classification. No 10 kHz full-band claim.'])
    (H/'results/full_pll_main_step_seed_matrix.json').write_text(json.dumps(out,indent=2)+'\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(11,4.5))
    for seed in [11,29]:
        records=[r for r in rows if r['seed']==seed]
        axes[0].plot([r['maxstep_ps'] for r in records],[r['band_rms_fs'] for r in records],'o-',label=f'Seed {seed}')
    axes[0].set(xlabel='Maximum timestep (ps)',ylabel='Diagnostic RMS (fs)',xticks=[.25,.5])
    for r,power in zip(rows,spectra):
        axes[1].semilogx(f[selected]/1e6,np.sqrt(np.cumsum(power[selected]))*1e15,label=f"{r['maxstep_ps']} ps / seed {r['seed']}")
    axes[1].set(xlabel='Offset (MHz)',ylabel='Cumulative diagnostic RMS (fs)')
    for ax in axes:ax.grid(alpha=.3);ax.legend()
    fig.suptitle('Original V14, TT 27 C: two timesteps x two seeds\n5.285-492 MHz only; numerical convergence and full-band acceptance remain open')
    fig.tight_layout();fig.savefig(H/'results/figures/main_step_seed_matrix.png',dpi=150);plt.close(fig)
    print(json.dumps(dict(records=rows,comparisons=comparisons,equal_record_summaries=pooled,
                         equal_record_rms_step_change_percent=out['equal_record_rms_step_change_percent']),indent=2))


if __name__=='__main__':main()
