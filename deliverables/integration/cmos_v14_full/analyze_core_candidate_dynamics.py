"""Compare actualLC candidate frequency and phase histories; not noise spectra."""
from pathlib import Path
import hashlib,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
validation=json.loads((H/'results/core_noise_candidates_validation.json').read_text())
fig,axs=plt.subplots(3,1,figsize=(9,8),sharex=True);rows=[]
for case in validation['cases']:
    if 'stationarity' not in case:continue
    rp=ROOT/case['source'];r=json.loads(rp.read_text());p=rp.parent/'waveforms.npz'
    assert hashlib.sha256(p.read_bytes()).hexdigest()==r['local_outputs_sha256']['waveforms.npz']
    with np.load(p) as z:d={k:z[k] for k in z.files}
    t=d['time'];ix=np.flatnonzero((abs(np.diff(d['obsphase']))>1e-9)|(abs(np.diff(d['obscycles']))>1e-9)|(abs(np.diff(d['obsctrl']))>1e-9))+1
    ix=ix[t[ix]>50e-9];tt=t[ix];rf=d['obscycles'][ix]*24e6;fo=d['obsdivcycles'][ix]*24e6
    # RF cycle-count error integrates phase without modulo-phase unwrapping.
    integrated=np.cumsum(d['obscycles'][ix]-164)*2*np.pi
    windows=[]
    for start,end in [(0.05,.25),(.25,.5),(.5,1),(1,2),(2,3)]:
        mask=(tt>start*1e-6)&(tt<=end*1e-6)
        windows.append(dict(window_us=[start,end],observations=int(sum(mask)),
            mean_rf_mhz=float(np.mean(rf[mask])*1e-6),mean_out_mhz=float(np.mean(fo[mask])*1e-6),
            mean_reference_sampled_control_v=float(np.mean(d['obsctrl'][ix][mask]))))
    ratio=fo*4/rf
    rows.append(dict(variant=case['variant'],source=case['source'],source_sha256=case['source_sha256'],
        functional_stationarity_passed=case['passed'],windows=windows,
        max_mean_divider_ratio_error=float(max(abs(ratio-1))),
        integrated_rf_cycle_error_rad=float(integrated[-1]),
        caution='Per-reference interpolated crossing counts, not instantaneousRF or randomnoise. Control is sampled at reference rise, not continuous meanVCTRL.'))
    axs[0].plot(tt*1e6,(rf-3936e6)/1e6,label=case['variant'])
    axs[1].plot(tt*1e6,integrated,label=case['variant'])
    axs[2].plot(tt*1e6,d['obsctrl'][ix],label=case['variant'])
axs[0].set_ylabel('RF frequency error [MHz]');axs[1].set_ylabel('Integrated RF phase error [rad]')
axs[2].set_ylabel('Reference-sampled control [V]');axs[2].set_xlabel('Time [us]')
for ax in axs:ax.grid(alpha=.25);ax.legend()
fig.suptitle('ActualLC loaded candidates: deterministic functional comparison')
fig.tight_layout();fig.savefig(H/'results/figures/core_candidate_dynamics.png',dpi=150);plt.close(fig)
out=dict(scope=__doc__,cases=rows,condition='Same TT27/1.2V/Q5/coarse23/10fF/real sampledloop, 3us/1ps/2ns observerstrobes; same inputstate, independent physical output-size/CF changes.',
    interpretation='A correct output/RF divider ratio with sustained RF frequency error is a failed near-lock operating point, not evidence of missed output edges. Static loading pull, reference coupling and nonlinear capture remain to be isolated.',
    limitations=['Initial state is held common across circuit changes; failure from this seed does not prove no valid locked solution or failure after a new FLL capture.',
        'The original-source local-chain noise numbers exclude feedback of retimer loading on the actual oscillator.',
        'Sparse observer data cannot measure RF amplitude, edge slew, reference spurs or average supply power.'],
    full_pll_acceptance=False,random_jitter_measured=False)
(H/'results/core_candidate_dynamics.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(rows,indent=2))
