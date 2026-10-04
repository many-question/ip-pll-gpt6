"""Plot completed edge checks and isolated VCO high-offset variance, with scope labels."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
H=Path(__file__).resolve().parent
edge=json.loads((H/'results/rt4_pulsetrip_audit_validation.json').read_text());assert edge['edge_passed']
vco=json.loads((H/'results/vco_high_offset_validation.json').read_text())
fig,ax=plt.subplots(1,2,figsize=(11,4.7),constrained_layout=True)
for i,f in enumerate(edge['offsets_hz']):
    ax[0].plot(range(1,7),[x['relative_to_edge1_db'][i] for x in edge['edge_rows']],marker=['o','x','^'][i],label=f'{f/1e6:g} MHz')
ax[0].set(xlabel='Output rising edge within PSS period',ylabel='Timing PSD relative to edge 1 (dB)',title='New divider + RT4: six actual output edges')
ax[0].legend(fontsize=8);ax[0].grid(alpha=.2);ax[0].set_xticks(range(1,7))
bands=vco['disjoint_bands'];values=np.array([x['timing_variance_fs2'] for x in bands]);percent=100*values/sum(values)
labels=['1–2','2–5','5–10','10–100','100–491.75']
bars=ax[1].bar(labels,percent,color=['#367ac2','#4386b8','#609abe','#83abc3','#a7c2d1'])
for bar,p,x in zip(bars,percent,bands):ax[1].text(bar.get_x()+bar.get_width()/2,p+.7,f"{p:.1f}%\n{x['equivalent_timing_rms_fs']:.1f} fs",ha='center',va='bottom',fontsize=8)
ax[1].set(xlabel='Offset band (MHz)',ylabel='Fraction of 1 MHz–491.75 MHz variance (%)',title='Isolated CF10 VCO: measured high-offset PM')
ax[1].set_ylim(0,max(percent)+12);ax[1].tick_params(axis='x',labelsize=8);ax[1].grid(axis='y',alpha=.2)
fig.suptitle('Separate circuit fixtures at TT / 1.2 V / 27 °C — neither is full-PLL jitter',fontsize=11)
dest=H/'results/figures/noise_evidence_42.png';fig.savefig(dest,dpi=170);plt.close(fig);print(dest)
