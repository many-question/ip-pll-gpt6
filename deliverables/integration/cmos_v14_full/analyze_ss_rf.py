"""Hash-checked actual-receiver regression for the separate SS repair."""
from pathlib import Path
import json,hashlib
import numpy as np
from analyze import divider
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
R=ROOT/'research/runs/spectre_cmos_v14_full/bankboostrf01'
p=json.loads((H/'results/ss_rf_protocol.json').read_text())
b=json.loads((H/'results/boundary_bank_preboost50_v14.json').read_text())
sha=lambda x:hashlib.sha256(x.read_bytes()).hexdigest()
rows=[]
for case in p['cases']:
 j=R/case
 if not (j/'result.json').exists():continue
 r=json.loads((j/'result.json').read_text())
 if not r.get('local_outputs_sha256'):continue
 assert r['remote_inputs_match']
 assert all(r['inputs_sha256'][k]==v and sha(j/'inputs'/k)==v for k,v in b['source_hashes'].items())
 row=dict(case=case,passed=False,source_result=(j/'result.json').relative_to(ROOT).as_posix(),source_sha256=sha(j/'result.json'));rows.append(row)
 if not r['ok'] or 'spectre completes with 0 errors' not in (j/'spectre.out').read_text():continue
 assert sha(j/'waveforms.npz')==r['local_outputs_sha256']['waveforms.npz']
 with np.load(j/'waveforms.npz') as z:d={k:z[k] for k in z.files}
 assert d['time'][0]>=59.999e-9 and d['time'][-1]>=99.999e-9
 v=divider(d,int(case.split('_')[1][1:]));v['scope']=p['scope']
 row.update(passed=v['passed'],divider=v)
out=dict(protocol=p,rows=rows,completed=len(rows),all_passed=len(rows)==6 and all(r['passed'] for r in rows))
(H/'results/ss_rf_validation.json').write_text(json.dumps(out,indent=2)+'\n')
print('Completed',len(rows),'of6; all_passed',out['all_passed'])
for r in rows:print(r['case'],r['passed'],r.get('divider',{}).get('output_mhz'))
