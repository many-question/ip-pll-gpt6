"""Reproduce the VCO repair figures from measured result files."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

H=Path(__file__).resolve().parent;O=H/'results';F=H/'figures';F.mkdir(exist_ok=True)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'savefig.dpi':170})
colors={'tt':'#2463a6','ss':'#c96724','ff':'#27936c'};labels={'tt':'TT / 27 C','ss':'SS / 60 C','ff':'FF / 0 C'}

def save(fig,name):
    fig.savefig(F/(name+'.png'),bbox_inches='tight');fig.savefig(F/(name+'.pdf'),bbox_inches='tight');plt.close(fig)

def main():
    d=json.loads((O/'final_validation.json').read_text());assert d['all_pass'],'Do not draw a complete coverage figure before verification finishes'
    fig,axs=plt.subplots(1,3,figsize=(11.6,9.6),sharex=True,sharey=True)
    for ax,c in zip(axs,colors):
        rows=[x for x in d['selected'] if x['corner']==c]
        for r in rows:
            ends=[(r[k]['f_ghz']*1e9-r['fvco_hz'])/1e6 for k in ['low','high']]
            ax.plot(ends,[r['k']]*2,color=colors[c],lw=2.3,marker='|',ms=7)
        ax.axvspan(-2,2,color='#e9edf2',zorder=0);ax.axvline(0,color='#26364a',lw=.8)
        ax.set_title(labels[c]);ax.set_xlabel('VCO frequency - target (MHz)');ax.grid(axis='y',alpha=.14)
        ax.set_yticks(range(9,42));ax.set_ylim(41.7,8.3)
    axs[0].set_ylabel('K  (output target = K x 24 MHz)')
    fig.suptitle('Repaired VCO R2: all 99 loaded channel checks pass',fontsize=15,y=.98)
    fig.text(.5,.925,'Each bar: measured frequencies at 0.2 V and 1.0 V fine control; shaded region: +/-2 MHz guard.',ha='center',fontsize=10)
    fig.text(.5,.035,'1.2 V; assumed inductor Q = 5 at 3.3 GHz; actual divider + sampler/CP/reference circuitry.\nEndpoint coverage and valid division are verified; these are not closed-loop PLL lock results.',ha='center',fontsize=9,color='#465366')
    fig.subplots_adjust(top=.89,bottom=.11,wspace=.15);save(fig,'channel_coverage')

    fig,axs=plt.subplots(1,2,figsize=(11.6,4.8))
    for c in colors:
        rows=sorted([x for x in d['selected'] if x['corner']==c],key=lambda x:x['k']);ks=[x['k'] for x in rows]
        for ax,metric in zip(axs,['vco_mw','total_mw']):
            a=[min(x[k][metric] for k in ['low','high']) for x in rows];b=[max(x[k][metric] for k in ['low','high']) for x in rows]
            ax.fill_between(ks,a,b,color=colors[c],alpha=.15);ax.plot(ks,b,color=colors[c],label=labels[c],lw=1.5)
            ax.set_xlabel('K');ax.set_ylabel('Measured DC power (mW)');ax.grid(alpha=.18)
    axs[0].set_title('VCO branch (including ideal IREF supply power)');axs[1].set_title('VCO + connected measurement branches');axs[0].legend(frameon=False)
    fig.suptitle('Power at the measured fine-control endpoints',fontsize=14)
    fig.text(.5,.015,'Connected branches omit the output retimer, GHz clock receiver, full control and real bias generators. This is not total PLL power.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.05,1,.94));save(fig,'power')

    rows=json.loads((O/'noise_summary.json').read_text());spectra=np.load(O/'noise_spectra.npz')
    fig,ax=plt.subplots(figsize=(10.2,6))
    for c in colors:
        for code in [6,243]:
            r=next(x for x in rows if x['case']==f'r2_noise_{c}_c{code}');key=r['run']+'__'+r['case']
            ax.semilogx(spectra[key+'_f'],10*np.log10(spectra[key+'_L']),color=colors[c],ls='-' if code==6 else '--',lw=1.3,label=f'{labels[c]}, code {code}: {r["frequency_hz"]/1e9:.3f} GHz')
    for case,style in [('r2_noise_divider','-'),('r2_noise_divider_refined','x')]:
        r=next((x for x in rows if x['case']==case),None)
        if r:
            key=r['run']+'__'+r['case'];ax.semilogx(spectra[key+'_f'],10*np.log10(spectra[key+'_L']),style,color='#22272e',lw=2,ms=7,label='TT with actual divider, sampler tracking' if style=='-' else 'Loaded refinement: 1 ps / 127 sidebands / gmin 1 pS')
    ax.set(xlabel='Offset from VCO carrier (Hz)',ylabel='SSB phase noise (dBc/Hz)',xlim=(1e4,5e8),ylim=(-165,-35));ax.grid(which='both',alpha=.16)
    ax.legend(fontsize=9,frameon=False,loc='lower left');ax.set_title('PDK MOS + noisy inductor RLC: VCO phase noise',fontsize=14)
    fig.text(.5,.01,'Colored curves: 140 fF proxy per tank node. Black: fixed tracking state, no periodic reference. Neither is closed-loop PLL jitter.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.045,1,1));save(fig,'phase_noise')

    d=json.loads((O/'fine_curve_validation.json').read_text());assert d['all_pass']
    fig,axs=plt.subplots(1,3,figsize=(11.6,4.6))
    for ax,r in zip(axs,d['cases']):
        c=r['corner'];v=[x['control_v'] for x in r['points']];f=[x['f_ghz']*1000 for x in r['points']];target=r['k']*24*r['points'][0]['m']
        ax.plot(v,f,'o-',color=colors[c]);ax.axhline(target,color='#52606d',ls='--',lw=1,label='Required VCO frequency')
        ax.set(title=f'{labels[c]}, K={r["k"]}, code={r["code"]}',xlabel='Fine control (V)',ylabel='VCO frequency (MHz)');ax.grid(alpha=.2)
    axs[0].legend(frameon=False,fontsize=8);fig.suptitle('Loaded fine tuning at three critical operating points',fontsize=14)
    fig.text(.5,.012,'Five measured control voltages per case; correct division checked at every point. No global monotonicity claim for unmeasured codes.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.055,1,.94));save(fig,'fine_tuning')
    print('Wrote four PNG/PDF figures')

if __name__=='__main__':main()
