"""Show same-interface original/candidate prescaler level failure; no noise claim."""
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
fig,axes=plt.subplots(4,2,figsize=(11,8),sharex=True,sharey=True,constrained_layout=True)
for col,(name,title) in enumerate([('base','Original bank: output works'),('boost','Boosted prescaler: output stops')]):
 p=ROOT/'research/runs/spectre_cmos_v14_full/bankckbuf01'/f'bankck{name}_m4_ss'/'waveforms.npz'
 with np.load(p) as d:
  t=d['time'];mask=t>=198e-9
  for row,key in enumerate(['clk','XD.q0','q1','XD.d4']):
   ax=axes[row,col];ax.plot((t[mask]-198e-9)*1e9,d[key][mask],lw=1.3)
   ax.axhline(1,color='#d97706',lw=.8,ls='--');ax.axhline(.2,color='#d97706',lw=.8,ls='--')
   ax.set_ylim(-.15,1.35);ax.grid(alpha=.2);ax.set_ylabel(key+' (V)')
   if row==0:ax.set_title(title)
   if row==3:ax.set_xlabel('Time from 198 ns (ns)')
fig.suptitle('SS 60 C, 1.2 V, measured SS tank replay + MOS receiver, RF 3.936 GHz\n200 ns settled comparison; dashed levels are functional screening thresholds')
fig.savefig(H/'results/figures/ss_prescaler_level.png',dpi=160);plt.close(fig)
