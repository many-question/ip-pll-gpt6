"""Compare one-module changes without mistaking only-on noise for total noise."""
import json
import numpy as np
from analyze import H,R,parse
from analyze_noise import device_totals,header
from analyze_gating import belongs

def main():
 pp=H/'results/optimization_protocol.json'
 if not pp.exists():return
 p=json.loads(pp.read_text());v=json.loads((H/'results/validation.json').read_text());vf={r['case']:r for r in v};n=json.loads((H/'results/noise_validation.json').read_text());by={r['case']:r for r in n['cases']};gate=json.loads((H/'results/gating_validation.json').read_text());g={r['group']:r for r in gate['cases']};gp=json.loads((H/'results/gating_protocol.json').read_text());baseline=by['noise_gate_all_coarse'];rows=[]
 for case,info in p['variants'].items():
  t=vf.get(case);row=dict(case=case,group=info['group'],change=info['change'],function_pass=bool(t and t.get('transient',{}).get('pass_function')));rows.append(row)
  if t and 'transient' in t:row['transient_power_mw']=t['transient']['power_mw']
  for mode in ['only','all']:
   key='noise_'+case.removesuffix('_tt')+'_'+mode+'_coarse';r=by.get(key)
   if not r:continue
   part=dict(case=key,valid_noise=r.get('valid_noise',False));row[mode]=part
   if not r.get('valid_noise'):continue
   target=g[info['group']]['jitter_fs'] if mode=='only' else baseline['numeric_jitter_fs'];part.update(jitter_fs=r['numeric_jitter_fs'],baseline_jitter_fs=target,relative_rms_change=r['numeric_jitter_fs']/target-1,power_mw=r['periodic']['power_mw'],power_delta_mw=r['periodic']['power_mw']['VDD:p']-baseline['periodic']['power_mw']['VDD:p'],noise_by_instance=r['noise_by_instance'])
   if mode=='only':
    raw=R/r['run']/key/(key+'.raw');f=parse(raw/'pnMedge.0.sample.pnoise')['freq'];dev=device_totals(raw/'pnMedge.0.sample.pnoise',len(f));sl=header(raw/'pnMedge.0.sample.pnoise','slew rate event_1')
    inactive=sum((x for k,x in dev.items() if not belongs(k,gp['boundaries'][info['group']])),np.zeros(len(f)))
    var=float(np.trapezoid(inactive/sl**2,f));part['inactive_variance_fraction']=var/(r['numeric_jitter_fs']*1e-15)**2;part['pass_single_on']=bool(part['inactive_variance_fraction']<1e-12 and not r['noise_option_conflict_warning'])
    part['passes_internal_reduction_target']=bool(part['pass_single_on'] and part['relative_rms_change']<=-.05)
  if row.get('all',{}).get('valid_noise') and row.get('only',{}).get('valid_noise'):
   aa=by[row['all']['case']];ss=by[row['only']['case']];partsum=sum(x['jitter_fs']**2 for k,x in aa['noise_by_subblock'].items() if belongs(k,gp['boundaries'][info['group']]))**.5
   # Bias group has flattened primitives combined as bias_and_passives in generic summaries.
   if info['group']=='bias':partsum=aa['noise_by_subblock']['XRT.bias_and_passives']['jitter_fs']
   row['selected_only_vs_all_contribution_relative_error']=ss['numeric_jitter_fs']/partsum-1
   waves=[]
   for r in [aa,ss]:waves.append(parse(R/r['run']/r['case']/(r['case']+'.raw')/'pss.td.pss'))
   wa,ws=waves;row['only_all_max_voltage_waveform_difference_v']=max(float(max(abs(np.interp(wa['time'],ws['time'],val)-wa[k]))) for k,val in ws.items() if k not in ('time','units') and ':' not in k)
   row['only_all_relative_slew_difference']=ss['slew_v_per_s']/aa['slew_v_per_s']-1
   spectra=[]
   for r in [aa,ss]:
    pp=R/r['run']/r['case']/(r['case']+'.raw')/'pnMedge.0.sample.pnoise';freq=parse(pp)['freq'];dv=device_totals(pp,len(freq))
    spectra.append(sum((x for k,x in dv.items() if belongs(k,gp['boundaries'][info['group']])),np.zeros(len(freq)))/r['slew_v_per_s']**2)
   row['only_all_selected_spectrum_max_difference_db']=float(max(abs(10*np.log10(spectra[1]/spectra[0]))))
   row['pass_only_all_consistency']=bool(abs(row['selected_only_vs_all_contribution_relative_error'])<.001 and row['only_all_max_voltage_waveform_difference_v']<1e-6 and abs(row['only_all_relative_slew_difference'])<1e-5 and row['only_all_selected_spectrum_max_difference_db']<.01)
   row['combined_stage']='all-on checked; numerical refinement remains separate'
 out=dict(protocol=p,cases=rows,precision=n['precision'],scope='One-module modifications evaluated at the output of the unchanged remainder of the chain. WholePLL and realRF loading are not validated.')
 (H/'results/optimization_validation.json').write_text(json.dumps(out,indent=2,allow_nan=False)+'\n')
 print(json.dumps([dict(case=r['case'],function=r['function_pass'],only=r.get('only'),all=r.get('all')) for r in rows],indent=2))

if __name__=='__main__':main()
