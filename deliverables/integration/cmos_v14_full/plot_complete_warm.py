"""Plot the documented native join and the actual fully sampled output window."""
from pathlib import Path
import json,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
d=np.load(R/'completewarm_joined/waveforms.npz');b=np.load(R/'completedense01/complete_warm_tt/waveforms.npz')
res=json.loads((H/'results/complete_warm_joined.json').read_text());out=H/'results/figures';out.mkdir(exist_ok=True)
t=d['time']; ix=np.flatnonzero(abs(np.diff(d['obsphase']))>1e-9)+1;ix=ix[d['obscycles'][ix]>0]
fig,ax=plt.subplots(4,1,figsize=(10,9),sharex=True,layout='constrained')
ax[0].plot(t[ix]*1e6,d['obsdivcycles'][ix]*24);ax[0].axhline(984,ls=':',color='k');ax[0].set_ylabel('Output (MHz)')
ax[1].plot(t[ix]*1e6,np.unwrap(d['obsphase'][ix]));ax[1].set_ylabel('RF phase (rad)')
ax[2].plot(t[ix]*1e6,d['obsctrl'][ix]);ax[2].set_ylabel('Held control (V)')
w=res['power_windows'];ax[3].step([(x['start_us']+x['stop_us'])/2 for x in w],[x['power_mw'] for x in w],where='mid',label='250 ns supply-energy average')
ax[3].axhline(4,color='r',ls='--',label='4 mW target');ax[3].set_ylabel('Full PLL (mW)');ax[3].set_xlabel('Time (us)');ax[3].legend()
for a in ax:a.grid(alpha=.2);a.axvline(res['join']['boundary_us'],ls=':',color='tab:orange',alpha=.6)
fig.suptitle('Complete programmable physical V14: TT, K41, 1.2 V, 10 fF\nConstructed near-lock start; 4 ps functional run, no random noise',fontsize=12)
fig.savefig(out/'complete_warm_joined.png',dpi=160);plt.close(fig)
fig,ax=plt.subplots(2,1,figsize=(10,5),layout='constrained')
t=b['time'];sel=t>t[-1]-3e-9;x=(t[sel]-t[-1])*1e9
ax[0].plot(x,b['out'][sel],label='Output');ax[0].plot(x,b['XP.data'][sel],label='Before retimer',alpha=.65)
ax[1].plot(x,b['XP.vp'][sel],label='VCO+');ax[1].plot(x,b['XP.vn'][sel],label='VCO-')
for a in ax:a.grid(alpha=.2);a.legend();a.set_ylabel('Voltage (V)')
ax[1].set_xlabel('Time relative to 8 us (ns)');fig.suptitle('Every accepted timestep retained; output duty ~43.97%')
fig.savefig(out/'complete_warm_dense_waveforms.png',dpi=160);plt.close(fig)
print('Saved complete warm baseline figures')
