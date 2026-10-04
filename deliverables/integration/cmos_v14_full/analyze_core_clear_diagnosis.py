"""Diagnose saved warm trajectories; no periodic acceptance or random jitter claim.

Compare the counter-clear candidate with its actual DAC-clear predecessor.
Both use the same measured text seed, 1 ps Gear2 and 2 us initialization.
Only common observed states are compared; hidden MOS charge is not measured.
"""
from pathlib import Path
import hashlib,json,re
import numpy as np
from noise_utils import cross

H=Path(__file__).resolve().parent;ROOT=H.parents[3];B=H.parents[1]/'blocks/cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    dest=H/'results/core_clear_initial_diagnosis.json'
    names=['core_dac_initial_period_drift.json','core_clear_initial_period_drift.json']
    proof=[json.loads((H/'results'/n).read_text()) for n in names]
    if dest.exists():
        previous=json.loads(dest.read_text())
        assert previous['source_files_sha256']=={n:sha(H/'results'/n) for n in names}
    protocols=[H/'results/core_dac_discharge_noise_protocol.json',H/'results/core_counter_clear_noise_protocol.json']
    p,q=[json.loads(x.read_text()) for x in protocols]
    assert q['source_protocol_sha256']==sha(protocols[0])
    assert p['seed_sha256']==q['seed_sha256']
    oldname='pll_noise_dacdischarge_core_v14';newname='pll_noise_counterclear_core_v14'
    old=B/(oldname+'.scs');new=B/(newname+'.scs')
    assert sha(old)==p['physical_dependencies_sha256'][old.name]
    assert sha(new)==q['physical_dependencies_sha256'][new.name]
    restored=new.read_text().replace(newname,oldname).replace('\ninclude "fll_counter_reset_clear_v14.scs"','')
    restored=re.sub(r'^(XCOUNT .*) fll_counter_reset_clear_v14$',r'\1 tx_fll_counter',restored,flags=re.M)
    assert restored==old.read_text()
    snapshots=[ROOT/'research/runs/spectre_cmos_v14_full'/v['run']/v['case']/'inputs' for v in [p,q]]
    for n in set(p['physical_dependencies_sha256'])&set(q['physical_dependencies_sha256']):
        assert p['physical_dependencies_sha256'][n]==q['physical_dependencies_sha256'][n]
        assert all(sha(s/n)==p['physical_dependencies_sha256'][n] for s in snapshots)
    rows=[{r['node']:r for r in v['rows']} for v in proof]
    reset=[n for n in rows[1] if 'XCOUNT.' in n and n.endswith('.XN.x')]
    common=sorted(set(reset)&set(rows[0]));assert len(reset)==28 and len(common)==6
    cases=[]
    for d,v in zip(rows,proof):
        rr=[d[n] for n in common]
        cases.append(dict(source=v['source'],source_sha256=v['source_sha256'],intervals_us=v['intervals_us'],
                          max_common_reset_abs_v=max(max(map(abs,r['range'])) for r in rr),
                          max_common_reset_period_difference_v=max(r['difference_peak'] for r in rr),
                          selected={n:d[n] for n in ['XP.ctrl','XP.vc1','VDD:p','out','XP.clk']}))
    cache=ROOT/'research/runs/spectre_cmos_v14_full/corecounterclear01/core_counter_clear_noise_tt/tstab_tstab_clear_snapshot_last_two_periods.npz'
    with np.load(cache) as z:
        assert str(z['source_sha256'])==proof[1]['source_sha256']
        t=z['time'];signals={n:z[n] for n in ['XP.vp','XP.vn','XP.clk','out','ref','XP.vc1','XP.ctrl']}
        raw_reset_max=max(float(max(abs(z[n]))) for n in reset)
    a,b=np.asarray(proof[1]['intervals_us'][0])*1e-6;period=250e-9
    traces={'differential_RF':signals['XP.vp']-signals['XP.vn'],'clock':signals['XP.clk'],'output':signals['out'],'reference':signals['ref']}
    edge_rows=[];edge_curves={}
    for n,y in traces.items():
        e=cross(t,y,threshold=0 if n=='differential_RF' else .6)
        e1=e[(e>=a)&(e<b)];e2=e[(e>=a+period)&(e<b+period)]
        assert len(e1)==len(e2)>0
        shift=(e2-e1-period)*1e15
        edge_rows.append(dict(signal=n,edges_in_each_interval=len(e1),mean_shift_fs=float(shift.mean()),
                              peak_to_peak_shift_fs=float(np.ptp(shift)),min_fs=float(shift.min()),max_fs=float(shift.max())))
        edge_curves[n]=((e1-a)*1e9,shift)
    assert [r['edges_in_each_interval'] for r in edge_rows]==[984,984,246,6]
    grid=np.linspace(a,b,250001)
    slow=[]
    for n in ['XP.vc1','XP.ctrl']:
        first=np.interp(grid,t,signals[n]);second=np.interp(grid+period,t,signals[n])
        slow.append(dict(node=n,first_mean_v=float(np.mean(first)),second_mean_v=float(np.mean(second)),
                         mean_change_v=float(np.mean(second-first))))
    out=dict(scope=__doc__,condition=q['condition'],source_files_sha256={n:sha(H/'results'/n) for n in names},
             protocols_sha256={x.name:sha(x) for x in protocols},
             same_seed_and_other_physical_dependencies_verified=True,cases=cases,
             common_reset_nodes=common,candidate_reset_nodes=reset,
             candidate_all_saved_reset_max_abs_v=raw_reset_max,edge_comparison=edge_rows,slow_control_means=slow,
             actual_saved_step_ps=dict(maximum=float(max(np.diff(t)))*1e12,median=float(np.median(np.diff(t)))*1e12),
             statements=[
                 'Reset-node clearing is observed in the candidate; the common RF/output advance and filter drift persist.',
                 'Shared RF, recovered-clock and output edge shifts support a common trajectory drift rather than extra output-chain random jitter.',
                 'The small initialization-period differences do not establish a shooting solution; Newton updates and hidden charge states are outside this trace.',
                 'These sub-picosecond differences use linear interpolation of a 1ps-limited transient. They are diagnostics, not calibrated jitter accuracy.'
             ],periodic_state_valid=False,random_jitter_measured=False,full_pll_acceptance=False,main_dut_modified=False)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(2,1,figsize=(10,6.5),layout='constrained')
    for n in ['differential_RF','output','reference']:
        x,y=edge_curves[n];ax[0].plot(x,y,'.',ms=2,label=n.replace('_',' '))
    ax[0].set(ylabel='Second minus first edge (fs)',xlabel='Time in first 250 ns interval (ns)',title='Warm trajectory: common deterministic edge advance')
    ax[0].legend();ax[0].grid(alpha=.2)
    for n in ['XP.vc1','XP.ctrl']:
        first=np.interp(grid,t,signals[n]);second=np.interp(grid+period,t,signals[n])
        # Preserve the RF ripple range instead of aliasing it through decimation.
        blocks=(second-first)[:-1].reshape(250,1000)*1e6
        centers=(np.arange(250)+.5)*(b-a)*1e9/250
        if n=='XP.ctrl':ax[1].fill_between(centers,blocks.min(axis=1),blocks.max(axis=1),alpha=.3,color='tab:orange',label=n+' 1 ns min/max')
        ax[1].plot(centers,blocks.mean(axis=1),label=n+' 1 ns mean')
    ax[1].set(ylabel='Second minus first voltage (uV)',xlabel='Time in first 250 ns interval (ns)',title='Residual loop-filter state change')
    ax[1].legend();ax[1].grid(alpha=.2)
    fig.suptitle('TT27 / 1.2 V / counter-clear diagnostic core / 1 ps Gear2\nInitialization only: no accepted PSS and no random-noise measurement',fontsize=11)
    image=H/'results/core_clear_initial_diagnosis.png'
    if image.exists():assert dest.exists() and previous['figure_sha256']==sha(image)
    fig.savefig(image,dpi=150);plt.close(fig)
    out['figure_sha256']=sha(image)
    dest.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({k:out[k] for k in ['candidate_all_saved_reset_max_abs_v','edge_comparison','slow_control_means','actual_saved_step_ps']},indent=2))

if __name__=='__main__':main()
