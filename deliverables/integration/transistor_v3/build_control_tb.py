from pathlib import Path
import sys,json
H=Path(__file__).resolve().parent
sys.path.insert(0,str(H.parent/'transistor_v2'))
from build_receiver import head
T=1/24e6

def pwl(node,points):
 return f'V{node} ({node} 0) vsource type=pwl wave=['+' '.join(f'{t:.14g} {v}' for t,v in points)+']'
def signal(node,events,initial=0):
 pts=[(0,1.2*initial)]
 for t,state in events:
  pts.extend([(t,pts[-1][1]),(t+50e-12,1.2*state)])
 return pwl(node,pts)
def base(c,temp):
 return [head(c,temp).replace('reltol=1e-5 vabstol=1e-7 iabstol=1e-13','reltol=1e-3 vabstol=1e-5 iabstol=1e-12'),'include "digital_cells_v2.scs"',
         'VDD (vdd 0) vsource dc=1.2',
         f'VREF (refclk 0) vsource type=pulse val0=0 val1=1.2 delay=10n rise=50p fall=50p width={T/2-50e-12} period={T}',
         signal('reset',[(100e-9,0)],1)]

def main():
 mapping=json.loads((H/'results/control_mapping.json').read_text())
 config=mapping[0]['ports'];supervisor=mapping[1]['ports']
 codes=list(range(64))+[41,9,28,18,27,10,13,14]
 schedule=[{'k':k,'time':200e-9+i*1e-6} for i,k in enumerate(codes)]
 (H/'results/config_stimulus.json').write_text(json.dumps(schedule,indent=2)+'\n')
 for corner,temp in [('tt',27),('ss',60),('ff',0)]:
  s=base(corner,temp)+['include "pll_config.scs"']
  for j in range(6):s.append(signal(f'cfg_k{j}',[(x['time']-50e-9,(x['k']>>j)&1) for x in schedule]))
  s.append(signal('apply',[(t,v) for x in schedule for t,v in [(x['time'],1),(x['time']+200e-9,0)]]))
  s+=['XD ('+' '.join(config)+' vdd 0) tx_pll_config']
  for n in ['divider_reset','ready']+[f'select_m{i}' for i in range(6)]:s.append(f'C{n} ({n} 0) capacitor c=20f')
  s+=['tran tran stop=72.5u maxstep=2n method=gear2only errpreset=moderate strobeperiod=2n strobeoutput=strobeonly',
      'save '+' '.join(config)+' VDD:p','saveOptions options save=selected']
  (H/'tb'/f'tb_config_{corner}.scs').write_text('\n'.join(s)+'\n')
  s=base(corner,temp)+['include "pll_supervisor.scs"',
    signal('cfg_ready',[(200e-9,1),(12e-6,0),(12.6e-6,1)]),
    signal('fll_enable',[(1e-6,1),(6.3e-6,0),(7e-6,1)]),
    signal('range_error',[(11e-6,1),(12e-6,0)]),
    signal('phase_good',[(1.5e-6,1),(4e-6,0),(4.075e-6,1),(6e-6,0),(7e-6,1)]),
    signal('frequency_good',[(500e-9,1),(9e-6,0),(9.5e-6,1)]),
    'XS ('+' '.join(supervisor)+' vdd 0) tx_pll_supervisor']
  for n in ['pll_enable','qualified','restart','fault']:s.append(f'C{n} ({n} 0) capacitor c=20f')
  s+=['tran tran stop=15u maxstep=2n method=gear2only errpreset=moderate strobeperiod=1n strobeoutput=strobeonly',
      'save '+' '.join(supervisor)+' VDD:p','saveOptions options save=selected']
  (H/'tb'/f'tb_supervisor_{corner}.scs').write_text('\n'.join(s)+'\n')
if __name__=='__main__':main()
