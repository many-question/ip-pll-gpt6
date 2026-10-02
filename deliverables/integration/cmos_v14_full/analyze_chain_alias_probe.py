"""Check finite-frequency noise near PSS harmonics without hiding pole warnings."""
from pathlib import Path
import json,re
import numpy as np
from virtuoso_bridge.spectre.parsers import parse_spectre_psf_ascii
def devices(p,n):
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
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
R=ROOT/'research/runs/spectre_cmos_v14_full'
job=R/'chainalias01/chain_alias_probe_tt'
rec=json.loads((job/'result.json').read_text())
assert rec['remote_inputs_match'] and rec['local_outputs_sha256']
log=(job/'spectre.out').read_text(errors='replace')
assert 'spectre completes with 0 errors' in log
base=json.loads((R/'chainnoise02/chain_noise_coarse_tt/result.json').read_text())
def deps(r,name):return {k:v for k,v in r['inputs_sha256'].items() if k!=name+'.scs'}
assert deps(rec,job.name)==deps(base,'chain_noise_coarse_tt')
p=job/(job.name+'.raw')/'pnMedge.0.sample.pnoise'
data={k:np.asarray(v) for k,v in parse_spectre_psf_ascii(p).data.items() if k!='units'}
slew=float(re.search(r'"slew rate event_1"\s+([0-9.eE+\-]+)',p.read_text())[1])
f=data['freq'];st=data['out']**2/slew**2
protocol=json.loads((H/'results/chain_alias_protocol.json').read_text())
assert np.allclose(f,protocol['offsets_hz'],rtol=1e-12)
z=np.load(H/'results/chain_noise_spectra.npz');bf=z['chain_noise_coarse_tt_f'];bs=z['chain_noise_coarse_tt_st']
baseline=np.exp(np.interp(np.log(f),np.log(bf),np.log(bs)))
delta=10*np.log10(st/baseline)
harmonic=np.rint(f/164e6).astype(int);distance=f-harmonic*164e6
warnings=[x.strip() for x in log.splitlines() if 'WARNING' in x or 'Warning from' in x]
result=dict(scope=__doc__,source_result=str((job/'result.json').relative_to(ROOT)),
    same_circuit_dependencies=True,condition='Currentphysicalchain,TT27,1.2V,984MHz/10fF,measuredRFreplay,firstedge,1ps/383sidebands. No device changes or suppression of noise sources.',
    warnings=warnings,offsets_hz=f.tolist(),distance_to_pss_harmonic_hz=distance.tolist(),
    timing_psd_s2_per_hz=st.tolist(),delta_vs_interpolated_coarse_db=delta.tolist(),
    max_absolute_delta_db=float(max(abs(delta))),
    finite_probe_passed=bool(max(abs(delta))<protocol['diagnostic_threshold_db'] and 'SPCRTRF-15037' not in log),
    interpretation='Finite-frequency probe only. No mathematical integral through a1/f singularity is asserted. If this check fails, the original logarithmic-grid141fs integral remains provisional and does not establish adequately resolved full-band chain noise.',
    protocol=protocol)
parts=devices(p,len(f));total=sum(parts.values())
assert max(abs(total/data['out']**2-1))<1e-6
excess=total[-1]-total[6]
ranked=sorted([(k,float((v[-1]-v[6])/excess)) for k,v in parts.items()],key=lambda x:-x[1])
result['near_492mhz_excess_contributors_1hz_vs_10khz_distance']=[dict(device=k,fraction=v) for k,v in ranked[:12]]
result['excess_diagnostic_boundary']='Difference between two finite offset PSDs in the same run; not full-band variance or proof of a physical low-frequency cutoff.'
# Preserve the failed pointwise threshold. Quantify how little bandwidth that
# narrow peak occupies under explicitly stated finite-observation assumptions.
# This is a sensitivity estimate, not a new acceptance limit or measured integral.
e1=st[-1]-bs[-1];e10=st[-2]-bs[-1]
if e1>0 and e10>0:
 alpha=float(np.log10(e1/e10));var=float(np.trapezoid(bs,bf));examples=[]
 for cut in [1.,1e-3,1e-6]:
  integral=e1*(1e4**(1-alpha)-cut**(1-alpha))/(1-alpha) if abs(alpha-1)>1e-8 else e1*np.log(1e4/cut)
  # Five sides: both sides at164/328MHz and the lower side at492MHz.
  extra=5*integral
  examples.append(dict(assumed_min_distance_hz=cut,estimated_added_variance_s2=float(extra),relative_to_coarse_variance=float(extra/var),estimated_jitter_increase_fs=float(np.sqrt(var)*np.expm1(.5*np.log1p(extra/var))*1e15)))
 result['conditional_peak_area_sensitivity']=dict(fitted_exponent_from_1_and_10hz=alpha,examples=examples,
  assumption='Assume all five harmonic sides have at most the observed492MHz1Hz excess and the same power-law exponent fitted at1/10Hz, between the stated cutoff and10kHz distance. This is an extrapolation; no physical cutoff is established and no requirement/band has been changed. Pointwise finite_probe_passed remains false when its original threshold is exceeded.')
(H/'results/chain_alias_validation.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
