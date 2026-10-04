"""Check dense complete-PLL continuations before any random-jitter claim."""
from pathlib import Path
import hashlib,json,argparse
import numpy as np
from noise_utils import cross
from transient_diagnostics import effective,recovery
from analyze_retimer_transient_noise_control import physical,edge_band_power
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--round',type=int,choices=[1,2],default=2);a=ap.parse_args()
    prefix='full_pll_jitter_preflight'+('2' if a.round==2 else '')
    pp=H/'results'/(prefix+'_protocol.json')
    if not pp.exists():print('Complete cold acquisition/seed is still pending.');return
    p=json.loads(pp.read_text());proof=H/'results'/p['source_capture'];assert sha(proof)==p['source_capture_sha256']
    src=ROOT/p['source_result'];assert sha(src)==p['source_result_sha256'];sr=json.loads(src.read_text())
    sourcebody=(src.parent/'inputs'/(p['case']+'.scs')).read_text();rows=[];edges={}
    for c in p['cases']:
        j=R/c['run']/p['case'];rp=j/'result.json';row=dict(c,completed=False);rows.append(row)
        if not rp.exists():continue
        r=json.loads(rp.read_text());log=(j/'spectre.out').read_text()
        if not r.get('local_outputs_sha256'):continue
        row.update(source_result=rp.relative_to(ROOT).as_posix(),source_sha256=sha(rp),recovery=recovery(log),effective_initial=effective(log))
        if not r['ok']:row['errors']=r['errors'];continue
        assert r['remote_inputs_match'] and 'spectre completes with 0 errors' in log
        dep=lambda r:{k:v for k,v in r['inputs_sha256'].items() if k!=p['case']+'.scs'}
        assert dep(r)==dep(sr) and all(sha(j/'inputs'/k)==v for k,v in r['inputs_sha256'].items())
        body=(j/'inputs'/(p['case']+'.scs')).read_text();assert physical(body)==physical(sourcebody)
        assert r['native_state']['sha256']==p['native_sha256']==sha(ROOT/p['native'])
        if a.round==1:assert r['numerical_overrides']['only_save']==p['observations']
        else:assert not r['numerical_overrides'].get('only_save') and not r.get('transient_solver_overrides')
        assert r['numerical_overrides']['dense_output']
        assert r['transient_noise_overrides']['noisefmax']==0
        assert effective(log)['reltol']==p['reltol'] and effective(log)['maxstep']==float(c['maxstep'][:-1])*1e-12
        cache=j/'waveforms.npz';assert sha(cache)==r['local_outputs_sha256'][cache.name]
        with np.load(cache) as z:d={k:z[k] for k in z.files}
        t=d['time'];assert abs(t[0]-64e-6)<1e-15 and t[-1]>=p['stop_s']-1e-15
        with np.load(src.parent/'waveforms.npz') as previous:
            skip={'time','units','energy_nj','power_mw','obsphase','obscycles','obsctrl','obsdivcycles'}
            names=[k for k in previous.files if k in d and k not in skip and ':' not in k]
            changes={k:abs(float(d[k][0])-float(previous[k][-1])) for k in names}
        assert changes and max(changes.values())<1e-3
        row['native_boundary']=dict(passed=True,compared_physical_nodes=len(changes),maximum_difference_v=max(changes.values()))
        sel=t>=p['measurement']['start_s'];e=cross(t,d['out'],.6);e=e[e>=p['measurement']['start_s']]
        n=p['measurement']['edges'];assert len(e)>=n and np.all(np.diff(e)>.8/984e6) and np.all(np.diff(e)<1.2/984e6)
        edges[c['run']]=e[:n]
        # The actual controller samples the combinational detector on ref_fall.
        # Continuous phase_good is not its acceptance signal; verify phase_held.
        good=all(np.min(d[k][sel])>1.0 for k in ['qualified','frequency_good','cfg_ready','amp_good','XP.XC.phase_held']) and np.max(abs(d['range_error'][sel]))<.2
        logic={k:dict(min_v=float(np.min(d[k][sel])),max_v=float(np.max(d[k][sel])),
            high_time_fraction=float(np.trapezoid((d[k][sel]>.6).astype(float),t[sel])/(t[sel][-1]-t[sel][0])))
            for k in ['qualified','frequency_good','cfg_ready','amp_good','phase_good','XP.XC.phase_held','range_error']}
        row.update(completed=True,numerically_clean=row['recovery']['numerically_clean'],status_stable=bool(good),
            measured_output_mhz=float((n-1)/(e[n-1]-e[0])/1e6),control_range_v=[float(min(d['XP.ctrl'][sel])),float(max(d['XP.ctrl'][sel]))],
            raw_cache_sha256=sha(cache),log_sha256=sha(j/'spectre.out'),logic=logic)
    out=dict(scope=__doc__,condition=p['condition'],protocol_sha256=sha(pp),cases=rows,complete=all(r['completed'] for r in rows),passed=False,
        random_noise_measured=False,full_pll_acceptance=False,limitations=p['limitations'])
    out['logic_gate_definition']='Use the actual held detector output XP.XC.phase_held: pll_control_capture_v14 XPH samples phase_good on ref_fall and feeds XS. Raw phase_good pulse fraction is diagnostic, not a continuous-high requirement.'
    if out['complete']:
        e1=edges[p['cases'][0]['run']];e2=edges[p['cases'][1]['run']];assert max(abs(e1-e2))<.25/984e6
        residual=e1-e2;residual-=np.mean(residual)
        m=edge_band_power(residual,984e6,*p['measurement']['band_hz']);rms=float(np.sqrt(m['variance'])*1e15)
        checks=dict(clean=all(r['numerically_clean'] for r in rows),state=all(r['status_stable'] for r in rows),step_floor=rms<p['measurement']['maximum_floor_fs'])
        out.update(step_difference_rms_fs=rms,effective_band_hz=[m['lower'],m['upper']],checks=checks,passed=all(checks.values()),
            difference_note='Mean removed only; no fitted trend or spur notch. This is deterministic step sensitivity, not device-noise jitter.')
    (H/'results'/(prefix+'_validation.json')).write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2))

if __name__=='__main__':main()
