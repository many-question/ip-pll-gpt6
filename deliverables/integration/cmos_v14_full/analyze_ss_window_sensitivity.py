"""Diagnose startup-window sensitivity without overturning original failures."""
from pathlib import Path
import json,hashlib
import numpy as np
from analyze import divider
from noise_utils import cross

H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
rows=[]
for run,case in [('bankpulse01','bankpulsetrip_m6_ss'),
                 ('bankungated01','bankungatedbal_m6_ss'),
                 ('bankmix01','bankmixskew_m6_ss')]:
    j=R/run/case;rec=json.loads((j/'result.json').read_text())
    assert rec['ok'] and rec['remote_inputs_match']
    p=j/'waveforms.npz';assert hashlib.sha256(p.read_bytes()).hexdigest()==rec['local_outputs_sha256']['waveforms.npz']
    with np.load(p) as z:d={k:z[k] for k in z.files}
    t=d['time'];windows=[]
    for start in [120,140,160,180]:
        mask=t>=start*1e-9
        v=divider({k:y[mask] for k,y in d.items()},6)
        windows.append(dict(start_ns=start,stop_ns=200,output_mhz=v['output_mhz'],
            max_period_error=v['max_period_error'],every_cycle_full_swing=v['every_cycle_full_swing'],
            window_function_passed=v['passed']))
    e=cross(t,d['data']);rf=cross(t,d['clk']);fr=1/np.mean(np.diff(rf))
    errors=abs(np.diff(e)*fr/6-1);bad=np.flatnonzero(errors>.02)
    means=[]
    for start in range(120,200,10):
        mask=(t>=start*1e-9)&(t<=(start+10)*1e-9);tt=t[mask]
        means.append(dict(window_start_ns=start,
            rx_gate_average_v=float(np.trapezoid(d['XRX.g0'][mask],tt)/(tt[-1]-tt[0]))))
    rows.append(dict(run=run,case=case,source=(j/'result.json').relative_to(ROOT).as_posix(),
        source_sha256=hashlib.sha256((j/'result.json').read_bytes()).hexdigest(),windows=windows,
        period_error_times_ns=(e[:-1][bad]*1e9).tolist(),period_errors=errors[bad].tolist(),
        rx_gate_window_means=means,original_failure_preserved=True,new_acceptance=False))
out=dict(scope=__doc__,cases=rows,
    inference='PB1 threshold candidate has a passing late window; unlike old trees, its early-window error may be startup settling. This motivates an independent longer run; it does not prove absence of later failures.',
    followup='banktripsettled01 uses600ns with predeclared400-600ns acceptance for all6modes; no hindsight trimming.',
    full_pll_acceptance=False)
(H/'results/ss_window_sensitivity.json').write_text(json.dumps(out,indent=2)+'\n')
print([(r['case'],[(w['start_ns'],w['window_function_passed']) for w in r['windows']]) for r in rows])
