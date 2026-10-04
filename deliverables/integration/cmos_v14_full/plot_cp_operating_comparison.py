"""Compare accepted same-phase CP operating trials; do not infer noise benefit."""
from pathlib import Path
import hashlib,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from noise_utils import cross
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    outpath=H/'results/cp_operating_comparison.json';figpath=H/'figures/cp_operating_comparison.png'
    assert not outpath.exists() and not figpath.exists()
    configurations=[('Baseline','#5b6470','frontend_operating_probe_validation.json','cp_noise_mechanism_traces.npz'),
        ('Short tail','#0072b2','cp_fasttail_branch_validation.json','cp_operating_trial_traces.npz'),
        ('Higher midpoint','#d55e00','cp_mid70_probe_validation.json','cp_operating_trial_traces.npz')]
    fig,axs=plt.subplots(3,1,figsize=(9,8),sharex=True,constrained_layout=True);rows=[]
    for label,color,proofname,cachename in configurations:
        proof=H/'results'/proofname;v=json.loads(proof.read_text());m=v['periodic']
        assert v['operating_data_valid'] and m['periodic_passed']
        rp=ROOT/m['source_result'];assert sha(rp)==m['source_sha256'];j=rp.parent
        raw=j/(j.name+'.raw')/'pss.td.pss';cache=j/cachename
        assert sha(raw)==m['td_sha256']
        with np.load(cache) as z:
            assert str(z['source_sha256'])==sha(raw)
            d={n:z[n] for n in ['time','XCP.gate','XCP.ng','XCP.tail','XCP.MIP:id','XCP.MIN:id']}
        t=d['time'];r=cross(t,d['XCP.gate']);f=cross(t,-d['XCP.gate'],-.6);assert len(r)==len(f)==1
        x=(t-r[0])*1e9;keep=(x>=-1)&(x<=16)
        for ax,n,scale in [(axs[0],'XCP.ng',1),(axs[1],'XCP.tail',1)]:ax.plot(x[keep],d[n][keep]*scale,label=label,color=color)
        pair=d['XCP.MIP:id']+d['XCP.MIN:id'];axs[2].plot(x[keep],pair[keep]*1e6,label=label,color=color)
        if label=='Baseline':
            for ax in axs:ax.axvspan(0,(f[0]-r[0])*1e9,color='#0072b2',alpha=.08)
        rows.append(dict(label=label,validation=proofname,validation_sha256=sha(proof),
            source_result=m['source_result'],source_sha256=sha(rp),source_td_sha256=sha(raw),cache=cache.relative_to(ROOT).as_posix(),
            phase_deg=m['phase_deg'],clamp_current_na=m['mean_clamp_current_a']*1e9,phase_good_fraction=m['phase_good_fraction']))
    assert max(x['phase_deg'] for x in rows)-min(x['phase_deg'] for x in rows)<1e-12
    axs[0].set_ylabel('Tail gate voltage (V)');axs[1].set_ylabel('Tail node voltage (V)')
    axs[2].set_ylabel('Input-pair conductive\ncurrent sum (uA)');axs[2].set_xlabel('Time after each CP enable 50% rising edge (ns)')
    axs[0].legend(ncol=3)
    for ax in axs:ax.grid(alpha=.25);ax.set_xlim(-1,16)
    fig.suptitle('CP operating trials: same RF phase, TT 27 C, 1.2 V, 24 MHz reference\nShaded: enable high. Candidates are not rebalanced; this is not a noise comparison.',fontsize=11)
    fig.savefig(figpath,dpi=150);plt.close(fig)
    out=dict(scope=__doc__,condition=v['condition'],cases=rows,figure=figpath.relative_to(H).as_posix(),figure_sha256=sha(figpath),
        noise_measured=False,full_pll_acceptance=False,main_dut_modified=False,
        limitation='The original baseline has no branch probes. The separate branch probe control established unchanged voltages within 1.576e-12 V; candidate variants retain the same three probes.')
    outpath.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))

if __name__=='__main__':main()
