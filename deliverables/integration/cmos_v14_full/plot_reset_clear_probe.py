"""Show quiet-node discharge separately from preserved running-clock kickback."""
from pathlib import Path
import hashlib,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from noise_utils import parse
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    fig,ax=plt.subplots(2,1,figsize=(9,7),layout='constrained');sources=[]
    for corner,color in [('tt','#1f77b4'),('ss','#d95f02'),('ff','#26945b')]:
        j=R/'resetclearquiet01'/f'reset_clear_quiet_{corner}';tp=next((j/(j.name+'.raw')).glob('tran*.tran'));d=parse(tp);t=d['time'];mask=t<=3e-9
        sources.append(dict(path=tp.relative_to(ROOT).as_posix(),sha256=sha(tp)))
        ax[0].semilogy(t[mask]*1e9,np.maximum(abs(d['XNEW.XS.XN.x'][mask]),1e-9)*1e3,color=color,label=f'Candidate {corner.upper()}',lw=1.5)
        ax[0].semilogy(t[mask]*1e9,abs(d['XOLD.XS.XN.x'][mask])*1e3,color=color,ls='--',label=f'Original {corner.upper()}',alpha=.7)
    ax[0].axhline(1,color='gray',ls=':',label='1 mV engineering gate');ax[0].set_ylabel('|Stack node| (mV)');ax[0].set_title('Clock held low during initial reset; 1 nV plotting floor')
    j=R/'resetclearunit01/reset_clear_dff_tt';tp=next((j/(j.name+'.raw')).glob('tran*.tran'));d=parse(tp);t=d['time'];mask=t<=3e-9
    sources.append(dict(path=tp.relative_to(ROOT).as_posix(),sha256=sha(tp)))
    ax[1].plot(t[mask]*1e9,d['XOLD.XS.XN.x'][mask]*1e3,label='Original TT',color='#555555')
    ax[1].plot(t[mask]*1e9,d['XNEW.XS.XN.x'][mask]*1e3,label='Candidate TT',color='#1f77b4')
    ax[1].set_title('984 MHz clock running during reset: residual kickback remains')
    ax[1].set_ylabel('Stack node (mV)')
    for a in ax:a.set_xlabel('Time (ns)');a.grid(alpha=.2);a.set_xlim(0,3);a.legend(fontsize=8,ncol=2)
    fig.suptitle('Reset-node transistor experiment\n1.2 V, 2 fF output; TT27 / SS60 / FF0; original vs reset discharge candidate')
    fig.supxlabel('Unit evidence only. Whole counter, PLL periodic convergence and random noise are separate checks.',fontsize=9)
    path=H/'figures/reset_clear_probe.png';fig.savefig(path,dpi=140);plt.close(fig)
    (H/'results/reset_clear_figure_sources.json').write_text(json.dumps(dict(figure=path.relative_to(ROOT).as_posix(),sources=sources),indent=2)+'\n')
    print(path)

if __name__=='__main__':main()
