"""Review autonomous coarse SAR prefix; never label20us as full capture."""
from pathlib import Path
import datetime,json,sys
import numpy as np
from review_pdk_callback110 import ROOT,H,sha,stats
from decode_callback_low122 import decode

def main():
    ap,bp,out=map(Path,sys.argv[1:]);assert not out.exists()
    aa=[json.loads(x.read_text()) for x in [ap,bp]]
    gap=(datetime.datetime.fromisoformat(aa[1]['time'])-datetime.datetime.fromisoformat(aa[0]['time'])).total_seconds();assert gap>=60
    pp=H/'results/rt4_callback_low122_protocol.json';p=json.loads(pp.read_text());c=p['cases'][0]
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
    t=d['time'];assert len(t)==10001 and abs(t[0])<1e-18 and abs(t[-1]-20e-6)<1e-15 and np.all(np.diff(t)>0)
    assert all(len(v)==len(t) and np.isfinite(v).all() for v in d.values())
    def bits(pref,n):return sum((d[pref+str(i)]>.6).astype(np.int64)*(1<<i) for i in range(n))
    state=bits('XP.XC.state',3);coarse=bits('XP.b',8);dac=bits('XP.XC.d',6);counts=bits('XP.XC.m',14)
    snapshots=[];maskbit=128;endpoint=True;fine=False;first_fine=None
    for i in np.flatnonzero((state[1:]==3)&(state[:-1]!=3))+1:
        k=int(np.searchsorted(t,t[i]+20e-9))
        assert k<len(t) and state[k]==3, 'Inspect unexpectedly brief EVAL; no silent filtering'
        remain=np.flatnonzero(state[k:]!=3)
        if not len(remain):continue
        end=k+int(remain[0]);after=int(np.searchsorted(t,t[end]+20e-9))
        if after>=len(t):continue
        row=dict(time_s=float(t[k]),coarse=int(coarse[k]),dac=int(dac[k]),measured_count=int(counts[k]),
            transition_time_s=float(t[end]),next_coarse=int(coarse[after]),next_dac=int(dac[after]),
            count_gate_V=float(d['XP.count_gate'][k]),nfilt_V=float(d['XP.XV.XL.nfilt'][k]),ctrl_V=float(d['XP.ctrl'][k]),
            observer_instant_rf_MHz=float(d['obscycles'][k]*24))
        if not fine:
            measured=int(counts[k]);high=measured>p['coarse_target_count'];row['count_error']=measured-p['coarse_target_count']
            if endpoint:
                expected_coarse=128 if high else 0;expected_dac=11 if high else 32
                endpoint=False;fine=not high
            else:
                keep=int(coarse[k]) if high else int(coarse[k])&~maskbit
                if maskbit==1:expected_coarse=min(255,keep+2);expected_dac=32;fine=True
                else:maskbit>>=1;expected_coarse=keep|maskbit;expected_dac=11
            row.update(expected_coarse=expected_coarse,expected_dac=expected_dac,
                transition_matches=(int(coarse[after])==expected_coarse and int(dac[after])==expected_dac))
            if fine and first_fine is None:first_fine=dict(time_s=float(t[end]),coarse=int(coarse[after]),dac=int(dac[after]),transition_matches=row['transition_matches'])
        else:row['stage']='fine_search'
        snapshots.append(row)
    rows=[]
    for lo,hi in [[1e-6,2e-6],[15e-6,16e-6],[19e-6,20e-6]]:
        m=(t>=lo)&(t<=hi)
        rows.append(dict(window_s=[lo,hi],ctrl=stats(t,d['XP.ctrl'],lo,hi),nfilt=stats(t,d['XP.XV.XL.nfilt'],lo,hi),
            nb=stats(t,d['XP.XV.XL.nb'],lo,hi),observer_rf_MHz=stats(t,d['obscycles']*24,lo,hi),
            observer_output_MHz=stats(t,d['obsdivcycles']*24,lo,hi)))
    controller=decode(t,d,p['coarse_target_count'],p['fresh_target_count'])
    assert all(sha(w/'inputs'/n)==v for n,v in r['inputs_sha256'].items())
    assert sha(w/'waveforms.npz')==r['local_outputs_sha256']['waveforms.npz']
    assert aa[0]['jobs'][0]['completed_output_hashes']==aa[1]['jobs'][0]['completed_output_hashes']
    signals={n:dict(max_V=float(np.max(d[n])),final_V=float(d[n][-1]),high_fraction=float(np.mean(d[n]>.6))) for n in ['qualified','frequency_good','range_error','XP.en','XP.restart','XP.XC.acquired']}
    data=dict(time=datetime.datetime.now().astimezone().isoformat(),protocol_sha256=sha(pp),script_sha256=sha(Path(__file__)),
        terminal=dict(exit_code=0,errors=0,stable_interval_s=gap,psf_end=True,raw_sha256=sha(raw),log_sha256=sha(w/'spectre.out'),final_ic_sha256=sha(w/'final.ic'),inputs_sha256=r['inputs_sha256']),
        audits=[dict(path=x.as_posix(),sha256=sha(x)) for x in [ap,bp]],points=len(t),finite_physical_waveforms=True,units_metadata_excluded=True,
        waveforms_sha256=sha(w/'waveforms.npz'),eval_snapshots=snapshots,first_fine_search=first_fine,coarse_search_completed=first_fine is not None,
        sar_transition_checks_all_match=bool(snapshots) and all(x.get('transition_matches',True) for x in snapshots),windows=rows,signals=signals,
        controller=controller,full_capture_evaluated=False,interpretation='Observed autonomous coarse search only. Low enable/qualified in a planned20us startup prefix is not evidence of capture failure. Observer instantaneous RF is not the acquisition-window count.',boundary=p['evidence_boundary'])
    out.write_text(json.dumps(data,indent=2)+'\n');print(json.dumps(dict(points=len(t),snapshots=snapshots,first_fine=first_fine,signals=signals),indent=2))
if __name__=='__main__':main()
