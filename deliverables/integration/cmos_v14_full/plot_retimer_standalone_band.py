"""Plot measured standalone RT4 spectra, contributions and numerical comparison."""
from pathlib import Path
import hashlib,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from noise_utils import parse,header,devices
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
v=json.loads((H/'results/retimer_standalone_band_validation.json').read_text());assert v['precision_passed']
row=v['cases'][1];rp=ROOT/row['source_result'];assert hashlib.sha256(rp.read_bytes()).hexdigest()==row['source_sha256']
j=rp.parent;path=j/(j.name+'.raw/pnMedge.0.sample.pnoise');pn=parse(path);f=pn['freq'];slope=header(path,'slew rate event_1');dev=devices(path,len(f))
groups={label:np.zeros(len(f)) for label in ['TSPC retimer','First buffer','Last buffer']}
for n,s in dev.items():groups['TSPC retimer' if '.XFF.' in n else 'First buffer' if '.X0.' in n else 'Last buffer']+=s/slope**2
fig,ax=plt.subplots(2,1,figsize=(8,6),sharex=True,layout='constrained',gridspec_kw={'height_ratios':[3,1]})
ax[0].loglog(f,np.sqrt(pn['out']**2/slope**2)*1e15,color='#111111',lw=2,label=f"Total: {row['rms_fs']:.2f} fs RMS")
for label,s in groups.items():ax[0].loglog(f,np.sqrt(s)*1e15,label=label,lw=1.3)
ax[0].set(ylabel='Timing noise (fs / sqrt(Hz))',title='Standalone CMOS RT4: 10 kHz to 492 MHz')
ax[0].legend(frameon=False,fontsize=9)
ax[1].semilogx(v['offsets_hz'],v['psd_finer_minus_fine_db'],color='#1d6e97')
ax[1].set(xlabel='Offset frequency (Hz)',ylabel='PSD change (dB)',ylim=(-.1,.1))
ax[1].axhline(0,color='0.6',lw=.6)
for a in ax:a.grid(True,which='both',alpha=.15)
fig.suptitle('TT 27 C | 1.2 V | 984 MHz output | 10 fF\nIdeal noiseless clock/data; full PLL excluded',fontsize=10)
dest=H/'figures/retimer_standalone_band.png';dest.parent.mkdir(exist_ok=True);fig.savefig(dest,dpi=160);print(dest)
