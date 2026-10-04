"""Plot actual diagnostic noise attribution and the verified sampler partition."""
from pathlib import Path
import hashlib, json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

H = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    names = ['frontend_noise_r2_all_validation.json', 'sampler_noise_mechanism_validation.json']
    names += [f'frontend_noise_r2_{g}_validation.json' for g in ['reference','charge_pump','sampler']]
    values = [json.loads((H/'results'/n).read_text()) for n in names]
    allv, sampler = values[:2]
    assert all(v['noise_valid'] and v['isolated_vs_all_group_check']['passed'] for v in values[2:])
    fig, axes = plt.subplots(1,2,figsize=(12.5,5.3),gridspec_kw={'width_ratios':[1.4,1]})
    colors = ['#4069b2','#e8913a','#369b80','#9674ba','#8999a4','#d4b784']
    keys = ['reference','charge_pump','sampler','bias','pulser','validity']
    labels = ['Reference','Charge pump','Sampler','Bias','Pulse timing','Validity']
    x = np.arange(3); bottom = np.zeros(3)
    for key,label,color in zip(keys,labels,colors):
        y = np.array(allv['group_variance_fraction'][key])*100
        axes[0].bar(x,y,bottom=bottom,label=label,color=color,width=.62)
        for k,value in enumerate(y):
            if value>=7:axes[0].text(k,bottom[k]+value/2,f'{value:.1f}%',ha='center',va='center',color='white',fontsize=10)
        bottom += y
    assert max(abs(bottom-100))<1e-7
    axes[0].set(xticks=x,xticklabels=['10 kHz','1 MHz','10 MHz'],ylim=(0,102),
                ylabel='Fraction of frontend current-noise power (%)',title='Frontend attribution at measured offsets')
    axes[0].legend(ncol=3,loc='upper center',bbox_to_anchor=(.5,1.42),frameon=False,fontsize=9)
    s = sampler['group_fraction_of_sampler']; gkeys = ['clock_inverter','nmos_switches','pmos_switches']
    y = [s[g][1]*100 for g in gkeys]
    axes[1].barh(np.arange(3),y,color=['#369b80','#5478b9','#e8913a'],height=.6)
    axes[1].set(yticks=np.arange(3),yticklabels=['Clock inverter','NMOS switches','PMOS switches'],
                xlim=(0,60),xlabel='Fraction of sampler noise power (%)',title='Inside the sampler at 1 MHz')
    axes[1].invert_yaxis()
    for k,value in enumerate(y):axes[1].text(value+1,k,f'{value:.2f}%',va='center',fontsize=10)
    for ax in axes:
        ax.spines[['top','right']].set_visible(False)
    fig.suptitle('Three independent noise-on groups verified: reference, charge pump, sampler',fontsize=13,y=.99)
    fig.text(.05,.025,'TT 27 C / 1.2 V / 24 MHz reference / 3.936 GHz ideal RF replay / clamped control.\nThree diagnostic offsets, not integrated PLL jitter; other noise-on groups remain in progress.',fontsize=9,color='#444444')
    fig.subplots_adjust(left=.075,right=.97,top=.72,bottom=.22,wspace=.53)
    image = H/'figures/frontend_noise_sources.png'; assert not image.exists(); fig.savefig(image,dpi=180);plt.close(fig)
    out = dict(scope=__doc__,sources_sha256={n:sha(H/'results'/n) for n in names},
               image_sha256=sha(image),independent_groups_verified=['reference','charge_pump','sampler'],
               full_pll_acceptance=False)
    target = H/'results/frontend_noise_sources_figure.json';assert not target.exists()
    target.write_text(json.dumps(out,indent=2)+'\n');print(image)


if __name__=='__main__':main()
