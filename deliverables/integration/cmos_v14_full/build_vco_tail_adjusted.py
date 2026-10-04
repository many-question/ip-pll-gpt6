"""Reduce the enlarged tail width to test its observed operating-point shift.

The earlier 600um/2um tail increased VCO supply current by about 7.2 percent.
560um/2um is a measured-current-informed trial, not an assertion of matched
current or frequency. The base300um/1um and previous600um/2um remain intact.
"""
from pathlib import Path
import datetime,hashlib,json
H=Path(__file__).resolve().parent;B=H.parents[1]/'blocks/cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
old=B/'lc_core_cf40_tail2_v14.scs';body=old.read_text()
line='MT (tail nfilt vss vss) nch w=600u l=2u ad=600u*240n as=600u*240n pd=2*(600u+240n) ps=2*(600u+240n)'
assert body.count(line)==1
name='lc_core_cf40_tail560_v14'
body=body.replace(line,line.replace('600u','560u')).replace('lc_core_cf40_tail2_v14',name)
dest=B/(name+'.scs');assert not dest.exists();dest.write_text(body)
src=B/'lc_vco_cf40_tail2_v14.scs';vco=B/'lc_vco_cf40_tail560_v14.scs';assert not vco.exists()
vco.write_text(src.read_text().replace('lc_core_cf40_tail2_v14',name).replace('lc_vco_cf40_tail2_v14','lc_vco_cf40_tail560_v14'))
tbsource=H/'tb/vco_bias_cf40_tail2_tt.scs';case='vco_bias_cf40_tail560_tt';tb=H/'tb'/(case+'.scs');assert not tb.exists()
tb.write_text(tbsource.read_text().replace('lc_vco_cf40_tail2_v14','lc_vco_cf40_tail560_v14'))
proof=H/'results/vco_tail_noise_validation.json';e=json.loads(proof.read_text())
ratio=e['candidate']['vco_supply_power_mw']/e['baseline']['vco_supply_power_mw']
p=dict(scope=__doc__,run='vcotail560_01',case=case,time=datetime.datetime.now().astimezone().isoformat(),
    prior_validation_sha256=sha(proof),prior_supply_current_ratio=ratio,
    inverse_current_width_estimate_um=600/ratio,selected_width_um=560,length_um=2,
    physical_change='Only MT width/diffusion geometry600um->560um from the earlier600um/2um candidate; CF40, MR and remaining circuits unchanged.',
    source_tb_sha256=sha(tbsource),tb_sha256=sha(tb),core_sha256=sha(dest),vco_sha256=sha(vco),
    condition='TT27/1.2V/Q5RLC/coarse23/ctrl.679V/CF40/static-reference/fixedM4/10fF/onlyXVnoise/freshPSS .5ps255sidebands.',
    hypothesis='Recover some of the current/carrier shift while retaining a larger tail area. Actual operating point and noise must be measured.',
    offsets_hz=[1e4,1e5,1e6,1e7,1e8,492e6],main_dut_modified=False,full_pll_acceptance=False,
    limitations=['Six offsets do not establish RMS.','Width estimate uses total VCO supply current, not isolated MT DC current; equal-current matching is not presumed.','No target-frequency rematch or fullPLL/PVT validation.','CF40 all-band precision still pending independently.'])
(H/'results/vco_tail_adjusted_protocol.json').write_text(json.dumps(p,indent=2)+'\n');print(case,ratio)
