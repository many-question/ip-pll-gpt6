"""Three-offset phase and noise-isolation diagnostics, not full-band jitter."""
from pathlib import Path
import json,re
import numpy as np
from virtuoso_bridge.spectre.parsers import parse_spectre_psf_ascii
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
protocol=json.loads((H/'results/chain_probe_protocol.json').read_text())
basejob=R/'chainnoise02/chain_noise_coarse_tt';baserec=json.loads((basejob/'result.json').read_text())
basez=np.load(H/'results/chain_noise_spectra.npz');bn='chain_noise_coarse_tt';bf=basez[bn+'_f']
def parse(p):return {k:np.asarray(v) for k,v in parse_spectre_psf_ascii(p).data.items() if k!='units'}
def header(p,key):return float(re.search('"'+re.escape(key)+'"\\s+([0-9.eE+\\-]+)',p.read_text())[1])
def columns(p,n):
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
rows=[]
for rp in sorted(R.glob('chainprobes01/*/result.json')):
 job=rp.parent;rec=json.loads(rp.read_text());log=(job/'spectre.out').read_text(errors='replace')
 row=dict(case=job.name,source_result=str(rp.relative_to(ROOT)),simulator_completed='spectre completes with 0 errors' in log);rows.append(row)
 assert rec['remote_inputs_match']
 current={k:v for k,v in rec['inputs_sha256'].items() if k!=job.name+'.scs'}
 expected={k:v for k,v in baserec['inputs_sha256'].items() if k!=basejob.name+'.scs'}
 assert current==expected,'Diagnostic circuit dependencies changed'
 if not row['simulator_completed']:continue
 warnings=[x.strip() for x in log.splitlines() if 'ignore' in x.lower() and 'noise' in x.lower()]
 row['ignored_noise_warnings']=warnings
 row['exact_harmonic_flicker_warning']=any('SPCRTRF-15037' in x for x in warnings)
 # An exact-harmonic 1/f pole warning is different from an ignored noiseon
 # control. Preserve it explicitly; the separate finite-offset probe checks
 # its significance. Neither this diagnostic nor PSD bookkeeping certifies
 # the complete-band integral.
 assert not any('SPCRTRF-15037' not in x for x in warnings),warnings
 raw=job/(job.name+'.raw');samples=[]
 for p in sorted(raw.glob('pnM*.0.sample.pnoise')):
  d=parse(p);f=d['freq'];assert np.allclose(f,protocol['offsets_hz'],rtol=1e-10)
  ix=np.array([int(np.argmin(abs(bf-x))) for x in f]);assert np.allclose(bf[ix],f,rtol=1e-10)
  slew=header(p,'slew rate event_1');st=d['out']**2/slew**2
  recs=dict(file=p.name,offsets_hz=f.tolist(),time_ps=header(p,'jittereventtime')*1e12,slew_v_per_s=slew,timing_psd_s2_per_hz=st.tolist())
  if job.name=='chain_edge_probe_tt':
   delta=10*np.log10(st/basez[bn+'_st'][ix]);recs.update(delta_vs_first_edge_db=delta.tolist(),passed=bool(max(abs(delta))<protocol['limits']['max_phase_psd_delta_db']))
  else:
   key=job.name.removeprefix('chain_gate_').removesuffix('_tt');groups=protocol['isolated_groups'][key]
   expected_st=sum(basez[bn+'_'+g+'_st'][ix] for g in groups);rel=st/expected_st-1
   cols=columns(p,len(f));excluded=sum(v for k,v in cols.items() if k.split('.')[0] not in groups)
   fraction=float(max(np.asarray(excluded)/np.maximum(d['out']**2,1e-300)))
   recs.update(enabled_groups=groups,relative_psd_difference=rel.tolist(),max_excluded_noise_fraction=fraction,passed=bool(max(abs(rel))<protocol['limits']['max_gate_psd_relative_difference'] and fraction<protocol['limits']['max_excluded_noise_fraction']))
  samples.append(recs)
 expected_count=5 if job.name=='chain_edge_probe_tt' else 1
 row.update(samples=samples,passed=bool(len(samples)==expected_count and all(x['passed'] for x in samples)))
result=dict(scope=__doc__,protocol=protocol,cases=rows,completed=len(rows)==5 and all(x['simulator_completed'] for x in rows),passed=len(rows)==5 and all(x.get('passed') for x in rows),limitation='Only1MHz,100MHz,492MHz; no full-band integral or all-offset edge invariance follows from these checks. Isolated-noise controls validate PSD contribution bookkeeping in the same loaded physicalchain.')
(H/'results/chain_probe_validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
