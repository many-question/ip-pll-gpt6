"""Validate divider periodic waveforms and independently integrate sampled noise."""
import json,re
import numpy as np
from analyze import H,R,parse,periodic

def header(path,key):
 return float(re.search('"'+re.escape(key)+'"\\s+([0-9.eE+\\-]+)',path.read_text())[1])

def main():
 protocol=json.loads((H/'results/divider_noise_protocol.json').read_text());limits=protocol['precision_limits']
 rows=[];spectra={}
 for job in sorted(R.glob('divider_noise*/*')):
  result=job/'result.json'
  if not result.exists():continue
  rec=json.loads(result.read_text())
  if not rec.get('remote_inputs_match'):continue
  row=dict(run=job.parent.name,case=job.name,simulator_ok=rec['ok'],valid_noise=False)
  rows.append(row)
  if not rec['ok']:continue
  p=job/(job.name+'.raw')/'pnMedge.0.sample.pnoise'
  if not p.exists():continue
  d=parse(p);f=d['freq'];slew=header(p,'slew rate event_1');st=d['out']**2/slew**2
  jee=float(parse(p.parent/'pnMedge.0.Jee.pnoise')['Jee'][0]);numeric=float(np.sqrt(np.trapezoid(st,f)))
  wave=periodic(job);err=abs(numeric/jee-1)
  row.update(periodic=wave,band_hz=[float(f[0]),float(f[-1])],fundamental_hz=header(p,'fundamental frequency'),slew_v_per_s=slew,spectre_jee_fs=jee*1e15,numeric_jitter_fs=numeric*1e15,integration_relative_error=err)
  row['valid_noise']=bool(wave['pass_divider_periodic'] and abs(f[0]/1e4-1)<1e-9 and abs(f[-1]/492e6-1)<1e-9 and err<limits['numeric_vs_spectre_jee_relative'])
  spectra[job.name+'_f']=f;spectra[job.name+'_st']=st
 by={x['case']:x for x in rows};precision={}
 for variant in ['base','clamp']:
  ka=f'noise_divider_{variant}_2ps';kb=f'noise_divider_{variant}_1ps'
  if ka not in by or kb not in by:continue
  a,b=by[ka],by[kb]
  x=dict(pass_precision=False);precision[variant]=x
  if not a['valid_noise'] or not b['valid_noise']:continue
  rel=b['numeric_jitter_fs']/a['numeric_jitter_fs']-1
  fa=spectra[ka+'_f'];fb=spectra[kb+'_f'];sa=spectra[ka+'_st'];sb=spectra[kb+'_st']
  assert np.allclose(fa,fb,rtol=1e-10,atol=0)
  delta=10*np.log10(sb/sa)
  x.update(relative_jitter_change=rel,max_abs_spectrum_delta_db=float(max(abs(delta))),pass_precision=bool(abs(rel)<limits['max_relative_integrated_jitter_change'] and max(abs(delta))<limits['max_spectrum_delta_db']))
 comparison=None
 if all(precision.get(v,{}).get('pass_precision') for v in ['base','clamp']):
  base=by['noise_divider_base_1ps']['numeric_jitter_fs'];clamp=by['noise_divider_clamp_1ps']['numeric_jitter_fs']
  comparison=dict(base_fs=base,clamp_fs=clamp,clamp_minus_base_fs=clamp-base,clamp_relative_change=clamp/base-1,scope=protocol['scope'])
  comparison['precision_change_fs']={v:abs(by[f'noise_divider_{v}_1ps']['numeric_jitter_fs']-by[f'noise_divider_{v}_2ps']['numeric_jitter_fs']) for v in ['base','clamp']}
  comparison['interpretation']='The base/clamp difference is smaller than the observed joint numerical refinement shifts; no resolved additive-noise benefit or penalty in this ideal-input fixture. Does not bound noise fed back into a real VCO.'
 out=dict(protocol=protocol,cases=rows,precision=precision,verified_comparison=comparison)
 (H/'results/divider_noise_validation.json').write_text(json.dumps(out,indent=2)+'\n')
 np.savez_compressed(H/'results/divider_noise_spectra.npz',**spectra)
 print(json.dumps(dict(cases=len(rows),precision=precision,comparison=comparison),indent=2))

if __name__=='__main__':main()
