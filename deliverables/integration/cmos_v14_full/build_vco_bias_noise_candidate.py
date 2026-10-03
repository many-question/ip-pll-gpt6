"""Prepare a single-change VCO bias-noise candidate, not main-DUT adoption.

Existing fine six-offset VCO-only noise attributes about20% of the1MHz output
noise variance to the1Mohm bias filter resistor. Increase only its shunt C from
10pF to40pF. High-frequency RC filtering predicts16x reduction of this resistor's
gate-voltage PSD; actual oscillator contribution and startup must be simulated.
"""
from pathlib import Path
import hashlib,json

H=Path(__file__).resolve().parent
B=H.parents[1]/'blocks/cmos_v14_full'
core=B/'lc_core_physical_v14.scs'
vco=B/'lc_vco_physical_v14.scs'
src=core.read_text()
assert src.count('CF (nfilt vss) capacitor c=10p')==1
src=src.replace('lc_core_physical_v14','lc_core_cf40_v14')
src=src.replace('CF (nfilt vss) capacitor c=10p','CF (nfilt vss) capacitor c=40p')
p=B/'lc_core_cf40_v14.scs';assert not p.exists();p.write_text(src)
src=vco.read_text().replace('lc_core_physical_v14','lc_core_cf40_v14').replace('lc_vco_physical_v14','lc_vco_cf40_v14')
p=B/'lc_vco_cf40_v14.scs';assert not p.exists();p.write_text(src)
tb=(H/'tb/vco_noise_check6_tt.scs').read_text().replace('lc_vco_physical_v14','lc_vco_cf40_v14')
p=H/'tb/vco_bias_cf40_tt.scs';assert not p.exists();p.write_text(tb)
(H/'results/vco_bias_noise_protocol.json').write_text(json.dumps(dict(scope=__doc__,
    case=p.stem,planned_run='vcocf40_01',source_core_sha256=hashlib.sha256(core.read_bytes()).hexdigest(),
    source_vco_sha256=hashlib.sha256(vco.read_bytes()).hexdigest(),status='prepared_not_run',
    change='Only bias filter CF10pF->40pF; R1Mohm and all transistor sizes unchanged.',
    conditions='TT27/1.2V/Q5RLC,coarse23/control0.679V,actual fixedM4 chain/10fF,referenceDC0,onlyXVnoise;0.5ps/255sidebands,fresh autonomousPSS.',
    offsets_hz=[1e4,1e5,1e6,1e7,1e8,492e6],
    hypothesis='At high offsets, resistor contribution falls roughly16x if loading and operating point are unchanged. No simulated improvement yet.',
    risks=['Bias RC nominal time constant increases10us->40us; power-up settling must be checked.',
           'No integrated free-running or PLL jitter can be inferred from six frequency points.',
           'FixedM4/static-reference fixture omits full programmable and active sampling loads.'],
    main_dut_modified=False,full_pll_acceptance=False),indent=2)+'\n')
print(p.stem)
