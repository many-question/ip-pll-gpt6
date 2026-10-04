"""Require actual full-circuit stationarity and intact physical initialization."""
from pathlib import Path
import argparse,hashlib,json
import numpy as np
from analyze import loop
from transient_diagnostics import effective,recovery
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser();g=ap.add_mutually_exclusive_group();g.add_argument('--gear',action='store_true');g.add_argument('--moderate',action='store_true');a=ap.parse_args()
    prefix='full_pll_noise_gear_diagnosis' if a.gear else 'full_pll_noise_moderate_settling' if a.moderate else 'full_pll_noise_settling'
    pp=H/'results'/(prefix+'_protocol.json');p=json.loads(pp.read_text())
    j=R/p['run']/p['case'];rp=j/'result.json';r=json.loads(rp.read_text())
    assert r['remote_inputs_match'] and not r.get('native_state')
    if not r['ok']:
        log=(j/'spectre.out').read_text()
        out=dict(scope=__doc__,protocol_sha256=sha(pp),source_result=rp.relative_to(ROOT).as_posix(),source_sha256=sha(rp),
            passed=False,simulator_completed=False,errors=r['errors'],recovery=recovery(log),effective=effective(log),
            log_sha256=sha(j/'spectre.out'),full_pll_acceptance=False,limitations=p['limitations'])
        (H/'results'/(prefix+'_validation.json')).write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2));return
    cache=j/'waveforms.npz';assert sha(cache)==r['local_outputs_sha256'][cache.name]
    log=(j/'spectre.out').read_text();eff=effective(log);rec=recovery(log)
    assert eff['reltol']==p['reltol'] and eff['maxstep']==p['maxstep_s'] and eff['abstol(V)']==p['vabstol'] and eff['abstol(I)']==p['iabstol']
    assert eff['method']==p.get('method','traponly')
    assert 'tran noise is turning OFF on time 0.000000e+00' in log and 'tran noise is turning ON' not in log
    with np.load(cache) as z:d={k:z[k] for k in z.files if k!='units'}
    source=R/'rt4bankcold01/rt4bank_capture_tt'
    with np.load(source/'waveforms.npz') as z:
        skip={'time','units','energy_nj','power_mw','obsphase','obscycles','obsctrl','obsdivcycles'}
        boundary={k:abs(float(d[k][0]-z[k][-1])) for k in d if k in z and k not in skip and ':' not in k}
        bitnames=['XP.b'+str(i) for i in range(8)]+['XP.XC.d'+str(i) for i in range(6)]
        code_ok=all(np.all((d[k]>.6)==(z[k][-1]>.6)) for k in bitnames)
    assert d['time'][0]==0 and d['time'][-1]>=p['stop_s']-1e-15
    s=loop(d);sel=d['time']>=p['measurement_start_s']
    status=all(np.min(d[k][sel])>1.0 for k in ['qualified','frequency_good','cfg_ready','amp_good','XP.XC.phase_held']) and max(abs(d['range_error'][sel]))<.2
    checks=dict(initialization=max(boundary.values())<1e-9,clean=rec['numerically_clean'],stationarity=s['passed'],status=bool(status),code=bool(code_ok))
    out=dict(scope=__doc__,protocol_sha256=sha(pp),source_result=rp.relative_to(ROOT).as_posix(),source_sha256=sha(rp),
        cache_sha256=sha(cache),log_sha256=sha(j/'spectre.out'),checks=checks,passed=all(checks.values()),
        stationarity=s,physical_initialization=dict(compared_nodes=len(boundary),maximum_difference_v=max(boundary.values())),
        recovery=rec,effective=eff,noise_enabled=False,full_pll_acceptance=False,limitations=p['limitations'])
    (H/'results'/(prefix+'_validation.json')).write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2))

if __name__=='__main__':main()
