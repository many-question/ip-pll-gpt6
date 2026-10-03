"""Prescaler feedback screens with real RF receiver; not PLL acceptance."""
from pathlib import Path
import hashlib,json,sys
import numpy as np
from analyze import divider,cross
H=Path(__file__).resolve().parent;ROOT=H.parents[3];run=sys.argv[1] if len(sys.argv)>1 else 'bankfeed01';R=ROOT/'research/runs/spectre_cmos_v14_full'/run
assert run in ['bankfeed01','bankrestore01','bankrfbase01','banksswave01']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rows=[]
for p in sorted(R.glob('*/result.json')):
 r=json.loads(p.read_text());j=p.parent
 if not r.get('local_outputs_sha256'):continue
 assert r['remote_inputs_match']
 row=dict(case=j.name,source_result=p.relative_to(ROOT).as_posix(),source_sha256=sha(p),passed=False);rows.append(row)
 if not r['ok'] or 'spectre completes with 0 errors' not in (j/'spectre.out').read_text():continue
 assert sha(j/'waveforms.npz')==r['local_outputs_sha256']['waveforms.npz']
 with np.load(j/'waveforms.npz') as z:d={k:z[k] for k in z.files}
 assert d['time'][0]>=19.999e-9 and d['time'][-1]>=59.999e-9
 v=divider(d,int(j.name.split('_')[1][1:]))
 v['scope']='SS60/1.2V/10fF,60ns,last40ns,1ps/reltol1e-5; physical receiver+MOS bank+RT/output+quiet counter load; frequency-scaled external TT tank waveform. Independent candidate, not full PLL.'
 if run=='banksswave01':v['scope']=v['scope'].replace('external TT','external measured SS')
 e=cross(d['time'],d['q1']);v['q1_mhz']=float(1e-6/np.mean(np.diff(e))) if len(e)>2 else None
 row.update(passed=v['passed'],divider=v)
output={'bankfeed01':'ss_feedback_validation.json','bankrestore01':'ss_restore_validation.json','bankrfbase01':'ss_rf_baseline_validation.json','banksswave01':'ss_waveform_validation.json'}[run]
(H/'results'/output).write_text(json.dumps(dict(run=run,cases=rows,expected=3 if run=='bankrfbase01' else 6),indent=2)+'\n')
for r in rows:print(r['case'],r['passed'],r.get('divider',{}).get('output_mhz'),r.get('divider',{}).get('q1_mhz'))
