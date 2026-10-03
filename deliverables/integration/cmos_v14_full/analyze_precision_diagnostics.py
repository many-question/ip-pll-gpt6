"""Retain observed restart events from deliberately stopped precision probes.

These are negative diagnostics, not completed retention/capture screens.
The same native state with tighter numerics is a parameter-change experiment,
not evidence that a strict-precision reset search must fail.
"""
from pathlib import Path
import hashlib,json,contextlib,io
import numpy as np
from virtuoso_bridge.spectre.parsers import parse_psf_ascii_directory
from analyze import cross
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rows=[]
for run,case in [('repairstrict01','repair_strict_tt'),('repairstrict02','repair_retain_tt')]:
 j=R/run/case;rec=json.loads((j/'result.json').read_text());assert rec['remote_inputs_match']
 assert (j/'cancellation.json').exists()
 wave=j/'diagnostic_waveforms.npz'
 if not wave.exists():
  with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
   data=parse_psf_ascii_directory(j/(case+'.raw'))
  data={k:np.atleast_1d(v) for k,v in data.items() if k!='units' and np.asarray(v).dtype.kind in 'biufc'}
  np.savez_compressed(wave,**data)
 with np.load(wave) as z:d={k:z[k] for k in z.files}
 t=d['time'];restart=cross(t,d['XP.restart']);fall=cross(t,1.2-d['qualified'])
 end=restart[0] if len(restart) else t[-1]
 samples=np.flatnonzero((abs(np.diff(d['obsphase']))>1e-9)|(abs(np.diff(d['obscycles']))>1e-9))+1
 samples=samples[(t[samples]>t[0]+1e-9)&(t[samples]<end-10e-9)&(d['obscycles'][samples]>0)]
 row=dict(run=run,case=case,scope=__doc__,simulator_completed=False,deliberately_stopped=True,
  source_result=(j/'result.json').relative_to(ROOT).as_posix(),source_result_sha256=sha(j/'result.json'),
  raw_sha256=sha(j/(case+'.raw')/'tran.tran.tran'),waveform_sha256=sha(wave),
  input_hashes=rec['inputs_sha256'],native_state=rec.get('native_state'),
  observed_time_us=[float(t[0]*1e6),float(t[-1]*1e6)],
  restart_us=[float(x*1e6) for x in restart],qualified_falling_us=[float(x*1e6) for x in fall],
  pre_restart_observations=[dict(time_us=float(t[i]*1e6),phase_rad=float(d['obsphase'][i]),rf_error_mhz=float(d['obscycles'][i]*24-3936)) for i in samples],
  final_state={k:float(d[k][-1]) for k in ['cfg_ready','qualified','XP.restart','XP.XC.acquired','XP.en']},
  consequence='4ps reset capture is a functional result without numerical convergence proof. Run the entire reset/FLL acquisition at strict precision before final capture acceptance.')
 rows.append(row)
out=dict(scope=__doc__,cases=rows,strict_reset_followup='repaircoldstrict01/repair_capture_strict_tt:64us,1ps/reltol1e-5,from reset; no seed/recovery. Pending.')
(H/'results/precision_diagnostics.json').write_text(json.dumps(out,indent=2)+'\n')
for row in rows:print(row['run'],'restart',row['restart_us'],'qualified falls',row['qualified_falling_us'])
