"""Independent periodic checks, sampled PSD integration and device noise budget."""
import json,re
import numpy as np
from analyze import H,R,parse,wavecheck

def header(path,key):
 return float(re.search('"'+re.escape(key)+'"\\s+([0-9.eE+\\-]+)',path.read_text())[1])

def device_totals(path,nfreq):
 # The bridge flat parser cannot decode device STRUCT values. Parse the named
 # total field explicitly and validate every instance length and the total PSD.
 text=path.read_text();types={}
 for name,body in re.findall(r'"([^"]+)" STRUCT\((.*?)\) PROP\(',text,re.S):
  fields=re.findall(r'^"([^"]+)" FLOAT DOUBLE PROP\(',body,re.M)
  if 'total' in fields:types[name]=(len(fields),fields.index('total'))
 trace=text.split('\nTRACE\n',1)[1].split('\nVALUE\n',1)[0]
 names=dict(re.findall(r'^"([^"]+)" "([^"]+)"$',trace,re.M))
 values=text.split('\nVALUE\n',1)[1];cols={}
 for name,body in re.findall(r'^"([^"]+)" \(\n(.*?)\n\)',values,re.M|re.S):
  typ=names[name];assert typ in types,typ
  count,idx=types[typ];v=np.fromstring(body,sep=' ');assert len(v)==count
  cols.setdefault(name,[]).append(v[idx])
 for k,v in cols.items():
  assert len(v)==nfreq,(k,len(v),nfreq)
  assert np.all(np.isfinite(v)) and min(v)>=0,(k,'nonfinite or negative device total PSD')
 return {k:np.asarray(v) for k,v in cols.items()}

def main():
 protocol=json.loads((H/'results/noise_protocol.json').read_text());lim=protocol['precision_limits']
 rows=[];spectra={}
 for job in sorted(R.glob('noise_*/*')):
  rp=job/'result.json'
  if not rp.exists():continue
  rec=json.loads(rp.read_text())
  if not rec.get('remote_inputs_match'):continue
  row=dict(case=job.name,run=job.parent.name,simulator_ok=rec['ok'],valid_noise=False);rows.append(row)
  if not rec['ok']:continue
  raw=job/(job.name+'.raw');p=raw/'pnMedge.0.sample.pnoise'
  if not p.exists():continue
  wave=wavecheck(parse(raw/'pss.td.pss'),True)
  fd=parse(raw/'pss.fd.pss');f0=984e6
  fd_signals=dict(out=fd['out'],rf=fd['vp']-fd['vn'])
  if wave['topology']=='cml':fd_signals.update(data=fd['dp']-fd['dn'],clock=fd['XRT.ckp']-fd['XRT.ckn'],retimed=fd['XRT.qp']-fd['XRT.qn'])
  else:fd_signals.update(data=fd['data'],clock=fd['clk'])
  harmonics={k:int(round(fd['freq'][1+np.argmax(np.abs(v[1:]))]/f0)) for k,v in fd_signals.items()}
  expected=dict(out=1,rf=4,data=1,clock=4)
  if wave['topology']=='cml':expected['retimed']=1
  periodic_ok=wave['pass_periodic'] and harmonics==expected
  d=parse(p);f=d['freq'];slew=header(p,'slew rate event_1');sv=d['out']**2;st=sv/slew**2
  assert np.all(np.diff(f)>0) and np.all(np.isfinite(st)) and np.all(sv>0) and slew>0
  jee=float(parse(raw/'pnMedge.0.Jee.pnoise')['Jee'][0]);variance=float(np.trapezoid(st,f));numeric=np.sqrt(variance)
  bands=[]
  for lo,hi in zip([1e4,1e6,1e7,1e8],[1e6,1e7,1e8,492e6]):
   grid=np.r_[lo,f[(f>lo)&(f<hi)],hi];part=float(np.trapezoid(np.interp(grid,f,st),grid))
   bands.append(dict(band_hz=[lo,hi],jitter_fs=float(np.sqrt(part)*1e15),variance_fraction=part/variance))
  components=device_totals(p,len(f))
  # Device arrays are PSD; out is ASD. Check the decomposition before attribution.
  sum_psd=sum(components.values());sumerr=float(max(abs(sum_psd/sv-1)))
  grouped={};subgroups={};rank=[]
  for k,v in components.items():
   var=float(np.trapezoid(v/slew**2,f));prefix=k.split('.')[0]
   grouped[prefix]=grouped.get(prefix,0)+var
   sub='.'.join(k.split('.')[:2]) if len(k.split('.'))>2 else k.split('.')[0]+'.bias_and_passives'
   subgroups[sub]=subgroups.get(sub,0)+var
   rank.append(dict(device=k,variance_s2=var,jitter_fs=float(np.sqrt(max(0,var))*1e15),variance_fraction=var/variance))
  row.update(periodic=wave,dominant_harmonics=harmonics,pass_periodic=bool(periodic_ok),band_hz=[float(f[0]),float(f[-1])],noise_by_band=bands,fundamental_hz=header(p,'fundamental frequency'),slew_v_per_s=slew,numeric_jitter_fs=float(numeric*1e15),spectre_jee_fs=jee*1e15,integration_relative_error=float(abs(numeric/jee-1)),
   device_psd_sum_max_relative_error=sumerr,noise_budget_valid=bool(sumerr<.01),noise_by_instance={k:dict(variance_s2=v,jitter_fs=float(np.sqrt(max(0,v))*1e15),variance_fraction=v/variance) for k,v in grouped.items()},noise_by_subblock={k:dict(jitter_fs=float(np.sqrt(max(0,v))*1e15),variance_fraction=v/variance) for k,v in subgroups.items()},top_devices=sorted(rank,key=lambda x:x['variance_s2'],reverse=True)[:25])
  row['valid_noise']=bool(periodic_ok and row['noise_budget_valid'] and abs(f[0]/1e4-1)<1e-9 and abs(f[-1]/492e6-1)<1e-9 and abs(numeric/jee-1)<lim['numeric_vs_jee'])
  spectra[job.name+'_f']=f;spectra[job.name+'_st']=st
 by={x['case']:x for x in rows};precision={}
 for a in rows:
  if not a['case'].endswith('_coarse'):continue
  b=by.get(a['case'].removesuffix('_coarse')+'_fine');key=a['case'].removesuffix('_coarse')
  x=dict(status='not_run',pass_precision=False);precision[key]=x
  if not b:continue
  x['status']='completed'
  if a['valid_noise'] and b['valid_noise']:
   assert np.allclose(spectra[a['case']+'_f'],spectra[b['case']+'_f'],rtol=1e-10,atol=0)
   rel=b['numeric_jitter_fs']/a['numeric_jitter_fs']-1;delta=10*np.log10(spectra[b['case']+'_st']/spectra[a['case']+'_st'])
   x.update(relative_jitter_change=float(rel),max_abs_spectrum_delta_db=float(max(abs(delta))),pass_precision=bool(abs(rel)<lim['relative_integrated_jitter'] and max(abs(delta))<lim['max_spectrum_delta_db']))
 out=dict(protocol=protocol,cases=rows,precision=precision)
 (H/'results/noise_validation.json').write_text(json.dumps(out,indent=2,allow_nan=False)+'\n')
 np.savez_compressed(H/'results/noise_spectra.npz',**spectra)
 print(json.dumps(dict(cases=[{k:r.get(k) for k in ['case','simulator_ok','valid_noise','numeric_jitter_fs','noise_by_instance','noise_budget_valid']} for r in rows],precision=precision),indent=2))

if __name__=='__main__':main()

