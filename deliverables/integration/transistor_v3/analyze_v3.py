"""Independent checks against saved, immutable Spectre inputs and raw results."""
from pathlib import Path
import json,sys,re
import numpy as np
H=Path(__file__).resolve().parent;D=H.parents[2]
ROOT=D.parent if D.name=='share' and (D.parent/'AGENTS.md').exists() else D
R=ROOT/'research/runs/spectre_transistor_v3'
sys.path.insert(0,str(H))
from build_inductor import impedance
from virtuoso_bridge.spectre.parsers import parse_spectre_psf_ascii

def cross(t,v,level=.6,up=True):
 ii=np.flatnonzero(((v[:-1]<level)&(v[1:]>=level)) if up else ((v[:-1]>=level)&(v[1:]<level)))
 return t[ii]+(level-v[ii])*(t[ii+1]-t[ii])/(v[ii+1]-v[ii])
def word(d,prefix,n):return sum((d[f'{prefix}{i}']>.6).astype(int)*(1<<i) for i in range(n))
def get(run,case):
 p=R/run/case
 if not (p/'result.json').exists():return None
 rec=json.loads((p/'result.json').read_text())
 if not rec['ok']:return None
 return np.load(p/'waveforms.npz')
def parse(p):return {k:np.asarray(v) for k,v in parse_spectre_psf_ascii(p).data.items() if k!='units'}
def power(d,start):
 t=d['time'];m=t>=start
 return float(-1.2*np.trapezoid(d['VDD:p'][m],t[m])/(t[m][-1]-t[m][0])*1e3)

def check_config(d):
 t=d['time'];active=word(d,'active_k',6);sel=word(d,'select_m',6)
 schedule=json.loads((H/'results/config_stimulus.json').read_text());checks=[]
 for x in schedule:
  if x['time']+.8e-6>=t[-1]:continue
  k=x['k'];at=x['time']+.8e-6;i=np.argmin(abs(t-at));valid=9<=k<=41
  m=14 if k==9 else 12 if k<=11 else 10 if k<=13 else 8 if k<=18 else 6 if k<=27 else 4
  expect=(1<<([4,6,8,10,12,14].index(m))) if valid else 0
  ok=(active[i]==k and sel[i]==expect and (d['ready'][i]>.6)==valid and (d['invalid'][i]>.6)==(not valid) and (d['divider_reset'][i]>.6)==(not valid))
  checks.append(dict(k=k,active=int(active[i]),selection=int(sel[i]),pass_check=bool(ok)))
 # No K changes or non-one-hot selection while divider is released.
 released=d['divider_reset']<.3
 multi=(sel!=0)&((sel&(sel-1))!=0)
 changes=np.flatnonzero(active[1:]!=active[:-1])+1
 reset_safe=all(np.min(d['divider_reset'][max(0,i-2):i+3])>.9 for i in changes)
 return dict(pass_check=all(x['pass_check'] for x in checks) and bool(reset_safe) and not np.any(multi&released),cases=len(checks),checks=checks,reset_safe=bool(reset_safe),power_mw=power(d,1e-6))

def check_supervisor(d):
 # Independent integer-cycle oracle. Inspect well after each 24 MHz edge.
 t=d['time'];good=bad=restart_count=0;qualified=restart=fault=0;errors=[]
 for edge in np.arange(10.025e-9,t[-1]-20e-9,1/24e6):
  i=np.searchsorted(t,edge-2e-9);j=np.searchsorted(t,edge+18e-9)
  inp={n:int(d[n][i]>.6) for n in ['reset','cfg_ready','fll_enable','range_error','phase_good','frequency_good']}
  if inp['reset'] or not inp['cfg_ready']:qualified=restart=fault=good=bad=restart_count=0
  elif inp['range_error']:qualified=0;fault=1;good=bad=0
  elif restart:
   if restart_count==7:restart=restart_count=0
   else:restart_count+=1
  elif not inp['fll_enable']:qualified=good=bad=0
  elif inp['phase_good'] and inp['frequency_good']:
   bad=0
   if not qualified:
    if good==31:qualified=1;good=0
    else:good+=1
  else:
   good=0
   if qualified:
    if bad==3:qualified=0;restart=1;restart_count=bad=0
    else:bad+=1
  expected={'qualified':qualified,'restart':restart,'fault':fault}
  for n,v in expected.items():
   if (d[n][j]>.6)!=bool(v):errors.append(dict(time_s=float(t[j]),signal=n,expected=v,observed=float(d[n][j])))
 return dict(pass_check=not errors,errors=errors[:20],qualified_edges_ns=(cross(t,d['qualified'])*1e9).tolist(),restart_edges_ns=(cross(t,d['restart'])*1e9).tolist(),power_mw=power(d,2e-6))

