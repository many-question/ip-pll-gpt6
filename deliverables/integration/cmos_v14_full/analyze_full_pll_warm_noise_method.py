"""Compare cold-derived text initialization with an independently valid native continuation."""
from pathlib import Path
import hashlib,json
import numpy as np
from transient_diagnostics import recovery,effective
H=Path(__file__).resolve().parent; ROOT=H.parents[3]; R=ROOT/'research/runs/spectre_cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def data(j):
    r=json.loads((j/'result.json').read_text());assert r['ok'] and r['remote_inputs_match']
    assert sha(j/'waveforms.npz')==r['local_outputs_sha256']['waveforms.npz']
    assert all(sha(j/'inputs'/k)==v for k,v in r['inputs_sha256'].items())
    with np.load(j/'waveforms.npz') as z:d={k:z[k] for k in z.files if k!='units'}
    return r,d

def main():
    pp=H/'results/full_pll_warm_noise_method_protocol.json';p=json.loads(pp.read_text())
    j=R/p['run']/p['case'];r,w=data(j)
    source=ROOT/p['source_result'];assert sha(source)==p['source_result_sha256'];sr,c=data(source.parent)
    nr,n=data(R/p['reference_native_run']/p['reference_native_case'])
    log=(j/'spectre.out').read_text();diagnostics=recovery(log)
    assert not r.get('native_state') and 'tran noise is turning OFF on time 0.000000e+00' in log
    assert 'tran noise is turning ON' not in log
    skip={'time','units','energy_nj','power_mw','obsphase','obscycles','obsctrl','obsdivcycles'}
    names=[k for k in w if k in c and k not in skip and ':' not in k]
    boundary={k:abs(float(w[k][0]-c[k][-1])) for k in names}
    assert abs(w['time'][0])<1e-15 and w['time'][-1]>=p['local_stop_s']-1e-15
    # Compare on the actual sparse output grid. Fast square-wave differences
    # are not a valid scalar trajectory metric, so report control and held state.
    q=(w['time']>=50e-9)&(w['time']<=240e-9);tw=w['time'][q]+p['source_time_s']
    differences={}
    for k in ['XP.ctrl','XP.hp','XP.hn','XP.XC.phase_held','qualified','frequency_good','cfg_ready','range_error']:
        v=w[k][q]-np.interp(tw,n['time'],n[k])
        differences[k]=dict(rms_v=float(np.sqrt(np.mean(v*v))),maximum_v=float(max(abs(v))))
    bits=['XP.b'+str(i) for i in range(8)]+['XP.XC.d'+str(i) for i in range(6)]
    bit_stable=all(np.all((w[k]>.6)==(c[k][-1]>.6)) for k in bits)
    checks=dict(initial_physical_state=max(boundary.values())<1e-9,noise_off=True,
        no_recovery=diagnostics['numerically_clean'],code_unchanged=bool(bit_stable),
        qualification_preserved=bool(np.min(w['qualified'])>1.0),
        control_trajectory=differences['XP.ctrl']['rms_v']<.002)
    out=dict(scope=__doc__,protocol_sha256=sha(pp),source_result=p['run']+'/'+p['case'],
        source_sha256=sha(j/'result.json'),log_sha256=sha(j/'spectre.out'),raw_cache_sha256=sha(j/'waveforms.npz'),
        compared_physical_nodes=len(boundary),initial_maximum_difference_v=max(boundary.values()),
        physical_boundary_differences_v=boundary,trajectory_differences=differences,checks=checks,
        initialization_screen_passed=all(checks.values()),recovery=diagnostics,effective=effective(log),
        warnings=[s.strip() for s in log.splitlines() if 'WARNING (' in s],
        random_noise_measured=False,steady_operating_point_accepted=False,full_pll_acceptance=False,
        limitations=p['limitations']+['Trajectory gate is a preliminary initialization screen, not a noise accuracy or stationary-state gate.'])
    (H/'results/full_pll_warm_noise_method_validation.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2))

if __name__=='__main__':main()
