"""Render the measured TT DAC-off comparisons; no noise inference."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
rows=[]
for run,case,label in [('dacdischarge01','dac_discharge_tt','Rail clamp only'),('dacdischargeall01','dac_discharge_all_tt','Rail + six internal clamps')]:
    j=ROOT/'research/runs/spectre_cmos_v14_full'/run/case
    r=json.loads((j/'result.json').read_text());assert r['ok'] and r['remote_inputs_match']
    with np.load(j/'waveforms.npz') as z:d={k:z[k] for k in ['time','XO.vd','XN.vd','XO.b0','XN.b0','ctrl_o','ctrl_n']}
    rows.append((label,d))
fig,ax=plt.subplots(3,1,figsize=(8,8),layout='constrained')
for ni,(label,d) in enumerate(rows):
    t=d['time'];m=(t>=1.001e-6)&(t<=3.99e-6);ix=np.flatnonzero(m)[::100]
    if ni==0:
        ax[0].plot((t[ix]-1e-6)*1e6,d['XO.vd'][ix],label='Original',color='0.35')
        ax[1].plot((t[ix]-1e-6)*1e6,d['XO.b0'][ix],label='Original',color='0.35')
    ax[0].plot((t[ix]-1e-6)*1e6,d['XN.vd'][ix],label=label)
    ax[1].plot((t[ix]-1e-6)*1e6,d['XN.b0'][ix],label=label)
    before=(t>=.9e-6)&(t<=.99e-6)
    delta=(d['ctrl_n']-np.mean(d['ctrl_n'][before]))-(d['ctrl_o']-np.mean(d['ctrl_o'][before]))
    m=(t>=1e-6)&(t<=1.025e-6)
    ax[2].plot((t[m]-1e-6)*1e9,delta[m]*1e6,label=label)
for a in ax:a.grid(alpha=.2);a.legend(fontsize=8)
ax[0].set(ylabel='Off rail vd (V)',xlabel='Time after acquired rises (us)',title='Physical DAC38 + precharge filter, TT 27 C, 1.2 V')
ax[1].set(ylabel='Internal b0 (V)',xlabel='Time after acquired rises (us)')
ax[2].set(ylabel='Additional held-control change (uV)',xlabel='Time after acquired rises (ns)')
fig.suptitle('DAC shutdown: remove floating states with physical MOS clamps',fontsize=12)
dest=H/'figures/dac_discharge_tt.png';dest.parent.mkdir(exist_ok=True);fig.savefig(dest,dpi=150);print(dest)
