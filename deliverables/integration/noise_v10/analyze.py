"""Check physical clock-chain experiments; waveform pass is not retiming signoff."""
from pathlib import Path
import json,re
import numpy as np
from virtuoso_bridge.spectre.parsers import parse_spectre_psf_ascii
H=Path(__file__).resolve().parent;D=H.parents[2]
ROOT=D.parent if D.name=='share' and (D.parent/'AGENTS.md').exists() else D
R=ROOT/'research/runs/spectre_noise_v10'
def parse(p):return {k:np.asarray(v) for k,v in parse_spectre_psf_ascii(p).data.items() if k!='units'}
def cross(t,v,level=0):
 i=np.flatnonzero((v[:-1]<level)&(v[1:]>=level));return t[i]+(level-v[i])*(t[i+1]-t[i])/(v[i+1]-v[i])
def describe(t,v,f,level=0,periodic=False):
 e=cross(t,v,level);T=t[-1]-t[0]
 dt=np.diff(np.r_[e,e[0]+T]) if periodic and len(e) else np.diff(e)
 avg=len(e)/T if periodic else (1/np.mean(dt) if len(dt) else 0)
 pe=float(max(abs(dt*f-1))) if len(dt) else None
 return dict(edges=len(e),frequency_hz=float(avg),range_v=[float(min(v)),float(max(v))],max_period_error=pe,
  pass_frequency=bool(len(e)>=(1 if periodic else 3) and abs(avg/f-1)<.001 and pe is not None and pe<.02))
def wavecheck(d,periodic=False):
 t=d['time'];mask=np.ones(len(t),dtype=bool) if periodic else ((t>=70e-9)&(t<=100e-9));t=t[mask];d={k:v[mask] for k,v in d.items() if k not in ('time','units')}
 T=t[-1]-t[0];out=dict(window_s=[float(t[0]),float(t[-1])],signals={});typ='cml' if 'dp' in d else 'feedback';out['topology']=typ
 sig={'rf':(d['vp']-d['vn'],3936e6,0),'out':(d['out'],984e6,.6)}
 if typ=='cml':sig.update(data=(d['dp']-d['dn'],984e6,0),clock=(d['XRT.ckp']-d['XRT.ckn'],3936e6,0),retimed=(d['XRT.qp']-d['XRT.qn'],984e6,0))
 else:sig.update(data=(d['data'],984e6,.6),clock=(d['clk'],3936e6,.6))
 for k,(v,f,lev) in sig.items():out['signals'][k]=describe(t,v,f,lev,periodic)
 ok=all(w['pass_frequency'] for w in out['signals'].values()) and min(d['out'])<.2 and max(d['out'])>1
 if typ=='feedback':ok &=min(d['clk'])<.2 and max(d['clk'])>1
 else:ok &=all(np.ptp(sig[k][0])>.05 and min(sig[k][0])<0<max(sig[k][0]) for k in ['data','clock','retimed'])
 out['pass_function']=bool(ok and (periodic or out['signals']['out']['edges']>20))
 out['power_mw']={k:float(-1.2*np.trapezoid(d[k],t)/T*1e3) for k in ['VDD:p','VRX:p','VRT:p'] if k in d}
 # Harmonic projections on dense time samples, independent of timestep uniformity.
 a,b=(t[0],t[-1]) if periodic else (np.ceil(t[0]*984e6)/984e6,np.floor(t[-1]*984e6)/984e6)
 grid=np.r_[a,t[(t>a)&(t<b)],b]
 out['projection_window_s']=[float(a),float(b)]
 out['rf_harmonic_peak_v']={k:float(abs(2*np.trapezoid(np.interp(grid,t,v)*np.exp(-2j*np.pi*3936e6*grid),grid)/(b-a))) for k,v in d.items() if ':' not in k}
 if typ=='cml' and not periodic:
  de=np.sort(np.r_[cross(t,sig['data'][0]),cross(t,-sig['data'][0])]);ce=np.sort(np.r_[cross(t,sig['clock'][0]),cross(t,-sig['clock'][0])]);re=np.sort(np.r_[cross(t,sig['retimed'][0]),cross(t,-sig['retimed'][0])])
  margins=[]
  for e in re[1:-1]:
   prev=de[de<e];near=ce[np.argmin(abs(ce-e))]
   if len(prev):margins.append([float((e-prev[-1])*1e12),float((e-near)*1e12)])
  out['retimed_edge_delays_ps']=margins
  out['timing_note']='Each row is retimed differential crossing minus previous raw data edge and nearest differential clock zero. Descriptive only; functional waveform does not prove suppression of divider timing errors.'
 if periodic:
  out['period_s']=float(T);out['endpoint_voltage_error']={k:float(abs(v[-1]-v[0])) for k,v in d.items() if ':' not in k}
  out['pass_periodic']=bool(ok and abs(T*984e6-1)<1e-7 and out['signals']['rf']['edges']==4 and out['signals']['out']['edges']==1 and out['signals']['data']['edges']==1 and max(out['endpoint_voltage_error'].values())<1e-3)
 return out
def main():
 rows=[]
 for rp in sorted(R.glob('*/*/result.json')):
  rec=json.loads(rp.read_text());job=rp.parent
  if not rec.get('remote_inputs_match'):continue
  log=(job/'spectre.out').read_text(errors='replace');row=dict(case=job.name,run=job.parent.name,sim_ok=rec['ok'],errors=rec['errors'],diagnostic_only=job.name.startswith('timing_'),final_counts=re.findall(r'spectre completes with (\d+) errors?, (\d+) warnings?',log),settings={k:re.findall(r'^\s{4}'+re.escape(k)+r' = (.+)$',log,re.M) for k in ['reltol','abstol(V)','abstol(I)','maxstep','method','relref']});rows.append(row)
  if not rec['ok']:continue
  raw=job/(job.name+'.raw');p=raw/'pss.td.pss'
  if p.exists():row['periodic']=wavecheck(parse(p),True)
  else:
   with np.load(job/'waveforms.npz') as z:row['transient']=wavecheck({k:z[k] for k in z.files})
 (H/'results/validation.json').write_text(json.dumps(rows,indent=2,allow_nan=False)+'\n')
 for r in rows:
  w=r.get('transient',r.get('periodic',{}));print(r['case'],r['sim_ok'],w.get('pass_function'),w.get('power_mw'),w.get('signals',{}).get('clock',{}).get('range_v'))
if __name__=='__main__':main()
