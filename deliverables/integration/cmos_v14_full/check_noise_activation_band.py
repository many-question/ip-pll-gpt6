"""Regression checks for noise-band reporting; no new simulation is performed."""
from pathlib import Path
import hashlib,json,re
from analyze_full_pll_noise_activation_probe import noise_band_diagnostic
H=Path(__file__).resolve().parent;ROOT=H.parents[3]

def main():
    pp=H/'results/full_pll_noise_activation_probe_protocol.json'
    p=json.loads(pp.read_text())
    observation=json.loads((H/'results/full_pll_noise_activation_band_observation.json').read_text())
    lp=ROOT/observation['log_path'];log=lp.read_text()
    assert hashlib.sha256(lp.read_bytes()).hexdigest()==observation['log_sha256']
    assert hashlib.sha256(pp.read_bytes()).hexdigest()==observation['protocol_sha256']
    actual=noise_band_diagnostic(p,log)
    assert actual==observation['noise_band']
    tests={}
    tests['actual_log_preserves_requested_failure']=not actual['requested_configuration_matched']
    tests['actual_log_recognizes_documented_5MHz_floor']=actual['documented_duration_floor_applied']
    tests['actual_log_never_implies_jitter_acceptance']=not actual['low_offset_coverage_established'] and actual['integrated_jitter_fs'] is None
    # The following are deliberately altered log fixtures, not measured results.
    stripped=log
    for notice in actual['adjustment_notices']:stripped=stripped.replace(notice,'')
    tests['unexplained_band_change_rejected']=not noise_band_diagnostic(p,stripped)['activation_configuration_understood']
    wrong_min=re.sub(r'^    noisefmin = [^\n]+','    noisefmin = 4 MHz',log,flags=re.M)
    tests['wrong_effective_floor_rejected']=not noise_band_diagnostic(p,wrong_min)['activation_configuration_understood']
    wrong_max=re.sub(r'^    noisefmax = [^\n]+','    noisefmax = 80 GHz',log,flags=re.M)
    tests['wrong_effective_maximum_rejected']=not noise_band_diagnostic(p,wrong_max)['activation_configuration_understood']
    matched=noise_band_diagnostic(dict(p,stop_s=2.2e-6),'    noisefmin = 1 MHz\n    noisefmax = 160 GHz\n')
    tests['unaltered_longer_duration_band_matches']=matched['requested_configuration_matched'] and not matched['documented_duration_floor_applied']
    out=dict(scope=__doc__,source_log_sha256=observation['log_sha256'],checks=tests,passed=all(tests.values()),
             simulated_new_circuit=False,full_pll_acceptance=False,integrated_jitter_fs=None)
    assert out['passed'],out
    (H/'results/noise_activation_band_regression.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2))

if __name__=='__main__':main()
