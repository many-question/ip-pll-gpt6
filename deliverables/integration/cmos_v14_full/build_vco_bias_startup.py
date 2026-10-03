"""Extract actual MOS bias charging; static tail clamp is a diagnostic boundary.

Both bias references and mirror gates retain their devices/geometry. The RF
tail voltage is held at its measured CF40 mean instead of simulating hundreds
of microseconds of RF. This does not prove oscillator or PLL power-up.
"""
from pathlib import Path
import json
import numpy as np
from noise_utils import parse
H=Path(__file__).resolve().parent;ROOT=H.parents[3];B=H.parents[1]/'blocks/cmos_v14_full'
td=parse(ROOT/'research/runs/spectre_cmos_v14_full/vcocf40_01/vco_bias_cf40_tt/vco_bias_cf40_tt.raw/pss.td.pss')
t=td['time'];tail=float(np.trapezoid(td['XV.XL.tail'],t)/(t[-1]-t[0]))
source=(B/'lc_core_physical_v14.scs').read_text()
rows=[line for line in source.splitlines() if line.startswith(('MT ','MR ','RREF ','RF ','CF ','MA','ME'))]
assert len(rows)==15,len(rows)
net='simulator lang=spectre\nsubckt vco_bias_gate_start_v14 (tail b3 b4 b5 b6 b7 vdd vss)\nparameters bias_r=2500 boost_unit=5u filter_c=10p\n'
net+='\n'.join(rows).replace('CF (nfilt vss) capacitor c=10p','CF (nfilt vss) capacitor c=filter_c')
net+='\nends vco_bias_gate_start_v14\n'
p=B/'vco_bias_gate_start_v14.scs';assert not p.exists();p.write_text(net)
tb=f'''simulator lang=spectre
global 0
include "/home/process/tsmc180bcd_gen2_2022/PDK/TSMC180BCD/models/spectre/c018bcd_gen2_v1d6.scs" section=tt
simulator lang=spectre insensitive=no
include "vco_bias_gate_start_v14.scs"
simulatorOptions options temp=27 reltol=1e-5 vabstol=1e-7 iabstol=1e-13
VDD (vdd 0) vsource dc=0 type=pwl wave=[0 0 100n 0 110n 1.2]
VT (tail 0) vsource dc=0 type=pwl wave=[0 0 100n 0 110n {tail:.16g}]
X10 (tail 0 vdd 0 0 0 vdd 0) vco_bias_gate_start_v14 filter_c=10p
X40 (tail 0 vdd 0 0 0 vdd 0) vco_bias_gate_start_v14 filter_c=40p
tran tran stop=400u maxstep=50n method=traponly errpreset=conservative writefinal="__FINAL_STATE__"
save vdd tail X10.nb X10.nfilt X40.nb X40.nfilt X10.MT:d X40.MT:d
saveOptions options save=selected
'''
p=H/'tb/vco_bias_gate_start_tt.scs';assert not p.exists();p.write_text(tb)
(H/'results/vco_bias_startup_protocol.json').write_text(json.dumps(dict(scope=__doc__,run='vcobiasstart01',case=p.stem,
    conditions='TT27,0-to1.2V in10ns at100ns,coarse23 bias boost,400us/50ns maxstep,actual MOS reference/mirror gates.',
    static_tail_clamp_v=tail,full_pll_acceptance=False,oscillator_startup_verified=False),indent=2)+'\n')
print(p.stem,'tail clamp',tail)
