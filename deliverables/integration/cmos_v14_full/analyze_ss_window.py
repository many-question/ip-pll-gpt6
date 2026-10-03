"""Measure clock windows; distinguish diagnostic-source and physical tests."""
from pathlib import Path
import json,re,hashlib,sys
import numpy as np
from analyze import divider,cross
H=Path(__file__).resolve().parent; ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
def edges(t,y):
 def duration(y):
  a=cross(t,y,.12);b=cross(t,y,1.08);v=[]
  for x in a:
   after=b[b>x]
   if len(after) and after[0]-x<1e-9:v.append((after[0]-x)*1e12)
  return float(np.median(v)) if v else None
 er=cross(t,y);ef=cross(t,1.2-y);dut=[]
 for a,b in zip(er[:-1],er[1:]):
  f=ef[(ef>a)&(ef<b)]
  if len(f)==1:dut.append((f[0]-a)/(b-a))
 return dict(min_v=float(min(y)),max_v=float(max(y)),rise_10_90_ps=duration(y),fall_90_10_ps=duration(1.2-y),duty_pct=float(100*np.mean(dut)) if dut else None,frequency_mhz=float(1e-6/np.mean(np.diff(er))) if len(er)>2 else None)
rows=[]
for run in sys.argv[1:] or ['bankwindow01']:
 for p in sorted((R/run).glob('*/result.json')):
  rec=json.loads(p.read_text());job=p.parent
  assert rec['remote_inputs_match']
  if not rec.get('ok'):continue
  assert 'spectre completes with 0 errors' in (job/'spectre.out').read_text(errors='replace')
  assert hashlib.sha256((job/'waveforms.npz').read_bytes()).hexdigest()==rec['local_outputs_sha256']['waveforms.npz']
  with np.load(job/'waveforms.npz') as z:d={k:z[k] for k in z.files}
  mask=d['time']>=d['time'][-1]-40e-9;d={k:v[mask] for k,v in d.items() if len(v)==len(mask)}
  m=int(re.search(r'_m(\d+)_',job.name)[1])
  row=dict(run=run,case=job.name,source_result=p.relative_to(ROOT).as_posix(),source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),divider=divider(d,m),clocks={k:edges(d['time'],d[k]) for k in ['q1','ck','XD.q0','XD.qb0','XD.qb1','XD.qb2','XD.ck','XD.mck','XD.gn','XD.cb'] if k in d})
  row['divider']['scope']='Final40ns; diagnostic external CK source for bankwindow*, otherwise physical CMOS candidate. Ideal external RF20ps/1.2V; not PLL acceptance.'
  rows.append(row)
  print(job.name,row['divider']['passed'],round(row['divider']['output_mhz'],3),row['clocks'].get('ck',row['clocks'].get('XD.ck')))
(H/'results/ss_window_validation.json').write_text(json.dumps(dict(scope=__doc__,rows=rows),indent=2)+'\n')
