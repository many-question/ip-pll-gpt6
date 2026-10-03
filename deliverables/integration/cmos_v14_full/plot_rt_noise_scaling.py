"""Plot completed fresh-PSS sizing evidence with its acceptance limits visible."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

H=Path(__file__).resolve().parent
v=json.loads((H/'results/rt_noise_scaling_validation.json').read_text())
z=np.load(H/'results/rt_noise_scaling_spectra.npz')
base=np.load(H/'results/chain_noise_spectra.npz')
fig,ax=plt.subplots(1,2,figsize=(11,4.3),layout='constrained')
colors=['#2563eb','#b45309']
ax[0].loglog(base['chain_noise_fine_tt_f']/1e6,
    np.sqrt(base['chain_noise_fine_tt_st'])*1e15,color='#64748b',label='Baseline: 141.281 fs')
labels=[];ff=[];out=[];rx=[]
for row,color in zip(v['cases'],colors):
    if not row.get('periodic_passed'):continue
    case=row['case'];factor=row['factor']
    ax[0].loglog(z[case+'_f']/1e6,np.sqrt(z[case+'_st'])*1e15,color=color,
        label=f'{factor}x: {row["provisional_jitter_fs"]:.3f} fs')
    parts=row['provisional_group_jitter_fs'];labels.append(f'{factor}x')
    ff.append(parts['XR.XFF']);out.append(np.hypot(parts['XR.X0'],parts['XR.X1']));rx.append(parts['XRX'])
x=np.arange(len(labels));width=.23
for values,offset,label,color in [(ff,-width,'Retimer FF','#2563eb'),(out,0,'Output pair (RSS)','#b45309'),(rx,width,'RF receiver','#0f766e')]:
    bars=ax[1].bar(x+offset,values,width,label=label,color=color)
    ax[1].bar_label(bars,fmt='%.1f',padding=3,fontsize=9)
ax[0].set(xlabel='Offset frequency (MHz)',ylabel='Timing noise ASD (fs/sqrt(Hz))',title='10 kHz to 492 MHz; first output rising edge')
ax[0].grid(which='both',alpha=.17);ax[0].legend(fontsize=9)
ax[1].set(xticks=x,xticklabels=labels,ylabel='Individual RSS contribution (fs)',title='Device-noise attribution before closure checks')
ax[1].set_ylim(0,max(ff+[90])*1.3);ax[1].legend(fontsize=8);ax[1].grid(axis='y',alpha=.17)
fig.suptitle('Local CMOS output chain: provisional sizing results\nTT27 /1.2 V /984 MHz /10 fF /noiseless external RF replay',fontsize=12)
fig.text(.5,-.045,'Not full-PLL jitter. Further noise-on, harmonic-neighborhood integration, numerical/PVT checks remain.',ha='center',fontsize=9)
dest=H/'results/figures/rt_noise_scaling.png';fig.savefig(dest,dpi=165,bbox_inches='tight');plt.close(fig)
print(dest)
