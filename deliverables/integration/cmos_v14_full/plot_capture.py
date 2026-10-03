"""Plot the completed, provenance-checked reset trajectory and its handoff."""
from pathlib import Path
import sys,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
name=sys.argv[1] if len(sys.argv)>1 else 'completecold05'
r=json.loads((H/'results'/('capture_'+name+'.json')).read_text())
assert r['final_simulator_completed'] and r['circuit_hashes_identical']
d=np.load(ROOT/r['joined_waveform']);t=d['time']*1e6
i=np.flatnonzero(np.diff(d['obsphase'])!=0)+1;i=i[d['obscycles'][i]>0]
handoff=r['logic']['XP.XC.acquired']['first_rising_us']
late=i[t[i]>handoff] if handoff is not None else i
fig,ax=plt.subplots(3,2,figsize=(13,10),layout='constrained')
ax[0,0].plot(t[i],d['obscycles'][i]*24/1000)
ax[0,0].axhline(3.936,color='k',ls=':');ax[0,0].set_ylabel('VCO frequency (GHz)')
ax[0,0].set_title('From reset, unchanged physical DUT')
ax[0,1].plot(t[late],d['obscycles'][late]*24-3936)
ax[0,1].axhline(0,color='k',ls=':');ax[0,1].set_ylabel('RF frequency error (MHz)')
ax[0,1].set_title('After FLL handoff')
ax[1,0].plot(t[i],d['obsctrl'][i]);ax[1,0].set_ylabel('Held control (V)')
ax[1,1].plot(t[late],d['obsphase'][late]);ax[1,1].set_ylabel('RF phase at reference (rad mod2pi)')
coarse=np.zeros(len(t),dtype=int);dac=coarse.copy()
for a,prefix,bits in [(coarse,'XP.b',8),(dac,'XP.XC.d',6)]:
 for b in range(bits):a+=((d[prefix+str(b)]>.6).astype(int)<<b)
ax[2,0].step(t,coarse,label='Coarse',where='post')
ax[2,0].step(t,dac,label='DAC',where='post');ax[2,0].set_ylabel('Digital code');ax[2,0].legend()
for key,label in [('XP.XC.acquired','FLL done'),('qualified','Qualified'),('frequency_good','Frequency good')]:
 ax[2,1].plot(t,d[key]/1.2,label=label,lw=.8)
ax[2,1].set_ylabel('Logic state');ax[2,1].legend()
for a in ax.flat:
 a.grid(alpha=.2);a.set_xlabel('Simulation time (us)')
for a in [ax[0,0],ax[1,0],ax[2,0],ax[2,1]]:
 if handoff is not None:a.axvline(handoff,color='grey',ls='--',lw=.8)
fig.suptitle('V14 complete PLL reset acquisition: TT27,1.2V,K41/M4,10fF,Q5 RLC\n'
             'DC supply; no rail ramp. Functional capture screen: '+str(r['functional_capture_screen_passed']),fontsize=13)
out=H/'results/figures';out.mkdir(exist_ok=True)
filename='complete_reset_capture.png' if name=='completecold05' else f'{name}_reset_capture.png'
fig.savefig(out/filename,dpi=160);plt.close(fig)
print('Plotted completed reset trajectory')
