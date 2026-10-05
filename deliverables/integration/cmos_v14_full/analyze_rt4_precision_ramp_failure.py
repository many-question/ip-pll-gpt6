"""Audit the interrupted numerical bridge; no jitter or lock acceptance is inferred."""
from pathlib import Path
import datetime, hashlib, json, re
import numpy as np
from noise_utils import parse, stream_selected
from transient_diagnostics import recovery

H=Path(__file__).resolve().parent; ROOT=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    pp=H/'results/full_pll_precision_ramp_protocol.json'; p=json.loads(pp.read_text())
    d=ROOT/'research/runs/spectre_cmos_v14_full'/p['run']/p['case']
    r=json.loads((d/'result.json').read_text()); log=(d/'spectre.out').read_text()
    audit=json.loads((ROOT/'research/rt4_precision_ramp_remote_audit.json').read_text())
    assert not r['ok'] and 'spectre completes with 1 error, 2 warnings, and 97 notices.' in log
    assert 'SPECTRE-25' in log and not r['state_file']['collected']
    inputs={n:sha(d/'inputs'/n) for n in r['inputs_sha256']}
    assert inputs==r['inputs_sha256']==r['remote_inputs_sha256']
    outputs={n:dict(sha256=sha(d/n),bytes=(d/n).stat().st_size) for n in audit['outputs']}
    assert outputs==audit['outputs']
    raw=d/(p['case']+'.raw/tran.tran.tran'); a=parse(raw)
    independent,duplicates=stream_selected(raw,['qualified','frequency_good','XP.XC.phase_held','XP.XC.acquired','XP.restart','XP.vc1','XP.ctrl'])
    diffs={k:float(np.max(abs(v-a[k]))) for k,v in independent.items()}
    assert not duplicates and not any(diffs.values())
    np.savez_compressed(d/'waveforms.npz',**a)
    groups={}
    keys=['qualified','XP.XC.acquired','XP.XC.phase_held','frequency_good','amp_good','XP.en','XP.restart','range_error','XP.vc1']
    for label,lo,hi in [('prefix',0,16e-6),('last_intermediate_us',15e-6,16e-6),('after_transition',16e-6,20e-6)]:
        m=(a['time']>=lo)&(a['time']<hi)
        groups[label]=dict(samples=int(m.sum()),time_s=[float(a['time'][m][0]),float(a['time'][m][-1])],
            ranges_v={k:[float(a[k][m].min()),float(a[k][m].max())] for k in keys})
    event=re.search(r"Warning from spectre at time = ([0-9.]+) us.*?SPECTRE-16780.*?signal: ([^.\s]+(?:\.[^.\s]+)*?)\. Check",log,re.S)
    assert event and event[2]=='XP.XV.XBN.MP5:int_s'
    warning_s=float(event[1])*1e-6
    cancellation=json.loads((d/'cancellation.json').read_text())
    out=dict(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),run=p['run'],case=p['case'],
        protocol_sha256=sha(pp),source_result=(d/'result.json').relative_to(ROOT).as_posix(),source_result_sha256=sha(d/'result.json'),
        input_count=len(inputs),all_inputs_match=True,outputs=outputs,remote_local_outputs_match=True,
        termination='Project guard SIGINT after observed LTE recovery; SPECTRE-25 is the cancellation result.',
        cancellation=cancellation,completed=False,final_state_available=False,recovery=recovery(log),
        warning_time_s=warning_s,transition_time_s=16e-6,warning_delay_after_transition_s=warning_s-16e-6,
        warning_node=event[2],device_mapping='Negative tank capacitor-bank bit5 PMOS clamp MP5; reported node int_s is internal to its PDK model.',
        sampled_windows=groups,independent_parser_max_differences=diffs,saved_samples=len(a['time']),
        cache_sha256=sha(d/'waveforms.npz'),noise_enabled=False,full_pll_acceptance=False,integrated_jitter_fs=None,
        observation='No reported Newton/skipped-breakpoint recovery before the 16us tolerance step. Sampled control states remain high; no sampled reacquisition is observed.',
        inference='Temporal proximity suggests a dynamic-tolerance transition problem; it does not yet prove causation or a transistor defect.',
        next_experiment='Replay unchanged prefix only to15.9us, collecting a complete clean intermediate IC. Then test a separate constant-fine analysis with phase-continuous reference.',
        limitations=['2ns strobe data cannot verify RF edge timing, continuous lock or jitter.',
          'Both reltol and vabstol changed at16us; their individual effect is unresolved.',
          'Interrupted run has no final IC; partial observed voltages must not be used as a complete transistor state.'])
    (H/'results/full_pll_precision_ramp_failure.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({k:out[k] for k in ['saved_samples','warning_time_s','warning_node','recovery','full_pll_acceptance']},indent=2))

if __name__=='__main__':main()
