"""Loaded oscillator endpoint evidence for the new physical bias; not PLL lock."""
from pathlib import Path
import re
H=Path(__file__).resolve().parent
for corner in ['tt','ss','ff']:
 for code in [0,255]:
  for vc,label in [(.2,'02'),(1.,'10')]:
   s=(H/'tb'/f'bias_lc_r2500_{corner}.scs').read_text()
   s=re.sub(r'^VC .*$',f'VC (ctrl 0) vsource dc={vc}',s,flags=re.M)
   for i in range(8):s=re.sub(rf'^VB{i} .*$',f'VB{i} (b{i} 0) vsource dc={1.2 if code&(1<<i) else 0}',s,flags=re.M)
   s=s.replace('include "div_fb50buf24_v14.scs"','include "cmos_even_bank_acq_v14.scs"\ninclude "validity_physical_v14.scs"')
   pins='vdd 0 0 0 0 0' if code==0 else '0 0 0 0 0 vdd'
   s=s.replace('XD (clk q1 data vdd 0) div_fb50buf24_v14',f'VDRESET (div_reset 0) vsource type=pwl wave=[0 1.2 20n 1.2 20.01n 0]\nXD (clk div_reset {pins} q1 data acqclk vdd 0) cmos_even_bank_acq_v14\nXDET (vp hp hn amp_good phase_good vdd 0) validity_physical_v14')
   s+='\nsave amp_good phase_good acqclk\n'
   (H/'tb'/f'range_c{code}_v{label}_{corner}.scs').write_text(s)
print('Built12 loaded new-bias endpoints; fixed-code/control, not PLL lock')
