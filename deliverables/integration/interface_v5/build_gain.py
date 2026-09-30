"""Replay measured tank shape as a noiseless RF source for detector characterization.

This fixture retains the physical sampler, AC input network, reference buffer and
CP pulser. It does not reproduce VCO source impedance, back-action, or loop noise.
"""
from pathlib import Path
import argparse,hashlib,json,re
import numpy as np
from analyze import H,R,cross,load_data
ap=argparse.ArgumentParser();ap.add_argument('--phases',nargs='+',type=float,default=list(range(0,360,60)));ap.add_argument('--clamp',type=float,default=.6);ap.add_argument('--prefix',default='gain');a=ap.parse_args()
p=R/'calibration_fine/cal_fine/waveforms.npz';d=load_data(p);t=d['time'];sel=(t>480e-9)&(t<530e-9)
edges=cross(t[sel],(d['vp']-d['vn'])[sel]);waves={}
for node in ['vp','vn']:
 shapes=[np.interp(e0+np.arange(128)/128*(e1-e0),t,d[node]) for e0,e1 in zip(edges[:16],edges[1:17])]
 waves[node]=np.mean(shapes,axis=0)
lines=['`include "disciplines.vams"','`include "constants.vams"','// Measured waveform replay, testbench only; ideal drive has no VCO impedance.','module tank_waveform_v5(vp,vn,vss);','output vp,vn; input vss; electrical vp,vn,vss;','parameter real phase_deg=0; parameter real frequency=3.936G;','real theta;','analog begin',' theta=2*`M_PI*frequency*$abstime+phase_deg*`M_PI/180;']
data={}
for node,y in waves.items():
 coeff=np.fft.rfft(y)/len(y);expr=f'{coeff[0].real:.16g}'
 for k in range(1,21):expr+=f'+({2*coeff[k].real:.16g})*cos({k}*theta)+({-2*coeff[k].imag:.16g})*sin({k}*theta)'
 lines.append(f' V({node},vss)<+{expr};')
 reconstructed=np.fft.irfft(np.r_[coeff[:21],np.zeros(len(coeff)-21)]*128,n=128)
 data[node]=dict(dc_v=float(coeff[0].real),pp_v=float(np.ptp(y)),max_reconstruction_error_v=float(np.max(abs(reconstructed-y))))
lines+=['end','endmodule']
(H.parents[1]/'blocks/interface_v5/tank_waveform_v5.va').write_text('\n'.join(lines)+'\n')
data.update(source=str(p.relative_to(R.parent.parent.parent)).replace('\\','/'),source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),cycles_averaged=16,control_v=.85,condition='Ideal replay source at 3.936 GHz, periodic shape averaged from real loaded transient. No source impedance or back-action.')
(H/'results/gain_source.json').write_text(json.dumps(data,indent=2)+'\n')
s=(H/'tb/timing_both.scs').read_text()
s='\n'.join(x for x in s.splitlines() if not re.match(r'^(VVCO|VC |VB[0-7]|XV |XD |CL |VRST |ic |tran |save |saveOptions)',x))+'\n'
s+='VRST (rst 0) vsource dc=0\n'
s+='ahdl_include "tank_waveform_v5.va"\nXRF (vp vn 0) tank_waveform_v5 phase_deg=PHASE\n'
s+='pss pss fund=24M harms=4 tstab=350n maxstep=2p method=traponly errpreset=conservative saveinit=no\n'
s+='save vp vn hp hn sp sn refb pulse VO:p VDD:p\nsaveOptions options save=selected\n'
s=s.replace('VO (cpout 0) vsource dc=.6',f'VO (cpout 0) vsource dc={a.clamp}')
for phase in a.phases:
 name=a.prefix+'_p'+f'{phase:.6f}'.rstrip('0').rstrip('.').replace('-','m').replace('.','d')
 (H/'tb'/f'{name}.scs').write_text(s.replace('PHASE',f'{phase:.12g}'))
 print(name)
