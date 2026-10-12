"""Analyze completed quick AX records without imposing noise-signoff precision."""
from pathlib import Path
import datetime, hashlib, json, re
import numpy as np
from transient_diagnostics import effective
from analyze import cross
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
P=H/'results/rt4_fast_range_protocol.json';OUT=ROOT/'research/rt4_fast_range_validation_latest.json'
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()
def analyze(c,p):
    j=R/c['run']/c['case'];rp=j/'result.json'
    if not rp.exists():return dict(**c,state='pending')
    r=json.loads(rp.read_text());lp=j/'spectre.out'
    if not r.get('local_outputs_sha256') or not lp.exists():return dict(**c,state='collecting_or_needs_recovery')
    log=lp.read_text(errors='replace')
    if not re.search(r'spectre completes with \d+ errors?',log):return dict(**c,state='unconfirmed_terminal')
    row=dict(**c,state='completed',source_result=rp.relative_to(ROOT).as_posix(),source_result_sha256=sha(rp),effective=effective(log))
    if not r['ok'] or 'spectre completes with 0 errors' not in log:
        return dict(row,state='simulator_failed',errors=r['errors'])
    assert r['remote_inputs_match']
    assert all(sha(j/'inputs'/n)==v for n,v in r['inputs_sha256'].items())
    assert sha(j/'waveforms.npz')==r['local_outputs_sha256']['waveforms.npz']
    eff=row['effective']
    assert np.isclose(eff['maxstep'],p['maxstep_s'],rtol=1e-9,atol=0) and eff['reltol']==p['reltol']
    raw=j/(c['case']+'.raw/tran.tran.tran')
    with raw.open('rb') as f:f.seek(max(0,raw.stat().st_size-256));end=f.read().rstrip()
    assert end.endswith(b'END'),'Raw transient incomplete'
    row['raw_sha256']=sha(raw);row['raw_bytes']=raw.stat().st_size
    row['numerical_messages']={k:log.count(v) for k,v in dict(newton='Newton iteration fails to converge',skipped='SPECTRE-17087',lte='SPECTRE-16780').items()}
    with np.load(j/'waveforms.npz') as z:d={k:z[k] for k in z.files}
    t=d['time'];assert t[-1]>=c['stop_s']*(1-1e-6)
    row['final_time_s']=float(t[-1]);row['input_hashes_verified']=True
    if c['kind']=='tuning':
        e=cross(t,d['vp']-d['vn'],0);o=cross(t,d['out'])
        assert len(e)>10,'Oscillation absent in endpoint record'
        rf=float(1e-6/np.mean(np.diff(e)));fo=float(1e-6/np.mean(np.diff(o))) if len(o)>3 else None
        row.update(rf_mhz=rf,output_mhz=fo,differential_swing_pp_v=float(np.ptp(d['vp']-d['vn'])),divider_ratio_ok=bool(fo and abs(fo*c['m']/rf-1)<.005))
    else:
        win=t>=t[-1]-p['capture_screen']['window_s']
        # Observe actual crossing counts per reference, rather than aliasing the strobed RF waveform.
        change=np.r_[False,(np.diff(d['obsphase'])!=0)|(np.diff(d['obscycles'])!=0)|(np.diff(d['obsdivcycles'])!=0)]
        m=win&change;assert np.count_nonzero(m)>10
        f=d['obsdivcycles'][m]*24;rf=d['obscycles'][m]*24
        target=c['target_out_mhz'];error=float(abs(np.mean(f)/target-1));spread=float(np.ptp(f)/target)
        q=float(np.mean(d['qualified'][win]>.6));good=float(np.mean(d['frequency_good'][win]>.6));range_max=float(np.max(d['range_error'][win]))
        row.update(output_mhz=float(np.mean(f)),rf_mhz=float(np.mean(rf)),output_relative_error=error,output_relative_spread=spread,
            qualified_fraction=q,frequency_good_fraction=good,range_error_max_v=range_max,control_v=[float(np.min(d['XP.ctrl'][win])),float(np.max(d['XP.ctrl'][win]))],
            coarse_code_final=sum((int(d['XP.b'+str(b)][-1]>.6)<<b) for b in range(8)),
            acquired_final=bool(d['XP.XC.acquired'][-1]>.6),
            fast_functional_screen_passed=bool(error<=.005 and spread<=.005 and q>=.99 and good>=.99 and range_max<.2))
        if not row['fast_functional_screen_passed']:row['interpretation']='Did not meet quick capture gates within64us; not proof of permanent inability to lock.'
    return row
def main():
    p=json.loads(P.read_text());rows=[]
    for c in p['cases']:
        try:rows.append(analyze(c,p))
        except Exception as e:rows.append(dict(**c,state='analysis_needs_review',reason=repr(e)))
    tunes=[r for r in rows if r['kind']=='tuning' and r['state']=='completed']
    summary=dict(time=datetime.datetime.now().astimezone().isoformat(),protocol_sha256=sha(P),cases=rows,
        completed=sum(r['state']=='completed' for r in rows),expected=len(rows),full_pll_acceptance=False,
        boundary='Sparse TT functional/tuning screen, relaxed AX settings; no random jitter or complete33-channel/PVT acceptance.')
    by={(r['coarse_code'],r['control_v']):r for r in tunes}
    if (255,.2) in by and (0,1.) in by:
        low=by[(255,.2)]['rf_mhz'];high=by[(0,1.)]['rf_mhz']
        summary['observed_endpoint_range_mhz']=[low,high]
        summary['target_endpoints_covered']=bool(low<=2688 and high>=3936)
        summary['low_end_gap_mhz']=max(0,low-2688)
        summary['representative_targets_below_observed_low']=[r['target_out_mhz'] for r in p['cases'] if r['kind']=='capture' and r['target_rf_mhz']<low]
    if (127,.2) in by and (128,1.) in by:
        summary['binary_carry_overlap_mhz']=by[(128,1.)]['rf_mhz']-by[(127,.2)]['rf_mhz']
    OUT.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k!='cases'},ensure_ascii=False))
if __name__=='__main__':main()
