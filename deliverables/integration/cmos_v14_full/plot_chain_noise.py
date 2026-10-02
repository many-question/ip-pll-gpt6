"""Plot completed physical-chain noise only; no fullPLL claim."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
H=Path(__file__).resolve().parent
d=json.loads((H/'results/chain_noise_validation.json').read_text())
valid=[r for r in d['cases'] if r.get('single_case_valid')];assert valid
r=next((r for r in valid if r['case']=='chain_noise_fine_tt'),valid[-1]);name=r['case']
z=np.load(H/'results/chain_noise_spectra.npz');f=z[name+'_f'];st=z[name+'_st']
fig,ax=plt.subplots(1,2,figsize=(12,4.5),layout='constrained')
ax[0].loglog(f,st*1e30,label='Total',lw=2)
labels={'XR':'Retimer + output','XRX':'RF receiver','XD':'Divider bank','XACQ1':'Selected counter clock TG'}
for key,label in labels.items():ax[0].loglog(f,z[name+'_'+key+'_st']*1e30,label=label,alpha=.8)
ax[0].set(xlabel='Offset frequency (Hz)',ylabel='Timing noise PSD (fs^2/Hz)');ax[0].legend(fontsize=8);ax[0].grid(which='both',alpha=.2)
v=np.r_[0,np.cumsum((st[1:]+st[:-1])*.5*np.diff(f))];ax[1].semilogx(f,np.sqrt(v)*1e15,lw=2)
ax[1].annotate(f"{r['jitter_fs']:.2f} fs",(f[-1],r['jitter_fs']),xytext=(-65,-20),textcoords='offset points')
ax[1].set(xlabel='Integration upper limit (Hz)',ylabel='Integrated RMS timing noise (fs)',ylim=(0,r['jitter_fs']*1.1));ax[1].grid(which='both',alpha=.2)
fig.suptitle('V14 physical output chain: 984 MHz, TT27, 1.2 V, 10 fF\nIdeal RF replay, first output rising edge; excludes VCO/main-loop/reference noise',fontsize=11)
out=H/'results/figures';out.mkdir(exist_ok=True);fig.savefig(out/'chain_noise_spectrum.png',dpi=160);plt.close(fig)
rows=r['top_devices'][:10];fig,ax=plt.subplots(figsize=(9,5),layout='constrained')
ax.barh([x['device'] for x in rows][::-1],[x['variance_fraction']*100 for x in rows][::-1])
ax.set(xlabel='Fraction of total timing-noise variance (%)',title='Largest individual device contributions, first output rising edge');ax.grid(axis='x',alpha=.2)
fig.savefig(out/'chain_noise_devices.png',dpi=160);plt.close(fig)
print('Plotted',r['run'],r['case'],'precision',d['precision'])
