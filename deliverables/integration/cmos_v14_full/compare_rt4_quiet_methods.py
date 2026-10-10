"""Compare matched RT4 quiet trajectories: deterministic method sensitivity only."""
from pathlib import Path
import datetime,json
import numpy as np
from compare_main_quiet_timesteps import trajectory,sha

H=Path(__file__).resolve().parent

def main():
    files=[H/'results/full_pll_rt4_quarter_pair_protocol.json',H/'results/full_pll_rt4_gear_quarter_pair_protocol.json']
    p=[json.loads(f.read_text()) for f in files];assert p[1]['parent_protocol_sha256']==sha(files[0])
    for k in ['condition','text_state_sha256','physical_dependency_hashes','reference_phase_preservation','ref_hz','output_hz','measurement_start_s','edge_count','reltol','vabstol','iabstol','stop_s','maxstep_s','noisefmin_hz','noisefmax_hz','seed']:
        assert p[0][k]==p[1][k],k
    tb=[H/'tb'/(q['cases'][0]['case']+'.scs') for q in p]
    assert all(sha(f)==q['cases'][0]['tb_sha256'] for f,q in zip(tb,p))
    assert tb[0].read_text().replace('method=traponly','method=gear2only')==tb[1].read_text()
    ap=H/'results/full_pll_rt4_gear_quiet_recovery_audit.json';a=json.loads(ap.read_text());assert a['recovery_audit_passed']
    vv=[H/'results/full_pll_rt4_quarter_pair_validation.json',H/'results/full_pll_rt4_gear_quarter_pair_validation.json']
    v=[json.loads(f.read_text()) for f in vv]
    assert all(x['cases'][0]['stationarity']['passed'] and x['cases'][0]['status_stable'] for x in v)
    data=[trajectory(q) for q in p]
    assert all(x['source_result_sha256']==z['cases'][0]['source_sha256'] for x,z in zip(data,v))
    delta=data[1]['edges']-data[0]['edges'];assert np.max(abs(delta))*p[0]['output_hz']<.25
    residual=delta-delta.mean();n=len(delta);f=np.fft.fftfreq(n,d=1/p[0]['output_hz']);power=abs(np.fft.fft(residual)/n)**2
    band=(abs(f)>=p[0]['band_hz'][0])&(abs(f)<=p[0]['band_hz'][1]);pe=abs(power.sum()/np.mean(residual**2)-1);assert pe<1e-12
    diagnostics=dict(edge_count=n,edge_threshold_v=.6,difference_order='Gear2 minus trapezoidal, matched rising-edge ordinal',mean_edge_difference_ps=float(delta.mean()*1e12),peak_to_peak_difference_ps=float(np.ptp(delta)*1e12),maximum_absolute_difference_ps=float(np.max(abs(delta))*1e12),mean_removed_difference_rms_fs=float(np.std(delta)*1e15),fft_bin_width_hz=p[0]['output_hz']/n,selected_bin_centers_hz=[float(abs(f[band]).min()),float(abs(f[band]).max())],effective_bin_coverage_hz=[float(abs(f[band]).min()-p[0]['output_hz']/n/2),p[0]['output_hz']/2],band_limited_deterministic_difference_rms_fs=float(np.sqrt(power[band].sum())*1e15),parseval_relative_error=float(pe),random_jitter=False)
    frequency_delta=(v[1]['cases'][0]['stationarity']['mean_output_mhz']-v[0]['cases'][0]['stationarity']['mean_output_mhz'])*1e6
    assert len(data[0]['refs'])==len(data[1]['refs']) and np.max(abs(data[1]['refs']-data[0]['refs']))<1e-11
    controls={}
    for k in ['XP.ctrl','XP.vc1']:
        diff=data[1]['controls'][k]-data[0]['controls'][k]
        controls[k]=dict(mean_difference_mv=float(diff.mean()*1e3),peak_to_peak_difference_mv=float(np.ptp(diff)*1e3),maximum_absolute_difference_mv=float(abs(diff).max()*1e3))
    result=dict(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),condition=p[0]['condition'],protocol_sha256=[sha(f) for f in files],validation_at_comparison_sha256=[sha(f) for f in vv],gear_quiet_audit_sha256=sha(ap),only_method_changed=True,matched_physical_dependency_hashes=p[0]['physical_dependency_hashes'],quiet=[x['cases'][0] for x in v],sources=[{k:x[k] for k in ['source_result','source_result_sha256','cache_sha256']} for x in data],last_1us_output_frequency_difference_hz=frequency_delta,deterministic_edge_diagnostics=diagnostics,comparison_valid=True,numerical_convergence_established=False,full_pll_acceptance=False,integrated_10khz_jitter_fs=None,limitations=['All differences are from noiseless traces; none is random jitter or an absolute numerical error floor.','Both methods passing the same quiet gate does not validate noisy-method convergence or eliminate artificial damping.','The Gear noisy run must use its own Gear quiet template.','No fitted trend or spur notch is removed; the edge-difference RMS subtracts the mean only.','RT4 remains an unadopted candidate; final 10 kHz-to-half-output noise and discrete spurs are unresolved.'])
    result['reference_sampled_control_differences']=controls
    dest=H/'results/full_pll_rt4_quiet_method_comparison.json';dest.write_text(json.dumps(result,indent=2)+'\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(3,1,figsize=(8,8))
    for x,label in zip(data,['Trapezoidal','Gear2']):
        ax[0].plot(x['refs']*1e6,x['phase']-x['phase'][0],'.-',label=label)
        ax[1].plot(x['refs']*1e6,x['controls']['XP.ctrl']*1e3,'.-',label=label)
    ax[0].set_ylabel('RF phase change (rad)');ax[1].set_ylabel('Control voltage (mV)');ax[1].set_xlabel('Continuation time (us)')
    ax[2].plot(np.arange(n),delta*1e12);ax[2].set_ylabel('Gear2 - trap edge time (ps)');ax[2].set_xlabel('Matched rising edge index (from 1.1 us)')
    for x in ax:x.grid(alpha=.3)
    ax[0].legend();fig.suptitle('RT4 full PLL quiet method sensitivity: 0.25 ps, 1 pA, TT 27 C\nDeterministic differences; no noise or convergence acceptance')
    fig.tight_layout();fig.savefig(H/'results/figures/rt4_quiet_method_comparison.png',dpi=150);plt.close(fig)
    print(json.dumps(dict(frequency_delta_hz=frequency_delta,deterministic_edge_diagnostics=diagnostics)),flush=True)

if __name__=='__main__':main()
