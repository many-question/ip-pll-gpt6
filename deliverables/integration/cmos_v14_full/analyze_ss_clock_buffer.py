"""Check output and prescaler integrity after receiver-clock restoration."""
from pathlib import Path
import json,hashlib
import numpy as np
from analyze import divider,cross
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full/bankckbuf01'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def edge_ps(t,v):
 def one(v):
  a=cross(t,v,.12);b=cross(t,v,1.08);out=[]
  for x in a:
   k=np.searchsorted(b,x)
   if k<len(b) and b[k]-x<200e-12:out.append((b[k]-x)*1e12)
  return float(np.mean(out)) if out else None
 return dict(rise_ps=one(v),fall_ps=one(1.2-v))
rows=[]
for p in sorted(R.glob('*/result.json')):
 j=p.parent;r=json.loads(p.read_text())
 if not r.get('local_outputs_sha256'):continue
 assert r['remote_inputs_match']
 row=dict(case=j.name,passed=False,source_result=p.relative_to(ROOT).as_posix(),source_sha256=sha(p));rows.append(row)
 if not r['ok'] or 'spectre completes with 0 errors' not in (j/'spectre.out').read_text():continue
 assert sha(j/'waveforms.npz')==r['local_outputs_sha256']['waveforms.npz']
 with np.load(j/'waveforms.npz') as z:d={k:z[k] for k in z.files}
 t=d['time'];assert t[0]>=119.999e-9 and t[-1]>=199.999e-9
 v=divider(d,int(j.name.split('_')[1][1:]));rf=v['rf_mhz']*1e6;e=cross(t,d['q1'])
 qerr=float(max(abs(np.diff(e)*rf/2-1))) if len(e)>2 else None
 qfreq=float(1e-6/np.mean(np.diff(e))) if len(e)>2 else 0
 qcycles=[d['q1'][(t>=a)&(t<=b)] for a,b in zip(e[:-1],e[1:])]
 qswing=bool(qcycles and all(min(x)<.2 and max(x)>1 for x in qcycles))
 qpass=bool(len(e)>2 and abs(qfreq*2/v['rf_mhz']-1)<.001 and qerr<.02 and qswing)
 row.update(output=v,prescaler=dict(mhz=qfreq,max_period_error=qerr,every_cycle_full_swing=qswing,range_v=[float(min(d['q1'])),float(max(d['q1']))],passed=qpass),edges={k:edge_ps(t,d[k]) for k in ['clk','rxclk','q1'] if k in d},passed=bool(v['passed'] and qpass))
 row['output']['scope']='SS60/1.2V/10fF;200ns,last80ns,1ps/reltol1e-5;actualreceiver,SS tank replay,quiet counter load. Optional twoMOS inverter clock buffer; not complete PLL.'
(H/'results/ss_clock_buffer_validation.json').write_text(json.dumps(dict(cases=rows,expected=8),indent=2)+'\n')
for r in rows:print(r['case'],r['passed'],r.get('output',{}).get('output_mhz'),r.get('prescaler'),r.get('edges'))
