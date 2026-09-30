"""Compare identical-condition noise solves with tighter numerical settings."""
import json
from pathlib import Path
H=Path(__file__).resolve().parent
rows={x['case']:x for x in json.loads((H/'results/noise_summary.json').read_text())}
for old,new,outfile in [('noise_both','noise_both_full','noise_precision.json'),('noise_quiet10_retry','noise_quiet10_refined','quiet10_noise_precision.json')]:
 if new not in rows:
  if old=='noise_quiet10_retry':
   result=dict(reference=old,refinement=new,status='inconclusive',pass_internal_precision=False,reason='Independent 1 ps/127-sideband X and APS solves and the tank phase constraint trial did not yield accepted converged noise evidence; cancelled numerical trials retained. The 2 ps/63-sideband spectrum is provisional.')
   (H/'results'/outfile).write_text(json.dumps(result,indent=2)+'\n');print(result)
  continue
 a,b=rows[old],rows[new];delta={k:b['phase_noise_dbc_hz'][k]-v for k,v in a['phase_noise_dbc_hz'].items() if k in b['phase_noise_dbc_hz']}
 result=dict(reference=old,refinement=new,delta_db=delta,max_absolute_delta_db=max(abs(v) for v in delta.values()),delta_carrier_hz=b['frequency_hz']-a['frequency_hz'],pass_internal_precision=max(abs(v) for v in delta.values())<.1,conditions='Same netlist circuit and bias, independent steady-state solve; 2 ps / 63 sidebands versus 1 ps / 127 sidebands. See input snapshots and logs for solver and sweep settings.')
 (H/'results'/outfile).write_text(json.dumps(result,indent=2)+'\n');print(result)
