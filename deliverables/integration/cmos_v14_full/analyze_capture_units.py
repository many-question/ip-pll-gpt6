"""Compare MOS controller outputs with independently clocked graph expectations."""
from pathlib import Path
import json,re,hashlib
import numpy as np
from virtuoso_bridge.spectre.parsers import parse_psf_ascii_directory
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
R=ROOT/'research/runs/spectre_cmos_v14_full'
reference=json.loads((H/'results/capture_repair_logic.json').read_text())
rows=[];fragments=[];completed={}
for run in sorted(R.glob('repairunits*')):
 for rp in sorted(run.glob('*/result.json')):
  rec=json.loads(rp.read_text())
  if not rec.get('local_outputs_sha256'):continue
  assert rec['remote_inputs_match']
  job=rp.parent;log=(job/'spectre.out').read_text(errors='replace')
  row=dict(run=run.name,case=job.name,source_result=str(rp.relative_to(ROOT)),
           simulator_completed='spectre completes with 0 errors' in log)
  if not row['simulator_completed']:
   fragments.append(row);continue
  if job.name not in completed or rec['time']>completed[job.name][0]['time']:
   completed[job.name]=(rec,row,job)
for rec,row,job in completed.values():
  chain=[(rec,job)]
  while chain[0][0].get('native_state'):
   native=chain[0][0]['native_state']
   assert native['remote_hash_match']
   assert hashlib.sha256((ROOT/native['local']).read_bytes()).hexdigest()==native['sha256']
   prior=R/native['source_snapshot']/job.name
   assert prior not in [p for _,p in chain]
   pr=json.loads((prior/'result.json').read_text());assert pr['remote_inputs_match']
   a={k:v for k,v in rec['inputs_sha256'].items() if k!=job.name+'.scs'}
   b={k:v for k,v in pr['inputs_sha256'].items() if k!=job.name+'.scs'}
   assert a==b
   chain.insert(0,(pr,prior))
  sets=[]
  for record,path in chain:
   raw=path/'waveforms.npz'
   if not raw.exists():
    parsed=parse_psf_ascii_directory(path/(job.name+'.raw'))
    parsed={k:np.atleast_1d(v) for k,v in parsed.items() if k!='units' and np.asarray(v).dtype.kind in 'biufc'}
    np.savez_compressed(raw,**parsed)
   with np.load(raw) as z:sets.append({k:z[k] for k in z.files})
   tb=(path/'inputs'/(job.name+'.scs')).read_text()
   assert 'maxstep=500p' in tb and 'reltol=1e-4' in tb
  assert sets[0]['time'][0]==0
  keys=set.intersection(*(set(x) for x in sets));pieces=[]
  for i,x in enumerate(sets):
   keep=x['time']<sets[i+1]['time'][0] if i+1<len(sets) else np.ones(len(x['time']),bool)
   pieces.append({k:x[k][keep] for k in keys if len(x[k])==len(x['time'])})
  d={k:np.concatenate([p[k] for p in pieces]) for k in pieces[0]}
  assert np.all(np.diff(d['time'])>0) and max(np.diff(d['time']))<1.1e-9
  row['source_segments']=[str((p/'result.json').relative_to(ROOT)) for _,p in chain]
  rows.append(row)
  trial='fll' if 'repair_fll_' in job.name else 'supervisor'
  trace=reference['fll_mos_stimulus' if trial=='fll' else 'supervisor_mos_stimulus']
  errors=[];min_low=0.;min_high=1.2;max_low=0.;valid=True
  widths={'coarse':8,'dac':6,'state_out':3}
  for point in trace:
   time=(135+point['cycle']*1000/24)*1e-9 if trial=='fll' else point['time_us']*1e-6
   sample=time+10e-9
   assert sample<=d['time'][-1]
   for key,value in point['expected'].items():
    width=widths.get(key,1)
    for bit in range(width):
     name=key+str(bit) if width>1 else key
     voltage=float(np.interp(sample,d['time'],d[name]));expect=(value>>bit)&1
     passed=voltage>1.0 if expect else voltage<.2
     if expect:min_high=min(min_high,voltage)
     else:max_low=max(max_low,voltage);min_low=min(min_low,voltage)
     if not passed:
      valid=False
      if len(errors)<30:errors.append(dict(time_us=time*1e6,signal=name,expected=expect,voltage=voltage))
  row.update(passed=valid,sampled_reference_edges=len(trace),min_expected_high_v=min_high,
    max_expected_low_v=max_low,min_expected_low_v=min_low,first_mismatches=errors,
    measurement='All output bits sampled10ns after each nominal reference rise; high>1.0V,low<0.2V,1.2V supply. Not completePLL capture.')
out=dict(scope=__doc__,cases=rows,checkpoint_fragments=fragments,completed=len(rows)==6,passed=len(rows)==6 and all(r.get('passed',False) for r in rows))
(H/'results/capture_repair_units.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
