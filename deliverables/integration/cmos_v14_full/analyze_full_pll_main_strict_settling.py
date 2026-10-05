"""Window the completed original V14 quiet trace without removing its drift."""
from pathlib import Path
import hashlib,json,sys
import numpy as np
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
sys.path.insert(0,str(H))
from noise_utils import cross
j=ROOT/'research/runs/spectre_cmos_v14_full/pllmainstrictoff01/full_pll_main_strict_off_tt'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
r=json.loads((j/'result.json').read_text());assert r['ok'] and r['remote_inputs_match']
assert 'spectre completes with 0 errors' in (j/'spectre.out').read_text()
assert sha(j/'waveforms.npz')==r['local_outputs_sha256']['waveforms.npz']
with np.load(j/'waveforms.npz') as z:
 t=z['time'];dense=t>=1e-6
 # Sparse pre-1us RF samples are unsuitable for event extraction.
 rf=cross(t[dense],(z['XP.vp']-z['XP.vn'])[dense],0)
 oe=cross(t[dense],z['out'][dense],.6)
 refs=cross(t[dense],z['XP.refb'][dense],.6)
 refs=refs[(refs>rf[0])&(refs>oe[0])&(refs<min(rf[-1],oe[-1]))]
 ur=np.interp(refs,rf,np.arange(len(rf)));uo=np.interp(refs,oe,np.arange(len(oe)))
 phase=np.unwrap(2*np.pi*(ur-np.floor(ur)))
 vc=np.interp(refs,t,z['XP.vc1']);ctrl=np.interp(refs,t,z['XP.ctrl'])
 windows=[]
 for lo,hi in [(1,1.5),(1.5,2),(1.7,2.2),(1.2,2.2),(2,2.2)]:
  q=(refs>=lo*1e-6)&(refs<=hi*1e-6)
  windows.append(dict(start_us=lo,end_us=hi,samples=int(sum(q)),phase_pp_rad=float(np.ptp(phase[q])),
   phase_drift_rad_per_us=float(np.polyfit(refs[q]*1e6,phase[q],1)[0]),
   mean_output_mhz=float(np.mean(np.diff(uo[q]))*24),
   vc1_drift_v_per_us=float(np.polyfit(refs[q]*1e6,vc[q],1)[0]),
   max_rf_cycles_error=float(max(abs(np.diff(ur[q])-164)))))
out=dict(scope=__doc__,source_result_sha256=sha(j/'result.json'),cache_sha256=sha(j/'waveforms.npz'),
 windows=windows,reference_times_s=refs.tolist(),phase_rad=phase.tolist(),vc1_v=vc.tolist(),ctrl_v=ctrl.tolist(),
 full_pll_acceptance=False,integrated_jitter_fs=None)
(H/'results/full_pll_main_strict_settling_diagnosis.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(dict(windows=windows,first_phase_rad=float(phase[0]),last_phase_rad=float(phase[-1])),indent=2))
