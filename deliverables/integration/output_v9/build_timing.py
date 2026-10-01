"""Measured raw-data replay for finite timing-perturbation diagnostics only."""
from analyze import H,R,ROOT
import argparse,datetime,hashlib,json,re
import numpy as np
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--case');ap.add_argument('--run');ap.add_argument('--tag');a=ap.parse_args()
 assert all([a.case,a.run,a.tag]) or not any([a.case,a.run,a.tag])
 cases=[(a.case,a.run,a.tag)] if a.case else [('cml1_s1_tt','cml','same'),('cml1_opp_s1_tt','phase','opp')]
 B=H.parents[1]/'blocks/output_v9';sources=[];f=984e6;T=1/f
 for case,run,tag in cases:
  p=R/run/case/'waveforms.npz';rec=json.loads((p.parent/'result.json').read_text());assert rec['ok'] and rec['remote_inputs_match']
  with np.load(p) as z:
   t=z['time'];grid=(96+np.linspace(0,1,8193))/f;theta=2*np.pi*f*grid;coeff={};err={};end={}
   for k in ['dp','dn']:
    y=np.interp(grid,t,z[k]);dc=float(np.trapezoid(y,grid)/T)
    cs=[float(2*np.trapezoid(y*np.cos(n*theta),grid)/T) for n in range(1,64)]
    sn=[float(2*np.trapezoid(y*np.sin(n*theta),grid)/T) for n in range(1,64)]
    fit=dc+sum(a*np.cos(n*theta)+b*np.sin(n*theta) for n,(a,b) in enumerate(zip(cs,sn),1))
    coeff[k]=dict(dc=dc,cos=cs,sin=sn);err[k]=float(max(abs(fit-y)));end[k]=float(abs(y[-1]-y[0]))
  assert max(err.values())<.0005,(case,err)
  name=f'data_wave_{tag}_v9';va=B/(name+'.va');assert not va.exists()
  s=f'''`include "disciplines.vams"
`include "constants.vams"
// Diagnostic only: ideal replay of actual raw divider waveform, no source noise/impedance.
module {name}(dp,dn,vss);
output dp,dn; input vss; electrical dp,dn,vss;
parameter real delay_s=0;
real theta;
analog begin
theta=2*`M_PI*984e6*($abstime-delay_s);
'''
  for k,c in coeff.items():s+=f'V({k},vss)<+{c["dc"]:.16g}'+''.join(f'+({a:.16g})*cos({n}*theta)+({b:.16g})*sin({n}*theta)' for n,(a,b) in enumerate(zip(c['cos'],c['sin']),1))+';\n'
  s+='end\nendmodule\n';va.write_text(s,encoding='utf-8',newline='\n')
  sources.append(dict(case=case,tag=tag,source=p.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),fit_max_error_v=err,end_difference_v=end,fit_window_s=[float(grid[0]),float(grid[-1])]))
  for label,delay in [('early',-10e-12),('zero',0),('late',10e-12)]:
   p=H/'tb'/f'timing_{tag}_{label}.scs';assert not p.exists()
   s=(H/'tb'/f'{case}.scs').read_text();s=re.sub(r'^XD .*$',f'ahdl_include "{name}.va"\nXDATA (dp dn 0) {name} delay_s={delay:.16g}',s,flags=re.M)
   s=s.replace('include "divider_raw_v9.scs"\n','');s=re.sub(r'^VRST .*\n','',s,flags=re.M)
   p.write_text(s,encoding='utf-8',newline='\n')
 protocol=dict(time=datetime.datetime.now().astimezone().isoformat(),sources=sources,method='63-harmonic fit to one raw differential data period aligned to absolute RF phase. Replace the divider only in this diagnostic with ideal replay, apply-10/0/+10ps time shift to both data polarities, leave actual retimer/RF shape unchanged.',
  qualification='Fit error<0.5mV. Zero-shift output rising-edge phase must match the physical-divider source fixture within2ps before interpreting timing sensitivity. Unchanged frequency/swing screen.',
  diagnostic_target='Report delta output edge time / delta actual raw data edge time for±10ps. Magnitude<0.1 is an internal research target, not a new user requirement or universal setup/hold specification.',
  scope='Deterministic local sensitivity only, oneTT/984MHz phase. Ideal replay has no divider noise/impedance or bidirectional coupling; no power or integrated-noise signoff from these TBs. Actual integrated-noise TBs retain the physical divider.')
 dest=H/'results'/('timing_'+a.tag+'_protocol.json' if a.tag else 'timing_protocol.json');assert not dest.exists()
 dest.write_text(json.dumps(protocol,indent=2)+'\n')
 print('Generated timing diagnostics; fit errors',[s['fit_max_error_v'] for s in sources])
if __name__=='__main__':main()
