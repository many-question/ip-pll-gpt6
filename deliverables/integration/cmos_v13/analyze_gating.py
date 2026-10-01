"""Check the three single-noise-on CMOS-chain reruns against the all-on chain."""
import json
import numpy as np
from analyze import H,R,parse
from analyze_noise import device_totals,header

def main():
 rows=json.loads((H/'results/noise_validation.json').read_text())['cases'];by={r['case']:r for r in rows}
 def get(case):
  row=by[case];assert row['valid_noise'];p=R/row['run']/case/(case+'.raw');noise=p/'pnMedge.0.sample.pnoise'
  return parse(p/'pss.td.pss'),parse(noise),device_totals(noise,len(parse(noise)['freq'])),header(noise,'slew rate event_1')
 allcase='noise_cc4_rtcomb_coarse';a,n,dev,slew=get(allcase);records=[];ss=0
 for group in ['XRX','XD','XR']:
  case=f'noise_cc4_rtcomb_gate{group}_coarse';b,m,d,bslew=get(case)
  assert np.array_equal(n['freq'],m['freq'])
  voltage=max(float(max(abs(a[k]-b[k]))) for k in a if k!='time' and ':' not in k)
  pwr=abs(by[case]['periodic']['power_mw']['VDD:p']-by[allcase]['periodic']['power_mw']['VDD:p'])
  expected=sum(v for k,v in dev.items() if k.startswith(group+'.'));inactive=sum(v for k,v in d.items() if not k.startswith(group+'.'))
  spectrum_error=float(max(abs(m['out']**2-expected)/np.maximum(expected,1e-300)));inactive_max=float(max(inactive)) if isinstance(inactive,np.ndarray) else 0
  records.append(dict(group=group,jitter_fs=by[case]['numeric_jitter_fs'],voltage_max_difference_v=voltage,power_difference_mw=pwr,slew_relative_difference=bslew/slew-1,active_spectrum_max_relative_error=spectrum_error,inactive_psd_max=inactive_max,pass_gate=bool(voltage<1e-9 and pwr<1e-8 and abs(bslew/slew-1)<1e-9 and spectrum_error<1e-8 and inactive_max==0)))
  ss=ss+m['out']**2
 closure=float(max(abs(ss-n['out']**2)/np.maximum(n['out']**2,1e-300)))
 out=dict(cases=records,PSD_closure_max_relative_error=closure,pass_gating=bool(all(x['pass_gate'] for x in records) and closure<1e-8))
 (H/'results/gating_validation.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
if __name__=='__main__':main()
