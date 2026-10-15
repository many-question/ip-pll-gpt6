"""Review one physical DAC/free-bias/count-window experiment with stable independent terminal proofs."""
from pathlib import Path
import datetime
import json
import sys
import numpy as np
from review_pdk_callback110 import ROOT, H, sha, clock, stats


def main():
    ap, bp, out = map(Path, sys.argv[1:])
    assert not out.exists()
    aa = [json.loads(p.read_text()) for p in (ap, bp)]
    gap = (datetime.datetime.fromisoformat(aa[1]['time']) -
           datetime.datetime.fromisoformat(aa[0]['time'])).total_seconds()
    assert gap >= 60
    pp = H / 'results/rt4_callback_margin115_protocol.json'
    protocol = json.loads(pp.read_text())
    c = protocol['cases'][0]
    work = ROOT / 'research/runs/spectre_cmos_v14_full' / c['run'] / c['case']
    r = json.loads((work / 'result.json').read_text())
    assert r['ok'] and not r['errors'] and r['remote_inputs_match']
    raw = work / (c['case'] + '.raw/tran.tran.tran')
    for a in aa:
        assert a['transport_identity'] == dict(hostname='thu-xia', user='jielu', uid=528)
        j = next(x for x in a['jobs'] if x['case'] == c['case'])
        assert not j['alive'] and j['exit_marker'] == '0' and j['raw_end']
        assert j['remote_inputs_match'] and j['inputs'] == r['inputs_sha256']
        assert j['final_state_sha256'] == sha(work / 'final.ic')
        assert j['completed_output_hashes'][c['case'] + '.raw/tran.tran.tran'] == sha(raw)
        assert j['completed_output_hashes']['spectre.out'] == sha(work / 'spectre.out')
        assert j['effective']['method'] == 'traponly' and j['effective']['maxstep'] == 8e-12
        assert j['effective']['reltol'] == .001
    assert 'spectre completes with 0 errors' in (work / 'spectre.out').read_text()
    with raw.open('rb') as f:
        f.seek(-128, 2)
        assert f.read().rstrip().endswith(b'END')
    with np.load(work / 'waveforms.npz') as z:
        d = {k: z[k] for k in z.files if k != 'units'}
    t = d['time']
    assert len(t) == c['expected_points'] and abs(t[0]) < 1e-18
    assert abs(t[-1] - c['stop_s']) < 1e-16 and np.all(np.diff(t) > 0)
    assert all(len(v) == len(t) and np.isfinite(v).all() for v in d.values())
    def rises(y, lo, hi, threshold=.6):
        ix=np.flatnonzero((y[:-1]<threshold)&(y[1:]>=threshold))
        et=t[ix]+(threshold-y[ix])*(t[ix+1]-t[ix])/(y[ix+1]-y[ix])
        return et[(et>=lo)&(et<=hi)]
    lo,hi=protocol['counter_snapshot_window_s']; mask=(t>=lo)&(t<=hi)
    decoded=sum((d['m'+str(i)][mask]>.6).astype(np.int64)*(1<<i) for i in range(14))
    unique_counts=np.unique(decoded).tolist()
    logic_valid=all(np.all((d['m'+str(i)][mask]<.2)|(d['m'+str(i)][mask]>1.0)) for i in range(14))
    assert logic_valid and len(unique_counts)==1, 'Snapshot not a settled digital word'
    count=int(unique_counts[0]); target=protocol['target_count']
    gate_edges=rises(d['count_gate'],0,t[-1])
    gate_falls=rises(-d['count_gate'],0,t[-1],-.6)
    assert len(gate_edges)==1 and len(gate_falls)==1
    ga,gb=float(gate_edges[0]),float(gate_falls[0])
    planned_a,planned_b=protocol['count_gate_half_crossings_s']
    saved_edge_errors=[ga-planned_a,gb-planned_b]
    # A piecewise ramp sampled every10ps can straddle a flat/ramp breakpoint.
    # Threshold interpolation therefore cannot promise2fs edge accuracy.
    # Check the saved waveform against the exact hashed PWL input instead.
    strobe=c['strobe_s']
    assert max(abs(v) for v in saved_edge_errors)<=strobe
    ramp=10e-12
    expected_gate=np.minimum(np.clip((t-(planned_a-ramp/2))/ramp,0,1),
                             np.clip(((planned_b+ramp/2)-t)/ramp,0,1))*1.2
    gate_error=float(np.max(np.abs(d['count_gate']-expected_gate)))
    assert gate_error<1e-4, 'Saved gate disagrees with the frozen PWL source'
    assert abs((planned_b-planned_a)-protocol['measurement_duration_s'])<2e-15
    observed_ga,observed_gb=ga,gb
    ga,gb=planned_a,planned_b
    for i in range(8):assert np.allclose(d['b'+str(i)],1.2 if (protocol['coarse']>>i)&1 else 0,atol=1e-6)
    for i in range(6):assert np.allclose(d['d'+str(i)],1.2 if (protocol['dac']>>i)&1 else 0,atol=1e-6)
    # Ignore reset-high startup. Count the physical safe-gated clock through drain.
    gated_edges=rises(d['XCOUNT.gclk'],1.46e-6,7e-6)
    raw_acq_edges=rises(d['acqclk'],ga,gb)
    count_clock_edges=rises(d['count_clock'],ga,gb)
    rows=[]
    for lo,hi in protocol['frequency_windows_s']:
        mask=(t>=lo)&(t<=hi)
        rf=clock(t,d['vp']-d['vn'],lo,hi,0.)
        output=clock(t,d['out'],lo,hi)
        sub=[clock(t,d['vp']-d['vn'],lo+i*100e-9,lo+(i+1)*100e-9,0.)['frequency_Hz'] for i in range(3)]
        rows.append(dict(window_s=[lo,hi],rf=rf,output=output,rf_100ns_means_Hz=sub,
            divide4_observed=abs(rf['frequency_Hz']/output['frequency_Hz']-4)<.004,
            ctrl=stats(t,d['ctrl'],lo,hi),preset=stats(t,d['preset'],lo,hi),
            nfilt=stats(t,d['XV.XL.nfilt'],lo,hi),nb=stats(t,d['XV.XL.nb'],lo,hi),
            nfilt_linear_drift_V_per_us=float(np.polyfit((t[mask]-lo)*1e6,d['XV.XL.nfilt'][mask],1)[0])))
    measurement_rf=clock(t,d['vp']-d['vn'],ga,gb,0.)
    data=dict(time=datetime.datetime.now().astimezone().isoformat(),
        protocol_sha256=sha(pp),script_sha256=sha(Path(__file__).resolve()),
        terminal=dict(exit_code=0,errors=0,stable_interval_s=gap,psf_end=True,
            raw_sha256=sha(raw),final_ic_sha256=sha(work/'final.ic'),log_sha256=sha(work/'spectre.out'),inputs_sha256=r['inputs_sha256']),
        audits=[dict(path=p.as_posix(),sha256=sha(p)) for p in (ap,bp)],points=len(t),
        finite_physical_waveforms=True,units_metadata_excluded=True,waveforms_sha256=sha(work/'waveforms.npz'),
        coarse=protocol['coarse'],dac=protocol['dac'],gate_window_s=[ga,gb],
        saved_waveform_gate_crossings_s=[observed_ga,observed_gb],saved_gate_edge_errors_s=saved_edge_errors,
        gate_pwl_max_saved_voltage_error_V=gate_error,
        analysis_revision='116: retain115 script unchanged; verify saved gate against exact hashed PWL and bound interpolated crossings by10ps output resolution. Use exact PWL half-crossings for the counting interval; solver/input unchanged.',
        physical_snapshot_count=count,target_count=target,signed_count_error=count-target,
        physical_gated_clock_edges=len(gated_edges),counter_matches_gated_edges=count==len(gated_edges),
        raw_acq_edges_within_gate=len(raw_acq_edges),buffered_clock_edges_within_gate=len(count_clock_edges),
        measurement_rf=measurement_rf,segments=rows,
        rtl_predicate_if_evaluated_at_this_code=dict(need_faster=protocol['dac']>=49 and count<target,
            need_slower=protocol['dac']<=15 and count>target,within_one_count=abs(count-target)<=1),
        interpretation='RTL predicates are offline evaluation of the observed snapshot, not execution of the absent FLL FSM. One sample cannot prove consecutive acceptance, selected next coarse code, handoff or lock.',
        boundary=protocol['evidence_boundary'])
    out.write_text(json.dumps(data,indent=2)+'\n')
    print(json.dumps({k:data[k] for k in ['points','physical_snapshot_count','signed_count_error','counter_matches_gated_edges','rtl_predicate_if_evaluated_at_this_code','segments']},indent=2))

if __name__=='__main__':main()
