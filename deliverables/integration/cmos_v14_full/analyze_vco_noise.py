"""Current VCO noise under a static-reference fixedM4 load; not PLL jitter."""
from pathlib import Path
import json,re
import numpy as np
from virtuoso_bridge.spectre.parsers import parse_spectre_psf_ascii
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
def parse(p):return {k:np.asarray(v) for k,v in parse_spectre_psf_ascii(p).data.items() if k!='units'}
def components(p,n):
 s=p.read_text();types={}
 for name,body in re.findall(r'"([^\"]+)" STRUCT\((.*?)\) PROP\(',s,re.S):
  fields=re.findall(r'^"([^\"]+)" FLOAT DOUBLE PROP\(',body,re.M)
  if 'total' in fields:types[name]=(len(fields),fields.index('total'))
 names=dict(re.findall(r'^"([^\"]+)" "([^\"]+)"$',s.split('\nTRACE\n',1)[1].split('\nVALUE\n',1)[0],re.M));cols={}
 for name,body in re.findall(r'^"([^\"]+)" \(\n(.*?)\n\)',s.split('\nVALUE\n',1)[1],re.M|re.S):
  size,i=types[names[name]];a=np.fromstring(body,sep=' ');assert len(a)==size
  cols.setdefault(name,[]).append(a[i])
 assert all(len(v)==n for v in cols.values())
 return {k:np.asarray(v) for k,v in cols.items()}
rows=[];spectra={};circuit_hashes=None
for rp in sorted(R.glob('vconoise*/*/result.json')):
 job=rp.parent;rec=json.loads(rp.read_text());assert rec['remote_inputs_match']
 log=(job/'spectre.out').read_text(errors='replace');row=dict(run=job.parent.name,case=job.name,simulator_completed='spectre completes with 0 errors' in log,source_result=str(rp.relative_to(ROOT)));rows.append(row)
 raw=job/(job.name+'.raw')
 if not row['simulator_completed'] or not (raw/'pn.pm.pnoise').exists():continue
 tb=(job/'inputs'/(job.name+'.scs')).read_text()
 assert 'noiseout=[usb am pm]' in tb and 'relharmnum=4' in tb
 assert 'noiseon_inst=[XV]' in tb
 current={k:v for k,v in rec['inputs_sha256'].items() if k!=job.name+'.scs'}
 if circuit_hashes is None:circuit_hashes=current
 assert current==circuit_hashes,'VCO precision comparison uses different circuit dependencies'
 if m:=re.search(r'estimated line width of the oscillator is\s+([0-9.eE+\-]+)\s*([kMG]?)Hz',log):
  row['tool_estimated_free_running_linewidth_hz']=float(m[1])*{'':1,'k':1e3,'M':1e6,'G':1e9}[m[2]]
  row['close_in_note']='Retain the tool-estimated free-running linewidth as a diagnostic. No integrated free-running jitter is inferred from the close-in linearized PM spectrum; no closed-loop jitter is claimed.'
 fd=parse(raw/'pss.fd.pss');td=parse(raw/'pss.td.pss');pn=parse(raw/'pn.pm.pnoise');f=pn['relative frequency'];t=td['time'];T=t[-1]-t[0]
 fc=float(fd['freq'][4]);peak=float(abs(fd['vp'][4]-fd['vn'][4]));carrier=peak**2/2
 numerical_peak=float(abs(2/T*np.trapezoid((td['vp']-td['vn'])*np.exp(-2j*np.pi*4*(t-t[0])/T),t)))
 L=pn['out']**2/carrier;parts=components(raw/'pn.pm.pnoise',len(f));summed=sum(parts.values())
 err=float(max(abs(summed/np.maximum(pn['out']**2,1e-300)-1)))
 excluded=sum(v for k,v in parts.items() if not k.startswith('XV.'));exfrac=float(max(np.asarray(excluded)/np.maximum(summed,1e-300)))
 h={k:int(round(fd['freq'][1+np.argmax(abs(fd[k][1:]))]/fd['freq'][1])) for k in ['vp','vn','clk','q1','data','out']}
 periodic=bool(h==dict(vp=4,vn=4,clk=4,q1=2,data=1,out=1) and abs(fc*T/4-1)<1e-8 and max(abs(td[k][-1]-td[k][0]) for k in ['vp','vn','out'])<1e-3)
 i=int(np.argmin(abs(np.log(f/1e6))));groups={}
 for k,v in parts.items():
  group='other'
  if '.XL.XP.' in k or '.XL.XN.' in k:group='inductor_RLC'
  elif '.XL.MN' in k:group='cross_coupled_core'
  elif '.XL.' in k:group='tail_and_bias'
  elif '.XBP.' in k or '.XBN.' in k:group='switched_cap_bank'
  groups[group]=groups.get(group,0)+float(v[i]/summed[i])
 row.update(frequency_hz=fc,output_hz=fc/4,rf_carrier_peak_v=peak,carrier_td_crosscheck_relative_error=numerical_peak/peak-1,dominant_harmonics=h,periodic_passed=periodic,
  phase_noise_dbc_per_hz={str(int(x)):float(np.interp(np.log(x),np.log(f),10*np.log10(L))) for x in [1e4,1e5,1e6,1e7,1e8]},
  vco_supply_power_mw=float(-1.2*np.trapezoid(td['VVCO:p'],t)/T*1e3),fixture_total_power_mw=float(-1.2*np.trapezoid(td['VDD:p'],t)/T*1e3),tank_range_v=[float(min(min(td['vp']),min(td['vn']))),float(max(max(td['vp']),max(td['vn'])))],
  component_psd_sum_error=err,excluded_noise_fraction=exfrac,fractions_at_1mhz=groups,top_contributors_at_1mhz=sorted([dict(device=k,variance_fraction=float(v[i]/summed[i])) for k,v in parts.items()],key=lambda x:-x['variance_fraction'])[:12],
  single_case_valid=bool(periodic and err<1e-6 and exfrac<1e-8 and abs(numerical_peak/peak-1)<.002))
 spectra[job.name+'_f']=f;spectra[job.name+'_L']=L
