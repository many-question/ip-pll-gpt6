"""Record effective logged analysis tolerances, not just netlist requests."""
import json,re
from analyze import H,R

def main():
 rows=[]
 for p in sorted(R.glob('*/*/result.json')):
  rec=json.loads(p.read_text());log=p.parent/'spectre.out'
  if not log.exists():continue
  text=log.read_text(errors='replace')
  # Anchored assignment lines under Important parameter values (the global
  # options summary uses reverse spacing, and is not the final analysis value).
  values={k:re.findall(r'^\s{4}'+re.escape(k)+r' = (.+)$',text,re.M) for k in ['reltol','abstol(V)','abstol(I)','maxstep','errpreset','method','steadyratio','lteratio','relref']}
  rows.append(dict(run=p.parent.parent.name,case=p.parent.name,simulator_ok=rec['ok'],effective_values=values,command=rec.get('metadata',{}).get('spectre_command')))
 out=dict(note='Spectre X may change a requested netlist option. These are effective analysis values printed in the complete logs. Lists preserve multiple analyses. Empty means unavailable, not zero.',loop_transient_limit='The four original LC loop transients used effective reltol=1e-3, maxstep=2 ps and method=trap. Their phase drift is preliminary and requires explicit tighter-tolerance cross-check before attributing it solely to physical slow states.',rows=rows)
 (H/'results/solver_settings.json').write_text(json.dumps(out,indent=2)+'\n')
 print('Audited analysis settings:',len(rows))

if __name__=='__main__':main()
