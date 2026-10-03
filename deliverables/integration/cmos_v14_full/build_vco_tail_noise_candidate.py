"""Target measured tail flicker noise, preserving the nominal MT W/L ratio.

This candidate is separate from the main PLL. Only MT dimensions and its
declared diffusion geometry change relative to the CF40pF noise fixture.
"""
from pathlib import Path
import hashlib
import json

H=Path(__file__).resolve().parent; B=H.parents[1]/'blocks/cmos_v14_full'
evidence=json.loads((H/'results/vco_bias_noise_validation.json').read_text())
assert evidence['comparable_operating_point']
fraction=evidence['candidate']['selected_device_components']['XV.XL.MT']['fraction_of_output_psd']['fn'][2]
assert fraction>.1
core=B/'lc_core_cf40_v14.scs'; source=core.read_text()
old='MT (tail nfilt vss vss) nch w=300u l=1u ad=300u*240n as=300u*240n pd=2*(300u+240n) ps=2*(300u+240n)'
new='MT (tail nfilt vss vss) nch w=600u l=2u ad=600u*240n as=600u*240n pd=2*(600u+240n) ps=2*(600u+240n)'
assert source.count(old)==1
target=B/'lc_core_cf40_tail2_v14.scs'; assert not target.exists()
target.write_text(source.replace(old,new).replace('lc_core_cf40_v14','lc_core_cf40_tail2_v14'))
vco=B/'lc_vco_cf40_v14.scs'
dest=B/'lc_vco_cf40_tail2_v14.scs'; assert not dest.exists()
dest.write_text(vco.read_text().replace('lc_core_cf40_v14','lc_core_cf40_tail2_v14').replace('lc_vco_cf40_v14','lc_vco_cf40_tail2_v14'))
tb=H/'tb/vco_bias_cf40_tt.scs'; p=H/'tb/vco_bias_cf40_tail2_tt.scs'; assert not p.exists()
p.write_text(tb.read_text().replace('lc_vco_cf40_v14','lc_vco_cf40_tail2_v14'))
out=dict(scope=__doc__,planned_run='vcotail2_01',case=p.stem,
         base_core_sha256=hashlib.sha256(core.read_bytes()).hexdigest(),
         measured_cf40_mt_flicker_fraction_at_1mhz=fraction,
         geometric_hypothesis='Gate area x4 may reduce intrinsic flicker noise. Actual model, capacitance, drain swing and operating-point changes require simulation; W/L preservation is not a guarantee of equal current.',
         condition='Same fresh autonomous PSS and six offsets as vcocf40_01, TT27/1.2V/Q5/10fF/fixedM4/static reference.',
         source_state_reused=False,main_dut_modified=False,full_pll_acceptance=False,
         pending=['Check exact physical delta','Compare carrier, current, frequency and periodic solution','Measure thermal/flicker output contributions','Bias startup and actual PLL/PVT'])
(H/'results/vco_tail_noise_protocol.json').write_text(json.dumps(out,indent=2)+'\n')
print(p.stem)
