"""Compare two preregistered seeds across integration methods; no convergence claim."""
from pathlib import Path
import datetime, json
import numpy as np
from audit_rt4_gear_noise_recovery import sha
from noise_utils import cross

H=Path(__file__).resolve().parent; ROOT=H.parents[3]

def main():
    names=['full_pll_rt4_quarter','full_pll_rt4_quarter_seed29',
           'full_pll_rt4_gear_quarter','full_pll_rt4_gear_seed29']
    audit_names=['full_pll_rt4_quarter_noise_recovery_audit',
                 'full_pll_rt4_quarter_seed29_noise_recovery_audit',
                 'full_pll_rt4_gear_noise_recovery_audit',
                 'full_pll_rt4_gear_seed29_noise_recovery_audit']
    rows=[]; protocols=[]; traces={}; bodies={}; edge_cache={}
    for name,aname in zip(names,audit_names):
        pp=H/'results'/(name+'_pair_protocol.json'); p=json.loads(pp.read_text())
        vp=H/'results'/(name+'_pair_validation.json'); v=json.loads(vp.read_text())
        ap=H/'results'/(aname+'.json'); audit=json.loads(ap.read_text())
        assert audit['recovery_audit_passed'] and audit['validation_sha256']==sha(vp)
        assert v['high_offset_diagnostic_valid'] and all(v['checks'].values()) and v['protocol_sha256']==sha(pp)
        if protocols:
            for k in ['text_state_sha256','physical_dependency_hashes','reference_phase_preservation','ref_hz','output_hz','measurement_start_s','edge_count','reltol','vabstol','iabstol','stop_s','maxstep_s','noisefmax_hz','noisefmin_hz','band_hz']:
                assert p[k]==protocols[0][k],k
        protocols.append(p); edges=[]; sources=[]
        for c,vc in zip(p['cases'],v['cases']):
            d=ROOT/'research/runs/spectre_cmos_v14_full'/c['run']/c['case']; rp=d/'result.json'; r=json.loads(rp.read_text()); cache=d/'waveforms.npz'
            assert r['ok'] and sha(rp)==vc['source_sha256']
            key=str(cache)
            if key not in edge_cache:
                digest=sha(cache)
                with np.load(cache) as z:e=cross(z['time'],z['out'],.6)
                e=e[e>=p['measurement_start_s']][:p['edge_count']];assert len(e)==p['edge_count']
                edge_cache[key]=(digest,e)
            digest,e=edge_cache[key];assert digest==vc['cache_sha256']==r['local_outputs_sha256']['waveforms.npz']
            edges.append(e);sources.append(dict(run=c['run'],case=c['case'],result_sha256=sha(rp),cache_sha256=digest))
            tb=H/'tb'/(c['case']+'.scs');assert sha(tb)==c['tb_sha256']
            if c['noise_enabled']:bodies[(p.get('method','traponly'),p['seed'])]=tb.read_text()
        delta=edges[1]-edges[0];delta-=delta.mean();n=len(delta);fs=p['output_hz'];freq=np.fft.rfftfreq(n,1/fs)
        mask=(freq>=p['band_hz'][0])&(freq<=p['band_hz'][1]);windows=[]
        for wn,w in [('rectangular',np.ones(n)),('symmetric_hann',np.hanning(n))]:
            power=abs(np.fft.rfft(delta*w))**2/(n*np.sum(w*w));power[1:-1]*=2
            assert np.isclose(power.sum(),np.sum((delta*w)**2)/np.sum(w*w),rtol=1e-12,atol=0)
            windows.append(dict(window=wn,band_rms_fs=float(np.sqrt(power[mask].sum())*1e15),enbw_bins=float(n*np.sum(w*w)/np.sum(w)**2)))
        assert np.isclose(windows[0]['band_rms_fs'],v['diagnostic_band_rms_fs'],rtol=1e-12)
        method=p.get('method','traponly');traces[(method,p['seed'])]=delta
        rows.append(dict(method=method,seed=p['seed'],protocol=pp.relative_to(ROOT).as_posix(),protocol_sha256=sha(pp),validation_sha256=sha(vp),audit_sha256=sha(ap),sources=sources,endpoint_difference_ps=float((delta[-1]-delta[0])*1e12),windows=windows))
    for seed in [11,29]:
        assert bodies[('traponly',seed)].replace('method=traponly','method=gear2only')==bodies[('gear2only',seed)]
    for method in ['traponly','gear2only']:
        assert bodies[(method,11)].replace('noiseseed=11','noiseseed=29')==bodies[(method,29)]
    comparisons=[]
    for seed in [11,29]:
        pair=[next(r for r in rows if r['method']==m and r['seed']==seed) for m in ['traponly','gear2only']]
        comparisons.append(dict(seed=seed,windows=[dict(window=pair[0]['windows'][i]['window'],gear_minus_trap_fs=pair[1]['windows'][i]['band_rms_fs']-pair[0]['windows'][i]['band_rms_fs'],relative_difference_percent=(pair[1]['windows'][i]['band_rms_fs']/pair[0]['windows'][i]['band_rms_fs']-1)*100) for i in [0,1]]))
    means=[]
    for method in ['traponly','gear2only']:
        rr=[r for r in rows if r['method']==method]
        means.append(dict(method=method,windows=[dict(window=rr[0]['windows'][i]['window'],mean_variance_rms_fs=float(np.sqrt(np.mean([r['windows'][i]['band_rms_fs']**2 for r in rr]))),individual_rms_fs=[r['windows'][i]['band_rms_fs'] for r in rr]) for i in [0,1]]))
    out=dict(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),condition=protocols[0]['condition'],records=rows,method_comparison=comparisons,seed_variance_means=means,only_method_or_seed_changed=True,comparison_valid=True,primary_metric_changed=False,numerical_convergence_established=False,statistical_convergence_established=False,full_pll_acceptance=False,integrated_10khz_jitter_fs=None,effective_band_hz=[float(freq[mask][0]),float(freq[mask][-1])],edge_count=n,limitations=['Each method uses its own quiet template; only mean removal, no trend fitting, amplitude scaling or spectral notches.','Two seeds do not establish statistical confidence or full numerical convergence. Mean variances are descriptive, not a confidence interval.','Adaptive timesteps and method changes need not preserve the same random excitation even with equal seeds.','Hann uses sum(w^2) energy normalization and is secondary sensitivity evidence; the rectangular preregistered metric remains primary.','Neither this short record nor the 1MHz source-noise floor can establish 10kHz full-band jitter.','Gear damping, record length and bandwidth remain unresolved; RT4 is an unadopted candidate.'])
    dest=H/'results/full_pll_rt4_method_seed_matrix.json';assert not dest.exists();dest.write_text(json.dumps(out,indent=2)+'\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(10,4))
    for i,ax in enumerate(axes):
        for method in ['traponly','gear2only']:
            rr=[r for r in rows if r['method']==method]
            ax.plot([r['seed'] for r in rr],[r['windows'][i]['band_rms_fs'] for r in rr],marker='o',label=method)
        ax.set(xlabel='Noise seed',ylabel='Diagnostic RMS (fs)',title=['Rectangular (primary)','Hann (sensitivity only)'][i],xticks=[11,29]);ax.grid(alpha=.3);ax.legend()
    fig.suptitle('RT4 full PLL: 0.25 ps, 1 pA, 160 GHz; 5.285-492 MHz\nTwo-seed method sensitivity; no full-band acceptance')
    fig.tight_layout();fig.savefig(H/'results/figures/rt4_method_seed_matrix.png',dpi=150);plt.close(fig)
    print(json.dumps(dict(records=[{k:r[k] for k in ['method','seed','endpoint_difference_ps','windows']} for r in rows],method_comparison=comparisons,seed_variance_means=means),indent=2),flush=True)

if __name__=='__main__':main()
