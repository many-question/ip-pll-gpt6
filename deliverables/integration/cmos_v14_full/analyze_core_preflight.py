"""Diagnose deterministic core capture before attempting device-noise analysis.

Failed PSS stabilization is retained as a negative convergence experiment, never
as a jitter measurement. Compact extraction is cached against the raw SHA256.
"""
from pathlib import Path
import json,hashlib,math
import numpy as np
from analyze import cross
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()

def scan(p):
 wanted={'time','XP.vp','XP.vn','XP.refb','XP.ctrl','XP.vc1','out'}
 previous=None;current={};rf=[];out=[];ref=[];samples=[];slope={x:[] for x in ['r10','r90','f90','f10']}
 def accept(d):
  nonlocal previous
  if not wanted.issubset(d):return
  if previous:
   t=d['time'];a=previous['time']
   for name,key,level,fall in [('rf',None,0,False),('out','out',.6,False),('ref','XP.refb',.6,False),('r10','XP.refb',.12,False),('r90','XP.refb',1.08,False),('f90','XP.refb',1.08,True),('f10','XP.refb',.12,True)]:
    x=previous[key] if key else previous['XP.vp']-previous['XP.vn']
    y=d[key] if key else d['XP.vp']-d['XP.vn']
    hit=x>level>=y if fall else x<level<=y
    if not hit:continue
    edge=a+(t-a)*(level-x)/(y-x)
    if name in slope:slope[name].append(edge)
    elif name=='rf':rf.append(edge)
    elif name=='out':out.append(edge)
    else:
     ref.append(edge)
     if rf:samples.append([edge,(edge-rf[-1])*3936e6*2*math.pi,d['XP.ctrl'],d['XP.vc1']])
  previous=d
 with p.open() as f:
  for line in f:
   if not line.startswith('"'):continue
   v=line.split()
   if len(v)!=2:continue
   k=v[0].strip('"')
   if k not in wanted:continue
   try:x=float(v[1])
   except ValueError:continue
   if k=='time':accept(current);current={}
   current[k]=x
 accept(current)
 def freq(e):
  q=np.asarray(e);q=q[q>previous['time']-200e-9]
  return float((len(q)-1)/(q[-1]-q[0])/1e6) if len(q)>1 else None
 def width(a,b):
  q=[]
  for t in slope[a]:
   after=[x for x in slope[b] if t<x<t+5e-9]
   if after:q.append((after[0]-t)*1e12)
  return float(np.mean(q)) if q else None
 a=np.asarray(samples);u=np.unwrap(a[:,1]);ts=a[:,0]*1e6
 last=ts>previous['time']*1e6-1;window=ts[last];pu=u[last]
 pp=float(np.ptp(pu));drift=float(np.polyfit(window,pu,1)[0]);span=float(window[-1]-window[0])
 return dict(end_us=previous['time']*1e6,rf_last200ns_mhz=freq(rf),out_last200ns_mhz=freq(out),reference_rise_ps=width('r10','r90'),reference_fall_ps=width('f90','f10'),reference_samples=[dict(time_us=float(x[0]*1e6),phase_rad=float(x[1]),ctrl_v=float(x[2]),vc1_v=float(x[3])) for x in samples],phase_drift_rad_per_us=float(np.polyfit(ts,u,1)[0]),unwrapped_phase_span_rad=float(np.ptp(u)),phase_slip_observed=bool(np.ptp(u)>2*np.pi),last_window=dict(span_us=span,phase_pp_rad=pp,drift_rad_per_us=drift,stationary=bool(span>.94 and pp<.02 and abs(drift)<.01)))

rows=[]
cases=[('corenoiseprobe01','core_noise_probe_tt','pss.tran.pss'),('corepreflight4ps01','core_preflight_4ps_tt','tran.tran.tran')]
cases += [('coreload01',f'core_load{cap}p_tt','tran.tran.tran') for cap in [2,5,10]]
cases += [('coreregister01','core_register_preflight_tt','tran.tran.tran')]
for run,case,file in cases:
 j=R/run/case;p=j/(case+'.raw')/file
 if not (j/'result.json').exists() or not p.exists():continue
 rec=json.loads((j/'result.json').read_text())
 if not rec.get('local_outputs_sha256'):continue
 assert rec.get('remote_inputs_match')
 cache=j/'preflight_extract.json';digest=sha(p)
 d=json.loads(cache.read_text()) if cache.exists() else {}
 if d.get('raw_sha256')!=digest or 'last_window' not in d:d=dict(raw_sha256=digest,**scan(p));cache.write_text(json.dumps(d,indent=2)+'\n')
 log=(j/'spectre.out').read_text();row=dict(run=run,case=case,source_raw=p.relative_to(ROOT).as_posix(),raw_bytes=p.stat().st_size,source_result_sha256=sha(j/'result.json'),simulator_completed='spectre completes with 0 errors' in log,intentionally_stopped=(j/'cancellation.json').exists(),**d)
 row['scope']='Deterministic transient only; fixed ideal controls and removed reference loading differ from full PLL; phase slips are not RMS jitter.'
 row['ready_for_noise']=False
 rows.append(row)
(H/'results/core_preflight_validation.json').write_text(json.dumps(dict(cases=rows,full_pll_jitter_fs=None),indent=2)+'\n')
for r in rows:print(json.dumps({k:v for k,v in r.items() if k!='reference_samples'}))
