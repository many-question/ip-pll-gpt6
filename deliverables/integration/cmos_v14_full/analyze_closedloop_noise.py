"""Validate periodic locked-core results without claiming full-PLL jitter."""
from pathlib import Path
import argparse,re,json,hashlib,sys
import numpy as np
from virtuoso_bridge.spectre.parsers import parse_spectre_psf_ascii
from analyze import cross
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
def parse(p):return {k:np.asarray(v) for k,v in parse_spectre_psf_ascii(p).data.items() if k!='units'}
def contributions(p,n):
 s=p.read_text();types={}
 for name,body in re.findall(r'"([^\"]+)" STRUCT\((.*?)\) PROP\(',s,re.S):
  fields=re.findall(r'^"([^\"]+)" FLOAT DOUBLE PROP\(',body,re.M)
  if 'total' in fields:types[name]=(len(fields),fields.index('total'))
 names=dict(re.findall(r'^"([^\"]+)" "([^\"]+)"$',s.split('\nTRACE\n',1)[1].split('\nVALUE\n',1)[0],re.M));cols={}
 for name,body in re.findall(r'^"([^\"]+)" \(\n(.*?)\n\)',s.split('\nVALUE\n',1)[1],re.M|re.S):
  length,idx=types[names[name]];a=np.fromstring(body,sep=' ');assert len(a)==length
  cols.setdefault(name,[]).append(a[idx])
 for k,v in cols.items():assert len(v)==n and np.all(np.isfinite(v)) and min(v)>=0,k
 return {k:np.asarray(v) for k,v in cols.items()}
