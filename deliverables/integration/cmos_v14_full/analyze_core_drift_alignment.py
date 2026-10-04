"""Diagnose common RF phase drift without treating an aligned waveform as periodic proof."""
from pathlib import Path
import hashlib,json
import numpy as np
from noise_utils import cross
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=json.loads((H/'results/core_gear_dense_validation.json').read_text())
j=(ROOT/p['source_result']).parent;r=json.loads((j/'result.json').read_text())
assert sha(j/'result.json')==p['source_sha256'] and sha(j/'waveforms.npz')==r['local_outputs_sha256']['waveforms.npz']
with np.load(j/'waveforms.npz') as z:d={k:z[k] for k in z.files}
t=d['time'];T=250e-9
rf=cross(t,d['XP.vp']-d['XP.vn'],0)
a=rf[(rf>=250e-9)&(rf<500e-9)];b=rf[(rf>=500e-9)&(rf<750e-9)]
assert len(a)==len(b)==984
shift=b-a-T
grid=np.linspace(a[0],a[-1],250000)
warped=grid+T+np.interp(grid,a,shift)
assert np.all(np.diff(warped)>0) and warped[-1]<=t[-1]
rows=[]
for k in ['XP.vp','XP.vn','XP.clk','XP.q1','XP.data','out','XP.XR.ob','XP.XD.d8','XP.XD.d12']:
    original=np.interp(grid+T,t,d[k])-np.interp(grid,t,d[k])
    aligned=np.interp(warped,t,d[k])-np.interp(grid,t,d[k])
    rms=float(np.sqrt(np.mean(original**2)));arms=float(np.sqrt(np.mean(aligned**2)))
    rows.append(dict(node=k,raw_peak_v=float(max(abs(original))),raw_rms_v=rms,rf_aligned_peak_v=float(max(abs(aligned))),rf_aligned_rms_v=arms,rms_reduction_fraction=1-arms/rms))
out=dict(scope=__doc__,source_result=p['source_result'],source_sha256=p['source_sha256'],
    common_rf_displacement_ps=dict(mean=float(np.mean(shift)*1e12),peak_abs=float(max(abs(shift))*1e12),
        first_quarter_mean=float(np.mean(shift[:246])*1e12),last_quarter_mean=float(np.mean(shift[-246:])*1e12)),
    rows=rows,raw_period_gate_remains_failed=True,random_jitter_measured=False,periodic_state_valid=False,
    interpretation='Time warping uses measured paired RF edges to expose the part of fast-node waveform mismatch explained by common RF drift. The forced reference is not warped physically; aligned residuals cannot pass the original periodic gate or establish jitter.',
    limitation='Sub-ps timing and residual voltage depend on1psGear2 integration and linear interpolation; this is mechanism diagnosis, not a precision noise measurement.')
(H/'results/core_drift_alignment_validation.json').write_text(json.dumps(out,indent=2)+'\n')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
fig,axes=plt.subplots(1,2,figsize=(11.5,4.2),layout='constrained')
axes[0].plot((a-a[0])*1e9,shift*1e12,lw=1,color='#234e70')
axes[0].set(xlabel='Position in first 250 ns period (ns)',ylabel='Paired RF edge displacement (ps)',title='Common deterministic RF drift')
axes[0].grid(alpha=.2)
labels=[x['node'].replace('XP.','') for x in rows];xx=np.arange(len(rows))
axes[1].bar(xx-.18,[x['raw_rms_v']*1e3 for x in rows],.36,label='Raw')
axes[1].bar(xx+.18,[x['rf_aligned_rms_v']*1e3 for x in rows],.36,label='RF phase aligned')
axes[1].set_xticks(xx,labels,rotation=55,ha='right');axes[1].set(ylabel='Waveform difference RMS (mV)',title='Diagnostic alignment only; gate still FAILED')
axes[1].legend(frameon=False);fig.suptitle('Actual LC core, 1 ps Gear2 after text restore — no random noise',fontsize=12)
dest=H/'results/figures/core_drift_diagnosis_43.png';fig.savefig(dest,dpi=160);plt.close(fig)
print(json.dumps(out,indent=2))