def main():
 summary={'timing':[],'config':[],'supervisor':[],'precision':[],'loops':[],'config_divider':[],'frontend':[],'inductor':[],'vco':[]}
 for c in ['tt','ss','ff']:
  d=get('timing03',f'tb_cp_timing_{c}')
  if d is not None:
   t=d['time'];r=cross(t,d['pulse']);f=cross(t,d['pulse'],up=False);rr=cross(t,d['ref'])
   widths=np.array([f[f>x][0]-x for x in r if np.any(f>x)])
   normal=(r<260e-9)|(r>280e-9)
   delays=np.array([x-rr[rr<x][-1] for x in r])
   expected_cycles=[1,2,5,6,7,8,9]
   cycles=np.rint((r-10e-9)/ (1/24e6)).astype(int)
   off_reset=float(np.max(d['pulse'][(t>264e-9)&(t<275e-9)]))
   checks=(cycles.tolist()==expected_cycles and np.min(widths[normal])>1e-9 and off_reset<.1)
   summary['timing'].append(dict(corner=c,pass_check=checks,pulse_cycles=cycles.tolist(),normal_width_ns=[float(np.min(widths[normal])*1e9),float(np.max(widths[normal])*1e9)],delay_ns=[float(min(delays)*1e9),float(max(delays)*1e9)],reset_off_max_v=off_reset,power_including_cp_mw=power(d,280e-9)))
  for name,fn in [('config',check_config),('supervisor',check_supervisor)]:
   d=get('control02',f'tb_{name}_{c}')
   if d is not None:summary[name].append(dict(corner=c,**fn(d)))
 for name,fn in [('config',check_config),('supervisor',check_supervisor)]:
  d=get('precision01',f'tb_{name}_tt_tight')
  if d is not None:summary['precision'].append(dict(block=name,**fn(d)))
 for run,case in [('integrate01','loop_s10_timing_tt'),('system_ss','loop_s10_corner_ss'),('system_ff','loop_s10_corner_ff'),('system_config_ax','loop_s11_moderate_tt')]:
  d=get(run,case)
  if d is None:continue
  t=d['time'];m=t>5.5e-6
  r=dict(case=case,freq_mhz=float(d['freqout'][-1]*1000),control_v=float(d['ctrl'][-1]),cycle_control_pp_uv=float(np.ptp(d['cycle_ctrl'][m])*1e6),partial_power_mw=float(d['power_mw'][-1]),duty=float(d['dutyout'][-1]))
  r['pass_check']=abs(r['freq_mhz']-984)<.01 and r['cycle_control_pp_uv']<100 and .15<r['control_v']<1.05
  if case.startswith('loop_s11'):
   expected={'ready':1,'invalid':0,'rst':0,'enable':1,'qualified':0,'restart':0,'fault':0}
   r['control_final_v']={name:float(d[name][-1]) for name in expected}
   r['pass_check']=r['pass_check'] and all((r['control_final_v'][name]>.9 if value else abs(r['control_final_v'][name])<.3) for name,value in expected.items())
  summary['loops'].append(r)
 for m in [4,6,8,10,12,14]:
  d=get('config_divider01',f'tb_config_divider_m{m}')
  if d is None:continue
  t=d['time'];window=t>650e-9;rr=cross(t[window],d['out'][window]);k={4:41,6:27,8:18,10:13,12:11,14:9}[m]
  f=1/np.mean(np.diff(rr)) if len(rr)>3 else 0
  low=float(np.min(d['out'][window]));high=float(np.max(d['out'][window]))
  summary['config_divider'].append(dict(m=m,k=k,output_mhz=float(f/1e6),output_min_v=low,output_max_v=high,pass_check=bool(abs(f/(24e6*k)-1)<1e-3 and low<.2 and high>1.0 and d['ready'][-1]>.9 and d['invalid'][-1]<.3),power_mw=power(d,650e-9)))
 for c in ['tt','ss']:
  d=get('frontend02',f'tb_control_frontend_{c}')
  if d is None:continue
  counts=word(d,'XC.q',14);t=d['time'];code=word(d,'b',8);selection=word(d,'s',6)
  reset_release=cross(t,d['count_reset'],up=False)[-1]
  edges=cross(t,d['XC.XCOUNT.gclk']);edges=edges[edges>reset_release]
  safe=all(float(np.max(d[n]))<.3 for n in ['enable','pulse','qualified','range_error','config_invalid','restart'])
  summary['frontend'].append(dict(corner=c,observed_gated_edges=len(edges),final_count=int(counts[-1]),pass_check=bool(safe and len(edges)==counts[-1] and len(edges)>100 and np.ptp(counts[t>1.3e-6])==0 and code[-1]==0 and selection[-1]==1 and d['config_ready'][-1]>.9),preset_v=float(d['preset'][-1]),power_mw=power(d,1e-6)))
 params=json.loads((H/'results/inductor_parameters.json').read_text())
 for par in params:
  q=par['q_at_3p3ghz'];p=R/'inductor01'/f'tb_inductor_q{q}'/f'tb_inductor_q{q}.raw'/'ac.ac'
  if p.exists():
   d=parse(p);freq=d['freq'];z=-1/d['VTEST:p'];ref=impedance(freq,par['rs_ohm'])
   # Q is meaningful only below self resonance (positive imaginary impedance).
   sign=np.flatnonzero((z.imag[:-1]>0)&(z.imag[1:]<=0))
   summary['inductor'].append(dict(q_target=q,ac_relative_error=float(np.max(abs(z/ref-1))),q_at_3p3ghz=float(np.interp(3.3e9,freq,z.imag/z.real)),q_at_band_edges=[float(np.interp(f,freq,z.imag/z.real)) for f in [2.688e9,3.936e9]],srf_ghz=float(freq[sign[0]]/1e9) if len(sign) else None))
 for p in R.glob('inductor*/tb_rlc_*/waveforms.npz'):
  if 'noise' in p.parent.name:continue
  d=np.load(p);t=d['time'];v=d['vp']-d['vn'];start=max(250e-9,float(t[-1])-50e-9);m=t>start;r=cross(t[m],v[m],0)
  amplitude=float(np.ptp(v[m]));oscillating=len(r)>3 and amplitude>.05
  mid=(start+t[-1])/2;early=np.ptp(v[(t>start)&(t<mid)]);late=np.ptp(v[t>mid])
  rec=dict(case=p.parent.name,run=p.parent.parent.name,oscillating=oscillating,frequency_ghz=float(1/np.mean(np.diff(r))/1e9) if oscillating else None,differential_pp_v=amplitude,power_mw=power(d,start),measurement_window_s=[start,float(t[-1])],tail_amplitude_change_fraction=float(late/early-1) if early else None)
  if 'out' in d:
   rr=cross(t[m],d['out'][m]);rec['output_mhz']=float(1/np.mean(np.diff(rr))/1e6) if len(rr)>3 else None
   net=(p.parent/'inputs'/f'{p.parent.name}.scs').read_text()
   select=re.search(r'XD \(vp vn rst (.*?) out vdd 0\)',net)
   if select:
    bits=select.group(1).split();ratio=4+2*bits.index('vdd')
    rec['selected_division']=ratio
    rec['output_ratio_valid']=bool(oscillating and rec['output_mhz'] and abs(rec['output_mhz']/(rec['frequency_ghz']*1000/ratio)-1)<1e-3)
  summary['vco'].append(rec)
 # A 1 A differential test current enters vp and leaves vn. The net
 # admittance includes the active core and passive tank at symmetric DC.
 startup=[]
 for case in sorted((R/'startup_ac01').glob('tb_startup_ac_*')):
  p=case/f'{case.name}.raw'/'ac.ac'
  if not p.exists():continue
  d=parse(p);freq=d['freq'];y=1/(d['vp']-d['vn'])
  idx=np.flatnonzero(y.imag[:-1]*y.imag[1:]<=0);resonances=[]
  for i in idx:
   fraction=-y.imag[i]/(y.imag[i+1]-y.imag[i])
   resonances.append(dict(f_hz=float(freq[i]+fraction*(freq[i+1]-freq[i])),g_s=float(y.real[i]+fraction*(y.real[i+1]-y.real[i]))))
  startup.append(dict(case=case.name,resonances=resonances))
 (H/'results/startup_admittance.json').write_text(json.dumps(startup,indent=2)+'\n')
 (H/'results/validation.json').write_text(json.dumps(summary,indent=2)+'\n')
 print(json.dumps({k:([ {a:b for a,b in x.items() if a!='checks'} for x in v]) for k,v in summary.items()},indent=2))
if __name__=='__main__':main()
