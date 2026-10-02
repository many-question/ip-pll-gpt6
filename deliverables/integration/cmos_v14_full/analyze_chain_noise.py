"""Current-chain device noise with measured RF replay; never full-PLL jitter."""
from pathlib import Path
import json,re
import numpy as np
from virtuoso_bridge.spectre.parsers import parse_spectre_psf_ascii
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
def parse(p):return {k:np.asarray(v) for k,v in parse_spectre_psf_ascii(p).data.items() if k!='units'}
def header(p,key):return float(re.search('"'+re.escape(key)+'"\\s+([0-9.eE+\\-]+)',p.read_text())[1])
def cross(t,v,level=.6):
 i=np.flatnonzero((v[:-1]<level)&(v[1:]>=level));return t[i]+(level-v[i])*np.diff(t)[i]/np.diff(v)[i]
def devices(p,n):
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
calibration=json.loads((H/'results/noise_measurement_fixture.json').read_text())
assert calibration['passed'],'The exact164MHz/ratio6 tool calibration must pass first'
rows=[];spectra={}
for rp in sorted(R.glob('chainnoise*/*/result.json')):
 job=rp.parent;rec=json.loads(rp.read_text());assert rec['remote_inputs_match'];log=(job/'spectre.out').read_text(errors='replace')
 row=dict(run=job.parent.name,case=job.name,simulator_completed='spectre completes with 0 errors' in log,source_result=str(rp.relative_to(ROOT)));rows.append(row)
 row['exact_harmonic_flicker_warning']='SPCRTRF-15037' in log
 if not rec['ok']:continue
 raw=job/(job.name+'.raw');td=parse(raw/'pss.td.pss');fd=parse(raw/'pss.fd.pss');t=td['time'];T=t[-1]-t[0]
 expected={'vp':24,'clk':24,'q1':12,'data':6,'out':6,'acqclk':6,'XD.d8':3,'XD.d12':2}
 harmonics={k:int(round(fd['freq'][1+np.argmax(abs(fd[k][1:]))]/164e6)) for k in expected}
 e=cross(t,td['out']);periods=np.diff(np.r_[e,e[0]+T]) if len(e) else np.array([0.])
 endpoint=max(float(abs(td[k][-1]-td[k][0])) for k in expected)
 periodic=bool(harmonics==expected and len(e)==6 and abs(T*164e6-1)<1e-7 and max(abs(periods*984e6-1))<.02 and endpoint<1e-3)
 row.update(periodic_passed=periodic,dominant_harmonics=harmonics,output_edges=len(e),endpoint_max_v=endpoint,period_ns=float(T*1e9),output_voltage_range_v=[float(min(td['out'])),float(max(td['out']))])
 p=raw/'pnMedge.0.sample.pnoise';d=parse(p);f=d['freq'];slew=header(p,'slew rate event_1');sv=d['out']**2;st=sv/slew**2
 assert slew>0 and np.all(np.diff(f)>0) and np.all(np.isfinite(st))
 components=devices(p,len(f));sumerr=float(max(abs(sum(components.values())-sv)/np.maximum(sv,1e-300)))
 var=float(np.trapezoid(st,f));jitter=float(np.sqrt(var)*1e15);jee=float(parse(raw/'pnMedge.0.Jee.pnoise')['Jee'][0])*1e15
 # The independently validated Spectre21.1 fixture inaccuracy_v7 shows that
 # autoJee clips at the last saved frequency<=PSSfund/2 even with sampleratio>1.
 # Preserve both numbers and compare Jee only with that actual clipped band.
 clip=f<=164e6/2*(1+1e-12)
 clipped_fs=float(np.sqrt(np.trapezoid(st[clip],f[clip]))*1e15)
 cliperr=abs(clipped_fs/jee-1)
 ratio=header(p,'sample ratio factor')
 grouped={}
 detail={};device_variances={}
 for k,v in components.items():
  value=float(np.trapezoid(v/slew**2,f));g=k.split('.')[0];grouped[g]=grouped.get(g,0)+value
  sub='.'.join(k.split('.')[:2]);detail[sub]=detail.get(sub,0)+value;device_variances[k]=value
 row.update(jitter_fs=jitter,spectre_jee_fs=jee,full_band_vs_auto_jee_relative_difference=jitter/jee-1,
    auto_jee_grid_cutoff_hz=float(f[clip][-1]),grid_clipped_integral_fs=clipped_fs,clipped_vs_auto_jee_relative_error=cliperr,
    sample_ratio_header=ratio,slew_v_per_s=slew,band_hz=[float(f[0]),float(f[-1])],device_psd_sum_max_relative_error=sumerr,
    noise_by_instance={k:dict(jitter_fs=float(np.sqrt(v)*1e15),variance_fraction=v/var) for k,v in grouped.items()},
    noise_by_subinstance={k:dict(jitter_fs=float(np.sqrt(v)*1e15),variance_fraction=v/var) for k,v in sorted(detail.items(),key=lambda kv:-kv[1])},
    top_devices=[dict(device=k,jitter_fs=float(np.sqrt(v)*1e15),variance_fraction=v/var) for k,v in sorted(device_variances.items(),key=lambda kv:-kv[1])[:20]],
    power_mw={k:float(-1.2*np.trapezoid(td[k],t)/T*1e3) for k in ['VDD:p','VRX:p','VRT:p']})
 row['single_case_valid']=bool(periodic and sumerr<.01 and cliperr<.015 and ratio==6 and abs(f[0]/1e4-1)<1e-9 and abs(f[-1]/492e6-1)<1e-9 and row['simulator_completed'])
 spectra[job.name+'_f']=f;spectra[job.name+'_st']=st
 for group in grouped:
  spectra[job.name+'_'+group+'_st']=sum(v for k,v in components.items() if k.split('.')[0]==group)/slew**2