result=dict(scope=__doc__,condition='TT27,1.2V,Q5RLC,coarse23,control0.679V,actual fixedM4 chain/10fF,sampler continuously tracking with referenceDC0,onlyXVnoise. Includes physical resistor/MOS bias. Omits unused programmable branches and active24MHz sampling/closed loop.',cases=rows,precision=dict(completed=False,passed=False),normalization='Spectre21.1 help pnoise documents noiseout=[usb am pm] as SSB; this is distinct from the deprecated augmented AM/PM DSB output. L_SSB=out_V_per_sqrtHz^2/(RF_carrier_peak_V^2/2), with relharmnum=4. Carrier peak is independently checked by time-domain Fourier integration.',circuit_hashes=circuit_hashes,limitation='Phase-noise spectra at this static-reference operating point are block evidence. No complete-PLL RMS jitter or closed-loop suppression has been inferred.')
valid=[r for r in rows if r.get('single_case_valid')]
a=next((r for r in valid if r['case']=='vco_noise_coarse_tt'),None)
b=next((r for r in valid if r['case']=='vco_noise_check6_tt'),None)
if a and b:
 fa=spectra[a['case']+'_f'];fb=spectra[b['case']+'_f'];ix=np.array([int(np.argmin(abs(fa-x))) for x in fb]);assert np.allclose(fa[ix],fb,rtol=1e-9)
 delta=10*np.log10(spectra[b['case']+'_L']/spectra[a['case']+'_L'][ix]);frel=b['frequency_hz']/a['frequency_hz']-1
 result['precision']=dict(completed=True,scope='Six-offset check only, not full-grid convergence',offsets_hz=fb.tolist(),phase_noise_delta_db=delta.tolist(),max_phase_noise_delta_db=float(max(abs(delta))),relative_carrier_change=frel,passed=bool(max(abs(delta))<.1 and abs(frel)<1e-4))
(H/'results/vco_noise_validation.json').write_text(json.dumps(result,indent=2)+'\n');np.savez_compressed(H/'results/vco_noise_spectra.npz',**spectra);print(json.dumps(result,indent=2))
