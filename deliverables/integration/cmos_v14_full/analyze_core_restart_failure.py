"""Retain failed skipdc/tstart experiment without treating Newton excursions as device stress."""
from pathlib import Path
import hashlib
import json
import re
import numpy as np
from noise_utils import stream_selected, cross

H=Path(__file__).resolve().parent; ROOT=H.parents[3]
j=ROOT/'research/runs/spectre_cmos_v14_full/corerestart01/core_register_noise_restart_tt'
log=(j/'spectre.out').read_text(errors='replace'); r=json.loads((j/'result.json').read_text())
assert not r['ok'] and 'SPECTRE-25' in log
raw=j/(j.name+'.raw'); source=raw/'pss.tran.pss'; cache=j/'tstab_diagnostic.npz'
keys=['out','XP.vp','XP.vn','XP.ctrl','XP.refb','XP.q1','XP.XD.d8','XP.XD.d12',
      'XP.XD.XRL.a','XP.XD.XRL.b','XP.XD.load','XP.XD.loadb','XP.XD.ck']
if not cache.exists():
    d,duplicates=stream_selected(source,keys)
    np.savez_compressed(cache,**d,duplicate_fields=duplicates)
with np.load(cache) as z: d={k:z[k] for k in z.files}
t=d['time']; a=float(t[-1]-250e-9); b=float(t[-1]); ix=(t>=a)&(t<=b)
counts={k:len(cross(t[ix],d[k][ix])) for k in ['out','XP.q1','XP.XD.d8','XP.XD.d12']}
out=dict(scope=__doc__,source_result=(j/'result.json').relative_to(ROOT).as_posix(),
         source_sha256=hashlib.sha256((j/'result.json').read_bytes()).hexdigest(),
         stopped=json.loads((j/'cancellation.json').read_text()),
         convergence_history=re.findall(r'^Conv norm.*$',log,re.M),
         stabilization_saved_us=[float(t[0]*1e6),float(t[-1]*1e6)],
         last_saved_period_us=[a*1e6,b*1e6],edge_counts=counts,
         endpoint_delta_v={k:float(np.interp(b,t,d[k])-np.interp(a,t,d[k])) for k in keys},
         observed_stabilization_ranges_v={k:[float(min(d[k][ix])),float(max(d[k][ix]))] for k in keys},
         segmentation_fault_after_stop='SPECTRE-18' in log and log.index('SPECTRE-18')>log.index('SPECTRE-25'),
         pnoise_ran=bool(list(raw.glob('*.pnoise'))),periodic_state_valid=False,full_pll_acceptance=False,
         conclusions=['Skipping DC and changing absolute shooting phase did not resolve divergence.',
                      'Simulator logged SPECTRE-25 after owned SIGINT, then SPECTRE-18; this is not evidence of an earlier spontaneous crash.',
                      'Over-voltage warnings during failed Newton iterations are not an accepted operating trajectory or reliability result.',
                      'A physical continuous-clock divider candidate is undergoing real-LC transient validation; floating dynamic nodes remain a hypothesis, not an established root cause.'])
(H/'results/core_restart_failure.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:out[k] for k in ['convergence_history','stabilization_saved_us','edge_counts','pnoise_ran','segmentation_fault_after_stop']},indent=2))
