"""Noise-first CMOS retimer/output sizing experiment, not a main-DUT change.

TT27,1.2V,984MHz/10fF; actual RX and full divider, external measured RF replay.
Baseline attribution has the output buffers and retimer dominating local jitter.
Scale their widths and diffusions together; retain actual clock/data loading.
Power is recorded but is not an optimization gate in this experiment.
"""
from pathlib import Path
import json,hashlib,re
H=Path(__file__).resolve().parent;B=H.parents[1]/'blocks/cmos_v14_full'
base=(H/'tb/chain_noise_coarse_tt.scs').read_text()
cells=[]
for factor in [2,4]:
 name=f'rt_noise_scale{factor}_v14'
 cell=f'''simulator lang=spectre
subckt {name} (data clk out vdd vss)
XFF (data clk qb vdd vss) rtcomb_ff_v13 scale={1.2*factor:g}
X0 (qb ob vdd vss) pll_inv wn={3*factor:g}u wp={.5*factor:g}u
X1 (ob out vdd vss) pll_inv wn={.8*factor:g}u wp={3*factor:g}u
ends {name}
'''
 (B/(name+'.scs')).write_text(cell)
 s=base.replace('rt_light24s12_out083_v14',name)
 s=s.replace('dec=10','dec=20')
 s=s.replace('writefinal="__FINAL_STATE__"','writefinal="__FINAL_STATE__" writepss="__PERIODIC_STATE__"')
 # Retain the requested upper endpoint; finite-offset alias tests remain necessary.
 s+='save XR.qb XR.ob\n'
 dest=H/'tb'/f'chain_rtscale{factor}_tt.scs';dest.write_text(s)
 cells.append(dict(case=dest.stem,factor=factor,netlist_sha256=hashlib.sha256(s.encode()).hexdigest()))
(H/'results/rt_noise_scaling_protocol.json').write_text(json.dumps(dict(scope=__doc__,cases=cells,full_pll_acceptance=False,main_dut_modified=False,band_hz=[1e4,492e6],pending=['PSS functional checks','actual device PSD integral','noise-on attribution','alias/edge/step convergence','closed-loop loading and PVT']),indent=2)+'\n')
print([x['case'] for x in cells])
