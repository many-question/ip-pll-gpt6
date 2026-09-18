"""Attach real decoded configuration to the established MOS divider bank."""
from pathlib import Path
import sys
H=Path(__file__).resolve().parent
sys.path.insert(0,str(H.parent/'transistor_v2'))
from build_receiver import head
def main():
 for k,m in [(41,4),(27,6),(18,8),(13,10),(11,12),(9,14)]:
  f=24e6*k*m
  s=[head().replace('reltol=1e-5','reltol=1e-4'),'include "digital_cells_v2.scs"','include "pll_config.scs"','include "divider_v2.scs"','include "limiter_chain.scs"','include "bank_divider_light.scs"',
     'VDD (vdd 0) vsource dc=1.2',
     f'VP (vp 0) vsource type=sine dc=1.0 ampl=.2 freq={f}',
     f'VN (vn 0) vsource type=sine dc=1.0 ampl=.2 freq={f} sinephase=180',
     'VR (ref 0) vsource type=pulse val0=0 val1=1.2 delay=10n rise=50p fall=50p width=20.7833333333n period=41.6666666667n',
     'VRESET (reset 0) vsource type=pulse val0=1.2 val1=0 delay=20n rise=50p fall=50p width=1m period=2m',
     'VAPPLY (apply 0) vsource type=pulse val0=0 val1=1.2 delay=60n rise=50p fall=50p width=300n period=2u']
  s += [f'VK{i} (k{i} 0) vsource dc={1.2 if k&(1<<i) else 0}' for i in range(6)]
  s += ['XC (ref reset apply '+' '.join(f'k{i}' for i in range(6))+' '+' '.join(f'ak{i}' for i in range(6))+' '+' '.join(f's{i}' for i in range(6))+' ready invalid rst vdd 0) tx_pll_config',
        'XD (vp vn rst s0 s1 s2 s3 s4 s5 out vdd 0) tx_divider_bank_light',
        'CL (out 0) capacitor c=10f',
        'tran tran stop=800n maxstep=10p errpreset=moderate',
        'save ref apply reset rst ready invalid out VDD:p '+' '.join(f's{i}' for i in range(6)),
        'saveOptions options save=selected']
  (H/'tb'/f'tb_config_divider_m{m}.scs').write_text('\n'.join(s)+'\n')
if __name__=='__main__':main()
