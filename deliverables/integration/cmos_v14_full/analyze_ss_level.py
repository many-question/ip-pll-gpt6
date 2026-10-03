"""Accept completed level-restoration experiments only, including all-cycle swing."""
from pathlib import Path
import hashlib,json,sys,argparse
import numpy as np
from analyze import cross,divider
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rows=[]
parser=argparse.ArgumentParser();parser.add_argument('runs',nargs='*');parser.add_argument('--output',default='ss_level_validation.json')
parser.add_argument('--expected-start-ns',type=float,default=120)
parser.add_argument('--expected-stop-ns',type=float,default=200)
args=parser.parse_args()
assert Path(args.output).name==args.output and args.output.endswith('.json')
runs=args.runs or ['banklevel01','bankssorig01','banktaper02','bankskew01','bankmix01']
for run in runs:
 for p in sorted((R/run).glob('*/result.json')):
  j=p.parent;r=json.loads(p.read_text())
  if not r.get('local_outputs_sha256'):continue
  assert r['remote_inputs_match']
  row=dict(run=run,case=j.name,passed=False,source=p.relative_to(ROOT).as_posix(),source_sha256=sha(p));rows.append(row)
  if not r['ok'] or 'spectre completes with 0 errors' not in (j/'spectre.out').read_text():continue
  assert sha(j/'waveforms.npz')==r['local_outputs_sha256']['waveforms.npz']
  with np.load(j/'waveforms.npz') as z:d={k:z[k] for k in z.files}
  t=d['time'];assert abs(t[0]*1e9-args.expected_start_ns)<.002 and abs(t[-1]*1e9-args.expected_stop_ns)<.002
  v=divider(d,int(j.name.split('_')[1][1:]));fr=v['rf_mhz']*1e6;stages={}
  keys=['clk','XD.q0','XD.qb0','q1','XD.d4','predata','data']+[k for k in ['XD.gn','XD.ct0','XD.ct1','XD.ct2','XD.cb','XD.ck'] if k in d]
  for k in keys:
   y=d[k];e=cross(t,y);cycles=[y[(t>=a)&(t<=b)] for a,b in zip(e[:-1],e[1:])]
   stages[k]=dict(range_v=[float(min(y)),float(max(y))],mhz=float(1e-6/np.mean(np.diff(e))) if len(e)>2 else 0,
    all_cycle_swing=bool(cycles and all(min(c)<.2 and max(c)>1 for c in cycles)),
    min_cycle_peak_v=float(min(max(c) for c in cycles)) if cycles else None,
    max_cycle_trough_v=float(max(min(c) for c in cycles)) if cycles else None)
  e=cross(t,d['q1']);err=float(max(abs(np.diff(e)*fr/2-1))) if len(e)>2 else None
  qpass=bool(len(e)>2 and abs(stages['q1']['mhz']*2/v['rf_mhz']-1)<.001 and err<.02 and stages['q1']['all_cycle_swing'])
  v['scope']=f'Actual SS receiver, measured SS tank waveform replay; quiet counter load; SS60/1.2V/10fF,{args.expected_stop_ns:g}ns/fixedwindow{args.expected_start_ns:g}-{args.expected_stop_ns:g}ns,1ps/reltol1e-5. Not full PLL or jitter.'
  row.update(output=v,stages=stages,q1_max_period_error=err,q1_passed=qpass,passed=bool(v['passed'] and qpass))
out=H/'results'/args.output;out.write_text(json.dumps(dict(cases=rows),indent=2)+'\n')
for r in rows:
 if r['run']==runs[-1]:print(r['case'],r['passed'],r.get('output',{}).get('output_mhz'),r.get('stages',{}).get('q1'))
