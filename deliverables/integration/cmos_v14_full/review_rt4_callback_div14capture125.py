"""Review K9 callback full capture with independent terminal audits."""
from pathlib import Path
import datetime,json,sys
import numpy as np
from review_pdk_callback110 import ROOT,H,sha,stats

def main():
    ap,bp,out=map(Path,sys.argv[1:]);assert not out.exists()
    aa=[json.loads(x.read_text()) for x in [ap,bp]]
    gap=(datetime.datetime.fromisoformat(aa[1]['time'])-datetime.datetime.fromisoformat(aa[0]['time'])).total_seconds();assert gap>=60
    pp=H/'results/rt4_callback_div14capture125_protocol.json';p=json.loads(pp.read_text());c=p['cases'][0]
    w=ROOT/'research/runs/spectre_cmos_v14_full'/c['run']/c['case'];r=json.loads((w/'result.json').read_text())
    assert r['ok'] and not r['errors'] and r['remote_inputs_match']
    raw=w/(c['case']+'.raw/tran.tran.tran')
    for a in aa:
        assert a['transport_identity']==dict(hostname='thu-xia',user='jielu',uid=528)
        j=next(x for x in a['jobs'] if x['case']==c['case'])
        assert not j['alive'] and j['exit_marker']=='0' and j['raw_end']
        assert j['inputs']==r['inputs_sha256'] and j['remote_inputs_match']
        assert j['final_state_sha256']==sha(w/'final.ic')
        assert j['completed_output_hashes'][c['case']+'.raw/tran.tran.tran']==sha(raw)
        assert j['completed_output_hashes']['spectre.out']==sha(w/'spectre.out')
        assert j['effective']['maxstep']==8e-12 and j['effective']['reltol']==.001 and j['effective']['method']=='traponly'
    log=(w/'spectre.out').read_text();assert 'spectre completes with 0 errors' in log
    with raw.open('rb') as f:f.seek(-128,2);assert f.read().rstrip().endswith(b'END')
    with np.load(w/'waveforms.npz') as z:d={k:z[k] for k in z.files if k!='units'}
    t=d['time'];assert len(t)==60001 and abs(t[0])<1e-18 and abs(t[-1]-120e-6)<1e-15 and np.all(np.diff(t)>0)
    assert all(len(v)==len(t) and np.isfinite(v).all() for v in d.values())
    assert all(sha(w/'inputs'/n)==v for n,v in r['inputs_sha256'].items())
    assert sha(w/'waveforms.npz')==r['local_outputs_sha256']['waveforms.npz']
    assert aa[0]['jobs'][0]['completed_output_hashes']==aa[1]['jobs'][0]['completed_output_hashes']
    from decode_callback_low122 import decode,intervals
    from analyze_rt4_fast_range import analyze
    trace=decode(t,d,p['coarse_target_count'],p['fresh_target_count']);screen=analyze(c,p)
    screen.pop('interpretation',None)
    signal_names=['qualified','frequency_good','phase_good','amp_good','range_error','XP.en','XP.restart','XP.XC.acquired']
    signals={n:dict(max_V=float(np.max(d[n])),final_V=float(d[n][-1]),intervals=intervals(t,d[n])) for n in signal_names}
    change=np.r_[False,(np.diff(d['obsphase'])!=0)|(np.diff(d['obscycles'])!=0)|(np.diff(d['obsdivcycles'])!=0)]
    windows=[]
    spans=[dict(start_s=float(t[-1]-1e-6),end_s=float(t[-1]),label='last1us')]
    for n in ['XP.en','qualified']:
        spans.extend(dict(**x,label=n) for x in signals[n]['intervals'])
    for span in spans:
        lo,hi=span['start_s'],span['end_s'];m=(t>=lo)&(t<=hi)&change
        item=dict(**span,observer_updates=int(np.count_nonzero(m)))
        if hi>lo and np.count_nonzero(m):
            f=d['obsdivcycles'][m]*24;rf=d['obscycles'][m]*24
            item.update(output_MHz=float(np.mean(f)),rf_MHz=float(np.mean(rf)),max_abs_frequency_offset_ppm=float(np.max(np.abs(f/c['target_out_mhz']-1))*1e6),
                ctrl=stats(t,d['XP.ctrl'],lo,hi),nfilt=stats(t,d['XP.XV.XL.nfilt'],lo,hi),phase_observer=stats(t,d['obsphase'],lo,hi),
                enabled_duration_s=hi-lo,full_512ref_supervisor_horizon_observed=(hi-lo>=512/24e6))
        windows.append(item)
    from analyze_callback_div14capture125 import configuration_and_mode
    config,mode=configuration_and_mode(t,d,p)
    passed=bool(config['matches_expected'] and mode['ratio_screen_passed'] and screen.get('fast_functional_screen_passed') and trace['all_observed_transitions_match'] and trace['fresh_budget_respected']
        and trace['handoff_qualified_by_observed_counts'] and all(h['duration_matches_32ref'] for h in trace['handoff_intervals'])
        and not signals['range_error']['intervals'] and not signals['XP.restart']['intervals'])
    data=dict(time=datetime.datetime.now().astimezone().isoformat(),protocol_sha256=sha(pp),script_sha256=sha(Path(__file__)),decoder_sha256=sha(H/'decode_callback_low122.py'),
      terminal=dict(exit_code=0,errors=0,stable_interval_s=gap,psf_end=True,raw_sha256=sha(raw),log_sha256=sha(w/'spectre.out'),final_ic_sha256=sha(w/'final.ic'),inputs_sha256=r['inputs_sha256']),
      audits=[dict(path=x.as_posix(),sha256=sha(x)) for x in [ap,bp]],points=len(t),finite_physical_waveforms=True,units_metadata_excluded=True,
      configuration=config,output_mode_observer=mode,waveforms_sha256=sha(w/'waveforms.npz'),controller=trace,signals=signals,windows=windows,quick_screen=screen,callback_single_K9_capture_passed=passed,
      interpretation='Observed single-K9/M14 TT callback capture passes its functional screen.' if passed else 'The complete record did not satisfy every capture/transition gate; inspect state trace and observation boundaries before choosing a follow-up.',
      full_project_acceptance=False,noise_evaluated=False,boundary=p['evidence_boundary'],observation_limit=p['observation_limit'])
    out.write_text(json.dumps(data,indent=2)+'\n')
    print(json.dumps(dict(passed=passed,points=len(t),fresh=[x for x in trace['eval_snapshots'] if x['stage']=='fresh'],windows=windows),indent=2))
if __name__=='__main__':main()
