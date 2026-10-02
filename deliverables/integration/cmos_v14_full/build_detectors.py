"""Physical phase-window and RF-envelope qualification, with negative TB cases."""
from pathlib import Path
import numpy as np
H=Path(__file__).resolve().parent;B=H.parents[1]/'blocks/cmos_v14_full'
def m(n,t,d,g,s,b,w,l):return f'{n} ({d} {g} {s} {b}) {t} w={w} l={l} ad={w}*240n as={w}*240n pd=2*({w}+240n) ps=2*({w}+240n)'
s=['simulator lang=spectre','// Static MOS comparator; output high when vp>vn. Bias resistor is explicit.',
 'subckt cmp_physical_v14 (vp vn out vdd vss)',
 'RB (vdd nb) resistor r=100k',m('MB','nch','nb','nb','vss','vss','1u','1u'),
 m('MT','nch','tail','nb','vss','vss','2u','1u'),m('MP','nch','left','vp','tail','vss','1u','500n'),m('MN','nch','sense','vn','tail','vss','1u','500n'),
 m('PL','pch','left','left','vdd','vdd','2u','1u'),m('PR','pch','sense','left','vdd','vdd','2u','1u'),
 'XI0 (sense inv vdd vss) pll_inv wn=0.5u wp=1.25u','XI1 (inv out vdd vss) pll_inv wn=1u wp=2.5u','ends cmp_physical_v14',
 'subckt validity_physical_v14 (rf hp hn amp_good phase_good vdd vss)',
 '// MOS diode envelope and matched DC replica; finite RC decay rejects stopped RF.',
 m('MD','nch','rf','rf','env','vss','0.5u','180n'), 'RE (env vss) resistor r=1Meg','CE (env vss) capacitor c=50f',
 m('MR','nch','vdd','vdd','envref','vss','0.5u','180n'),'RR (envref vss) resistor r=1Meg',
 'RT0 (envref threshold) resistor r=10Meg','RT1 (threshold vdd) resistor r=90Meg',
 'XA (env threshold amp_good vdd vss) cmp_physical_v14',
 '// Window centered around held hn; approximately +/-60mV at0.6V common mode.',
 'RH0 (hn wh) resistor r=1Meg','RH1 (wh vdd) resistor r=9Meg','RL0 (hn wl) resistor r=1Meg','RL1 (wl vss) resistor r=9Meg',
 'XH (wh hp upper_ok vdd vss) cmp_physical_v14','XL (hp wl lower_ok vdd vss) cmp_physical_v14',
 'XW (upper_ok lower_ok window_ok vdd vss) tx_and','XG (window_ok amp_good phase_good vdd vss) tx_and','ends validity_physical_v14']
(B/'validity_physical_v14.scs').write_text('\n'.join(s)+'\n')
model='/home/process/tsmc180bcd_gen2_2022/PDK/TSMC180BCD/models/spectre/c018bcd_gen2_v1d6.scs'
t=np.arange(0,1.8001e-6,1/(3936e6*8));amp=np.where((t>=.2e-6)&(t<1.2e-6),.35,0);rf=1.2+amp*np.sin(2*np.pi*3936e6*t)
wave=' '.join(f'{tt:.12g} {vv:.12g}' for tt,vv in zip(t,rf))
for c,temp in [('tt',27),('ss',60),('ff',0)]:
 tb=[f'simulator lang=spectre\nglobal 0\ninclude "{model}" section={c}',f'include "{model}" section=stat_noise','simulator lang=spectre insensitive=no','include "cells.scs"','include "digital_cells_v2.scs"','include "validity_physical_v14.scs"',f'simulatorOptions options temp={temp} reltol=1e-5 vabstol=1e-7 iabstol=1e-13','VDD (vdd 0) vsource dc=1.2',f'VRF (rf 0) vsource type=pwl wave=[{wave}]',
 'VP (hp 0) vsource type=pwl wave=[0 .6 600n .6 600.1n .8 800n .8 800.1n .4 1u .4 1.0001u .6]',
 'VN (hn 0) vsource dc=.6','XDET (rf hp hn amp_good phase_good vdd 0) validity_physical_v14',
 'tran tran stop=1.8u maxstep=5p strobeperiod=1n strobeoutput=strobeonly method=traponly errpreset=conservative',
 'save hp hn amp_good phase_good XDET.env XDET.threshold XDET.envref XDET.upper_ok XDET.lower_ok VDD:p','saveOptions options save=selected']
 (H/'tb'/f'detector_{c}.scs').write_text('\n'.join(tb)+'\n')
print('Built detectors and three TBs')