out=dict(scope='Physical current RF receiver, full programmable divider and retimer/buffer, plus physical quiet shared-counter clock input load. TT27,1.2V,10fF,selectedM4. Ideal external measured RF replay at3.936GHz. This excludes VCO, main loop, reference, control and their impedance feedback; not full-PLL jitter.',
 period='164MHz PSS retains÷8/÷12 branch states;24 RF cycles and6 output cycles. sampleratio6, selected first rising-edge event. Other periodic edge positions are not yet checked.',
 integration_boundary='Explicit10kHz-492MHz PSD/slew^2 integral is the reported band. In this Spectreversion autoJee clips to the last saved gridpoint<=PSSfund/2(82MHz); it is not the full-band result. Check autoJee against its clipped numerical integral separately.',
 tool_normalization_evidence='share/deliverables/integration/cmos_v14_full/results/noise_measurement_fixture.json: exact164MHz/ratio6 identical-edge LTI RC fixture matches analytic kT/C within0.4percent and independently confirms clipped autoJee. Earlier accuracy_v7 also checked alternate PSS fundamental. Neither validates actual PLL edge-position invariance.',cases=rows)
out['frequency_grid_boundary']='The original log grid hits492MHz=3*PSSfund exactly and logsSPCRTRF-15037 (infinite flicker noise omitted). Retain the numerical integral, but require separate finite-offset checks around164/328/492MHz before treating the grid as adequately resolved. Single-case validity and step/sideband precision checks do not by themselves resolve that warning.'
coarse=next((r for r in rows if r['case']=='chain_noise_coarse_tt' and r.get('single_case_valid')),None)
fine=next((r for r in rows if r['case']=='chain_noise_fine_tt' and r.get('single_case_valid')),None)
out['precision']=dict(status='not_complete',passed=False)
if coarse and fine:
 a=spectra['chain_noise_coarse_tt_st'];b=spectra['chain_noise_fine_tt_st'];assert np.allclose(spectra['chain_noise_coarse_tt_f'],spectra['chain_noise_fine_tt_f'])
 delta=10*np.log10(b/a);rel=fine['jitter_fs']/coarse['jitter_fs']-1
 out['precision']=dict(status='complete',relative_jitter_change=rel,max_spectrum_delta_db=float(max(abs(delta))),passed=bool(abs(rel)<.01 and max(abs(delta))<.1))
(H/'results/chain_noise_validation.json').write_text(json.dumps(out,indent=2)+'\n')
np.savez_compressed(H/'results/chain_noise_spectra.npz',**spectra)
print(json.dumps(out,indent=2))
