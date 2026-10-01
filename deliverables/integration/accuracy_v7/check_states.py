"""Check overlap between each complete transient final state and saved waveform."""
import hashlib,json
import numpy as np
from analyze import H,R

def main():
 rows={}
 for job in sorted(R.glob('*/*')):
  if not (job/'final.ic').exists() or not (job/'result.json').exists():continue
  rec=json.loads((job/'result.json').read_text())
  if not rec.get('ok') or not rec.get('remote_inputs_match'):continue
  with np.load(job/'waveforms.npz') as z:
   if 'obsphase' not in z:continue
   states={}
   for line in (job/'final.ic').read_text().splitlines():
    p=line.split()
    if not p or p[0].startswith('#') or len(p)<2:continue
    try:states[p[0]]=float(p[1])
    except ValueError:continue
   deltas={k:abs(float(z[k][-1])-v) for k,v in states.items() if k in z}
   rows[job.name]=dict(max_abs_saved_state_delta=max(deltas.values()),saved_entries_checked=len(deltas),end_s=float(z['time'][-1]),pass_state_equality=bool(len(deltas)>=28 and max(deltas.values())<1e-10),state_sha256=hashlib.sha256((job/'final.ic').read_bytes()).hexdigest())
   assert rows[job.name]['pass_state_equality']
   source=next(iter(rec.get('initial_states',{}).values()),None)
   if source:
    initial={}
    for line in (job/'inputs'/source['source']).read_text().splitlines():
     p=line.split()
     if len(p)<2 or p[0].startswith('#'):continue
     try:
      if p[0] in z:initial[p[0]]=abs(float(z[p[0]][0])-float(p[1]))
     except ValueError:continue
    rows[job.name].update(initial_entries_checked=len(initial),max_abs_initial_state_delta=max(initial.values()),pass_initial_state_equality=bool(len(initial)>=20 and max(initial.values())<1e-10))
    assert rows[job.name]['pass_initial_state_equality']
 (H/'results/state_roundtrip_check.json').write_text(json.dumps(rows,indent=2)+'\n')
 print('Verified final-state overlap for',len(rows),'transients')

if __name__=='__main__':main()
