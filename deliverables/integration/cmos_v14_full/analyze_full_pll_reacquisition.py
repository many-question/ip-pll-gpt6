"""Audit actual pre-noise loss of qualification, keeping sparse-time uncertainty."""
from pathlib import Path
import hashlib,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from noise_utils import stream_selected
from transient_diagnostics import recovery,effective
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def event(d,key,direction):
    t=d['time'];y=d[key]
    selected=(y[:-1]>=.6)&(y[1:]<.6) if direction=='fall' else (y[:-1]<.6)&(y[1:]>=.6)
    ids=np.flatnonzero(selected)
    return [dict(bracket_ns=[float(t[i]*1e9),float(t[i+1]*1e9)],endpoint_v=[float(y[i]),float(y[i+1])]) for i in ids]

def main():
    cases=[('pllnoisesettle02','full_pll_noise_moderate_settling_tt'),
           ('pllnoisedirectoff01','full_pll_direct_noise_off_tt'),('pllnoisedirecton01','full_pll_direct_noise_on_tt')]
    keys=['phase_good','amp_good','XP.XC.phase_held','frequency_good','qualified','XP.en','XP.XC.acquired','XP.ctrl']
    rows=[];data={}
    for run,case in cases:
        j=R/run/case;raw=j/(case+'.raw')/'tran.tran.tran';rp=j/'result.json';log=(j/'spectre.out').read_text()
        extra=['XP.restart','XP.hp','XP.hn','XP.vc1','obsphase','obscycles','obsdivcycles','obsctrl'] if run=='pllnoisesettle02' else []
        d,_=stream_selected(raw,keys+extra);data[run]=d
        events={k:event(d,k,'fall') for k in ['XP.XC.phase_held','qualified','frequency_good','XP.en','XP.XC.acquired']}
        if 'XP.restart' in d:events['XP.restart']=event(d,'XP.restart','rise')
        rows.append(dict(run=run,case=case,source_result=rp.relative_to(ROOT).as_posix(),source_sha256=sha(rp),
            raw_sha256=sha(raw),log_sha256=sha(j/'spectre.out'),effective=effective(log),recovery=recovery(log),
            completed=False,noise_ever_enabled='tran noise is turning ON' in log,
            sampled_stop_ns=float(d['time'][-1]*1e9),amplitude_min_v=float(min(d['amp_good'])),events=events))
    # Same full circuit/engine and actual quiet prefix, differing only in future noise activation.
    a=data[cases[1][0]];b=data[cases[2][0]];common=a['time']<=b['time'][-1]+1e-18
    prefix={k:float(max(abs(a[k][common]-np.interp(a['time'][common],b['time'],b[k])))) for k in keys}
    # Compare fine native continuation with text initialization, including measured physical phase.
    native=R/'pllnoisefloor05p03/rt4bank_capture_tt/waveforms.npz'
    with np.load(native) as z:
        nt=z['time']-z['time'][0];nk={k:z[k] for k in ['obsphase','obscycles','obsctrl','XP.ctrl','XP.hp','XP.hn','XP.vc1','XP.XC.phase_held']}
    moderate=data['pllnoisesettle02'];sel=moderate['time']<nt[-1]-1e-12
    agreement={k:float(np.sqrt(np.mean((moderate[k][sel]-np.interp(moderate['time'][sel],nt,nk[k]))**2))) for k in ['obsphase','obsctrl','XP.ctrl','XP.vc1']}
    samples=[]
    for cycle in range(6):
        ts=(cycle/24e6+12e-9);i=int(np.argmin(abs(nt-ts)))
        hp=float(nk['XP.hp'][i]);hn=float(nk['XP.hn'][i])
        samples.append(dict(ref_cycle=cycle,time_ns=float(nt[i]*1e9),hp_v=hp,hn_v=hn,
            resistive_upper_window_v=.9*hn+.12,resistive_upper_margin_v=.9*hn+.12-hp,
            observed_rf_phase_rad=float(nk['obsphase'][i]),rf_cycles_per_reference=float(nk['obscycles'][i]),
            control_v=float(nk['obsctrl'][i]),filter_v=float(nk['XP.vc1'][i])))
    result=dict(scope=__doc__,cases=rows,common_quiet_prefix_max_delta_v=prefix,
        native_source_sha256=sha(native),native05ps_vs_text05ps_rms_differences=agreement,held_midpoint_samples=samples,
        measured_order='Phase-held loss146–148ns, qualification loss/restart292–294ns, enable loss294–296ns, acquired/frequency-good loss296–298ns.',
        observation='The repeated phase failures occur before FLL restart. RF amplitude remains good. Both matched cases were stopped before noise activation1us.',
        inference='Abrupt4ps-to-fine initialization shifts effective oscillator frequency and held phase. The four-bad-cycle supervisor restarts before the slow loop-filter state settles. This is consistent with, but does not yet prove, a recoverable precision-transition transient.',
        unproven=['No steady fine-precision RT4 state has yet been demonstrated.',
                  'Do not infer that phase detector thresholds or supervisor logic must be changed from these initialization traces.',
                  'Ideal resistor-divider margins omit comparator offset, finite response and loading; they are diagnostic, not acceptance thresholds.'],
        full_pll_acceptance=False,integrated_10khz_jitter_fs=None,
        precision='Event brackets reflect2ns saved samples. Sparse RF voltage samples cannot measure frequency or jitter; RF phase/cycles come from the timestep event observer and native dense run.')
    out=H/'results/full_pll_reacquisition_diagnosis.json';out.write_text(json.dumps(result,indent=2)+'\n')
    fig,ax=plt.subplots(4,1,figsize=(9,9),sharex=True,constrained_layout=True)
    t=moderate['time']*1e9
    for k,label in [('XP.XC.phase_held','phase held'),('qualified','qualified'),('XP.restart','restart'),('frequency_good','frequency good')]:ax[0].step(t,moderate[k],where='post',label=label)
    ax[0].legend(ncol=2);ax[0].set_ylabel('Logic (V)')
    ax[1].plot(t,moderate['obsphase'],label='Event-observed RF phase');ax[1].set_ylabel('Phase (rad)');ax[1].legend()
    ax[2].plot(t,(moderate['obscycles']-164)*24,label='RF frequency error');ax[2].set_ylim(-.3,1.5);ax[2].set_ylabel('RF error (MHz)');ax[2].legend()
    ax[3].plot(t,moderate['obsctrl'],label='control at reference edge');ax[3].plot(t,moderate['XP.vc1'],label='filter capacitor');ax[3].set_ylabel('Voltage (V)');ax[3].set_xlabel('Warm restart time (ns)');ax[3].legend()
    for a in ax:a.grid(alpha=.3);a.set_xlim(0,335);a.axvspan(292,298,color='red',alpha=.12)
    fig.suptitle('Complete RT4 PLL: deterministic loss before noise activation\nTT27 / 1.2 V / 984 MHz / 10 fF / Q5 RLC; 0.5 ps')
    dst=H/'results/figures/full_pll_pre_noise_reacquisition.png';dst.parent.mkdir(exist_ok=True);fig.savefig(dst,dpi=160);plt.close(fig)
    print(json.dumps(dict(result=out.name,common_prefix_max_v=max(prefix.values()),native_agreement=agreement,held_samples=samples),indent=2))

if __name__=='__main__':main()
