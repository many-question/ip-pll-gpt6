from pathlib import Path
import sys
H=Path(__file__).resolve().parent
sys.path.insert(0,str(H.parent/'transistor_v2'))
from build_receiver import head
def main():
 for c,tmp in [('tt',27),('ss',60)]:
  s=[head(c,tmp).replace('reltol=1e-5 vabstol=1e-7 iabstol=1e-13','reltol=1e-3 vabstol=1e-5 iabstol=1e-12')]
  s += [f'include "{n}.scs"' for n in ['digital_cells_v2','fll_circuit','pll_config','pll_supervisor','cp_timing','pll_control_frontend']]
  s += ['VDD (vdd 0) vsource dc=1.2',
        'VREF (refclk 0) vsource type=pulse val0=0 val1=1.2 delay=10n rise=50p fall=50p width=20.7833333333n period=41.6666666667n',
        'VR (reset 0) vsource type=pulse val0=1.2 val1=0 delay=20n rise=50p fall=50p width=1m period=2m',
        'VA (apply 0) vsource type=pulse val0=0 val1=1.2 delay=60n rise=50p fall=50p width=300n period=2u',
        ]
  # Stop at a completed pulse, then drain the ripple before reading the bus.
  # Continuous asynchronous-bus strobing is not a valid counter measurement.
  points=[(0,0)];n=0
  while True:
   t=20.25e-9+n*1.0162601626e-9
   if t>1.25e-6:break
   points.extend([(t,0),(t+20e-12,1.2),(t+508.13e-12,1.2),(t+528.13e-12,0)]);n+=1
  s+=['VC (outclk 0) vsource type=pwl wave=['+' '.join(f'{t:.14g} {v}' for t,v in points)+']']
  s += [f'VK{i} (k{i} 0) vsource dc={1.2 if 41&(1<<i) else 0}' for i in range(6)]
  s += ['XC (refclk reset apply '+' '.join(f'k{i}' for i in range(6))+' outclk 0 0 '+' '.join(f'b{i}' for i in range(8))+' '+' '.join(f's{i}' for i in range(6))+' divider_reset enable pulse preset qualified range_error config_ready config_invalid restart count_gate count_reset vdd 0) tx_pll_control_frontend',
        'XLF (ctrl vc1 enable preset vdd 0) tx_loop_filter rlf=100k',
        'tran tran stop=1.4u maxstep=50p method=gear2only errpreset=moderate strobeperiod=20p strobeoutput=strobeonly',
        'save outclk XC.XCOUNT.gclk config_ready config_invalid divider_reset enable pulse qualified range_error restart count_gate count_reset preset ctrl VDD:p '+' '.join(f'XC.q{i}' for i in range(14))+' '+' '.join(f'b{i}' for i in range(8))+' '+' '.join(f's{i}' for i in range(6)),
        'saveOptions options save=selected']
  (H/'tb'/f'tb_control_frontend_{c}.scs').write_text('\n'.join(s)+'\n')
if __name__=='__main__':main()
