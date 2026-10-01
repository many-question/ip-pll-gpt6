"""Independent source-edge and device-size controls; no fitted jitter sources."""
import json,re,datetime,hashlib
import numpy as np
from analyze import H,ROOT
def main():
 D=H.parents[1];B=D/'blocks/jitter_v11';p=B/'cmos_buffer_v11.scs';assert not p.exists()
 p.write_text('''simulator lang=spectre
subckt cmos_buffer_v11 (inp out vdd vss)
parameters s=1
X0 (inp mid vdd vss) pll_inv wn=.8u*s wp=2u*s
X1 (mid out vdd vss) pll_inv wn=2u*s wp=3.9u*s
ends cmos_buffer_v11
''',encoding='utf-8',newline='\n')
 prefix=(H/'tb/cmos_div4_s1.scs').read_text().split('include "cmos_cells_v11.scs"')[0]
 protocol={};T=1/984e6
 def put(name,body,nodes,info):
  s=prefix+body+'CL (out 0) capacitor c=10f\n'
  s+='pss pss fund=984M harms=63 tstab=100n maxstep=1p method=traponly errpreset=conservative maxperiods=30 saveinit=yes writefinal="__FINAL_STATE__"\n'
  s+='pn pnoise start=10k stop=492M dec=30 pnoisemethod=fullspectrum noisetype=sampled measurement=[edge] sampleratio=1 maxsideband=63\nedge jitterevent trigger=[out] triggerthresh=0.6 triggernum=1 triggerdir=rise target=[out] jittercal=[Jee]\n'
  s+='save inp out VDD:p '+nodes+'\nsaveOptions options save=selected\n';p=H/'tb'/f'noise_{name}_coarse.scs';assert not p.exists();p.write_text(s,encoding='utf-8',newline='\n');protocol[p.stem]=info
 for scale,rise in [(1,10),(1,100),(1,300),(2,10),(4,10)]:
  r=rise*1e-12
  body=f'include "cmos_buffer_v11.scs"\nVI (inp 0) vsource type=pulse val0=0 val1=1.2 delay=0 rise={r:.16g} fall={r:.16g} width={T/2-r:.16g} period={T:.16g}\nXB (inp out vdd 0) cmos_buffer_v11 s={scale}\n'
  put(f'cmos_buf_s{scale}_r{rise}',body,'XB.mid',dict(type='CMOS buffer',scale=scale,input_rise_ps=rise,input_swing_v=1.2,goal='Same full-swing input and load; separate source slew from size.'))
 # Replay actual retimer output voltage, including RF ripple and asymmetric edges.
 p=ROOT/'research/runs/spectre_noise_v10/opt_func_c/opt_outfirst2_tt/waveforms.npz'
 with np.load(p) as z:
  t=z['time'];grid=(96+np.linspace(0,1,8193))*T;y=np.interp(grid,t,z['XRT.qp']);th=2*np.pi*984e6*grid;dc=float(np.trapezoid(y,grid)/T);cs=[float(2*np.trapezoid(y*np.cos(n*th),grid)/T) for n in range(1,64)];sn=[float(2*np.trapezoid(y*np.sin(n*th),grid)/T) for n in range(1,64)]
  fit=dc+sum(a*np.cos(n*th)+b*np.sin(n*th) for n,(a,b) in enumerate(zip(cs,sn),1));err=float(max(abs(fit-y)));assert err<.0005
 va='''`include "disciplines.vams"
`include "constants.vams"
module qp_replay_v11(inp,vss);
output inp;input vss;electrical inp,vss;
real th;
analog begin
th=2*`M_PI*984e6*$abstime;
'''+f'V(inp,vss)<+{dc:.16g}'+''.join(f'+({a:.16g})*cos({n}*th)+({b:.16g})*sin({n}*th)' for n,(a,b) in enumerate(zip(cs,sn),1))+';\nend\nendmodule\n'
 (B/'qp_replay_v11.va').write_text(va,encoding='utf-8',newline='\n')
 q=(D/'blocks/noise_v10/cml_v10_outfirst2.scs').read_text();q=re.search(r'subckt tx_limiter4_first2_v10 .*?ends tx_limiter4_first2_v10',q,re.S)[0]
 (B/'restorer_v11.scs').write_text('simulator lang=spectre\n'+q+'\n',encoding='utf-8',newline='\n')
 body='include "restorer_v11.scs"\nahdl_include "qp_replay_v11.va"\nVI (inp 0) qp_replay_v11\nXB (inp out vdd 0) tx_limiter4_first2_v10 wn=2.4u wp=6u\n'
 put('restorer_replay',body,'XB.g0 XB.o0',dict(type='CML-to-CMOS restorer',input='Actual noiseless qp replay from physical chain',source=p.relative_to(ROOT).as_posix(),source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),fit_max_error_v=err,qualification='Must match full-chain output phase/slew and XL-only noise before interpreting replay comparison.'))
 for rise in [10,100,300]:
  rr=rise*1e-12;body=f'include "restorer_v11.scs"\nVI (inp 0) vsource type=pulse val0={min(y):.16g} val1={max(y):.16g} delay=0 rise={rr:.16g} fall={rr:.16g} width={T/2-rr:.16g} period={T:.16g}\nXB (inp out vdd 0) tx_limiter4_first2_v10 wn=2.4u wp=6u\n'
  put(f'restorer_small_r{rise}',body,'XB.g0 XB.o0',dict(type='CML-to-CMOS restorer',input_rise_ps=rise,input_range_v=[float(min(y)),float(max(y))],goal='Hold devices,swing,common-mode,load constant; change only source edge. Synthetic source does not reproduce RF ripple or impedance.'))
 (H/'results/buffer_protocol.json').write_text(json.dumps(dict(time=datetime.datetime.now().astimezone().isoformat(),cases=protocol),indent=2)+'\n');print(list(protocol))
if __name__=='__main__':main()
