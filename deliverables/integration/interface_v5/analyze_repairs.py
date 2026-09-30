"""Retain old-code failures; choose only separately verified replacement codes."""
import json,re,copy
from analyze import H,R,measure

def main():
 initial=json.loads((H/'results/q10corner_validation.json').read_text());selected=copy.deepcopy(initial['rows']);trials=[]
 for p in sorted(R.glob('quiet10_repair*/*/result.json')):
  job=p.parent;m=re.fullmatch(r'q10repair_(tt|ss|ff)_k(\d+)_c(\d+)',job.name)
  if not m:continue
  corner,k,code=m[1],int(m[2]),int(m[3]);row=next(x for x in selected if x['condition']['corner']==corner and int(x['condition']['K'])==k)
  ends=[measure(job,w) for w in [(110e-9,150e-9),(240e-9,280e-9)]]
  target=float(row['condition']['target_vco_MHz'])*1e6;fs=[x['f_ghz']*1e9 for x in ends];margin=min(target-min(fs),max(fs)-target)
  trial=dict(case=job.name,run=job.parent.name,corner=corner,K=k,code=code,endpoints=ends,endpoint_margin_hz=margin,pass_coverage=all(x['divide_valid'] for x in ends) and margin>2e6);trials.append(trial)
  if trial['pass_coverage'] and margin>row['endpoint_margin_hz']:
   row['original_case']=row['condition']['case'];row['original_code']=row['condition']['code'];row['condition'].update(case=job.name,code=str(code));row.update(endpoints=ends,endpoint_margin_hz=margin,pass_divide=True,pass_coverage=True)
 out=dict(expected=7,completed=len(selected),initial_all_pass=initial['all_pass'],all_pass=len(selected)==7 and all(x['pass_coverage'] for x in selected),selected=selected,repair_trials=trials,scope='Only seven critical corner/frequency pairs; not the full 99-point map.')
 (H/'results/q10_selected_validation.json').write_text(json.dumps(out,indent=2)+'\n')
 print([(x['condition']['case'],round(x['endpoint_margin_hz']/1e6,4),x['pass_coverage']) for x in selected])

if __name__=='__main__':main()
