"""Same-candidate six-mode/three-corner regression, not full PLL acceptance."""
from pathlib import Path
import json,hashlib,re
import numpy as np
from analyze import divider
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full/bankboostreg01'
protocol=json.loads((H/'results/ss_candidate_regression_protocol.json').read_text())
boundary=json.loads((H/'results/boundary_bank_preboost50_v14.json').read_text());assert boundary['physical_boundary_pass']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rows=[]
for case in protocol['cases']:
 j=R/case
 if not (j/'result.json').exists():continue
 rec=json.loads((j/'result.json').read_text())
 if not rec.get('local_outputs_sha256'):continue
 assert rec['remote_inputs_match']
 assert all(rec['inputs_sha256'][k]==v and sha(j/'inputs'/k)==v for k,v in boundary['source_hashes'].items())
 row=dict(case=case,source_result=(j/'result.json').relative_to(ROOT).as_posix(),source_sha256=sha(j/'result.json'),passed=False);rows.append(row)
 if not rec['ok'] or 'spectre completes with 0 errors' not in (j/'spectre.out').read_text(errors='replace'):continue
 assert sha(j/'waveforms.npz')==rec['local_outputs_sha256']['waveforms.npz']
 with np.load(j/'waveforms.npz') as z:d={k:z[k] for k in z.files}
 assert d['time'][0]>=59.999e-9 and d['time'][-1]>=99.999e-9
 m=int(case.split('_')[1][1:]);v=divider(d,m)
 v['scope']=protocol['scope'];row.update(passed=v['passed'],divider=v)
 tb=(j/'inputs'/(case+'.scs')).read_text();assert 'maxstep=1p' in tb and 'reltol=1e-5' in tb
 row['corner']=re.search(r'section=(tt|ss|ff)\b',tb)[1]
out=dict(scope=__doc__,protocol=protocol,source_hashes=boundary['source_hashes'],completed=len(rows),expected=len(protocol['cases']),all_completed=len(rows)==len(protocol['cases']),all_passed=len(rows)==len(protocol['cases']) and all(r['passed'] for r in rows),rows=rows)
(H/'results/ss_candidate_regression.json').write_text(json.dumps(out,indent=2)+'\n')
print('Completed',out['completed'],'of',out['expected'],'all_passed',out['all_passed'])
for r in rows:print(r['case'],r['passed'],r.get('divider',{}).get('output_mhz'))
