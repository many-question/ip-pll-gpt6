"""Plot current-bias VCO block evidence, not closed-loop PLL phase noise."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
H=Path(__file__).resolve().parent;d=json.loads((H/'results/vco_noise_validation.json').read_text());z=np.load(H/'results/vco_noise_spectra.npz')
r=next(r for r in d['cases'] if r['case']=='vco_noise_coarse_tt' and r.get('single_case_valid'));name=r['case']
fig,ax=plt.subplots(1,2,figsize=(12,4.8),layout='constrained')
ax[0].semilogx(z[name+'_f'],10*np.log10(z[name+'_L']),label='1ps /127 sidebands',lw=2)
fine=next((r for r in d['cases'] if r['case']=='vco_noise_check6_tt' and r.get('single_case_valid')),None)
if fine:
 n=fine['case'];ax[0].semilogx(z[n+'_f'],10*np.log10(z[n+'_L']),'o',ms=4,label='0.5ps /255, six offsets')
if 'tool_estimated_free_running_linewidth_hz' in r:ax[0].axvspan(1e4,r['tool_estimated_free_running_linewidth_hz'],alpha=.12,color='orange',label='Below estimated free-running linewidth')
ax[0].set(xlabel='Offset from RF carrier (Hz)',ylabel='SSB phase noise (dBc/Hz)',xlim=(1e4,492e6));ax[0].grid(which='both',alpha=.2);ax[0].legend(fontsize=8)
groups=r['fractions_at_1mhz'];labels={'tail_and_bias':'Tail + bias','cross_coupled_core':'Cross-coupled core','inductor_RLC':'Inductor RLC','switched_cap_bank':'Switched cap bank'}
items=sorted([(labels[k],v*100) for k,v in groups.items() if k in labels],key=lambda x:x[1])
bars=ax[1].barh([x[0] for x in items],[x[1] for x in items]);ax[1].bar_label(bars,fmt='%.1f%%',padding=4)
ax[1].set(xlabel='Fraction of VCO phase-noise PSD at 1 MHz (%)',xlim=(0,60));ax[1].grid(axis='x',alpha=.2)
fig.suptitle(f"V14 physical-bias VCO: TT27, 1.2 V, Q5 RLC; fixed M4 load, static reference\n{r['frequency_hz']/1e9:.6f} GHz, VCO supply {r['vco_supply_power_mw']:.3f} mW; VCO noise only, no PLL suppression",fontsize=11)
out=H/'results/figures';out.mkdir(exist_ok=True);fig.savefig(out/'vco_phase_noise.png',dpi=160);plt.close(fig);print('Plotted VCO block noise')
