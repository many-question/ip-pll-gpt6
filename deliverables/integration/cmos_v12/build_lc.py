"""Generate actual LC+sampler+CMOS receiver/divider/retimer transient trials."""
from pathlib import Path
import argparse,json,re,datetime
H=Path(__file__).resolve().parent;D=H.parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--receiver',required=True);p.add_argument('--codes',type=int,nargs='+',required=True);p.add_argument('--control',type=float,default=.6);p.add_argument('--corner',default='tt');p.add_argument('--temperature',type=int,default=27);a=p.parse_args()
 screen='screen_'+a.receiver
 valid={r['case']:r for r in json.loads((H/'results/validation.json').read_text())};assert valid[screen]['wave']['pass_function'],'Receiver must pass before actual LC trial'
 prefix=(D/'integration/vco_v4/tb/r2_tt_k41_c6.scs').read_text().split('include "lc_vco_v4r.scs"')[0]
 # Keep actual 24MHz sampler/CP/reference loading. Control is clamped for tuning;
 # CP output is separately clamped; this is explicitly not a closed PLL.
 old=(D/'integration/accuracy_v7/tb/clamp8_mid_pss.scs').read_text()
 sampler=old.split('include "cp_experiment.scs"')[1].split('XD (vp')[0]
 sampler='include "cp_experiment.scs"'+sampler.replace('XR (ref refb','XREF (ref refb').replace('VO (cpout ctrl) vsource dc=0','VO (cpout 0) vsource dc=.6')
 candidate=(H/'tb'/f'{screen}.scs').read_text();chain=candidate.split('include "rf_')[1].split('tran tran')[0];chain='include "rf_'+chain
 cases=[]
 for code in a.codes:
  assert 0<=code<256
  s=prefix+'include "lc_vco_repaired.scs"\nVDD (vdd 0) vsource dc=1.2\nVVCO (vco_vdd vdd) vsource dc=0\n'+f'VC (ctrl 0) vsource dc={a.control}\n'
  for bit in range(8):s+=f'VB{bit} (b{bit} 0) vsource dc={1.2 if (code>>bit)&1 else 0}\n'
  s+='XV (vp vn ctrl b0 b1 b2 b3 b4 b5 b6 b7 vco_vdd 0) tx_lc_vco_repaired\n'+sampler+chain
  s+='ic vp=1.20001 vn=1.2\ntran tran stop=400n start=0 outputstart=300n maxstep=1p method=traponly errpreset=conservative writefinal="__FINAL_STATE__"\n'
  s+='save vp vn clk q1 data out ctrl sp sn hp hn refb XV.XL.nb XV.XL.nfilt XV.XL.tail VDD:p VVCO:p VRX:p VRT:p\nsaveOptions options save=selected\n'
  s=s.replace('section=tt\n',f'section={a.corner}\n').replace('section=tt_bbmvar',f'section={a.corner}_bbmvar').replace('temp=27',f'temp={a.temperature}')
  name=f'lc_{a.receiver}_c{code}_v{str(a.control).replace(".","p")}_{a.corner}';path=H/'tb'/(name+'.scs');assert not path.exists();path.write_text(s,encoding='utf-8',newline='\n');cases.append(name)
 print(' '.join(cases))
 (H/'results'/f'protocol_{cases[0]}.json').write_text(json.dumps(dict(time=datetime.datetime.now().astimezone().isoformat(),scope='Actual R2 LC with Q5 RLC, actual24MHz sampler/CP/reference-buffer, real CMOS RF interface/divider/retimer,10fF. Fixed control and coarse code; not lockedPLL. No ideal RF or CMOS clock. Bias current source remains deferred.',cases=cases,control_v=a.control,codes=a.codes,corner=a.corner,temperature=a.temperature,acceptance='Sustained real LC RF differential>50mV; clk tracksRF and output=RF/4 within0.1%,per-cycle<2%,digital swing<.2/>1V. Frequency coverage/4mW evaluated separately, no inferred lock.'),indent=2)+'\n')
if __name__=='__main__':main()
