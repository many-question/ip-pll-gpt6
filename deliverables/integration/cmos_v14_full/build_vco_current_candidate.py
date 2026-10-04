"""Single-parameter stronger VCO bias experiment; power optimization is deferred."""
from pathlib import Path
import datetime,hashlib,json
H=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
src=H/'tb/vco_bias_cf40_tt.scs';body=src.read_text()
assert body.count('lc_vco_cf40_v14 bias_r=2500')==1
case='vco_bias_r2000_tt';dest=H/'tb'/(case+'.scs');assert not dest.exists()
dest.write_text(body.replace('lc_vco_cf40_v14 bias_r=2500','lc_vco_cf40_v14 bias_r=2000'))
p=dict(scope=__doc__,run='vcocurrent01',case=case,time=datetime.datetime.now().astimezone().isoformat(),
    source_case='vco_bias_cf40_tt',source_run='vcocf40_01',source_tb_sha256=sha(src),candidate_tb_sha256=sha(dest),
    physical_change='Only external VCO bias_r parameter2500ohm->2000ohm. CF40/MOS sizes/Q5RLC and all other physical dependencies unchanged.',
    hypothesis='Higher current may raise oscillation amplitude and improve timing noise. Measure actual PM PSD, current, amplitude and RF change; do not assume improvement.',
    condition='TT27/1.2V/Q5RLC/coarse23/ctrl.679V/CF40/static-reference/fixedM4/10fF/onlyXVnoise/freshPSS .5ps255sidebands.',
    offsets_hz=[1e4,1e5,1e6,1e7,1e8,492e6],
    checks=['Fresh converged PSS and correct RF/M4 harmonics','Independent time-domain carrier and SSB normalization','Device PSD sum closure and excluded-noise check','Compare actual RF frequency, waveform amplitudes, terminal ranges, supply current and high-offset PSD'],
    limitations=['Sixpoints are not integrated jitter.','Fixed-control frequency changes are retained, not silently retuned. A promising result requires target-frequency rematch.','Larger swing/current can change device operation; inspect before adopting.','No power saving claim; fullPLL noise/PVT/startup remain unverified.'],
    main_dut_modified=False,full_pll_acceptance=False)
(H/'results/vco_current_protocol.json').write_text(json.dumps(p,indent=2)+'\n');print(case)
