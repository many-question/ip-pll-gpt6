"""Generate project-owned differential Johnson divider and physical interface trials."""
from pathlib import Path
import json
from build_receiver import head
HERE=Path(__file__).resolve().parent
BLOCKS=HERE.parents[1]/'blocks/transistor_v2'

def mos(name,d,g,s,b,kind,w,l='180n'):
    return f'{name} ({d} {g} {s} {b}) {kind} w={w} l={l} ad={w}*240n as={w}*240n pd=2*({w}+240n) ps=2*({w}+240n)'

def build_cells():
    lines=['simulator lang=spectre', '// Device sizes and bias scale together; R scales inversely.',
           'subckt tx_cml_latch_v2 (dp dn cp cn qp qn nb reset vdd vss)',
           'parameters scale=.25 rload=2000',
           'RP (vdd qp) resistor r=rload/scale','RN (vdd qn) resistor r=rload/scale']
    for name,d,g,s,w in [('DP','qn','dp','st',8),('DN','qp','dn','st',8),('HP','qn','qp','ht',8),('HN','qp','qn','ht',8),('CS','st','cp','tail',10),('CH','ht','cn','tail',10),('T','tail','nb','vss',10)]:
        lines.append(mos('M'+name,d,g,s,'vss','nch',f'{w}u*scale','1u' if name=='T' else '180n'))
    lines += [mos('MR','qp','reset','vss','vss','nch','1u'), 'ends tx_cml_latch_v2',
              'subckt tx_johnson (cp cn reset s2 s3 s4 s5 s6 s7 op on vdd vss)',
              'parameters scale=.25 ibias=30u rload=2000',
              'CCP (cp ckp) capacitor c=500f','CCN (cn ckn) capacitor c=500f',
              'RBP (ckp cm) resistor r=50k','RBN (ckn cm) resistor r=50k',
              'RHI (vdd cm) resistor r=25k','RLO (cm vss) resistor r=50k','CB (cm vss) capacitor c=1p',
              'IREF (vdd nb) isource dc=ibias*scale',
              mos('MB','nb','nb','vss','vss','nch','2u*scale','1u')]
    for i in range(7):
        dp,dn=('on','op') if i==0 else (f'q{i-1}p',f'q{i-1}n')
        lines += [f'XM{i} ({dp} {dn} ckp ckn m{i}p m{i}n nb reset vdd vss) tx_cml_latch_v2 scale=scale rload=rload',
                  f'XS{i} (m{i}p m{i}n ckn ckp q{i}p q{i}n nb reset vdd vss) tx_cml_latch_v2 scale=scale rload=rload']
    for n in range(2,8):
        lines += [f'XI{n} (s{n} sb{n} vdd vss) pll_inv wn=300n wp=750n',
                  f'XP{n} (q{n-1}p op s{n} sb{n} vdd vss) pll_tg wn=300n wp=600n',
                  f'XN{n} (q{n-1}n on s{n} sb{n} vdd vss) pll_tg wn=300n wp=600n']
    lines+=['ends tx_johnson','',
            'subckt tx_ac_receiver_v2 (ip out vdd vss)', 'parameters wn=600n ratio=2.5 cc=100f',
            'C0 (ip a) capacitor c=cc','R0 (a b) resistor r=50k',
            'X0 (a b vdd vss) pll_inv wn=wn wp=wn*ratio',
            'C1 (b c) capacitor c=cc','R1 (c d) resistor r=50k',
            'X1 (c d vdd vss) pll_inv wn=wn wp=wn*ratio',
            'X2 (d e vdd vss) pll_inv wn=1u wp=2.5u',
            'X3 (e out vdd vss) pll_inv wn=3u wp=7.5u','ends tx_ac_receiver_v2']
    (BLOCKS/'divider_v2.scs').write_text('\n'.join(lines)+'\n')

def main():
    build_cells()
    for corner,temp in [('ss',60),('tt',27)]:
        lines=[head(corner,temp),'include "divider_v2.scs"',
               'VP (cp 0) vsource type=sine dc=1.2 ampl=.2 freq=4G',
               'VN (cn 0) vsource type=sine dc=1.2 ampl=.2 freq=4G sinephase=180',
               'VR (rst 0) vsource type=pulse val0=1.2 val1=0 delay=5n rise=20p fall=20p width=1u period=2u']
        save=['cp','cn','rst']
        params=[(scale,n) for scale in [.25,.5,1.] for n in [2,7]]
        for i,(scale,n) in enumerate(params):
            sels=' '.join('vdd'+str(i) if k==n else '0' for k in range(2,8))
            lines += [f'VD{i} (vdd{i} 0) vsource dc=1.2',
                      f'X{i} (cp cn rst {sels} p{i} n{i} vdd{i} 0) tx_johnson scale={scale}',
                      f'XP{i} (p{i} o{i} vdd{i} 0) tx_ac_receiver_v2',f'CL{i} (o{i} 0) capacitor c=10f']
            save +=[f'p{i}',f'n{i}',f'o{i}',f'VD{i}:p']
        lines+=['tran tran stop=150n maxstep=5p errpreset=conservative','save '+' '.join(save),'saveOptions options save=selected']
        (HERE/'tb'/f'tb_johnson_grid_{corner}.scs').write_text('\n'.join(lines)+'\n')
    (HERE/'results/johnson_grid_parameters.json').write_text(json.dumps(params,indent=2)+'\n')
    for corner,temp in [('ss',60),('tt',27)]:
        lines=[head(corner,temp),'include "divider_v2.scs"','VP (ip 0) vsource type=sine dc=1.05 ampl=.08 freq=2G']
        params=[(wn,ratio) for wn in [.3,.6,1.2,2.4] for ratio in [1.5,2.5,4.]]
        save=[]
        for i,(wn,ratio) in enumerate(params):
            lines += [f'VD{i} (vdd{i} 0) vsource dc=1.2', f'X{i} (ip o{i} vdd{i} 0) tx_ac_receiver_v2 wn={wn}u ratio={ratio}',f'CL{i} (o{i} 0) capacitor c=10f']
            save += [f'o{i}',f'VD{i}:p']
        lines+=['tran tran stop=100n maxstep=5p errpreset=conservative','save '+' '.join(save),'saveOptions options save=selected']
        (HERE/'tb'/f'tb_ac_receiver_grid_{corner}.scs').write_text('\n'.join(lines)+'\n')
    (HERE/'results/ac_receiver_grid_parameters.json').write_text(json.dumps(params,indent=2)+'\n')
if __name__=='__main__':main()
