"""Plot the frozen standalone reference-buffer screen, with its measurement limits."""
from pathlib import Path
import hashlib,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
H=Path(__file__).resolve().parent

def main():
    source=H/'results/reference_buffer_noise_validation.json';raw=source.read_bytes();v=json.loads(raw)
    assert hashlib.sha256(raw).hexdigest()=='f2f248d337aa8b1b8883151bfe394d78af87533e78be04d0e03f99fb648dbb40'
    assert v['complete'] and v['noise_all_valid'];b,c=v['cases'];colors=['#53677d','#008678']
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'font.family':'DejaVu Sans'})
    fig,axes=plt.subplots(1,2,figsize=(11.4,4.5),layout='constrained')
    for row,color,label in zip([b,c],colors,['Original: 1 / 4 / 16 / 64 um','Candidate: 8 / 16 / 32 / 64 um']):
        axes[0].loglog(row['offsets_hz'],np.sqrt(row['timing_psd_s2_per_hz'])*1e15,color=color,lw=2,label=label)
    axes[0].set(xlabel='Offset frequency (Hz)',ylabel='Output timing noise ASD (fs / sqrt(Hz))',title='Actual MOS sampled edge noise')
    axes[0].grid(True,which='both',alpha=.2);axes[0].legend(frameon=False,fontsize=9)
    x=np.arange(4);width=.35
    for row,color,offset in zip([b,c],colors,[-width/2,width/2]):
        bars=axes[1].bar(x+offset,[row['stage_rms_fs'][str(i)] for i in range(4)],width,color=color)
        axes[1].bar_label(bars,fmt='%.1f',fontsize=9,padding=3)
    axes[1].set_xticks(x,['Stage 1','Stage 2','Stage 3','Stage 4'])
    axes[1].set(ylabel='Output-referred contribution RMS (fs)',title='Per-stage contributions, 10 kHz to 12 MHz',ylim=(0,165))
    axes[1].grid(axis='y',alpha=.2);axes[1].set_axisbelow(True)
    fig.suptitle(f"Reference buffer: {b['rms_fs']:.2f} fs to {c['rms_fs']:.2f} fs  ({v['candidate_relative_rms_change']*100:.1f}%)",fontsize=15,weight='bold')
    fig.supxlabel('TT, 27 C, 1.2 V; ideal 24 MHz / 10 ps input; 2 pF load. PMOS widths = 2.5 x NMOS, L = 180 nm.\n'
                   'Fresh PSS. Contributions add as variances. Numerical refinement and full-frontend validation pending; not full-PLL jitter.',fontsize=9)
    dst=H/'results/reference_buffer_screen01.png';assert not dst.exists();fig.savefig(dst,dpi=160);plt.close(fig)
    assert dst.stat().st_size<5*1024*1024;print(str(dst))

if __name__=='__main__':main()
