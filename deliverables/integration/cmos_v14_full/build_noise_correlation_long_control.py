"""Extend the passed colored-RC control to the actual core's 250 ns PSS period."""
from pathlib import Path
import datetime,hashlib,json
H=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
prior=H/'results/noise_correlation_control_validation.json'
v=json.loads(prior.read_text());assert v['complete'] and v['passed']
case='noise_corr_ratio246_core';tb=H/'tb'/(case+'.scs');assert not tb.exists()
body=(H/'tb/noise_corr_ratio6.scs').read_text()
body=body.replace('fund=164000000 harms=383 maxacfreq=1T','fund=4M harms=4095')
body=body.replace('maxstep=250f','maxstep=1p').replace('sampleratio=6 maxsideband=383','sampleratio=246 maxsideband=4095')
body=body.replace('values=[1M 10M 82M 163M 164M 165M 246M 492M]','values=[1M 164M 492M]')
assert 'fund=4M' in body and 'sampleratio=246' in body and 'maxacfreq=' not in body
tb.write_text(body)
p=dict(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),status='prepared_not_run',
    run='noisecorr246_01',case=case,tb_sha256=sha(tb),prior_validation_sha256=sha(prior),
    offsets_hz=[1e6,164e6,492e6],resistance_ohm=1000.,capacitance_f=2e-12,temperature_k=300.15,
    sample_frequency_hz=984e6,input_amplitude_v=.5,fund_hz=4e6,sample_ratio=246,
    condition='Same colored1kohm/2pF/noiseless984MHz source/27C. Fresh4MHz PSS;1ps/Gear2/4095/default maxacfreq matches core numerical settings. Three PSD points only.',
    limits=dict(point_psd_error_db=.1,ratio1_to_ratio246_psd_db=.1,period_relative=1e-8,endpoint_v=1e-3,device_sum_relative=1e-7),
    launch_gate='One one-thread shortslot only after the existing RT4 matching case is collected; cap18threads/fourlong+oneshort. No automatic further calibration.',
    limitations=['Validates only this stationary linear colored-noise example and the selected numerical settings.',
        'Cannot validate246 non-equivalent transistor output edges, MOS1/f poles or fullPLL jitter.',
        'No RMS inferred from three sparse colored-noise points. Retain failure if the coarse method differs.'],
    main_dut_modified=False,full_pll_acceptance=False)
(H/'results/noise_correlation_long_protocol.json').write_text(json.dumps(p,indent=2)+'\n')
print(case)
