"""Separate CP off-window terminal charge by elapsed time after gate fall.

This is a deterministic timing diagnostic, not an intrinsic leakage/noise
measurement. Signed charge cancellation is retained rather than rectified.
"""
from pathlib import Path
import hashlib,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from noise_utils import parse,cross
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    proof=H/'results/frontend_pss_snapshot_validation.json';v=json.loads(proof.read_text())
    assert all(v['waveform_checks'].values())
    mp=ROOT/v['source_snapshot'];assert sha(mp)==v['source_snapshot_sha256']
    manifest=json.loads(mp.read_text());path=mp.parent/'pss.td.pss'
    assert sha(path)==manifest['files'][path.name]['sha256']
    d=parse(path);t=d['time'];T=t[-1]-t[0];gate=d['XCP.gate'];pulse=d['pulse']
    falls=cross(t,-gate,-.6);pfalls=cross(t,-pulse,-.6);assert len(falls)==len(pfalls)==1
    fall=falls[0];age=(t-fall)%T;off=gate<=.6
    boundaries=np.array([0,.05,.1,.25,.5,1,2,5,10,20,T*1e9])*1e-9
    currents=['VO:p','XCP.MT:d','XCP.MIP:d','XCP.MIN:d','XCP.MPO:d','XCP.MPD:d']
    avg=lambda a:float(np.trapezoid(a,t)/T)
    rows=[]
    for lo,hi in zip(boundaries[:-1],boundaries[1:]):
        z=((age>=lo)&(age<hi)&off).astype(float);fraction=avg(z)
        if fraction==0:continue
        rows.append(dict(elapsed_after_gate_fall_ns=[float(lo*1e9),float(hi*1e9)],fraction=fraction,
                         mean_terminal_current_a={n:avg(d[n]*z)/fraction for n in currents},
                         signed_terminal_charge_c={n:avg(d[n]*z)*T for n in currents},
                         mean_nodes_v={n:avg(d[n]*z)/fraction for n in ['XCP.ng','XCP.tail','hp','hn','XCP.mir']}))
    whole={n:avg(d[n]*off.astype(float))*T for n in currents}
    charge_error=max(abs(sum(r['signed_terminal_charge_c'][n] for r in rows)-whole[n]) for n in currents)
    assert charge_error<1e-24
    late=((age>=1e-9)&off).astype(float);fraction=avg(late)
    out=dict(scope=__doc__,source_validation_sha256=sha(proof),raw_sha256=sha(path),condition=v['condition'],
             gate_fall_s=float(fall),pulse_fall_s=float(pfalls[0]),gate_minus_pulse_fall_ps=float((fall-pfalls[0])*1e12),
             bins=rows,off_window_charge_c=whole,partition_absolute_charge_error_c=charge_error,
             after1ns_off_fraction=fraction,after1ns_mean_terminal_current_a={n:avg(d[n]*late)/fraction for n in currents},
             after1ns_signed_terminal_charge_c={n:avg(d[n]*late)*T for n in currents},
             noise_measured=False,full_pll_acceptance=False,
             limitations=['Terminal currents include displacement and any delayed gate response, not only channel conduction.',
                          'Off-window bins are relative to 0.6V gate crossing; changing threshold changes the partition.',
                          'No noise contribution is inferred from the deterministic current magnitude.'])
    (H/'results/frontend_off_windows_validation.json').write_text(json.dumps(out,indent=2)+'\n')
    x=(t-fall)*1e9;keep=(x>=-.5)&(x<=6)
    fig,axs=plt.subplots(3,1,figsize=(10,8),sharex=True,layout='constrained')
    for name,label in [('pulse','nominal pulse'),('XCP.gate','actual gate'),('XCP.ng','tail gate'),('XCP.tail','tail node')]:
        axs[0].plot(x[keep],d[name][keep],label=label,lw=1)
    axs[0].set_ylabel('Voltage (V)');axs[0].legend(ncol=4,fontsize=8)
    for name,label in [('XCP.MT:d','tail drain'),('XCP.MIP:d','input P drain'),('XCP.MIN:d','input N drain')]:
        axs[1].plot(x[keep],d[name][keep]*1e6,label=label,lw=1)
    axs[1].set_yscale('symlog',linthresh=.01);axs[1].set_ylabel('Terminal current (uA)');axs[1].legend(fontsize=8)
    axs[2].plot(x[keep],d['VO:p'][keep]*1e6,label='clamp current',lw=1)
    axs[2].set_yscale('symlog',linthresh=.01);axs[2].set_ylabel('Terminal current (uA)')
    axs[2].set_xlabel('Time relative to actual gate falling through 0.6 V (ns)')
    for ax in axs:
        ax.grid(alpha=.25);ax.axvline(0,color='black',lw=.6,ls='--')
    fig.suptitle('CP turn-off dynamics at measured balanced frontend\nTT27 / 1.2 V / ideal RF replay and output clamp; terminal currents include displacement',fontsize=11)
    fig.savefig(H/'figures/frontend_cp_turnoff.png',dpi=160);plt.close(fig)
    print(json.dumps({k:v for k,v in out.items() if k!='bins'},indent=2))

if __name__=='__main__':main()
