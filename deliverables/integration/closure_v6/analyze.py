"""Independent checks for strict-tolerance LC loops and divider PSS fixtures."""
from pathlib import Path
import json,re
import numpy as np
from virtuoso_bridge.spectre.parsers import parse_spectre_psf_ascii
H=Path(__file__).resolve().parent
D=H.parents[2]
ROOT=D.parent if D.name=='share' and (D.parent/'AGENTS.md').exists() else D
R=ROOT/'research/runs/spectre_closure_v6'

def parse(p):
 return {k:np.asarray(v) for k,v in parse_spectre_psf_ascii(p).data.items() if k!='units'}

def cross(t,v,level=0):
 i=np.flatnonzero((v[:-1]<level)&(v[1:]>=level))
 return t[i]+(level-v[i])*(t[i+1]-t[i])/(v[i+1]-v[i])

def effective(log):
 return {k:re.findall(r'^\s{4}'+re.escape(k)+r' = (.+)$',log,re.M) for k in ['reltol','abstol(V)','abstol(I)','maxstep','errpreset','method','steadyratio','lteratio','gmin']}

def linear_slope(t,x):
 return float(np.polyfit((t-t[0])*1e6,x,1)[0])

def loops(job):
 with np.load(job/'waveforms.npz') as z:d={k:z[k] for k in z.files}
 if 'obsphase' not in d:return None
 t=d['time'];idx=np.flatnonzero(np.diff(d['obsphase'])!=0)+1
 sm={k:d[k][idx] for k in ['time','obsphase','obscycles','obsctrl','obsdivcycles']}
 tail=sm['time']>t[-1]-1e-6;tt=sm['time'][tail];phase=np.unwrap(sm['obsphase'][tail]);nc=sm['obscycles'][tail];nd=sm['obsdivcycles'][tail]
 out=dict(end_s=float(t[-1]),last_window_samples=len(tt),phase_pp_rad=float(np.ptp(phase)),phase_drift_rad_per_us=linear_slope(tt,phase),max_vco_cycles_error=float(max(abs(nc-164))),max_div_cycles_error=float(max(abs(nd-41))),mean_output_mhz=float(np.mean(nd)*24),ctrl_range_v=[float(min(sm['obsctrl'][tail])),float(max(sm['obsctrl'][tail]))])
 out['pass_stationary']=bool(out['phase_pp_rad']<.02 and abs(out['phase_drift_rad_per_us'])<.01 and out['max_vco_cycles_error']<.001 and out['max_div_cycles_error']<.001 and .2<out['ctrl_range_v'][0]<=out['ctrl_range_v'][1]<1)
 out['criteria']='Last 1 us: phase pp<.02 rad, abs drift<.01 rad/us, VCO cycles/ref error<.001 from164, output cycles/ref error<.001 from41, control inside0.2..1 V. Same v5 functional screen, not jitter or full capture signoff.'
 m=t>t[-1]-1e-6;out['slow_nodes']={}
 for k in ['XV.XL.nb','XV.XL.nfilt','XD.acp3','XD.acn3','XD.acp7','XD.acn7','XD.cim','XD.cm','XD.nb7','vmid']:
  if k in d:
   v=d[k][m];out['slow_nodes'][k]=dict(mean_v=float(np.mean(v)),pp_v=float(np.ptp(v)),slope_v_per_us=linear_slope(t[m],v),final_v=float(v[-1]))
 # Sparse strobes alias RF: retain for slow states only, never RF frequency or power.
 sm.update({k:d[k] for k in d if k.startswith('XD.') or k.startswith('XV.') or k=='vmid'})
 sm['strobe_time']=t
 np.savez_compressed(H/'results'/f'{job.parent.name}_{job.name}_samples.npz',**sm)
 out['measurement_limit']='Phase/cycle outputs come from solver-edge observer; 1 ns strobes may alias RF and current, so no accurate swing/power is inferred from them.'
 return out

def periodic(job):
 raw=job/(job.name+'.raw');p=raw/'pss.td.pss'
 if not p.exists():return None
 d=parse(p);fd=parse(raw/'pss.fd.pss');t=d['time'];T=t[-1]-t[0]
 ev=cross(t,d['vp']-d['vn']);eo=cross(t,d['out'],.6)
 out=dict(period_s=float(T),vco_edges=len(ev),output_edges=len(eo),output_frequency_mhz=float(1/np.mean(np.diff(eo))/1e6) if len(eo)>2 else None,output_harmonic=int(np.argmax(abs(fd['out'][1:]))+1),output_range_v=[float(min(d['out'])),float(max(d['out']))],branch_power_mw=float(-1.2*np.trapezoid(d['VDD:p'],t)/T*1e3),endpoint_mismatch_v={k:float(abs(v[-1]-v[0])) for k,v in d.items() if k!='time' and ':' not in k},node_mean_v={k:float(np.trapezoid(d[k],t)/T) for k in d if k.startswith('XD.')})
 fundamental,nrf,nout=(984e6,4,1) if job.name.startswith('noise_divider_') else (24e6,164,41)
 out['expected_fundamental_hz']=fundamental
 out['pass_divider_periodic']=bool(abs(T*fundamental-1)<1e-6 and len(ev)==nrf and len(eo)==nout and out['output_harmonic']==nout and out['output_range_v'][0]<.2 and out['output_range_v'][1]>1 and max(out['endpoint_mismatch_v'].values())<1e-3)
 if 'ctrl' in d:
  out['ctrl_range_v']=[float(min(d['ctrl'])),float(max(d['ctrl']))]
  out['tank_diff_pp_v']=float(np.ptp(d['vp']-d['vn']))
  out['vco_harmonic']=int(np.argmax(abs(fd['vp'][1:]-fd['vn'][1:]))+1)
  out['reference_edges']=len(cross(t,d['refb'],.6))
  out['pass_loop_periodic']=bool(out['pass_divider_periodic'] and out['reference_edges']==1 and out['vco_harmonic']==164 and .2<min(d['ctrl'])<=max(d['ctrl'])<1 and .05<out['tank_diff_pp_v']<3.6 and max(max(abs(d['vp'])),max(abs(d['vn'])))<1.8)
 return out

