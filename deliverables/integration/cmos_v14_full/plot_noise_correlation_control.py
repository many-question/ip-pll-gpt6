"""Show simulated colored-noise controls against analytic sampling alternatives."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
H=Path(__file__).resolve().parent
p=json.loads((H/'results/noise_correlation_control_protocol.json').read_text());v=json.loads((H/'results/noise_correlation_control_validation.json').read_text())
assert v['complete'] and v['passed']
f=np.geomspace(1e6,492e6,1200);fs=p['sample_frequency_hz'];tau=p['resistance_ohm']*p['capacitance_f']
variance=1.380649e-23*p['temperature_k']/p['capacitance_f'];amp=.5/np.sqrt(1+(2*np.pi*fs*tau)**2);slope=2*np.pi*fs*amp
def curve(rate,normalization=1):
    rho=np.exp(-1/(rate*tau))
    return 2*variance/rate*(1-rho*rho)/(1-2*rho*np.cos(2*np.pi*f/rate)+rho*rho)/slope**2/normalization*1e30
fig,ax=plt.subplots(2,1,figsize=(9,7),gridspec_kw={'height_ratios':[2,1]},constrained_layout=True)
ax[0].loglog(f/1e6,curve(fs),color='#283a52',label='Analytic: sample every 984 MHz edge')
ax[0].loglog(f/1e6,curve(fs/6,6),color='#9d6c45',ls='--',label='Alternative: one event / PSS, normalized by 6')
colors=['#367ac2','#2a9d75']
for row,color,marker in zip(v['cases'],colors,['o','x']):
    x=np.asarray(v['offsets_hz'])/1e6;label=f"Spectre: sampleratio {int(row['sample_ratio'])}"
    ax[0].loglog(x,np.asarray(row['timing_psd_s2_per_hz'])*1e30,marker,ms=7,mfc='none',color=color,label=label)
    ax[1].semilogx(x,row['full_rate_error_db'],marker+'-',color=color,label=label)
long_path=H/'results/noise_correlation_long_validation.json'
if long_path.exists():
    z=json.loads(long_path.read_text());assert z['complete']
    x=np.asarray(z['offsets_hz'])/1e6
    label='Spectre: sampleratio 246 (1 ps / default maxacfreq)'
    ax[0].loglog(x,np.asarray(z['timing_psd_s2_per_hz'])*1e30,'^',ms=8,mfc='none',color='#ad4763',label=label)
    ax[1].semilogx(x,z['analytic_error_db'],'^-',color='#ad4763',label=label)
ax[0].set_ylabel('Timing PSD (fs²/Hz)');ax[0].set_title('Colored RC calibration: 1 kΩ / 2 pF, 984 MHz sine, 27 °C')
ax[0].legend(fontsize=8,loc='lower left');ax[1].set_ylabel('Error vs analytic (dB)');ax[1].set_xlabel('Offset frequency (MHz)');ax[1].axhline(0,color='gray',lw=.7)
for a in ax:a.grid(True,which='both',alpha=.18)
fig.suptitle('Linear diagnostic; ratios 1 and 6: 0.25 ps / 1 THz — no PLL jitter claim',fontsize=10)
dest=H/'results/figures/noise_correlation_control.png';fig.savefig(dest,dpi=170);plt.close(fig);print(dest)
