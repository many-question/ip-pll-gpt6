"""Validate the completed intermediate state before a separate constant-fine test."""
from pathlib import Path
import datetime, hashlib, json, re
import numpy as np
from noise_utils import stream_selected
from transient_diagnostics import recovery

H=Path(__file__).resolve().parent; ROOT=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    pp=H/'results/full_pll_precision_stage_protocol.json'; p=json.loads(pp.read_text())
    d=ROOT/'research/runs/spectre_cmos_v14_full'/p['run']/p['case']
    rp=d/'result.json'; r=json.loads(rp.read_text()); log=(d/'spectre.out').read_text()
    assert r['ok'] and r['remote_inputs_match'] and r['state_file']['collected']
    assert 'spectre completes with 0 errors, 1 warning, and 29 notices.' in log
    assert 'tran noise is turning ON' not in log
    inputs={k:sha(d/'inputs'/k) for k in r['inputs_sha256']}
    assert inputs==r['inputs_sha256']==r['remote_inputs_sha256']
    remote=json.loads((ROOT/'research/rt4_precision_stage_remote_audit.json').read_text())
    for k,v in remote.items():
        f=d/'inputs'/k if k in inputs else d/k
        assert v==dict(sha256=sha(f),bytes=f.stat().st_size)
    outputs={k:v for k,v in remote.items() if k not in inputs}
    assert all(sha(d/k)==v for k,v in r['local_outputs_sha256'].items())
    with np.load(d/'waveforms.npz') as z:a={k:z[k] for k in z.files if k!='units'}
    assert a['time'][0]==0 and abs(a['time'][-1]-p['stop_s'])<1e-15
    keys=['qualified','frequency_good','XP.XC.phase_held','XP.XC.acquired','XP.restart','XP.vc1','XP.ctrl']
    independent,duplicates=stream_selected(d/(p['case']+'.raw/tran.tran.tran'),keys)
    diffs={k:float(max(abs(a[k]-v))) for k,v in independent.items()}
    assert not duplicates and not any(diffs.values())
    old=ROOT/'research/runs/spectre_cmos_v14_full/pllprecisionramp01/full_pll_rt4_precision_ramp_tt'
    previous=json.loads((old/'result.json').read_text())
    assert all(previous['inputs_sha256'][k]==v for k,v in inputs.items() if k!=p['case']+'.scs')
    previous_cache=old/'waveforms.npz'
    failure=json.loads((H/'results/full_pll_precision_ramp_failure.json').read_text())
    assert sha(previous_cache)==failure['cache_sha256']
    with np.load(previous_cache) as z:
        n=len(a['time']); prefix={k:float(max(abs(v-z[k][:n]))) for k,v in a.items()}
    assert not any(prefix.values())
    source=H/'state_inputs'/p['text_state'];assert sha(source)==p['text_state_sha256']
    def values(path):
        return {s.split()[0]:float(s.split()[1]) for s in path.read_text().splitlines() if s.strip() and not s.startswith('#')}
    initial=values(source);final=values(d/'final.ic')
    delta={k:abs(float(a[k][0])-initial[k]) for k in a if k in initial and ':' not in k}
    assert max(delta.values())<1e-9
    # writefinal includes every physical node and branch state, not just the save list.
    omitted=set(initial)-set(final)
    # Spectre collapses these two ideal zero-volt source nodes to ground.
    # They were explicitly listed in the source cold capture, whose sources pulsed.
    tb=(d/'inputs'/(p['case']+'.scs')).read_text()
    assert omitted=={'reset','apply'} and not (set(final)-set(initial))
    assert 'VRST (reset 0) vsource dc=0' in tb and 'VAP (apply 0) vsource dc=0' in tb
    assert all(initial[k]==0 for k in omitted) and all(np.isfinite(v) for v in final.values())
    final_delta={k:abs(float(a[k][-1])-final[k]) for k in a if k in final and ':' not in k}
    high=['qualified','XP.XC.acquired','XP.XC.phase_held','frequency_good','amp_good','cfg_ready','XP.en']
    low=['XP.restart','range_error']
    ranges={k:[float(a[k].min()),float(a[k].max())] for k in high+low+['XP.vc1']}
    status=all(ranges[k][0]>1.0 for k in high) and all(max(abs(x) for x in ranges[k])<.2 for k in low)
    rec=recovery(log)
    passed=bool(status and rec['numerically_clean'])
    assert passed
    out=dict(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),run=p['run'],case=p['case'],
        protocol_sha256=sha(pp),source_result=rp.relative_to(ROOT).as_posix(),source_result_sha256=sha(rp),
        condition=p['condition'],completed=True,accepted_steps=int(re.search(r'Number of accepted tran steps =\s+(\d+)',log)[1]),
        terminal_summary='0 errors, 1 warning, 29 notices',wall_time_s=r['metadata']['timings']['remote_exec'],
        input_count=len(inputs),all_inputs_match=True,remote_local_output_hashes_match=True,outputs=outputs,
        cache_sha256=sha(d/'waveforms.npz'),recovery=rec,sampled_status_stable=bool(status),sampled_ranges_v=ranges,
        samples=len(a['time']),independent_parser_max_differences=diffs,duplicate_records=duplicates,
        previous_invalid_run='pllprecisionramp01',common_valid_prefix_max_differences=prefix,
        common_prefix_s=[float(a['time'][0]),float(a['time'][-1])],compared_voltage_initial_nodes=len(delta),
        initial_maximum_voltage_difference_v=max(delta.values()),full_final_state_entries=len(final),
        source_state_entries=len(initial),all_non_ground_source_state_keys_preserved=True,
        omitted_ideal_ground_source_nodes=sorted(omitted),
        final_saved_voltage_maximum_difference_v=max(final_delta.values()),
        stage_passed=passed,noise_enabled=False,full_pll_acceptance=False,integrated_10khz_jitter_fs=None,
        observation='All 7951 sparse samples and 23 saved signals exactly reproduce the valid prefix of the interrupted ramp. No numerical recovery is reported; a complete writefinal state is available.',
        next_experiment='Separate fixed0.5ps/reltol1e-6/vabstol1nV/iabstol1pA test using byte-identical full terminal IC and a phase-continuous reference.',
        limitations=p['limitations']+['Absence of sampled reacquisition is not dense RF stationarity or continuous lock evidence.',
            'This success does not isolate reltol from vabstol, prove the old dynamic-step failure cause, or establish RT4 jitter.'])
    (H/'results/full_pll_precision_stage_validation.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({k:out[k] for k in ['stage_passed','samples','accepted_steps','recovery','full_final_state_entries','initial_maximum_voltage_difference_v','final_saved_voltage_maximum_difference_v','outputs']},indent=2))

if __name__=='__main__':main()
