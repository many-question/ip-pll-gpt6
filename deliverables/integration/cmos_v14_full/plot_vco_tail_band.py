"""Plot measured tail-candidate spectra and the restricted high-offset integral."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

H=Path(__file__).resolve().parent

def main():
    p=H/'results/vco_tail_band_validation.json'
    if not p.exists():print('Dense tail validation pending');return
    v=json.loads(p.read_text());b,c=v['baseline'],v['candidate'];f=np.array(v['offsets_hz'])
    band=v['high_offset_bands'][0];fig,ax=plt.subplots(2,2,figsize=(11,7.7))
    colors=['#45677d','#007e72'];labels=['CF40 / MT 300 um, L1','CF40 / MT 560 um, L2']
    for row,col,label in zip([b,c],colors,labels):
        ax[0,0].semilogx(f,row['ssb_pm_dbc_per_hz'],color=col,label=label)
    line=max(b['tool_estimated_linewidth_hz'],c['tool_estimated_linewidth_hz'])
    ax[0,0].axvspan(f[0],line,color='0.9',label='Below estimated linewidth')
    ax[0,0].set(xlabel='Offset (Hz)',ylabel='RF SSB PM noise (dBc/Hz)',title='Free VCO: measured spectrum')
    ax[0,0].legend(fontsize=8);ax[0,0].grid(alpha=.2)
    ax[0,1].semilogx(f,v['timing_psd_change_db'],color=colors[1]);ax[0,1].axhline(0,color='0.5',lw=.8)
    ax[0,1].set(xlabel='Offset (Hz)',ylabel='Candidate / baseline (dB)',title='Timing PSD, carrier normalization included')
    ax[0,1].grid(alpha=.2)
    values=[band[x]['rms_fs'] for x in ['baseline','candidate']]
    ax[1,0].bar(['Baseline','Tail candidate'],values,color=colors,width=.5)
    for i,value in enumerate(values):ax[1,0].text(i,value+1,f'{value:.2f} fs',ha='center')
    ax[1,0].set(ylabel='Restricted timing RMS (fs)',ylim=(0,max(values)*1.17),
                title=f"1 MHz to {band['upper_hz']/1e6:.3f} MHz only")
    groups=['cross_coupled_core','tail_and_bias','inductor_RLC','switched_cap_bank']
    names=['Cross-coupled\nMOS','Tail and\nbias','Inductor\nRLC','Capacitor\nbank'];x=np.arange(len(groups))
    for i,key in enumerate(['baseline','candidate']):
        ax[1,1].bar(x+(i-.5)*.36,[band[key]['group_variance_fraction'][g]*100 for g in groups],width=.36,color=colors[i],label=labels[i])
    ax[1,1].set_xticks(x,names);ax[1,1].set(ylabel='High-offset variance (%)',title='Physical noise attribution')
    ax[1,1].legend(fontsize=8)
    flag='PASS' if v['frequency_match_passed'] else 'FAIL'
    fig.suptitle('VCO tail-noise experiment | TT 27 C, 1.2 V, Q5 RLC, fixed M4, 10 fF',fontsize=13)
    foot=f"Carrier match: {v['relative_rf_change']*1e6:+.2f} ppm ({flag}, 100 ppm limit). "
    foot+='No full PLL jitter claim; independent candidate numerical precision pending.'
    fig.text(.5,.018,foot,ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.045,1,.96));dst=H/'figures/vco_tail_band.png';fig.savefig(dst,dpi=150);plt.close(fig);print(dst)

if __name__=='__main__':main()
