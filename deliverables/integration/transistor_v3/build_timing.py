"""MOS-only delayed pulse generator, real CP load, and paired-corner tests."""
from pathlib import Path
import sys
H=Path(__file__).resolve().parent
B=H.parents[1]/'blocks/transistor_v3'
sys.path.insert(0,str(H.parent/'transistor_v2'))
from build_receiver import head

def main():
 s=['simulator lang=spectre',
 '// Uncalibrated MOS propagation delay; all pulse timing is physical.',
 'subckt tx_cp_timing (ref enable reset pulse vdd vss)',
 'parameters delay_l=360n',
 'XI (ref refb vdd vss) pll_inv',
 'XR (reset resetb vdd vss) pll_inv',
 '// Clear the arm latch on reset; releasing reset during ref high cannot',
 '// create a late partial pulse. Re-arm only in the next ref-low interval.',
 'XE (enable refb ref resetb en_hold vdd vss) tx_latch_r']
 for i in range(24):
  a='ref' if i==0 else f'd{i}'
  s.append(f'XD{i} ({a} d{i+1} vdd vss) pll_inv wn=500n wp=1.25u ln=delay_l')
 s+=['XN (d24 d24b vdd vss) pll_inv',
     'XP (d12 d24b raw vdd vss) tx_and',
     'XS (raw ref held vdd vss) tx_and',
     'XEN (held en_hold enabled vdd vss) tx_and',
     'XRESET (enabled resetb pulse vdd vss) tx_and',
     'ends tx_cp_timing']
 (B/'cp_timing.scs').write_text('\n'.join(s)+'\n')
 for c,temp in [('tt',27),('ss',60),('ff',0)]:
  s=[head(c,temp),'include "digital_cells_v2.scs"','include "cp_timing.scs"','include "cp_experiment.scs"',
     'VDD (vdd 0) vsource dc=1.2',
     'VR (ref 0) vsource type=pulse val0=0 val1=1.2 delay=10n rise=50p fall=50p width=20.7833333333n period=41.6666666667n',
     'VE (enable 0) vsource type=pwl wave=[0 0 40n 0 40.05n 1.2 96n 1.2 96.05n 0 210n 0 210.05n 1.2]',
     'VRESET (reset 0) vsource type=pwl wave=[0 1.2 5n 1.2 5.05n 0 263n 0 263.05n 1.2 264n 1.2 264.05n 0]',
     'VP (hp 0) vsource dc=.6002','VN (hn 0) vsource dc=.6','VO (out 0) vsource dc=.6',
     'XT (ref enable reset pulse vdd 0) tx_cp_timing',
     'XP (hp hn pulse vdd out vdd 0) tx_cp_experiment',
     'tran tran stop=400n maxstep=20p errpreset=conservative',
     'save ref enable reset pulse XT.d12 XT.d24 XT.en_hold VO:p VDD:p',
     'saveOptions options save=selected']
  (H/'tb'/f'tb_cp_timing_{c}.scs').write_text('\n'.join(s)+'\n')
if __name__=='__main__':main()
