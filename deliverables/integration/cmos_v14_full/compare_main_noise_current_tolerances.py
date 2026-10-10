"""Compare original V14 1 pA and 100 fA high-offset noise diagnostics."""
from pathlib import Path
import datetime, json
import numpy as np
from audit_rt4_half_seed29_noise_recovery import sha
from noise_utils import cross

H=Path(__file__).resolve().parent
ROOT=H.parents[3]
R=ROOT/'research/runs/spectre_cmos_v14_full'

def main():
    files=[H/'results/full_pll_main_quarter_pair_protocol.json',H/'results/full_pll_main_iab100_retry_pair_protocol.json']
    pp=[json.loads(f.read_text()) for f in files]
    for key in ['text_state_sha256','physical_dependency_hashes','reference_phase_preservation','ref_hz','output_hz','measurement_start_s','edge_count','reltol','vabstol','stop_s','maxstep_s','seed','noisefmax_hz','noisefmin_hz','band_hz']:
        assert pp[0][key]==pp[1][key],key
    assert pp[0]['iabstol']==1e-12 and pp[1]['iabstol']==1e-13
    audits=[H/'results/full_pll_main_quarter_noise_recovery_audit.json',H/'results/full_pll_main_iab100_noise_recovery_audit.json']
    assert all(json.loads(f.read_text())['recovery_audit_passed'] for f in audits)
    datasets=[];validation=[];sources=[]
    for pf,p in zip(files,pp):
        vf=pf.with_name(pf.name.replace('_protocol.json','_validation.json'))
        v=json.loads(vf.read_text());assert v['high_offset_diagnostic_valid'] and all(v['checks'].values()) and v['protocol_sha256']==sha(pf)
        validation.append(dict(path=vf.relative_to(ROOT).as_posix(),sha256=sha(vf),rms_fs=v['diagnostic_band_rms_fs']))
        edges=[]
        for c,vc in zip(p['cases'],v['cases']):
            d=R/c['run']/c['case'];rp=d/'result.json';r=json.loads(rp.read_text());cache=d/'waveforms.npz'
            assert r['ok'] and sha(rp)==vc['source_sha256'] and sha(cache)==vc['cache_sha256']==r['local_outputs_sha256']['waveforms.npz']
            with np.load(cache) as z:
                e=cross(z['time'],z['out'],.6)
            e=e[e>=p['measurement_start_s']][:p['edge_count']];assert len(e)==p['edge_count']
            edges.append(e);sources.append(dict(run=c['run'],case=c['case'],result_sha256=sha(rp),cache_sha256=sha(cache)))
        delta=edges[1]-edges[0];datasets.append(delta-delta.mean())
    for index in [0,1]:
        tb=[H/'tb'/(p['cases'][index]['case']+'.scs') for p in pp]
        assert all(sha(f)==p['cases'][index]['tb_sha256'] for f,p in zip(tb,pp))
        assert tb[0].read_text().replace('iabstol=1e-12','iabstol=1e-13')==tb[1].read_text()
    n=pp[0]['edge_count'];fs=pp[0]['output_hz'];f=np.fft.fftfreq(n,1/fs)
    mask=(abs(f)>=pp[0]['band_hz'][0])&(abs(f)<=pp[0]['band_hz'][1]);filtered=[];rms=[]
    for residual,v in zip(datasets,validation):
        spectrum=np.fft.fft(residual);variance=float(np.sum(abs(spectrum[mask])**2)/n**2)
        y=np.fft.ifft(spectrum*mask).real;assert np.isclose(np.mean(y*y),variance,rtol=1e-12,atol=0)
        value=float(np.sqrt(variance)*1e15);assert np.isclose(value,v['rms_fs'],rtol=1e-12)
        rms.append(value);filtered.append(y)
    out=dict(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),condition=pp[1]['condition'],protocol_sha256=[sha(f) for f in files],audit_sha256=[sha(f) for f in audits],validation=validation,sources=sources,only_current_tolerance_changed=True,iabstol_a=[1e-12,1e-13],rms_fs=rms,rms_difference_fs=rms[1]-rms[0],relative_rms_difference_percent=(rms[1]/rms[0]-1)*100,band_filtered_realization_difference_rms_fs=float(np.std(filtered[1]-filtered[0])*1e15),band_filtered_realization_correlation=float(np.corrcoef(filtered)[0,1]),edge_count=n,effective_band_hz=[5285156.25,492000000.0],comparison_valid=True,numerical_convergence_established=False,full_pll_acceptance=False,integrated_10khz_jitter_fs=None,limitations=['Each noisy trace is subtracted from its own matching quiet trace; mean removal only.','One fixed seed and a finite high-offset record provide a sensitivity observation, not statistical or full numerical convergence.','Same seed with adaptive timesteps need not mean identical random excitation; realization differences are not an absolute numerical-error floor.','Low-offset noise, complete discrete-spur classification, bandwidth and record-length convergence remain open.'])
    dest=H/'results/full_pll_main_noise_current_tolerance_comparison.json';assert not dest.exists();dest.write_text(json.dumps(out,indent=2)+'\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,1,figsize=(8,6))
    for y,label in zip(filtered,['1 pA','100 fA']):axes[0].plot(np.arange(n),y*1e15,lw=.8,label=label)
    axes[0].set(ylabel='Band filtered residual (fs)',xlabel='Matched edge index');axes[0].legend()
    axes[1].plot(np.arange(n),(filtered[1]-filtered[0])*1e15,lw=.8);axes[1].set(ylabel='100 fA minus 1 pA (fs)',xlabel='Matched edge index')
    for ax in axes:ax.grid(alpha=.3)
    fig.suptitle('Original full PLL: current tolerance sensitivity, seed 11, TT 27 C\n0.25 ps; 5.285-492 MHz diagnostic, no full-band acceptance')
    fig.tight_layout();fig.savefig(H/'results/figures/main_noise_current_tolerance_comparison.png',dpi=150);plt.close(fig)
    print(json.dumps({k:out[k] for k in ['rms_fs','rms_difference_fs','relative_rms_difference_percent','band_filtered_realization_difference_rms_fs','band_filtered_realization_correlation']},indent=2),flush=True)

if __name__=='__main__':main()
