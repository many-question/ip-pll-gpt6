"""Measure the CP conducting-window mismatch from accepted intrinsic PSS data.

This is deterministic conduction timing, not time-window noise attribution.
It motivates a separate settling experiment without adopting a candidate.
"""
from pathlib import Path
import hashlib,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from noise_utils import cross
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    dst=H/'results/cp_dynamic_timing_validation.json';assert not dst.exists()
    p=H/'results/frontend_operating_probe_validation.json';v=json.loads(p.read_text())
    assert v['operating_data_valid'] and v['balanced'] and v['periodic']['periodic_passed']
    j=(ROOT/v['periodic']['source_result']).parent
    raw=j/(j.name+'.raw')/'pss.td.pss';assert sha(raw)==v['periodic']['td_sha256']
    with np.load(j/'cp_noise_mechanism_traces.npz') as z:
        assert str(z['source_sha256'])==sha(raw)
        d={n:z[n] for n in z.files if n!='source_sha256'}
    t=d['time'];T=t[-1]-t[0];on=d['XCP.gate']>.6
    rise=cross(t,d['XCP.gate']);fall=cross(t,-d['XCP.gate'],-.6)
    assert len(rise)==len(fall)==1 and fall[0]>rise[0]
    t0=rise[0];ton=fall[0]-t0;mean=lambda y:float(np.trapezoid(y,t)/T)
    pair=d['XCP.MIP:id']+d['XCP.MIN:id'];tail=d['XCP.MT:id']
    qp=mean(pair)*T;qp_on=mean(pair*on)*T
    qt=mean(tail)*T;qt_on=mean(tail*on)*T
    samples=[]
    names=['XCP.ng','XCP.tail','XCP.mir','hp','hn','XCP.MT:id','XCP.MIP:id','XCP.MIN:id']
    for delay in [0,.2,.5,1,1.5,1.8,2,2.5,3,5,10]:
        samples.append(dict(after_gate_rise_ns=delay,values={n:float(np.interp(t0+delay*1e-9,t,d[n])) for n in names}))
    out=dict(scope=__doc__,condition=v['condition'],source_validation_sha256=sha(p),source_raw_sha256=sha(raw),
        gate_high_duration_ns=ton*1e9,input_pair_resistive_charge_c=qp,input_pair_gate_high_charge_c=qp_on,
        input_pair_charge_outside_gate_high_fraction=1-qp_on/qp,
        tail_resistive_charge_c=qt,tail_gate_high_charge_c=qt_on,
        tail_charge_in_gate_high_fraction=qt_on/qt,samples=samples,
        main_dut_modified=False,noise_measured=False,full_pll_acceptance=False,
        observations=['Most input-pair conductive charge occurs after the nominal gate-high interval, although almost all tail conductive charge occurs during it.',
            'At gate rise the tail is charged. Enabling the large tail MOS first raises the tail node before its current discharges it; input-pair conduction develops near gate fall.',
            'This establishes delayed conduction, not the unique capacitance or the time-resolved source of output noise. The terminal-current probe remains necessary.'],
        next_hypothesis='Reduce only tail-MOS gate and junction loading while retaining its nominal W/L, then measure actual settling, rebalanced gain and independent device noise. Short-channel mismatch/noise are not assumed negligible.',
        limitations=['Current integrals use saved BSIM4 resistive drain currents; output terminal charge includes additional displacement currents.',
            'No claim that delayed conduction alone explains the measured CP noise or that shortening the tail channel will improve input-referred jitter.',
            'This fixture uses ideal RF replay and a clamped control output; full PLL acceptance is pending.'])
    fig,axs=plt.subplots(3,1,figsize=(9,7),sharex=True,constrained_layout=True)
    x=(t-t0)*1e9;keep=(x>=-1)&(x<=12)
    for n in ['XCP.gate','XCP.ng','XCP.tail']:
        axs[0].plot(x[keep],d[n][keep],label=n.removeprefix('XCP.'))
    axs[0].set_ylabel('Voltage (V)');axs[0].legend(ncol=3)
    axs[1].plot(x[keep],tail[keep]*1e6,label='Tail resistive current')
    axs[1].plot(x[keep],pair[keep]*1e6,label='Input-pair sum')
    axs[1].set_ylabel('Current (uA)');axs[1].legend()
    for n in ['XCP.MIP','XCP.MIN','XCP.MPO','XCP.MPD']:
        axs[2].plot(x[keep],d[n+':gm'][keep]*1e6,label=n.removeprefix('XCP.'))
    axs[2].set_ylabel('Intrinsic gm (uS)');axs[2].legend(ncol=4);axs[2].set_xlabel('Time after CP gate 50% rising edge (ns)')
    for ax in axs:
        ax.axvspan(0,ton*1e9,color='tab:blue',alpha=.08);ax.grid(alpha=.25)
    fig.suptitle('Measured CP conduction timing: TT 27 C, 1.2 V, 24 MHz reference\nShaded: gate high; waveform diagnostic, not windowed noise')
    figpath=H/'figures/cp_dynamic_timing.png';figpath.parent.mkdir(exist_ok=True)
    fig.savefig(figpath,dpi=160);plt.close(fig)
    out['figure']=figpath.relative_to(H).as_posix();out['figure_sha256']=sha(figpath)
    dst.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k not in ['samples','observations','limitations']},indent=2))

if __name__=='__main__':main()
