"""Real sampler plus validity comparator and falling-edge qualification FF.

Input RF/reference are ideal TB stimuli; no phase-good stimulus drives DUT.
"""
from pathlib import Path
H=Path(__file__).resolve().parent
MODEL='/home/process/tsmc180bcd_gen2_2022/PDK/TSMC180BCD/models/spectre/c018bcd_gen2_v1d6.scs'
for c,temp in [('tt',27),('ss',60),('ff',0)]:
 for phase in [0,45,90,135,180,225,270,315]:
  s=[f'simulator lang=spectre\nglobal 0\ninclude "{MODEL}" section={c}',
     f'include "{MODEL}" section=stat_noise','simulator lang=spectre insensitive=no',
     'include "cells.scs"','include "digital_cells_v2.scs"','include "validity_physical_v14.scs"',
     f'simulatorOptions options temp={temp} reltol=1e-5 vabstol=1e-7 iabstol=1e-13',
     'VDD (vdd 0) vsource dc=1.2',
     f'VRF (rf 0) vsource type=sine dc=1.2 ampl=.35 freq=3936M sinephase={phase}',
     f'VSP (sp 0) vsource type=sine dc=.6 ampl=.2 freq=3936M sinephase={phase}',
     f'VSN (sn 0) vsource type=sine dc=.6 ampl=.2 freq=3936M sinephase={phase+180}',
     'VREF (ref 0) vsource type=pulse val0=0 val1=1.2 period=41.6666666666667n width=20.8233333333333n rise=10p fall=10p delay=1n',
     'VRST (reset 0) vsource type=pwl wave=[0 1.2 80n 1.2 80.01n 0]',
     'XS (ref sp sn hp hn vdd 0) tx_sampler',
     'XDET (rf hp hn amp_good phase_good vdd 0) validity_physical_v14',
     'XC (ref ref_fall vdd 0) pll_inv',
     'XPH (phase_good ref_fall reset phase_held vdd 0) tx_dff_r0',
     'tran tran stop=350n maxstep=2p strobeperiod=100p strobeoutput=strobeonly method=traponly errpreset=conservative',
     'save ref ref_fall hp hn amp_good phase_good phase_held XDET.wh XDET.wl VDD:p',
     'saveOptions options save=selected']
  (H/'tb'/f'phasehold_p{phase}_{c}.scs').write_text('\n'.join(s)+'\n')
print('Built24 phase-hold timing fixtures')
