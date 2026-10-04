"""Relate CP device PSD attribution to measured conducting and inactive windows.

Operating-point gm integrals are not time-resolved output noise attribution.
Source resistive drain currents are not a complete tail-node charge balance.
This analysis chooses experiments; it does not adopt a circuit or measure PLL jitter.
"""
from pathlib import Path
import hashlib,json
import numpy as np
from noise_utils import parse,cross,devices,selected_device_components

H=Path(__file__).resolve().parent;ROOT=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    dest=H/'results/cp_noise_mechanism_validation.json';assert not dest.exists()
    npth=H/'results/frontend_noise_r2_all_validation.json';opth=H/'results/frontend_operating_probe_validation.json'
    nv,ov=[json.loads(p.read_text()) for p in [npth,opth]]
    assert nv['noise_valid'] and ov['operating_data_valid'] and ov['balanced']
    assert nv['condition']==ov['condition']
    rp=ROOT/nv['periodic']['source_result'];assert sha(rp)==nv['periodic']['source_sha256']
    pn=rp.parent/(rp.parent.name+'.raw')/'pn.pnoise';assert sha(pn)==nv['noise_sha256']
    cols=devices(pn,3);cp=[n for n in cols if n.startswith('XCP.')]
    components=selected_device_components(pn,cp,3)
    total=np.array(nv['current_psd_a2_per_hz']);cp_total=sum(cols[n] for n in cp)
    assert max(abs(cp_total/np.array(nv['group_psd_a2_per_hz']['charge_pump'])-1))<1e-12
    four=['XCP.MIP','XCP.MIN','XCP.MPO','XCP.MPD']
    parts={k:sum(np.array(v.get(k,[0.,0.,0.])) for v in components.values()) for k in ['fn','id','total']}
    noise=dict(offsets_hz=nv['offsets_hz'],cp_fraction_of_frontend=(cp_total/total).tolist(),
               four_signal_devices_fraction_of_cp=(sum(cols[n] for n in four)/cp_total).tolist(),
               channel_noise_fraction_of_cp=(parts['id']/cp_total).tolist(),
               flicker_noise_fraction_of_cp=(parts['fn']/cp_total).tolist(),
               remaining_noise_fraction_of_cp=((cp_total-parts['id']-parts['fn'])/cp_total).tolist(),
               device_fraction_of_cp={n:(cols[n]/cp_total).tolist() for n in cp})
    orp=ROOT/ov['periodic']['source_result'];assert sha(orp)==ov['periodic']['source_sha256']
    td=orp.parent/(orp.parent.name+'.raw')/'pss.td.pss';assert sha(td)==ov['periodic']['td_sha256']
    cache=orp.parent/'cp_noise_mechanism_traces.npz'
    names=['time','refb','hp','hn','XCP.gate','XCP.ng','XCP.tail','XCP.mir']+[n+':'+q for n in ['XCP.MT',*four] for q in ['id','gm']]
    if cache.exists():
        with np.load(cache) as z:
            assert str(z['source_sha256'])==sha(td)
            d={n:z[n] for n in names}
    else:
        parsed=parse(td);d={n:parsed[n] for n in names}
        np.savez_compressed(cache,**d,source_sha256=sha(td))
    t=d['time'];T=t[-1]-t[0];mean=lambda a:float(np.trapezoid(a,t)/T)
    gate=d['XCP.gate']>.6;hold=d['refb']>.6
    falls=cross(t,-d['XCP.gate'],-.6);assert len(falls)==1
    age=(t-falls[0])%T
    masks=dict(gate_on=gate,inactive_hold=(~gate)&hold,inactive_track=(~gate)&(~hold),
               late_inactive_hold=(~gate)&hold&(age>=5e-9),late_inactive_track=(~gate)&(~hold)&(age>=5e-9))
    partition=['gate_on','inactive_hold','inactive_track']
    assert np.all(sum(masks[n].astype(int) for n in partition)==1)
    rows={}
    for label,mask in masks.items():
        z=mask.astype(float);fraction=mean(z);assert fraction>0
        rows[label]=dict(fraction=fraction,node_range_v={n:[float(min(d[n][mask])),float(max(d[n][mask]))] for n in ['hp','hn','XCP.tail','XCP.mir','XCP.ng']},
            devices={n:dict(mean_id_a=mean(d[n+':id']*z)/fraction,mean_gm_s=mean(d[n+':gm']*z)/fraction,
                signed_resistive_drain_charge_c=mean(d[n+':id']*z)*T,
                fraction_of_whole_period_gm_integral=mean(d[n+':gm']*z)/mean(d[n+':gm'])) for n in ['XCP.MT',*four]})
    on=rows['gate_on']['devices'];tailq=on['XCP.MT']['signed_resistive_drain_charge_c']
    pairq=sum(on[n]['signed_resistive_drain_charge_c'] for n in ['XCP.MIP','XCP.MIN'])
    out=dict(scope=__doc__,condition=nv['condition'],source_validation_sha256={npth.name:sha(npth),opth.name:sha(opth)},
        noise_source_sha256=sha(pn),operating_source_sha256=sha(td),noise_attribution=noise,operating_windows=rows,
        gate_high_duration_ns=rows['gate_on']['fraction']*T*1e9,
        gate_high_resistive_drain_charge_comparison=dict(tail_c=tailq,input_pair_sum_c=pairq,ratio_pair_to_tail=pairq/tailq,
            complete_tail_terminal_kcl_measured=False),
        observations=[
            'The four input/mirror transistors dominate CP-attributed noise; inspect actual channel/flicker fractions before selecting area scaling.',
            'The tail is almost off late in both hold and track phases, while input/mirror gm remains nonzero in both phases.',
            'Most CP gate-high tail resistive drain charge is not simultaneous input-pair resistive drain charge. Dynamic storage is a hypothesis, not a completed terminal KCL proof.'
        ],
        proposed_next_experiment='After independent CP noise-on passes, compare a separate charge-storage/settling candidate with actual rebalanced gain and fresh device noise. Preserve baseline; do not claim a benefit from sizing alone.',
        limitations=['Three PSD points are not an integral or a closed-loop result.',
            'Instantaneous gm or its time integral cannot assign what fraction of output noise occurs during a given clock phase.',
            'No complete source/gate/bulk terminal-current balance is saved, so dynamic storage cannot yet be quantitatively assigned to tail-node capacitance.',
            'Mask transitions use the accepted sampled grid and 0.6V thresholds; gate-on charge is diagnostic, not a new specification.',
            'Independent CP-only noise remains running; this uses the completed all-noise device attribution.'],
        main_dut_modified=False,integrated_jitter_fs=None,full_pll_acceptance=False)
    dest.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(dict(noise=noise,gate_high_duration_ns=out['gate_high_duration_ns'],gate_high_charge=out['gate_high_resistive_drain_charge_comparison']),indent=2))

if __name__=='__main__':main()
