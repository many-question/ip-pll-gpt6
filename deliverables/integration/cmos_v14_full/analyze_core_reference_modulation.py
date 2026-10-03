"""Localize deterministic24MHz modulation along an actualLC core trajectory.

Fundamental-band analytic phase is a deterministic waveform diagnostic, not
sampled device-noise jitter. Agreement upstream/downstream supports localization
but does not establish a unique physical coupling mechanism.
"""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from noise_utils import cross
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
p=ROOT/'research/runs/spectre_cmos_v14_full/coretripsupply01/core_pulsetrip_supply_noise_tt/tstab_last_two_periods.npz'
with np.load(p) as z:d={k:z[k] for k in z.files}
T=250e-9;start=d['time'][-1]-T;n=2**19;u=np.arange(n)*T/n
freq=np.fft.fftfreq(n,T/n);rows=[];timing={}
def demod(y,fc):
    spectrum=np.fft.fft(y)
    keep=(freq>.5*fc)&(freq<1.5*fc)
    analytic=np.fft.ifft(2*spectrum*keep)*np.exp(-2j*np.pi*fc*u)
    phase=np.unwrap(np.angle(analytic));phase-=np.mean(phase)
    amp=abs(analytic);relative_amp=amp/np.mean(amp)-1
    pm=2*np.fft.rfft(phase)/n;am=2*np.fft.rfft(relative_amp)/n
    return phase,amp,pm,am
for node,fc in [('rf_differential',3936e6),('XP.clk',3936e6),('out',984e6)]:
    source=d['XP.vp']-d['XP.vn'] if node=='rf_differential' else d[node]
    y=np.interp(start+u,d['time'],source)
    phase,amp,pm,am=demod(y,fc);coefficient=pm[6]
    timing[node]=phase/(2*np.pi*fc)*1e12
    rows.append(dict(node=node,carrier_hz=fc,mean_fundamental_amplitude_v=float(np.mean(amp)),
        pm24_peak_rad=float(abs(coefficient)),pm24_angle_rad=float(np.angle(coefficient)),
        am24_peak_fraction=float(abs(am[6])),equivalent_deterministic_time24_peak_ps=float(abs(coefficient)/(2*np.pi*fc)*1e12),
        fundamental_phase_equivalent_time_pp_ps=float(np.ptp(timing[node]))))
ctrl=np.interp(start+u,d['time'],d['XP.ctrl']);ref=np.interp(start+u,d['time'],d['XP.refb'])
e=cross(d['time'],d['XP.vp']-d['XP.vn'],0)
mid=(e[1:]+e[:-1])/2;periods=np.diff(e)
reference_edges=np.sort(np.r_[cross(d['time'],d['XP.refb']),cross(d['time'],1.2-d['XP.refb'])])
distance=np.min(abs(mid[:,None]-reference_edges[None,:]),axis=1)
level=np.interp(mid,d['time'],d['XP.refb'])
halves={}
for name,mask in [('reference_high_holding',level>.9),('reference_low_tracking',level<.3)]:
    good=mask&(distance>2e-9)&(mid>=start)&(mid<start+T)
    halves[name]=dict(cycles=int(sum(good)),mean_rf_hz=float(1/np.mean(periods[good])))
split=halves['reference_high_holding']['mean_rf_hz']-halves['reference_low_tracking']['mean_rf_hz']
sample=(u<1/24e6);fig,axs=plt.subplots(3,1,figsize=(9,7),sharex=True)
for k,y in timing.items():axs[0].plot(u[sample]*1e9,y[sample],label=k,lw=1)
axs[0].set_ylabel('Deterministic phase / (2pi f) [ps]');axs[0].legend();axs[0].grid(alpha=.25)
axs[1].plot(u[sample]*1e9,ctrl[sample]);axs[1].set_ylabel('Control [V]');axs[1].grid(alpha=.25)
axs[2].plot(u[sample]*1e9,ref[sample]);axs[2].set_ylabel('Buffered reference [V]');axs[2].set_xlabel('Time within first24MHz cycle [ns]');axs[2].grid(alpha=.25)
fig.suptitle('ActualLC diagnostic core: deterministic modulation, NOT random jitter')
fig.tight_layout();fig.savefig(H/'results/figures/core_reference_modulation.png',dpi=150);plt.close(fig)
out=dict(scope=__doc__,raw_source_sha256=str(d['source_sha256']),interval_us=[start*1e6,(start+T)*1e6],cases=rows,
    rf_to_output_time24_ratio=rows[-1]['equivalent_deterministic_time24_peak_ps']/rows[0]['equivalent_deterministic_time24_peak_ps'],
    equivalent_phase_waveform_correlation=float(np.corrcoef(timing['rf_differential'],timing['out'])[0,1]),
    control_peak_to_peak_v=float(np.ptp(ctrl)),control24_peak_v=float(abs(2*np.fft.rfft(ctrl)[6]/n)),
    rf_frequency_away_from_reference_edges=halves,holding_minus_tracking_rf_hz=float(split),
    square_frequency_modulation_approximation_dbc=float(20*np.log10(abs(split)/(np.pi*24e6*4))),
    square_fm_design_estimate=dict(target_single_sideband_dbc=-60.,reference_hz=24e6,divider=4,
        maximum_rf_hold_track_split_hz=float(np.pi*24e6*4*10**(-60/20)),
        required_split_reduction_factor=float(abs(split)/(np.pi*24e6*4*10**(-60/20))),
        note='First-order symmetric square-FM estimate for this one mechanism only. No margin for charge injection, AM, other lines or PVT; not an accepted circuit result.'),
    hypothesis='Large reference-rate PM already present at differentialLC nodes. Sampler switched loading is a candidate; control ripple, input coupling, and detector loading are not yet causally separated.',
    limitations=['Analytic phase retains the carrier fundamental band and excludes waveform harmonics; it is not threshold-crossing random jitter.',
        'The physical transient has small drift and no convergedPSS; no completePLL acceptance claim.',
        'Ideal external supply excludes shared supply impedance; static control boundary excludes fullslowlogic.'],
    random_jitter_measured=False,full_pll_acceptance=False)
(H/'results/core_reference_modulation.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