def switching(job):
 if 'switch' not in job.name:return None
 with np.load(job/'waveforms.npz') as z:d={k:z[k] for k in z.files}
 t=d['time'];rows=[]
 for i,m in enumerate([4,6,8,10,12,14]):
  a=(i*100+30)*1e-9;b=(i*100+95)*1e-9;mask=(t>=a)&(t<=b);tt=t[mask]
  ve=cross(tt,d['vp'][mask]-d['vn'][mask]);oe=cross(tt,d['out'][mask],.6)
  fv=1/np.mean(np.diff(ve));fo=1/np.mean(np.diff(oe)) if len(oe)>2 else 0
  err=float(max(abs(np.diff(oe)*fv/m-1))) if len(oe)>2 else None
  rows.append(dict(m=m,window_s=[a,b],rf_hz=float(fv),output_hz=float(fo),output_edges=len(oe),ratio_error=float(fo*m/fv-1),max_period_error=err,pass_divide=bool(len(oe)>5 and abs(fo*m/fv-1)<.001 and err<.02)))
 return dict(rows=rows,all_pass=all(x['pass_divide'] for x in rows),scope='STRESS TEST: TT27, ideal measured-shape RF3.936GHz for all modes,10fF; exceeds planned maximum RF for M6/8/10/12/14. 100ns mode dwell, externally sequenced selects/reset; includes settling. Not required-frequency/FLL/glitchless switching signoff.')

def static_divide(job):
 match=re.fullmatch(r'divider_clamp_m(\d+)_tt',job.name)
 if not match:return None
 m=int(match[1]);d=np.load(job/'waveforms.npz');t=d['time'];mask=(t>=200e-9)&(t<=280e-9);tt=t[mask]
 ve=cross(tt,d['vp'][mask]-d['vn'][mask]);oe=cross(tt,d['out'][mask],.6)
 fv=float(1/np.mean(np.diff(ve)));fo=float(1/np.mean(np.diff(oe))) if len(oe)>2 else 0
 pe=float(max(abs(np.diff(oe)*fv/m-1))) if len(oe)>2 else 1
 out=dict(m=m,rf_hz=fv,output_hz=fo,ratio_error=fo*m/fv-1,max_period_error=pe,output_edges=len(oe),pass_divide=bool(len(oe)>5 and abs(fo*m/fv-1)<.001 and pe<.02),window_s=[200e-9,280e-9],fixture='Ideal waveform replay at planned maximum RF for this divider mode; TT27,1.2V,10fF; not loaded VCO noise.')
 d.close();return out

def main():
 rows=[]
 for rp in sorted(R.glob('*/*/result.json')):
  rec=json.loads(rp.read_text());job=rp.parent
  if not rec.get('remote_inputs_match'):continue
  log=(job/'spectre.out').read_text(errors='replace')
  row=dict(run=job.parent.name,case=job.name,sim_ok=rec['ok'],settings=effective(log),state_file=rec.get('state_file'),norm_lines=[x for x in log.splitlines() if 'Conv norm =' in x],gmin_notices=[x.strip() for x in log.splitlines() if 'dV(XD.' in x])
  row['warnings']=[x.strip() for x in log.splitlines() if 'WARNING (' in x]
  row['errors']=[x.strip() for x in log.splitlines() if 'ERROR (' in x]
  row['iteration_limit_reached']='iterations has reached the maximum limit' in log
  row['cancelled']=(job/'cancellation.json').exists()
  if rec['ok']:
   row.update(transient=loops(job),periodic=periodic(job),switching=switching(job),static_divider=static_divide(job))
   if job.name.startswith('dc_'):row['dc_values']=rec.get('final_values')
  rows.append(row)
 (H/'results/validation.json').write_text(json.dumps(rows,indent=2)+'\n')
 dc={x['case']:x for x in rows if 'dc_values' in x}
 if len(dc)==4:
  delta={c:{k:dc[f'dc_{c}_g1p']['dc_values'][k]-dc[f'dc_{c}_g100f']['dc_values'][k] for k in ['dc_XD.acp3','dc_XD.acp7','dc_XD.cim']} for c in ['base','clamp']}
  (H/'results/dc_sensitivity.json').write_text(json.dumps(dict(scope='DC, RF pins fixed1.2V, selected divide4,reset0,TT27,1.2V. Change simulator gmin1pS to0.1pS; this probes bias conditioning, not AC noise or lock.',delta_v=delta),indent=2)+'\n')
 for row in rows:
  print(row['case'],'sim',row['sim_ok'],'transient',row.get('transient',{}).get('pass_stationary') if row.get('transient') else None,'periodic',row.get('periodic',{}).get('pass_divider_periodic') if row.get('periodic') else None)

if __name__=='__main__':main()
