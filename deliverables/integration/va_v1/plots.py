"""Render actual Spectre waveforms; no synthesized illustration data."""
import argparse
import os
from pathlib import Path
import numpy as np

DELIVERY=Path(__file__).resolve().parents[3]
ROOT=DELIVERY.parent if DELIVERY.name=='share' and (DELIVERY.parent/'AGENTS.md').exists() else DELIVERY

def load_wave(run,case):
    raw=ROOT/f'research/runs/spectre_va/{run}/{case}/waveforms.npz'
    published=Path(__file__).resolve().parent/'results'/f'{case}.npz'
    return np.load(raw if raw.exists() else published)

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);args=p.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    os.environ['MPLCONFIGDIR']=str(ROOT/'research/matplotlib_cache')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(4,1,figsize=(10,9),sharex=True)
    for k in [9,14,41]:
        data=load_wave('top01',f'top_k{k}')
        t=data['time']*1e6
        for ax,key in zip(axes,['fvco','ctrl','code','locked']):ax.plot(t,data[key],label=f'K={k}')
    for ax,label in zip(axes,['VCO frequency (GHz)','Control voltage (V)','Coarse bank code','Qualified lock (V)']):
        ax.set_ylabel(label);ax.grid(alpha=.2)
    axes[0].legend();axes[-1].set_xlabel('Time (us)')
    fig.suptitle('Spectre structural SSPLL: autonomous startup at band endpoints')
    fig.tight_layout();fig.savefig(args.out/'top_startup.png',dpi=140);plt.close(fig)
    fig,axes=plt.subplots(3,2,figsize=(12,8),sharex=True)
    for column,(run,case,title) in enumerate([('recovery01','top_k41_recovery','VCO -24 MHz disturbance'),('retune01','top_retune','Output 216 to 984 MHz reconfiguration')]):
        data=load_wave(run,case);t=data['time']*1e6
        for ax,key in zip(axes[:,column],['fvco','ctrl','locked']):ax.plot(t,data[key]);ax.axvline(20,color='tab:red',ls='--',alpha=.6);ax.grid(alpha=.2)
        axes[0,column].set_title(title);axes[-1,column].set_xlabel('Time (us)')
    for ax,label in zip(axes[:,0],['VCO frequency (GHz)','Control voltage (V)','Qualified lock (V)']):ax.set_ylabel(label)
    fig.tight_layout();fig.savefig(args.out/'top_recovery_retune.png',dpi=140);plt.close(fig)

if __name__=='__main__':main()
