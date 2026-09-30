"""Check the physical periodic LC solution separately from transient capture."""
import json,re,sys
import numpy as np
from analyze import H,R,cross
sys.path.insert(0,str(H.parent/'transistor_v2'))
from analyze_noise import parse

def analyze(job):
 rec=json.loads((job/'result.json').read_text());out=dict(case=job.name,run=job.parent.name,simulator_ok=rec['ok'],condition='TT27,Q5,quiet10,code6,physical LC/sample/CP/filter/divider; driven 24 MHz PSS. Existence of a periodic solution is not capture or stability proof.')
 out['cancelled']=(job/'cancellation.json').exists()
 log=(job/'spectre.out').read_text(errors='replace')
 out['shooting_norms']=[float(x) for x in re.findall(r'Conv norm = ([0-9.eE+\-]+)',log)]
 out['shooting_norm_log_lines']=[x for x in log.splitlines() if 'Conv norm =' in x]
 if (job/'stop_review.json').exists():out['stop_review']=json.loads((job/'stop_review.json').read_text())
 out['recovery_log_lines']=[x for x in log.splitlines() if 'Restarting at time' in x or 'Recovering from save-restart' in x]
 out['numerical_settings']={k:re.findall(r'^\s*'+k+r' = (.+)$',log,re.M) for k in ['reltol','lteratio','steadyratio','maxstep','method','errpreset']}
 out['noise_precision_verified']=False
 if out['cancelled']:out['cancellation']=json.loads((job/'cancellation.json').read_text())
 if rec['ok']:
  raw=job/(job.name+'.raw');d=parse(raw/'pss.td.pss');fd=parse(raw/'pss.fd.pss');t=d['time'];T=t[-1]-t[0]
  v=d['vp']-d['vn'];nv=len(cross(t,v));nd=len(cross(t,d['out'],.6));nr=len(cross(t,d['refb'],.6))
  out.update(period_s=float(T),vco_rising_edges=nv,divider_rising_edges=nd,reference_rising_edges=nr,tank_diff_pp_v=float(np.ptp(v)),control_range_v=[float(min(d['ctrl'])),float(max(d['ctrl']))],control_mean_v=float(np.trapezoid(d['ctrl'],t)/T),vco_mw=float(-1.2*np.trapezoid(d['VVCO:p'],t)/T*1e3),connected_branch_mw=float(-1.2*np.trapezoid(d['VDD:p'],t)/T*1e3),tail_bias_mean_v={k:float(np.trapezoid(d[k],t)/T) for k in ['XV.XL.nb','XV.XL.nfilt']},cp_average_current_a=float(np.trapezoid(d['VO:p'],t)/T),max_saved_voltage_endpoint_mismatch_v=max(float(abs(d[k][-1]-d[k][0])) for k in ['vp','vn','out','ctrl','vc1','hp','hn','XV.XL.nfilt']))
  out['dominant_vco_harmonic']=int(np.argmax(abs(fd['vp'][1:]-fd['vn'][1:]))+1)
  out['dominant_output_harmonic']=int(np.argmax(abs(fd['out'][1:]))+1)
  out['pass_periodic_waveform']=bool(abs(T*24e6-1)<1e-6 and nv==164 and nd==41 and nr==1 and out['dominant_vco_harmonic']==164 and out['dominant_output_harmonic']==41 and .05<out['tank_diff_pp_v']<3.6 and max(abs(d['vp']).max(),abs(d['vn']).max())<1.8 and .2<out['control_range_v'][0]<out['control_range_v'][1]<1 and out['max_saved_voltage_endpoint_mismatch_v']<1e-3)
 return out

def main():
 jobs=[R/'loop_periodic/loop_quiet10_pss',R/'loop_periodic_recover/loop_quiet10_pss_recover',R/'loop_periodic_functional/loop_quiet10_pss_functional']
 attempts=[analyze(job) for job in jobs if (job/'result.json').exists()]
 accepted=[a for a in attempts if a.get('pass_periodic_waveform')]
 out=dict(accepted[0] if accepted else attempts[-1]);out['attempts']=attempts
 out['tolerance_study']=json.loads((H/'results/pss_tolerance_study.json').read_text())
 out['initial_interruption_review']=json.loads((H/'results/pss_recovery_provenance.json').read_text())
 (H/'results/periodic_validation.json').write_text(json.dumps(out,indent=2)+'\n');print('Periodic attempts:',len(attempts),'accepted waveforms:',len(accepted))

if __name__=='__main__':main()
