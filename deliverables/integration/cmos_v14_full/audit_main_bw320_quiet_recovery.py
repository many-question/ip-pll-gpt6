"""Audit the complete original V14 320 GHz quiet record, without claiming noise acceptance."""
from pathlib import Path
import datetime, json, re
import numpy as np
from audit_rt4_half_seed29_noise_recovery import stream_selected, sha
from noise_utils import cross
from transient_diagnostics import effective, recovery

H=Path(__file__).resolve().parent
ROOT=H.parents[3]

def main():
    pp=H/'results/full_pll_main_bw320_pair_protocol.json';p=json.loads(pp.read_text())
    vp=H/'results/full_pll_main_bw320_quiet_validation89.json';v=json.loads(vp.read_text());q=v['cases'][0]
    c=p['cases'][0];d=ROOT/'research/runs/spectre_cmos_v14_full'/c['run']/c['case']
    rp=d/'result.json';r=json.loads(rp.read_text())
    ap=ROOT/'research/main_bw320_quiet_remote_audit89.json';proof=json.loads(ap.read_text())
    assert r['ok'] and r['remote_inputs_match'] and r['state_file']['collected']
    assert q['completed'] and q['source_sha256']==sha(rp) and v['protocol_sha256']==sha(pp)
    assert proof['before_after_identical'] and proof['local_hashes_match'] and proof['exit_code']=='0' and not proof['old_pid_exists']
    inputs={n:sha(d/'inputs'/n) for n in r['inputs_sha256']}
    assert inputs==r['inputs_sha256']==r['remote_inputs_sha256']==proof['inputs']
    outputs={}
    for n,x in proof['files'].items():
        f=d/('final.ic' if n=='final_state.ic' else n)
        outputs[n]=dict(bytes=f.stat().st_size,sha256=sha(f))
        assert all(outputs[n][k]==x[k] for k in outputs[n])
    log=(d/'spectre.out').read_text();settings=effective(log);numerics=recovery(log)
    assert settings['method']=='traponly' and settings['maxstep']==p['maxstep_s']
    assert settings['reltol']==p['reltol'] and settings['abstol(V)']==p['vabstol'] and settings['abstol(I)']==p['iabstol']
    assert settings['noisefmax']==p['noisefmax_hz'] and settings['noisefmin']==p['noisefmin_hz']
    assert 'tran noise is turning ON' not in log
    assert q['status_stable'] and q['stationarity']['passed'] and q['initial_maximum_voltage_difference_v']<1e-9
    assert numerics['numerically_clean']
    ringing='Trapezoidal ringing is detected' in log
    ringing_nodes=re.findall(r'Found trapezoidal ringing on node ([^\n]+)',log)
    # Preserve the established five gates. Ringing is a separate disclosed risk, not proof of convergence.
    summary=re.findall(r'spectre completes with[^\n]*',log,re.I);assert len(summary)==1 and '0 errors' in summary[0]
    assert 'Initial condition solution time' in log or 'initial condition' in log.lower()
    print('Terminal and remote/local hashes verified; independently reading raw.',flush=True)
    cache=d/'waveforms.npz';assert sha(cache)==r['local_outputs_sha256'][cache.name]
    a,duplicates=stream_selected(d/(c['case']+'.raw/tran.tran.tran'),p['observations'])
    with np.load(cache) as z:diffs={k:float(np.max(abs(x-z[k]))) for k,x in a.items()}
    assert not any(diffs.values()) and not duplicates
    t=a['time'];assert t[0]==0 and abs(t[-1]-p['stop_s'])<1e-15
    state={}
    for line in (d/'final.ic').read_text().splitlines():
        if line.strip() and not line.startswith('#'):
            fields=line.split();assert fields[0] not in state;state[fields[0]]=float(fields[1])
    initial={line.split()[0]:float(line.split()[1]) for line in (H/'state_inputs'/p['text_state']).read_text().splitlines() if line.strip() and not line.startswith('#')}
    assert sha(H/'state_inputs'/p['text_state'])==p['text_state_sha256']
    assert set(initial)==set(state) and len(state)>7800 and all(np.isfinite(x) for x in state.values())
    startdiff={k:abs(float(x[0])-initial[k]) for k,x in a.items() if k in initial and ':' not in k}
    finaldiff={k:abs(float(x[-1])-state[k]) for k,x in a.items() if k in state}
    assert len(startdiff)==19 and max(startdiff.values())<=1e-9 and max(finaldiff.values())<1e-9
    dense=t>=1e-6;rf=cross(t[dense],(a['XP.vp']-a['XP.vn'])[dense],0);out=cross(t[dense],a['out'][dense],.6)
    refs=cross(t[dense],a['XP.refb'][dense],.6);refs=refs[(refs>max(rf[0],out[0]))&(refs<min(rf[-1],out[-1]))]
    urf=np.interp(refs,rf,np.arange(len(rf)));uout=np.interp(refs,out,np.arange(len(out)));phase=np.unwrap(2*np.pi*(urf-np.floor(urf)))
    windows=[]
    for lo,hi in [(1.,1.5),(1.2,2.2),(1.5,2.),(1.7,2.2)]:
        m=(refs>=lo*1e-6)&(refs<=hi*1e-6);tr=refs[m]*1e6
        windows.append(dict(window_us=[lo,hi],reference_samples=int(m.sum()),phase_pp_rad=float(np.ptp(phase[m])),phase_drift_rad_per_us=float(np.polyfit(tr,phase[m],1)[0]),mean_output_mhz=float(np.mean(np.diff(uout[m]))*24),max_rf_cycles_error=float(np.max(abs(np.diff(urf[m])-164))),max_out_cycles_error=float(np.max(abs(np.diff(uout[m])-41))),control_slope_mv_per_us=float(np.polyfit(tr,np.interp(refs[m],t,a['XP.ctrl'])*1e3,1)[0]),filter_slope_mv_per_us=float(np.polyfit(tr,np.interp(refs[m],t,a['XP.vc1'])*1e3,1)[0])))
    w=windows[1];g=dict(minimum_reference_samples=23,phase_pp_rad_max=.02,abs_phase_drift_rad_per_us_max=.01,maximum_rf_cycles_error=.001,maximum_out_cycles_error=.001)
    assert w['reference_samples']>=g['minimum_reference_samples'] and w['phase_pp_rad']<=g['phase_pp_rad_max'] and abs(w['phase_drift_rad_per_us'])<=g['abs_phase_drift_rad_per_us_max'] and w['max_rf_cycles_error']<=g['maximum_rf_cycles_error'] and w['max_out_cycles_error']<=g['maximum_out_cycles_error']
    high=['qualified','cfg_ready','frequency_good','phase_good','amp_good','XP.XC.phase_held','XP.XC.acquired','XP.en'];low=['XP.restart','range_error'];m=t>=p['measurement_start_s']
    ranges={k:dict(min_v=float(a[k][m].min()),max_v=float(a[k][m].max())) for k in high+low}
    assert all(ranges[k]['min_v']>1.0 for k in high) and all(max(abs(ranges[k]['min_v']),abs(ranges[k]['max_v']))<.2 for k in low)
    result=dict(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),run=c['run'],case=c['case'],condition=p['condition'],source_result=rp.relative_to(ROOT).as_posix(),source_result_sha256=sha(rp),protocol_sha256=sha(pp),validation_at_audit_sha256=sha(vp),remote_hash_audit=ap.relative_to(ROOT).as_posix(),remote_hash_audit_sha256=sha(ap),remote_terminal_proof=proof,input_count=len(inputs),all_inputs_match=True,outputs=outputs,remote_local_raw_log_state_match=True,terminal_summary=summary[0],effective_settings=settings,numerical_diagnostics=numerics,trapezoidal_ringing_reported=ringing,ringing_nodes=ringing_nodes,numerical_convergence_established=False,cache_sha256=sha(cache),independent_parser_samples=len(t),independent_parser_max_differences=diffs,duplicate_records=duplicates,stop_s=float(t[-1]),initial_saved_voltage_differences_v=startdiff,final_state_entries=len(state),all_source_state_keys_preserved=True,final_state_saved_voltage_differences_v={k:x for k,x in finaldiff.items() if ':' not in k},final_state_saved_current_differences_a={k:x for k,x in finaldiff.items() if ':' in k},measurement_status_ranges=ranges,settling_windows=windows,quiet_validation=q,recovery_audit_passed=True,full_pll_acceptance=False,integrated_10khz_jitter_fs=None,limitations=['No noise result is produced by this quiet audit.','The unchanged complete last 1 us gate controls dispatch; shorter windows are diagnostic.','This bandwidth-only quiet study applies to original V14; RT4 remains separate.','Quiet similarity does not validate source-noise bandwidth convergence, noisy spectra or full-band jitter.','Spectre reports trapezoidal ringing at an internal node. The existing five gates do not test that internal waveform; its amplitude is unknown because it is not saved. Recovery audit success establishes data integrity and the stated gates only.'])
    dest=H/'results/full_pll_main_bw320_quiet_recovery_audit.json';assert not dest.exists();dest.write_text(json.dumps(result,indent=2)+'\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(2,1,figsize=(8,6),sharex=True)
    ax[0].plot(refs*1e6,phase-phase[0],'.-');ax[0].set_ylabel('RF phase change (rad)')
    for k in ['XP.ctrl','XP.vc1']:ax[1].plot(refs*1e6,np.interp(refs,t,a[k]),'.-',label=k)
    ax[1].set_ylabel('Voltage (V)');ax[1].set_xlabel('Continuation time (us)');ax[1].legend()
    for x in ax:x.grid(alpha=.3);x.axvspan(1.2,2.2,color='grey',alpha=.1)
    fig.suptitle('Original V14 full PLL: 320 GHz source-bandwidth quiet settling, TT 27 C\n0.25 ps, 100 fA, reltol 1e-6; shaded: required last 1 us gate')
    fig.tight_layout();fig.savefig(H/'results/figures/main_bw320_quiet_settling.png',dpi=150);plt.close(fig)
    print(json.dumps(dict(passed=True,samples=len(t),state_entries=len(state),windows=windows)),flush=True)

if __name__=='__main__':main()
