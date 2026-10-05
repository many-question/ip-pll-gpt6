"""Verify dynamic solver controls against the installed Spectre's log and steps."""
from pathlib import Path
import hashlib,json,re
import numpy as np
from transient_diagnostics import recovery
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    j=ROOT/'research/runs/spectre_cmos_v14_full/pllprecisionprobe01/precision_schedule_probe_tt'
    rp=j/'result.json';r=json.loads(rp.read_text());log=(j/'spectre.out').read_text()
    with np.load(j/'waveforms.npz') as z:t=z['time'];y=z['out']
    segments=[]
    for start,stop,limit in [(0,2e-9,4e-12),(2e-9,4e-9,2e-12),(4e-9,6e-9,.5e-12),(6e-9,8e-9,.5e-12)]:
        selected=(t[:-1]>=start+1e-14)&(t[1:]<=stop-1e-14)
        maximum=float(np.max(np.diff(t)[selected]))
        segments.append(dict(start_s=start,stop_s=stop,maxstep_limit_s=limit,observed_maximum_step_s=maximum,passed=maximum<=limit*(1+1e-9)))
    checks=dict(completed=bool(r['ok'] and r['remote_inputs_match'] and t[-1]==8e-9),
        clean=recovery(log)['numerically_clean'],steps=all(s['passed'] for s in segments),
        reltol='effective value of \'reltol\' is now 1e-06' in log,
        vabstol='abstol(V) = 1 nV' in log,
        delayed_noise=re.findall(r'tran noise is turning ON on time (\S+)\.',log)==['6.000000e-09'],
        finite=bool(np.all(np.isfinite(y))))
    result=dict(scope=__doc__,source_result=rp.relative_to(ROOT).as_posix(),source_result_sha256=sha(rp),
        cache_sha256=sha(j/'waveforms.npz'),log_sha256=sha(j/'spectre.out'),segments=segments,checks=checks,passed=all(checks.values()),
        limitation='Tiny driven real-MOS inverter API check only. Not PLL lock, jitter or precision acceptance.')
    (H/'results/precision_schedule_probe_validation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2));assert result['passed']
if __name__=='__main__':main()