parser=argparse.ArgumentParser()
parser.add_argument('runs',nargs='*')
parser.add_argument('--output',default='closedloop_noise_validation.json')
args=parser.parse_args()
assert Path(args.output).name==args.output and args.output.endswith('.json')
rows=[];spectra={}
for run in args.runs or ['corenoiseprobe01']:
 for rp in sorted((R/run).glob('*/result.json')):
  j=rp.parent;rec=json.loads(rp.read_text())
  if not rec.get('local_outputs_sha256'):continue
  assert rec['remote_inputs_match']
  log=(j/'spectre.out').read_text(errors='replace')
  row=dict(run=run,case=j.name,source_result=rp.relative_to(ROOT).as_posix(),source_sha256=hashlib.sha256(rp.read_bytes()).hexdigest(),simulator_completed='spectre completes with 0 errors' in log,warnings=[x.strip() for x in log.splitlines() if 'WARNING (' in x],full_pll_acceptance=False);rows.append(row)
  row['pss_converged']='pss: The steady-state solution was achieved' in log
  row['periodic_passed']=False
  row['noise_consistent']=False
  row['probe_passed']=False
  if not row['simulator_completed'] or not row['pss_converged']:continue
  tb=(j/'inputs'/(j.name+'.scs')).read_text()
  row['fresh_pss']=not rec.get('periodic_state') and 'readpss=' not in tb
  if not row['fresh_pss']:
   row['acceptance_status']='MOS readpss result excluded until the observed reuse inconsistency is resolved.'
   continue
  raw=j/(j.name+'.raw');td=parse(raw/'pss.td.pss');fd=parse(raw/'pss.fd.pss');t=td['time'];T=t[-1]-t[0]
  expected={'XP.refb':6,'XP.vp':984,'XP.clk':984,'XP.q1':492,'XP.data':246,'out':246,'XP.XD.d8':123,'XP.XD.d12':82}
  if 'XP.XD.d6' in td:expected['XP.XD.d6']=164
  if 'XP.acqclk' in td:expected['XP.acqclk']=246
  harmonic={k:int(round(fd['freq'][1+np.argmax(abs(fd[k][1:]))]/4e6)) for k in expected}
  e=cross(t,td['out']);period=np.diff(np.r_[e,e[0]+T]) if len(e) else np.array([0.])
  endpoints={k:float(abs(y[-1]-y[0])) for k,y in td.items() if k!='time' and ':' not in k}
  endpoint=max(endpoints.values())
  branch_edges={}
  for k,count in expected.items():
   if k=='XP.vp':continue
   edges=cross(t,td[k]);pt=np.diff(np.r_[edges,edges[0]+T]) if len(edges) else np.array([0.])
   branch_edges[k]=dict(rising_edges=len(edges),expected=count,
      max_period_fraction_error=float(max(abs(pt*count/T-1))),
      passed=bool(len(edges)==count and max(abs(pt*count/T-1))<.02 and min(td[k])<.2 and max(td[k])>1))
  coarse_held=all(np.all(td[f'XP.b{i}']>.9) if 23&(1<<i) else np.all(td[f'XP.b{i}']<.3) for i in range(8))
  row.update(period_ns=float(T*1e9),output_edges=len(e),dominant_harmonics=harmonic,endpoint_max_v=endpoint,
   endpoint_errors_v=endpoints,branch_edges=branch_edges,coarse23_held=bool(coarse_held),
   periodic_passed=bool(abs(T*4e6-1)<1e-7 and harmonic==expected and len(e)==246 and max(abs(period*984e6-1))<.02 and endpoint<1e-3 and coarse_held and all(v['passed'] for v in branch_edges.values())),
   analog_ranges_v={k:[float(min(td[k])),float(max(td[k]))] for k in ['XP.ctrl','XP.vc1','XP.hp','XP.hn','XP.vp','XP.vn','XP.preset']},
   period_power_mw=float(-1.2*np.trapezoid(td['VDD:p'],t)/T*1e3))
  p=raw/'pnMedge.0.sample.pnoise';d=parse(p);f=d['freq'];slew=float(re.search(r'"slew rate event_1"\s+([0-9.eE+\-]+)',p.read_text())[1]);sv=d['out']**2;st=sv/slew**2
  assert slew>0 and np.all(np.diff(f)>0) and np.all(np.isfinite(st))
  dev=contributions(p,len(f));err=float(max(abs(sum(dev.values())-sv)/np.maximum(sv,1e-300)))
  grouped={}
  for name,v in dev.items():
   group='.'.join(name.split('.')[:2])
   grouped[group]=grouped.get(group,0)+v/slew**2
  assert np.all(np.isfinite(sv)) and np.all(sv>0)
  row.update(offsets_hz=f.tolist(),timing_psd_s2_per_hz=st.tolist(),slew_v_per_s=slew,device_sum_relative_error=err,noise_consistent=bool(err<1e-7),group_psd_s2_per_hz={k:v.tolist() for k,v in grouped.items()},pnoise_sha256=hashlib.sha256(p.read_bytes()).hexdigest())
  row['probe_passed']=row['periodic_passed'] and row['noise_consistent']
  key=run+'_'+j.name
  spectra[key+'_f']=f;spectra[key+'_st']=st
  for k,v in grouped.items():spectra[key+'_'+k+'_st']=v
  # Six offsets are a feasibility/attribution probe, never an accepted integral.
  if row['probe_passed'] and len(f)>=90 and abs(f[0]/1e4-1)<1e-9 and abs(f[-1]/492e6-1)<1e-9:
   row['provisional_jitter_fs']=float(np.sqrt(np.trapezoid(st,f))*1e15)
   row['provisional_group_jitter_fs']={k:float(np.sqrt(np.trapezoid(v,f))*1e15) for k,v in grouped.items()}
  else:row['jitter_integral_status']='not_computed: sparse grid or periodic/noise gates not passed'
  row['acceptance_status']='Pending edge/alias and numerical convergence plus full-DUT excluded-control effects; not complete PLL.'
(H/'results'/args.output).write_text(json.dumps(dict(scope=__doc__,cases=rows,integration='10kHz to fout/2, deterministic spur lines excluded; autoJee is not used as the full-band integral',full_pll_acceptance=False),indent=2)+'\n')
if spectra:np.savez_compressed(H/'results'/(Path(args.output).stem+'_spectra.npz'),**spectra)
for r in rows:print(r['run'],r.get('periodic_passed'),r.get('provisional_jitter_fs'),r.get('jitter_integral_status'))
