"""Audit the failed physical-register core PSS; no noise result is fabricated."""
from pathlib import Path
import hashlib,json,re
import numpy as np
from noise_utils import cross,stream_selected
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
J=ROOT/'research/runs/spectre_cmos_v14_full/coreregisterprobe01/core_register_noise_probe_tt'
rec=json.loads((J/'result.json').read_text());assert not rec['ok'] and rec['remote_inputs_match']
raw=J/(J.name+'.raw')/'pss.tran.pss';cache=J/'failure_tstab.npz'
keys=['ref','out','XP.vp','XP.vn','XP.ctrl','XP.refb','XP.q1','XP.data','XP.XD.d8','XP.XD.d12']+[f'XP.b{i}' for i in range(8)]
d,duplicate_fields=stream_selected(raw,keys);np.savez_compressed(cache,**d)
t=d['time'];rf=cross(t,d['XP.vp']-d['XP.vn'],0);ref=cross(t,d['XP.refb']);p=(np.interp(ref,rf,np.arange(len(rf)))-np.arange(len(ref))*164)*2*np.pi
period_rows={}
for name,mult in [('out',246),('XP.q1',492),('XP.data',246),('XP.XD.d8',123),('XP.XD.d12',82)]:
    e=cross(t,d[name]);last=e[e>t[-1]-200e-9]
    period_rows[name]=dict(last200ns_mhz=float((len(last)-1)/(last[-1]-last[0])*1e-6),
        edges_last250ns=int(sum((e>251e-9)&(e<=501e-9))),expected_edges=mult,
        endpoint_v=np.interp([251e-9,501e-9],t,d[name]).tolist())
log=(J/'spectre.out').read_text(errors='replace')
out=dict(scope=__doc__,source_result=(J/'result.json').relative_to(ROOT).as_posix(),
 source_sha256=hashlib.sha256((J/'result.json').read_bytes()).hexdigest(),raw_sha256=hashlib.sha256(raw.read_bytes()).hexdigest(),
 simulator_errors=re.findall(r'ERROR \([^)]+\):[^\n]+',log),
 convergence_history=[l.strip() for l in log.splitlines() if 'Conv norm =' in l],
 tstab_time_ns=[float(t[0]*1e9),float(t[-1]*1e9)],reference_edge_times_ns=(ref*1e9).tolist(),phase_change_rad=(p-p[0]).tolist(),phase_pp_rad=float(np.ptp(p)),
 period_checks=period_rows,coarse23_held=all((min(d[f'XP.b{i}'])>.6 if (23>>i)&1 else max(d[f'XP.b{i}'])<.6) for i in range(8)),
 repeated_boundary_fields_coalesced=duplicate_fields,
 observations=['Text restart has a decaying phase disturbance; prior-transient stationarity does not validate this PSS start.',
 'Saved public divider outputs have the expected edge counts over the final250ns; no evidence here establishes a wrong fundamental.',
 'Newton initially reduces the norm, then generates nonphysical voltages in the inactive reset latch and subsequently other nodes.',
 'A file named periodic.state exists despite failed convergence and is explicitly invalid for reuse.'],
 hypotheses=['Longer same-analysis stabilization may reduce the restart disturbance.',
 'Inactive dynamic storage nodes may impair shooting conditioning; added observations test this, not yet proved.',
 'Gear2 is a numerical convergence experiment, not a circuit repair or a noise-performance result.'],
 pnoise_ran=False,full_pll_jitter_fs=None,full_pll_acceptance=False)
(H/'results/register_pss_failure.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:out[k] for k in ['phase_pp_rad','period_checks','simulator_errors','repeated_boundary_fields_coalesced']},indent=2))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
norm=[float(re.search(r'Conv norm = ([0-9.eE+\-]+)',s)[1]) for s in out['convergence_history']]
fig,ax=plt.subplots(1,2,figsize=(10,3.4),layout='constrained')
ax[0].plot(ref*1e9,p-p[0],'o-',color='#2563eb')
ax[0].set(xlabel='PSS initial transient time (ns)',ylabel='RF phase change at reference edge (rad)',title='Text-state restart: phase is still settling')
ax[1].semilogy(range(len(norm)),norm,'o-',color='#b45309');ax[1].axhline(1,color='#475569',ls='--')
ax[1].set(xlabel='Reported periodic residual index',ylabel='Spectre convergence norm',title='Shooting iteration diverged; no PNoise')
for a in ax:a.grid(alpha=.25)
fig.suptitle('V14 diagnostic core / TT27 / 1.2 V / 1 ps / 4 MHz PSS — not a jitter measurement',fontsize=10)
fig.savefig(H/'results/figures/register_pss_failure.png',dpi=160);plt.close(fig)
