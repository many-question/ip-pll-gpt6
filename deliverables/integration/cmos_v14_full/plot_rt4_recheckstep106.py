"""Actual completed MOS record: counts, tuning control and slow bias."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
r=json.loads((H/'results/rt4_recheckstep_review106.json').read_text())['result']
with np.load(ROOT/Path(r['source_result']).parent/'waveforms.npz') as z:d={k:z[k] for k in z.files if k!='units'}
t=d['time']*1e6
change=np.r_[False,np.diff(d['obscycles'])!=0]
fig,ax=plt.subplots(4,1,figsize=(10,9),sharex=True,layout='constrained')
ax[0].plot(t[change],d['obscycles'][change]*24,lw=.8);ax[0].axhline(3936,color='k',ls='--',lw=.8)
ax[0].set(ylim=(3910,3965),ylabel='RF (MHz)',title='RT4 4.8 fF variable-step FLL: complete 120 us, capture failed')
ax[1].plot(t,d['XP.ctrl'],lw=.5,label='ctrl');ax[1].plot(t,d['XP.preset'],lw=.8,label='preset');ax[1].set(ylabel='Tuning (V)');ax[1].legend(loc='upper right')
ax[2].plot(t,d['XP.XV.XL.nfilt'],lw=.8,label='filtered bias');ax[2].plot(t,d['XP.XV.XL.nb'],lw=.8,label='bias reference');ax[2].set(ylabel='VCO bias (V)');ax[2].legend(loc='upper right')
for sig in ['qualified','frequency_good','range_error','XP.en']:
    ax[3].plot(t,d[sig]>.6,lw=.8,label=sig)
ax[3].set(ylabel='Logic',xlabel='Time (us)');ax[3].legend(loc='upper left',ncol=4)
for a in ax:a.grid(alpha=.2);a.set_xlim(16,120)
fig.set_layout_engine('constrained',rect=(0,.04,1,1))
fig.text(.5,.012,'AX 8 ps / reltol 1e-3, TT, noise off. Frequency deviations are not jitter. Bias motion alone does not prove causality.',ha='center',fontsize=9)
out=H/'results/figures/rt4_recheckstep106.png';fig.savefig(out,dpi=140)
print(str(out))
