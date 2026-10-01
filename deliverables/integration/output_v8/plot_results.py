"""Plot accepted periodic waveforms and explicit-band sampled noise."""
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from analyze import H,R,parse
def main():
 dest=H/'figures';dest.mkdir(exist_ok=True)
 n=json.loads((H/'results/noise_validation.json').read_text())
 cases=[r for r in n['cases'] if r.get('valid_noise')]
 if not cases:return
 r=next((r for r in cases if r['case']=='noise_gain4small_halfps'),cases[0]);d=parse(R/r['run']/r['case']/(r['case']+'.raw')/'pss.td.pss');t=d['time']*1e9
 fig,ax=plt.subplots(2,1,figsize=(9,5.4),sharex=True,constrained_layout=True)
 for k in ['vp','vn']:ax[0].plot(t,d[k],label=k)
 ax[0].set(ylabel='Voltage (V)',title='Ideal noiseless RF replay; actual transistor output chain')
 for k in ['clk','data','out']:ax[1].plot(t,d[k],label=k)
 ax[1].set(xlabel='One 984 MHz PSS period (ns)',ylabel='Voltage (V)')
 for a in ax:a.grid(alpha=.2);a.legend(loc='upper right')
 fig.suptitle('TT27, 1.2 V, mirror + 4-stage receiver, C2MOS scale 2, 10 fF')
 fig.savefig(dest/'periodic_output.png',dpi=170);plt.close(fig)
 z=np.load(H/'results/noise_spectra.npz');fig,ax=plt.subplots(figsize=(8.5,4.6),constrained_layout=True)
 for r in cases:ax.loglog(z[r['case']+'_f'],np.sqrt(z[r['case']+'_st'])*1e15,label=r['case'].replace('noise_','')+f" : {r['numeric_jitter_fs']/1000:.4f} ps")
 ax.set(xlabel='Offset frequency (Hz)',ylabel='Edge-time ASD (fs / sqrt(Hz))',title='Output additive device noise, explicit 10 kHz - 492 MHz integral')
 ax.grid(alpha=.2,which='both');ax.legend();fig.savefig(dest/'sampled_noise.png',dpi=170);plt.close(fig)
if __name__=='__main__':main()
