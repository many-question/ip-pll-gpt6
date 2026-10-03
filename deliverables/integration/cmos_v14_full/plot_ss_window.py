"""Show the controlled clock-slew experiment, not a repaired PLL waveform."""
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
H=Path(__file__).resolve().parent;R=H.parents[3]/'research/runs/spectre_cmos_v14_full'
cases=[('bankwindow01','bankwindow_m10_e20_d50_ss',20,'PASS, 312 MHz'),('bankwindow01','bankwindow_m10_e80_d50_ss',80,'FAIL, pattern lost'),('banktail01','banktail_m10_e80_ss',80,'Tail isolated: PASS, 312 MHz')]
fig,axes=plt.subplots(2,3,figsize=(14,5),sharex='col',sharey=True,layout='constrained')
for col,(run,case,edge,title) in enumerate(cases):
 with np.load(R/run/case/'waveforms.npz') as z:d={k:z[k] for k in z.files}
 t=d['time']*1e9;sel=(t>=20)&(t<=24)
 axes[0,col].plot(t[sel],d['ck'][sel],color='#127C87',label='Internal diagnostic CK')
 axes[1,col].plot(t[sel],d['XD.r0'][sel],label='Ring r0',color='#9D5B99')
 axes[1,col].plot(t[sel],d['data'][sel],label='Retimed output',color='#C56836')
 axes[0,col].set_title(f'CK 10–90% = {edge*.8:g} ps\n'+title)
 axes[1,col].set_xlabel('Time (ns)')
 for ax in axes[:,col]:ax.set_ylim(-.12,1.36);ax.grid(alpha=.2);ax.legend(fontsize=8,loc='upper right')
for ax in axes[:,0]:ax.set_ylabel('Voltage (V)')
fig.suptitle('SS60 / 1.2 V / M10 / 3.120 GHz RF / 10 fF — clock slew and unused tail data loading',fontsize=11)
(H/'results/figures').mkdir(exist_ok=True)
fig.savefig(H/'results/figures/ss_clock_window.png',dpi=160)
