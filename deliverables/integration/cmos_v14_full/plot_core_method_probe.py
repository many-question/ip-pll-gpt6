"""Plot deterministic method/mesh evidence, explicitly separate from device noise."""
from pathlib import Path
import hashlib,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
d=json.loads((H/'results/core_method_probe_validation.json').read_text());assert d['complete']
grid=5e-9+np.arange(120000)*.125e-12;freq=np.fft.rfftfreq(len(grid),.125e-12)/1e9
fig,axes=plt.subplots(1,2,figsize=(12,4.5),layout='constrained')
colors=['#bb4c35','#e39035','#215f9c','#42a094']
labels=['Trap / 1 ps','Trap / 0.5 ps','Gear2 / 1 ps','Gear2 / 0.5 ps']
keys=['VDD:p','XP.VRX:p','XP.VRT:p']
for i,(r,label,color) in enumerate(zip(d['cases'],labels,colors)):
    result=ROOT/r['source_result'];assert hashlib.sha256(result.read_bytes()).hexdigest()==r['source_sha256']
    with np.load(result.parent/'waveforms.npz') as z:y=np.interp(grid,z['time'],z['XP.VRX:p'])
    a=abs(np.fft.rfft((y-y.mean())*np.hanning(len(y))))**2;a/=a.sum()*(freq[1]-freq[0])
    take=(freq>=80)&(freq<=1500)
    axes[0].semilogy(freq[take],a[take],label=label,color=color,lw=.8,alpha=.85)
    values=[r['metrics'][k]['finegrid_fraction_100_1500GHz'] for k in keys]
    axes[1].bar(np.arange(3)+(i-1.5)*.19,values,width=.18,color=color,label=label)
axes[0].set(xlabel='Frequency (GHz)',ylabel='Normalized deterministic spectral energy / GHz',title='RX supply current: peak moves with trap step',ylim=(1e-13,1e-2))
axes[0].axvline(500,color='0.6',ls=':',lw=.7);axes[0].axvline(1000,color='0.6',ls=':',lw=.7)
axes[0].legend(fontsize=8,loc='upper right');axes[0].grid(alpha=.2)
axes[1].set(yscale='log',xticks=range(3),xticklabels=['Total supply','RX supply','Retimer supply'],ylabel='Fraction of deterministic spectral energy',title='100-1500 GHz energy, including shifted peaks',ylim=(1e-7,.1))
axes[1].grid(axis='y',alpha=.2)
fig.suptitle('Numerical ringing diagnostic - no random noise sources or jitter measurement',fontsize=12)
path=H/'results/figures/core_method_probe.png';path.parent.mkdir(exist_ok=True);fig.savefig(path,dpi=170);plt.close(fig)
print(path)
