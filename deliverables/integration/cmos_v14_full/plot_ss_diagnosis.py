"""Waveform evidence for SS clock degradation and post-reset state loss."""
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
H=Path(__file__).resolve().parent;R=H.parents[3]/'research/runs/spectre_cmos_v14_full'
fig,axs=plt.subplots(3,1,figsize=(10,8),layout='constrained')
cases=[('bankdiag01','bankdiag_m6_ss',20,22,['q1','XD.ck','XD.ckb'],'Baseline /6: clock amplitude collapse'),
       ('bankclk01','bankclk_m6_ss',80,82,['XD.ck','XD.XD6.clkb','XD.XD6.q0'],'Stronger clock /6: full swing alone does not restore division'),
       ('bankdiag01','bankdiag_m10_ss',7.5,14,['XD.load','XD.r0','XD.r1','XD.r2','XD.r3','XD.r4'],'Baseline /10: initialized pattern is lost after release')]
for ax,(run,case,lo,hi,keys,title) in zip(axs,cases):
 with np.load(R/run/case/'waveforms.npz') as z:
  t=z['time']*1e9;s=(t>=lo)&(t<=hi)
  for i,k in enumerate(keys):
   if len(keys)>3:ax.plot(t[s],z[k][s]+i*1.4,label=k,lw=1)
   else:ax.plot(t[s],z[k][s],label=k,lw=1)
 ax.set_title(title);ax.set_xlabel('Time (ns)');ax.set_ylabel('Voltage (V)' if len(keys)<=3 else 'Voltage + trace offset (V)')
 ax.legend(loc='upper right',ncol=3,fontsize=8);ax.grid(alpha=.25)
fig.suptitle('Physical CMOS SS60, 1.2 V, ideal 20 ps RF; independent divider + retimer TB')
out=H/'results/figures/ss_clock_diagnosis.png';out.parent.mkdir(exist_ok=True)
fig.savefig(out,dpi=160);print(out)
