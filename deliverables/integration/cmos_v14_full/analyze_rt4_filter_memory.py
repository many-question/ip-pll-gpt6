"""Check actual C1 relaxation against the physical clamped RC time constant."""
from pathlib import Path
import hashlib,json
import numpy as np
H=Path(__file__).resolve().parent;ROOT=H.parents[3];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=json.loads((H/'results/rt4_matched_point_protocol.json').read_text());j=ROOT/'research/runs/spectre_cmos_v14_full'/p['run']/p['case']
r=json.loads((j/'result.json').read_text());assert r['ok'] and r['remote_inputs_match'] and sha(j/'waveforms.npz')==r['local_outputs_sha256']['waveforms.npz']
lf=j/'inputs/loop_filter_v5.scs';assert 'rlf=100k c1lf=7.1619724391353p' in lf.read_text()
top=(j/'inputs/pll_noise_rt4_program_core_v14.scs').read_text();assert 'rlf=100k' in top and 'tx_loop_filter_v5 rlf=rlf' in top
with np.load(j/'waveforms.npz') as z:t=z['time'];memory=z['XP.vc1']-z['XP.ctrl']
tau=100e3*7.1619724391353e-12
# Uniform weighting prevents an adaptive time grid from favoring switching events.
grid=np.linspace(t[0],t[-1],5001);y=np.interp(grid,t,memory)
a=np.column_stack([np.exp(-(grid-grid[0])/tau),np.ones(len(grid))]);coef=np.linalg.lstsq(a,y,rcond=None)[0];error=y-a@coef
nominal=p['initial_c1_minus_control_v']*np.exp(-t[-1]/tau)
out=dict(scope=__doc__,source_result=(j/'result.json').relative_to(ROOT).as_posix(),source_result_sha256=sha(j/'result.json'),
    physical_filter_sha256=sha(lf),nominal_tau_us=tau*1e6,window_us=[float(t[0]*1e6),float(t[-1]*1e6)],
    actual_final_memory_v=float(memory[-1]),initial_memory_v=p['initial_c1_minus_control_v'],zero_leakage_final_prediction_v=float(nominal),
    fitted_constant_memory_v=float(coef[1]),fit_rms_error_v=float(np.sqrt(np.mean(error**2))),fit_max_error_v=float(max(abs(error))),
    interpretation='Measured deterministic filter relaxation supports the longer physical settling interval. Fitted constant includes leakage/model/numerical effects; no random-noise inference, no alteration of stored state.',
    full_pll_acceptance=False,random_jitter_measured=False)
(H/'results/rt4_filter_memory_validation.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
