"""Compare saved voltage/current trajectories and their deterministic high bands.

This is a numerical diagnostic, not a device-noise spectrum or random jitter.
Interpolation cannot prove the origin of rapid current variation.
"""
from pathlib import Path
import hashlib,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
p=ROOT/'research/runs/spectre_cmos_v14_full/coretriplate01/core_pulsetrip_late_noise_tt/tstab_last_two_periods.npz'
audit=json.loads((H/'results/core_late_trial_audit.json').read_text())
with np.load(p) as z:d={k:z[k] for k in z.files}
assert str(d['source_sha256'])==audit['raw_tstab']['sha256']
t=d['time'];start=4e-6;period=250e-9;grid=start+np.arange(1000000)*.25e-12
rows=[]
for k in ['XP.vp','out','VDD:p','XP.VVCO:p','XP.VRX:p','XP.VRT:p']:
    y=np.interp(grid,t,d[k]);y-=np.mean(y)
    f=np.fft.rfftfreq(len(y),.25e-12);a=np.abs(np.fft.rfft(y*np.hanning(len(y))))**2
    # Discrete Fourier sums concern a deterministic trace and include aliasing.
    rows.append(dict(node=k,highband_fraction_100_to_500GHz=float(sum(a[(f>=100e9)&(f<=500e9)])/sum(a)),
        highband_fraction_250_to_500GHz=float(sum(a[(f>=250e9)&(f<=500e9)])/sum(a))))
fig,axes=plt.subplots(4,1,figsize=(10,8),sharex=True)
window=(t>=start+1e-9)&(t<=start+2e-9);tt=t[window]
for ax,k in zip(axes,['XP.vp','VDD:p','XP.VVCO:p','XP.VRX:p']):
    scale=1 if k=='XP.vp' else 1e3
    ax.plot((tt-start)*1e9,d[k][window]*scale,lw=.9,label='4 us period')
    ax.plot((tt-start)*1e9,np.interp(tt-period,t,d[k])*scale,lw=.8,alpha=.8,label='previous period, shifted')
    ax.set_ylabel(k+(' (V)' if scale==1 else ' (mA)'));ax.grid(alpha=.2)
axes[0].legend(loc='upper right',ncol=2);axes[-1].set_xlabel('Time relative to 4 us (ns)')
fig.suptitle('Actual LC warm trajectory: voltage and supply currents\nNoiseless transient; not a device-noise spectrum')
fig.tight_layout();dest=H/'results/figures/core_current_waveform.png';fig.savefig(dest,dpi=170);plt.close(fig)
out=dict(scope=__doc__,raw_source_sha256=audit['raw_tstab']['sha256'],cache_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
    window_s=[start,start+period],spectral_window='Hann, to suppress nonzero endpoint mismatch leakage',uniform_interpolation_step_ps=.25,rows=rows,figure=dest.relative_to(ROOT).as_posix(),
    interpretation='Ratios only describe a saved deterministic waveform. Significant current high-band content can motivate a timestep/integration-method control; it does not prove numerical ringing or physical device noise.',
    full_pll_acceptance=False,random_jitter_measured=False)
(H/'results/core_current_waveform.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(rows,indent=2))
