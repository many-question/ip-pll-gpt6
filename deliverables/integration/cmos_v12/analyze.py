from pathlib import Path
import json,re
import numpy as np
from virtuoso_bridge.spectre.parsers import parse_spectre_psf_ascii
H=Path(__file__).resolve().parent;D=H.parents[2];ROOT=D.parent if D.name=='share' and (D.parent/'AGENTS.md').exists() else D;R=ROOT/'research/runs/spectre_cmos_v12'
def parse(p):return {k:np.asarray(v) for k,v in parse_spectre_psf_ascii(p).data.items() if k!='units'}
def cross(t,v,lev):
 i=np.flatnonzero((v[:-1]<lev)&(v[1:]>=lev));return t[i]+(lev-v[i])*np.diff(t)[i]/np.diff(v)[i]
def describe(t,v,f,lev=.6,periodic=False,digital=True):
 e=cross(t,v,lev);T=t[-1]-t[0];dt=np.diff(np.r_[e,e[0]+T]) if periodic and len(e) else np.diff(e);freq=len(e)/T if periodic else (1/np.mean(dt) if len(dt) else 0)
 err=float(max(abs(dt*f-1))) if len(dt) else 1e9
 return dict(range_v=[float(min(v)),float(max(v))],frequency_hz=float(freq),edges=len(e),max_period_error=err,pass_frequency=bool(abs(freq/f-1)<.001 and err<.02 and len(e)>=(1 if periodic else 10)),pass_swing=bool(min(v)<.2 and max(v)>1) if digital else bool(np.ptp(v)>.05))
def wavecheck(d,case,periodic=False):
 t=d['time'];frf=3936e6;lc=case.startswith('lc_')
 if lc:
  e=cross(t,d['vp']-d['vn'],0);frf=float(1/np.mean(np.diff(e))) if len(e)>1 else 1e-20
 fs=frf/4
 out=dict(signals={},periodic=periodic,actual_LC=lc,reference_RF_frequency_hz=frf)
 for k,f in dict(clk=frf,q1=frf/2,data=fs,out=fs).items():out['signals'][k]=describe(t,d[k],f,periodic=periodic)
 out['signals']['rf']=describe(t,d['vp']-d['vn'],frf,0,periodic,False)
 out['power_mw']={k:float(-1.2*np.trapezoid(v,t)/(t[-1]-t[0])*1e3) for k,v in d.items() if k in ['VDD:p','VRT:p','VRX:p','VVCO:p']}
 out['node_ranges_v']={k:[float(min(v)),float(max(v))] for k,v in d.items() if k.startswith('XRX.') and ':' not in k}
 out['pass_function']=bool(all(x['pass_frequency'] and x['pass_swing'] for x in out['signals'].values()))
 if periodic:
  out['endpoint_v']=max(float(abs(v[-1]-v[0])) for k,v in d.items() if k!='time' and ':' not in k)
  out['pass_periodic']=bool(out['pass_function'] and out['endpoint_v']<1e-3 and abs((t[-1]-t[0])*fs-1)<1e-7)
 return out
def main():
 rows=[]
 for rp in sorted(R.glob('*/*/result.json')):
  rec=json.loads(rp.read_text());job=rp.parent
  if not rec.get('remote_inputs_match'):continue
  row=dict(case=job.name,run=job.parent.name,sim_ok=rec['ok'],errors=rec['errors']);rows.append(row)
  if not rec['ok']:continue
  raw=job/(job.name+'.raw');p=raw/'pss.td.pss'
  if p.exists():row['wave']=wavecheck(parse(p),job.name,True)
  else:
   with np.load(job/'waveforms.npz') as z:row['wave']=wavecheck(dict(z),job.name)
 (H/'results/validation.json').write_text(json.dumps(rows,indent=2,allow_nan=False)+'\n')
 print(json.dumps([dict(case=r['case'],sim=r['sim_ok'],wave=r.get('wave')) for r in rows],indent=2))
if __name__=='__main__':main()
