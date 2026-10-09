"""Compare matched 1 pA and 100 fA quiet records; differences are not random jitter."""
from pathlib import Path
import datetime,json
import numpy as np
from compare_main_quiet_timesteps import trajectory,sha
H=Path(__file__).resolve().parent
def main():
    files=[H/'results/full_pll_main_quarter_pair_protocol.json',H/'results/full_pll_main_iab100_pair_protocol.json']
    p=[json.loads(f.read_text()) for f in files]
    for key in ['text_state_sha256','physical_dependency_hashes','reference_phase_preservation','ref_hz','output_hz',
       'measurement_start_s','edge_count','reltol','vabstol','stop_s','maxstep_s','seed','noisefmax_hz','noisefmin_hz']:
        assert p[0][key]==p[1][key],key
    assert p[0]['iabstol']==1e-12 and p[1]['iabstol']==1e-13
    tb=[H/'tb'/(q['cases'][0]['case']+'.scs') for q in p]
    assert all(sha(f)==q['cases'][0]['tb_sha256'] for f,q in zip(tb,p))
    assert tb[0].read_text().replace('iabstol=1e-12','iabstol=1e-13')==tb[1].read_text()
    af=H/'results/full_pll_main_iab100_recovery_audit.json';a=json.loads(af.read_text());assert a['recovery_audit_passed']
    data=[trajectory(q) for q in p];diff=data[1]['edges']-data[0]['edges'];residual=diff-diff.mean()
    n=len(diff);freq=np.fft.fftfreq(n,1/p[0]['output_hz']);s=np.fft.fft(residual)/n
    band=(abs(freq)>=p[0]['band_hz'][0])&(abs(freq)<=p[0]['band_hz'][1])
    parseval=abs(np.sum(abs(s)**2)/np.mean(residual**2)-1);assert parseval<1e-12
    diagnostics=dict(edge_count=n,difference_order='100 fA minus 1 pA; same rising-edge ordinal',
      mean_edge_difference_fs=float(diff.mean()*1e15),maximum_absolute_difference_fs=float(max(abs(diff))*1e15),
      peak_to_peak_difference_fs=float(np.ptp(diff)*1e15),mean_removed_difference_rms_fs=float(np.std(diff)*1e15),
      band_limited_deterministic_difference_rms_fs=float(np.sqrt(np.sum(abs(s[band])**2))*1e15),
      selected_bin_centers_hz=[float(min(abs(freq[band]))),float(max(abs(freq[band])))],parseval_relative_error=float(parseval),random_jitter=False)
    out=dict(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),condition=p[1]['condition'],
      protocol_sha256=[sha(f) for f in files],recovery_audit_sha256=sha(af),same_dut_state_reference_solver_except_iabstol=True,
      sources=[{k:v for k,v in d.items() if k.startswith('source_') or k=='cache_sha256'} for d in data],
      deterministic_edge_sensitivity=diagnostics,numerical_convergence_established=False,full_pll_acceptance=False,
      limitations=['Noisy 100 fA record remains pending and must use its own quiet template.',
        'Quiet edge differences are deterministic sensitivity, not random noise or a noise floor.',
        'A small quiet difference does not prove stochastic accuracy, solver/bandwidth convergence or 10 kHz acceptance.'])
    target=H/'results/full_pll_main_quiet_current_tolerance_comparison.json';assert not target.exists();target.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(diagnostics,indent=2))
if __name__=='__main__':main()
