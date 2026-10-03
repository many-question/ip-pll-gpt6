"""Plot measured offsets and device-noise fractions without inferring an RMS integral."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
H=Path(__file__).resolve().parent
d=json.loads((H/'results/vco_bias_noise_validation.json').read_text())
fig,ax=plt.subplots(1,2,figsize=(10.5,4.2),layout='constrained')
rows=[d['baseline'],d['candidate']];labels=['CF 10 pF','CF 40 pF']
colors=['#64748b','#2563eb']
for row,label,color in zip(rows,labels,colors):
    ax[0].semilogx(np.array(row['offsets_hz'])/1e6,row['ssb_pm_dbc_per_hz'],'o-',color=color,label=label)
ax[0].set(xlabel='Offset (MHz)',ylabel='SSB phase noise (dBc/Hz)',title='Six simulated offsets; no jitter integral')
ax[0].grid(which='both',alpha=.2); ax[0].legend()
stack=[]
for row in rows:
    mt=row['selected_device_components']['XV.XL.MT']['fraction_of_output_psd']
    parts=[row['bias_resistor_fraction_1mhz'],mt['fn'][2],mt['id'][2]]
    stack.append(parts+[1-sum(parts)])
stack=np.array(stack);bottom=np.zeros(2)
for col,(label,color) in enumerate(zip(['Filter resistor','Tail flicker','Tail channel thermal','Other devices'],['#b45309','#2563eb','#38bdf8','#cbd5e1'])):
    values=stack[:,col]*100
    ax[1].bar(labels,values,bottom=bottom,color=color,label=label)
    for i,v in enumerate(values):
        if v>5:ax[1].text(i,bottom[i]+v/2,f'{v:.1f}%',ha='center',va='center',fontsize=9)
    bottom+=values
ax[1].set(ylabel='Fraction of output-noise variance (%)',ylim=(0,100),title='Device contributions at 1 MHz offset')
ax[1].legend(loc='upper center',bbox_to_anchor=(.5,-.12),ncol=2,fontsize=8)
fig.suptitle('VCO bias filtering: TT27 /1.2 V /Q5 RLC /fixed M4 load\nStatic reference, actual MOS bias; fresh PSS; not complete PLL noise',fontsize=11)
p=H/'results/figures/vco_bias_noise.png';fig.savefig(p,dpi=165,bbox_inches='tight');plt.close(fig)
print(p)
