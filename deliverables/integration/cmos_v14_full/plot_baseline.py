"""Plots only completed local data. Transient phase variation is not RMS jitter."""
from pathlib import Path
import sys,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
run,case=sys.argv[1:3];job=ROOT/'research/runs/spectre_cmos_v14_full'/run/case
rec=json.loads((job/'result.json').read_text());assert rec['remote_inputs_match']
d=np.load(job/'waveforms.npz');t=d['time'];ix=np.flatnonzero(np.diff(d['obsphase'])!=0)+1
ix=ix[d['obscycles'][ix]>0]  # first reference event has no complete cycle-count interval
fig,axes=plt.subplots(4,1,figsize=(10,10),sharex=True,layout='constrained')
x=t[ix]*1e6
axes[0].plot(x,d['obscycles'][ix]*24/1000,label='RF');axes[0].axhline(3.936,color='k',ls=':',label='Target3.936GHz')
axes[0].set_ylabel('VCO frequency (GHz)');axes[0].legend(loc='best');axes[0].grid(alpha=.2)
axes[1].plot(x,np.unwrap(d['obsphase'][ix]),label='RF phase at reference')
axes[1].set_ylabel('Unwrapped phase (rad)');axes[1].grid(alpha=.2)
axes[2].plot(x,d['obsctrl'][ix],label='Held control voltage')
axes[2].set_ylabel('Control voltage (V)');axes[2].grid(alpha=.2)
axes[3].plot(t*1e6,d['qualified']/1.2,label='qualified',lw=1)
axes[3].plot(t*1e6,d['XP.XC.acquired']/1.2,label='FLL done',lw=1,ls='--')
axes[3].set_ylabel('Logic state');axes[3].set_xlabel('Simulation time (us)');axes[3].legend(loc='best');axes[3].grid(alpha=.2)
fig.suptitle(case+'\nPhysical circuit transient; qualification is not stationarity or jitter acceptance',fontsize=12)
out=H/'results/figures';out.mkdir(exist_ok=True)
fig.savefig(out/(run+'_'+case+'.png'),dpi=160);plt.close(fig)
if 'energy_nj' in d:
 e=d['energy_nj'];step=max(1,int(round(.1e-6/np.median(np.diff(t)))));i=np.arange(0,len(t)-step,step)
 power=(e[i+step]-e[i])/((t[i+step]-t[i])*1e6)
 fig,ax=plt.subplots(figsize=(10,3),layout='constrained');ax.plot((t[i+step]+t[i])*.5e6,power)
 ax.axhline(4,color='r',ls='--',label='4mW full-PLL limit');ax.set(xlabel='Simulation time (us)',ylabel='Supply power (mW)',title='100ns averages from internal-timestep integrated supply energy')
 ax.legend();ax.grid(alpha=.2);fig.savefig(out/(run+'_'+case+'_power.png'),dpi=160);plt.close(fig)
print('Plotted',run,case)
