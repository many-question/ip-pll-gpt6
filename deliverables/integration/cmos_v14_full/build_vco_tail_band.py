"""Promote the measured frequency-matched tail candidate to a dense spectrum.

Use the same .25ps/511-sideband precision as the completed CF40 reference.
This launches nothing automatically and does not assume the finer carrier
still matches; both frequency and PSD must be checked in the new results.
"""
from pathlib import Path
import datetime,hashlib,json
H=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
proof=H/'results/vco_tail_matched2_noise_validation.json';v=json.loads(proof.read_text())
assert v['frequency_match_passed'] and all(x<0 for x in v['timing_psd_change_db'])
src=H/'tb/vco_tail560_matched2_tt.scs';body=src.read_text()
assert body.count('values=[10k 100k 1M 10M 100M 492M]')==1 and 'maxstep=0.5p' in body and 'maxsideband=255' in body
body=body.replace('values=[10k 100k 1M 10M 100M 492M]','start=10k stop=492M dec=20').replace('maxstep=0.5p','maxstep=0.25p').replace('maxsideband=255','maxsideband=511')
case='vco_tail560_band_finer_tt';dest=H/'tb'/(case+'.scs');assert not dest.exists();dest.write_text(body)
p=dict(scope=__doc__,run='vcotailband01',case=case,time=datetime.datetime.now().astimezone().isoformat(),
    source_validation_sha256=sha(proof),source_tb_sha256=sha(src),tb_sha256=sha(dest),
    baseline_run='vcobiasband01',baseline_case='vco_band_cf40_finer_tt',
    condition='TT27/1.2V/Q5RLC/CF40/MT560um2um/c21/control'+str(v['proposed_control_v'])+'V/staticreference/fixedM4/10fF;freshPSS .25ps/127harms/511sidebands;onlyXVnoise.',
    measured_prior_frequency_error=v['relative_rf_error'],frequency_grid=dict(start_hz=1e4,stop_hz=492e6,points_per_decade=20),
    integration='Only1MHz to commonminimum RF/8 is a high-offset timing estimate. Neverintegratefreeoscillator10kHzasPLLjitter.',
    main_dut_modified=False,full_pll_acceptance=False,
    limitations=['The new .25ps periodic solution and RF matching need verification.','No independent .125ps precision case is launched by this builder.','Active sampler/programmablebank/RT4/fullPLL/PVT remain excluded.'])
(H/'results/vco_tail_band_protocol.json').write_text(json.dumps(p,indent=2)+'\n');print(case)
