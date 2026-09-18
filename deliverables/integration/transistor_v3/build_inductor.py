"""Passive pi inductor model, Q fitted at 3.3 GHz. Not a foundry model."""
from pathlib import Path
import sys,json
import numpy as np
from scipy.optimize import brentq
H=Path(__file__).resolve().parent;B=H.parents[1]/'blocks/transistor_v3'
sys.path.insert(0,str(H.parent/'transistor_v2'))
from build_receiver import head,MODEL
L=2e-9;CW=20e-15;COX=80e-15;CSUB=50e-15;RSUB=300.;F0=3.3e9
def impedance(f,rs,cscale=1):
 w=2*np.pi*np.asarray(f)
 zsub=1/(1/RSUB+1j*w*CSUB*cscale)
 return 1/(1/(rs+1j*w*L)+1j*w*CW*cscale+1/(1/(1j*w*COX*cscale)+zsub))

def main():
 params=[]
 for q in [3,5,8]:
  rs=brentq(lambda r:impedance(F0,r).imag/impedance(F0,r).real-q,.1,40)
  params.append(dict(q_at_3p3ghz=q,rs_ohm=rs,l_h=L,cw_f=CW,cox_f=COX,csub_f=CSUB,rsub_ohm=RSUB))
 (H/'results/inductor_parameters.json').write_text(json.dumps(params,indent=2)+'\n')
 s='''simulator lang=spectre
// User-authorized preliminary model. Q=5 literature anchor; Q=3/8 sensitivity.
// No claim of TSMC180BCD foundry fit, geometry, coupling or EM extraction.
// p/n winding ports; sub is the grounded substrate, never a floating terminal.
subckt tx_inductor_pi (p n sub)
parameters ls=2n rs=7 cw=20f cox=80f csub=50f rsub=300
RW (p x) resistor r=rs
LW (x n) inductor l=ls
CW (p n) capacitor c=cw
COXP (p sp) capacitor c=cox
COXN (n sn) capacitor c=cox
RSP (sp sub) resistor r=rsub
RSN (sn sub) resistor r=rsub
CSP (sp sub) capacitor c=csub
CSN (sn sub) capacitor c=csub
ends tx_inductor_pi
'''
 (B/'inductor_pi.scs').write_text(s)
 core=(B.parent/'transistor_v2/lc_core_filtered_slow.scs').read_text()
 core=core.replace('tx_lc_core_filtered_slow','tx_lc_core_rlc').replace('tank_r=5','tank_r=7')
 start=core.index('RP (');end=core.index('CP (')
 core=core[:start]+'''XP (vdd vp vss) tx_inductor_pi ls=tank_l rs=tank_r cw=20f*cscale cox=80f*cscale csub=50f*cscale
XN (vdd vn vss) tx_inductor_pi ls=tank_l rs=tank_r cw=20f*cscale cox=80f*cscale csub=50f*cscale
'''+core[end:]
 core=core.replace('ibias=80u core_w=20u','ibias=80u core_w=20u cscale=1')
 core=core.replace('// Feasibility experiment, not a released VCO: tank R/L/C and reference current\n// are explicit assumptions. Core and current mirror use project PDK MOS devices.',
 '// Pi winding includes metal loss, winding capacitance and lossy substrate.\n// Fitted Q and all geometry remain explicitly provisional; IREF remains ideal.')
 (B/'lc_core_rlc.scs').write_text(core)
 vco=(B.parent/'transistor_v2/lc_vco_filtered_slow.scs').read_text().replace('lc_core_filtered_slow.scs','lc_core_rlc.scs').replace('tx_lc_vco_filtered_slow','tx_lc_vco_rlc').replace('tx_lc_core_filtered_slow','tx_lc_core_rlc')
 vco=vco.replace('include "lc_core_rlc.scs"','include "inductor_pi.scs"\ninclude "lc_core_rlc.scs"')
 vco=vco.replace('parameters fixed_c=190f','parameters fixed_c=190f series_r=7 cscale=1 core_w=40u ibias=80u')
 vco=vco.replace('tank_r=5 tank_c=fixed_c core_w=40u','tank_r=series_r tank_c=fixed_c core_w=core_w ibias=ibias cscale=cscale')
 (B/'lc_vco_rlc.scs').write_text(vco)
 for par in params:
  q=par['q_at_3p3ghz'];rs=par['rs_ohm']
  ac=['simulator lang=spectre','global 0','include "inductor_pi.scs"','VTEST (p 0) vsource dc=0 mag=1',f'XL (p 0 0) tx_inductor_pi rs={rs:.14g}',
      'ac ac start=10M stop=30G dec=60','save p VTEST:p','saveOptions options save=selected']
  (H/'tb'/f'tb_inductor_q{q}.scs').write_text('\n'.join(ac)+'\n')
  for code in [0,255]:
   for scale in ([1,.5,2] if q==5 else [1]):
    tag={1:'nom',.5:'clo',2:'chi'}[scale]
    s=[head(),f'include "{MODEL}" section=tt_bbmvar','simulator lang=spectre insensitive=no',
       'include "lc_vco_rlc.scs"','VDD (vdd 0) vsource dc=1.2','VC (ctrl 0) vsource dc=.6']
    s+=[f'VB{i} (b{i} 0) vsource dc={1.2 if code&(1<<i) else 0}' for i in range(8)]
    s+=[f'XV (vp vn ctrl b0 b1 b2 b3 b4 b5 b6 b7 vdd 0) tx_lc_vco_rlc series_r={rs:.14g} cscale={scale}',
        'ic vp=1.20001 vn=1.2',
        'tran tran stop=300n maxstep=5p errpreset=conservative',
        'save vp vn XV.XL.tail VDD:p','saveOptions options save=selected']
    (H/'tb'/f'tb_rlc_q{q}_c{code}_{tag}.scs').write_text('\n'.join(s)+'\n')
  # Noise comparison at the same devices, code and fixed capacitance as prior test.
  s='\n'.join(s) # Last transient template, replace code back to zero.
  for i in range(8):s=s.replace(f'VB{i} (b{i} 0) vsource dc=1.2',f'VB{i} (b{i} 0) vsource dc=0')
  s=s.replace('cscale=2','cscale=1')
  s=s.replace('tran tran stop=300n maxstep=5p errpreset=conservative',
      'pss (vp vn) pss fund=3.9G harms=31 tstab=300n maxstep=5p errpreset=conservative saveinit=yes\n'
      'pn (vp vn) pnoise start=10k stop=500M dec=20 maxsideband=31 noiseout=[usb am pm] sweeptype=relative relharmnum=1')
  (H/'tb'/f'tb_rlc_noise_q{q}.scs').write_text(s+'\n')
 print(params)
if __name__=='__main__':main()
