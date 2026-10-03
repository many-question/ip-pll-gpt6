"""Validate periodic locked-core results without claiming full-PLL jitter."""
from pathlib import Path
import re,json,hashlib,sys
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
rows=[];spectra={}
for run in sys.argv[1:] or ['corenoiseprobe01']:
 for rp in sorted((R/run).glob('*/result.json')):
  j=rp.parent;rec=json.loads(rp.read_text());assert rec['remote_inputs_match']
  log=(j/'spectre.out').read_text(errors='replace')
  row=dict(run=run,case=j.name,source_result=rp.relative_to(ROOT).as_posix(),source_sha256=hashlib.sha256(rp.read_bytes()).hexdigest(),simulator_completed='spectre completes with 0 errors' in log,warnings=[x.strip() for x in log.splitlines() if 'WARNING (' in x],full_pll_acceptance=False);rows.append(row)
  if not row['simulator_completed']:continue
  raw=j/(j.name+'.raw');td=parse(raw/'pss.td.pss');fd=parse(raw/'pss.fd.pss');t=td['time'];T=t[-1]-t[0]
  expected={'XP.refb':6,'XP.vp':984,'XP.clk':984,'XP.q1':492,'XP.data':246,'out':246,'XP.XD.d8':123,'XP.XD.d12':82}
  harmonic={k:int(round(fd['freq'][1+np.argmax(abs(fd[k][1:]))]/4e6)) for k in expected}
  e=cross(t,td['out']);period=np.diff(np.r_[e,e[0]+T]) if len(e) else np.array([0.])
  endpoint=max(float(abs(td[k][-1]-td[k][0])) for k in expected)
  row.update(period_ns=float(T*1e9),output_edges=len(e),dominant_harmonics=harmonic,endpoint_max_v=endpoint,
   periodic_passed=bool(abs(T*4e6-1)<1e-7 and harmonic==expected and len(e)==246 and max(abs(period*984e6-1))<.02 and endpoint<1e-3),
   analog_ranges_v={k:[float(min(td[k])),float(max(td[k]))] for k in ['XP.ctrl','XP.vc1','XP.hp','XP.hn','XP.vp','XP.vn','XP.preset']},
   period_power_mw=float(-1.2*np.trapezoid(td['VDD:p'],t)/T*1e3))
  p=raw/'pnMedge.0.sample.pnoise';d=parse(p);f=d['freq'];slew=float(re.search(r'"slew rate event_1"\s+([0-9.eE+\-]+)',p.read_text())[1]);sv=d['out']**2;st=sv/slew**2
  assert slew>0 and np.all(np.diff(f)>0) and np.all(np.isfinite(st))
  dev=contributions(p,len(f));err=float(max(abs(sum(dev.values())-sv)/np.maximum(sv,1e-300)))
  grouped={}
  for name,v in dev.items():
   group='.'.join(name.split('.')[:2])
   grouped[group]=grouped.get(group,0)+v/slew**2
  row.update(offsets_hz=f.tolist(),timing_psd_s2_per_hz=st.tolist(),slew_v_per_s=slew,device_sum_relative_error=err,noise_consistent=bool(err<1e-7),group_psd_s2_per_hz={k:v.tolist() for k,v in grouped.items()})
  spectra[run+'_f']=f;spectra[run+'_st']=st
  for k,v in grouped.items():spectra[run+'_'+k+'_st']=v
  # Six offsets are a feasibility/attribution probe, never an accepted integral.
  if len(f)>=90 and abs(f[0]/1e4-1)<1e-9 and abs(f[-1]/492e6-1)<1e-9:
   row['provisional_jitter_fs']=float(np.sqrt(np.trapezoid(st,f))*1e15)
   row['provisional_group_jitter_fs']={k:float(np.sqrt(np.trapezoid(v,f))*1e15) for k,v in grouped.items()}
  else:row['jitter_integral_status']='not_computed: sparse probe is not an integration grid'
  row['acceptance_status']='Pending edge/alias and numerical convergence plus full-DUT excluded-control effects; not complete PLL.'
(H/'results/closedloop_noise_validation.json').write_text(json.dumps(dict(scope=__doc__,cases=rows,protocol='closedloop_noise_protocol.json',integration='10kHz to fout/2, deterministic spur lines excluded; autoJee is not used as the full-band integral'),indent=2)+'\n')
if spectra:np.savez_compressed(H/'results/closedloop_noise_spectra.npz',**spectra)
for r in rows:print(r['run'],r.get('periodic_passed'),r.get('provisional_jitter_fs'),r.get('jitter_integral_status'))
