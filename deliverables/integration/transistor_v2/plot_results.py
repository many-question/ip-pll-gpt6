"""Standalone evidence plots from measured spectra and recovered transient data."""
from pathlib import Path
import os,json
import numpy as np
H=Path(__file__).resolve().parent
D=H.parents[2]
ROOT=D.parent if D.name=='share' and (D.parent/'AGENTS.md').exists() else D
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'research/matplotlib_cache'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})

def main():
    summary=json.loads((H/'results/noise_summary.json').read_text())
    v=json.loads((H/'results/validation.json').read_text())
    spec=np.load(H/'results/noise_spectra.npz')
    fig,ax=plt.subplots(1,2,figsize=(12,4.5),layout='constrained')
    names=['tb_noise_retimer','tb_noise_retimer_sp25_tt','tb_noise_retimer_sp25_ss','tb_noise_retimer_sp25_ff']
    rows=[next(x for x in summary['edges'] if x['case']==c) for c in names]
    bars=ax[0].bar(['Original TT','Revised TT','Revised SS/60 C','Revised FF/0 C'],[x['spectre_jee_fs'] for x in rows],color=['#94a3b8','#2563eb','#f97316','#16a34a'])
    ax[0].bar_label(bars,fmt='%.1f fs',padding=4)
    ax[0].axhline(200,color='#be123c',ls='--',label='200 fs: complete PLL requirement')
    ax[0].set(ylabel='Intrinsic RMS jitter (fs)',ylim=(0,320),title='Retimer + output only | 10 kHz to 492 MHz')
    ax[0].tick_params(axis='x',labelsize=8);ax[0].legend(fontsize=8)
    for name,label in [('noise04_tb_vco_noise_c0','Original bias'),('noise06_tb_vco_filtered_c0','200 kohm / 5 pF'),('noise14_tb_vco_filtered_slow_c0','1 Mohm / 10 pF')]:
        if name+'_f' in spec:ax[1].semilogx(spec[name+'_f'],10*np.log10(spec[name+'_sphi']/2),label=label)
    ax[1].set(xlabel='Offset frequency (Hz)',ylabel='SSB phase noise (dBc/Hz)',title='Unloaded VCO, code 0 | TT, 1.2 V')
    ax[1].grid(alpha=.2);ax[1].legend(fontsize=8)
    fig.suptitle('PDK MOS noise measurements; ideal clocks/supply and assumed passives',fontsize=12)
    fig.savefig(H/'results/device_noise.png',dpi=160);plt.close(fig)

    fig,ax=plt.subplots(3,1,figsize=(10,7),sharex=True,layout='constrained')
    p=ROOT/'research/runs/spectre_transistor_v2/fll14/tb_fll_controller_r3/waveforms.npz'
    revision='R3, 180 us' if p.exists() else 'R2, 170 us'
    z=np.load(p if p.exists() else ROOT/'research/runs/spectre_transistor_v2/fll09/tb_fll_controller_tt/waveforms.npz')
    t=z['time']*1e6
    code=sum((z[f'coarse{i}']>.6)*(1<<i) for i in range(8));dac=sum((z[f'dac{i}']>.6)*(1<<i) for i in range(6))
    ax[0].plot(t,code,label='Coarse code');ax[0].plot(t,dac,label='DAC code');ax[0].set(ylabel='Code');ax[0].legend(ncol=2)
    ax[1].plot(t,z['freq_ghz']*1e3);ax[1].axhline(984,ls='--',color='#be123c');ax[1].set(ylabel='Plant output (MHz)')
    ax[2].plot(t,z['ctrl'],label='Control voltage');ax[2].plot(t,z['enable']/1.2,label='Handoff');ax[2].set(xlabel='Time (us)',ylabel='V / logic');ax[2].legend(ncol=2)
    for a in ax:a.grid(alpha=.2)
    fig.suptitle('MOS FLL controller / DAC / filter, analytic finite-count stimulus\n'+revision+' acquisition test, TT; this is not a full-MOS PLL',fontsize=12)
    fig.savefig(H/'results/fll_acquisition.png',dpi=160);plt.close(fig)

    fig,ax=plt.subplots(1,2,figsize=(12,4.3),layout='constrained')
    source=v['divider_light'] if len(v['divider_light'])==18 else v['divider']
    for j,corner in enumerate(['tt','ss','ff']):
        rows=[r for r in source if r['corner']==corner]
        ax[0].plot([r['m'] for r in rows],[r['power_mw'] for r in rows],marker='o',label=corner.upper())
    ax[0].set(xticks=[4,6,8,10,12,14],xlabel='Divide ratio M',ylabel='Supply power (mW)',title='Divider at each mapped band maximum')
    ax[0].legend();ax[0].grid(alpha=.2)
    for key,label in [('noise04_tb_vco_noise_c0','Original bias'),('noise14_tb_vco_filtered_slow_c0','Slower bias filter')]:
        proj=json.loads((H/'results/noise_projection.json').read_text());rows=[r for r in proj['rows'] if r['vco_source']==key]
        ax[1].plot([r['unity_hz']/1e6 for r in rows],[r['partial_rss_fs'] for r in rows],marker='o',label=label)
    ax[1].axhline(200,ls='--',color='#be123c');ax[1].set(xlabel='Continuous unity frequency (MHz)',ylabel='Partial RSS estimate (fs)',title='Diagnostic projection; incomplete noise model')
    ax[1].legend();ax[1].grid(alpha=.2)
    fig.savefig(H/'results/power_and_noise_risk.png',dpi=160);plt.close(fig)
if __name__=='__main__':main()
