"""Independent single-on measurements versus all-on device contributions."""
import json
import numpy as np
from analyze import H,R,parse
from analyze_noise import device_totals,header

def belongs(device,paths):return any(device==p or device.startswith(p+'.') for p in paths)
def read_job(row):
 raw=R/row['run']/row['case']/(row['case']+'.raw');p=raw/'pnMedge.0.sample.pnoise';d=parse(p);slew=header(p,'slew rate event_1')
 return d['freq'],d['out']**2/slew**2,device_totals(p,len(d['freq'])),slew,parse(raw/'pss.td.pss')

def main():
 proto=json.loads((H/'results/gating_protocol.json').read_text());lim=proto['criteria'];noise=json.loads((H/'results/noise_validation.json').read_text());by={r['case']:r for r in noise['cases']};base=by.get('noise_gate_all_coarse')
 if not base or not base.get('valid_noise'):print('Waiting for valid all-on result');return
 f,st,dev,slew,wave=read_job(base);total=float(np.trapezoid(st,f));rows=[];group_spectra={}
 claimed=set()
 for name,paths in proto['boundaries'].items():
  keys={k for k in dev if belongs(k,paths)};assert not keys&claimed;claimed|=keys
 unassigned=sum((v for k,v in dev.items() if k not in claimed),np.zeros(len(f)))/slew**2
 assert max(unassigned/np.maximum(st,1e-300))<=lim['max_inactive_psd_fraction']
 for case,cfg in proto['cases'].items():
  r=by.get(case)
  if not r or not r.get('valid_noise'):continue
  g,y,parts,sl,w=read_job(r);assert np.array_equal(f,g)
  waveerr=max(float(max(abs(np.interp(wave['time'],w['time'],v)-wave[k]))) for k,v in w.items() if k not in ('time','units') and ':' not in k)
  powererr=abs(r['periodic']['power_mw']['VDD:p']/base['periodic']['power_mw']['VDD:p']-1);slerr=abs(sl/slew-1)
  paths=cfg['on'];expected=sum((v for k,v in dev.items() if belongs(k,paths)),np.zeros(len(f)))/slew**2
  inactive=sum((v for k,v in parts.items() if not belongs(k,paths)),np.zeros(len(f)))/sl**2
  inactivefraction=float(max(inactive/np.maximum(st,1e-300)))
  if cfg['group']=='off':
   db=None;rel=None;compare=r['numeric_jitter_fs']<lim['max_zero_noise_fs']
  else:
   assert np.all(expected>0) and np.all(y>0)
   db=float(max(abs(10*np.log10(y/expected))));rel=float(np.sqrt(np.trapezoid(y,f)/np.trapezoid(expected,f))-1)
   compare=db<lim['max_spectrum_difference_db'] and abs(rel)<lim['max_relative_rms_difference']
  ok=compare and inactivefraction<=lim['max_inactive_psd_fraction'] and waveerr<lim['max_voltage_waveform_difference_v'] and powererr<lim['max_relative_power_change'] and slerr<lim['max_relative_slew_change']
  rows.append(dict(case=case,group=cfg['group'],jitter_fs=r['numeric_jitter_fs'],expected_from_all_on_fs=float(np.sqrt(np.trapezoid(expected,f))*1e15),variance_fraction=float(np.trapezoid(y,f)/total),max_spectrum_difference_db=db,relative_rms_difference=rel,max_inactive_psd_fraction=inactivefraction,max_voltage_waveform_difference_v=waveerr,relative_power_difference=powererr,relative_slew_difference=slerr,pass_isolation=bool(ok)))
  if cfg['group'] in proto['boundaries']:group_spectra[cfg['group']]=y
 oldraw=R.parent/'spectre_output_v9/noise_double/noise_cml2_s2_coarse/noise_cml2_s2_coarse.raw';op=oldraw/'pnMedge.0.sample.pnoise';old=parse(op);assert np.array_equal(f,old['freq']);oldst=old['out']**2/header(op,'slew rate event_1')**2
 history_db=float(max(abs(10*np.log10(st/oldst))));closure=None
 if len(group_spectra)==len(proto['boundaries']):
  summed=sum(group_spectra.values());closure=dict(max_spectrum_difference_db=float(max(abs(10*np.log10(summed/st)))),variance_relative_error=float(np.trapezoid(summed,f)/total-1),rss_fs=float(np.sqrt(np.trapezoid(summed,f))*1e15))
 complete=len(rows)==len(proto['cases']);passed=bool(complete and all(r['pass_isolation'] for r in rows) and history_db<lim['max_spectrum_difference_db'] and closure and abs(closure['variance_relative_error'])<lim['max_partition_variance_relative_error'] and closure['max_spectrum_difference_db']<lim['max_spectrum_difference_db'])
 out=dict(protocol=proto,cases=rows,all_on_vs_v9_coarse_max_spectrum_difference_db=history_db,variance_closure=closure,completed=complete,pass_gating=passed)
 (H/'results/gating_validation.json').write_text(json.dumps(out,indent=2,allow_nan=False)+'\n')
 np.savez_compressed(H/'results/gating_spectra.npz',f=f,all_on=st,**group_spectra)
 print(json.dumps(dict(cases=rows,variance_closure=closure,completed=complete,pass_gating=passed),indent=2))

if __name__=='__main__':main()
