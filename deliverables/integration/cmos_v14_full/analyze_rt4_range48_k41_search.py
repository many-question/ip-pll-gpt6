"""Decode existing MOS FLL EVAL snapshots; no new simulation or design change."""
from pathlib import Path
import datetime,hashlib,json
import numpy as np
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    rows=[]
    for run,case in [('rt4r48k41ssd01','rt4r48_k41_tt')]:
        j=R/run/case;r=json.loads((j/'result.json').read_text())
        assert r['ok'] and sha(j/'waveforms.npz')==r['local_outputs_sha256']['waveforms.npz']
        assert all(sha(j/'inputs'/n)==v for n,v in r['inputs_sha256'].items())
        with np.load(j/'waveforms.npz') as z:d={n:z[n] for n in z.files}
        t=d['time']
        def bits(prefix,n):return sum((d[prefix+str(i)]>.6).astype(int)*(1<<i) for i in range(n))
        coarse=bits('XP.b',8);dac=bits('XP.XC.d',6);st=bits('XP.XC.state',3);counts=bits('XP.XC.m',14)
        ix=np.flatnonzero((st[1:]==3)&(st[:-1]!=3))+1;trials=[]
        for n,i in enumerate(ix):
            #20ns after decoded EVAL entry: prior count latch and ripple drain settled;
            #before next reference-clock EVAL action. Low-rate strobes are not RF edges.
            k=int(np.searchsorted(t,t[i]+20e-9));assert st[k]==3
            fine=n>=9;target=5248 if fine else 1312
            trials.append(dict(eval_us=float(t[i]*1e6),sample_us=float(t[k]*1e6),coarse=int(coarse[k]),dac=int(dac[k]),fine=fine,
                measured_count=int(counts[k]),target_count=target,error_count=int(counts[k]-target),
                counted_rf_mhz=float(counts[k]*(.75 if fine else 3)),
                observer_rf_mhz=float(d['obscycles'][k]*24),control_v=float(d['XP.ctrl'][k]),
                bias_v={n:float(d[n][k]) for n in ['XP.XV.XL.nb','XP.XV.XL.nfilt','XP.XV.XL.tail']}))
        late=t>=63e-6;change=np.r_[False,np.diff(d['obscycles'])!=0]
        rows.append(dict(run=run,case=case,source_result=(j/'result.json').relative_to(ROOT).as_posix(),source_result_sha256=sha(j/'result.json'),waveforms_sha256=sha(j/'waveforms.npz'),trials=trials,
            final_coarse=int(coarse[-1]),selected_dac=int(dac[-1]),late_rf_mhz=float(np.mean(d['obscycles'][late&change])*24),
            late_qualified=float(np.mean(d['qualified'][late]>.6)),late_control_v=[float(np.min(d['XP.ctrl'][late])),float(np.max(d['XP.ctrl'][late]))]))
    p=dict(time=datetime.datetime.now().astimezone().isoformat(),scope=__doc__,records=rows,
        observation='Range48 K41 selected coarse19/DAC46. Fine DAC48/40/44/46/45 counted5258/5239/5242/5251/5253 vs5248 target. DAC46 observer was3940.084885MHz during its earlier trial, rising to3944.49MHz near handoff and3947.997556MHz in the final microsecond; qualified never asserted.',
        inference='Best earlier count is stale at handoff; a stationary fine-search assumption is violated. Bias nfilt means also change, but cause is not isolated. No claim that AX error or bias alone caused this.',
        boundary='Single completed4.8fF cold capture. Counts from MOS logic snapshots; frequency from reference-triggered observer. No jitter claim, no forced-code repair.',
        action='One independent mapped-MOS candidate remeasures selected DAC, corrects one step from fresh counts, and requires two good windows before handoff; maximum8 checks. One K41 TT120us AX8ps/1e-3 only.',
        controller_source='share/deliverables/blocks/cmos_v14_full/fll_best128_v14.v',controller_sha256=sha(ROOT/'share/deliverables/blocks/cmos_v14_full/fll_best128_v14.v'))
    out=H/'results/rt4_range48_k41_search_review101.json';assert not out.exists();out.write_text(json.dumps(p,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps([{k:r[k] for k in ['run','final_coarse','selected_dac','late_rf_mhz']} for r in rows]))
if __name__=='__main__':main()
