"""Validate the physical40fF dummy's clamped-control curve, without a PLL claim."""
from pathlib import Path
import hashlib,json
import numpy as np
from noise_utils import cross
from reference_modulation_utils import fit_edges
from loading_timing_utils import loading_timing
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
p=json.loads((H/'results/sampler_tuning_protocol.json').read_text());sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
base=p['baseline'];brp=ROOT/base['source_result'];assert sha(brp)==base['source_sha256'];br=json.loads(brp.read_text())
expected={k:v for k,v in br['inputs_sha256'].items() if k not in [base['case']+'.scs','samplerload_clocked_tt.ic']}
items=[dict(case=base['case'],control_v=base['control_v'],source_result=base['source_result'],baseline=True)]
items += [dict(**x,source_result=f'research/runs/spectre_cmos_v14_full/{p["run"]}/{x["case"]}/result.json',baseline=False) for x in p['cases']]
rows=[]
for item in items:
    rp=ROOT/item['source_result']
    if not rp.exists():continue
    r=json.loads(rp.read_text())
    if not r.get('local_outputs_sha256'):continue
    j=rp.parent;row=dict(case=item['case'],control_v=item['control_v'],baseline=item['baseline'],source_result=item['source_result'],source_sha256=sha(rp),valid=False);rows.append(row)
    if not r['ok'] or 'spectre completes with 0 errors' not in (j/'spectre.out').read_text():continue
    assert r['remote_inputs_match']
    actual={k:v for k,v in r['inputs_sha256'].items() if k not in [item['case']+'.scs',item['case']+'.ic','samplerload_clocked_tt.ic']}
    assert actual==expected
    if not item['baseline']:assert r['inputs_sha256'][item['case']+'.ic']==item['seed_sha256']
    wp=j/'waveforms.npz';assert sha(wp)==r['local_outputs_sha256']['waveforms.npz']
    with np.load(wp) as z:d={k:z[k] for k in z.files}
    t=d['time'];assert abs(t[0]-250e-9)<1e-14 and abs(t[-1]-750e-9)<1e-14
    re=cross(t,d['XP.vp']-d['XP.vn'],0);oe=cross(t,d['out']);rf=fit_edges(re);of=fit_edges(oe)
    fs=[];pm=[]
    for first,last in [(250e-9,500e-9),(500e-9,750e-9)]:
        e=re[(re>=first)&(re<last)];fs.append(float(1/np.mean(np.diff(e))))
        e=oe[(oe>=first)&(oe<last)];pm.append(fit_edges(e)['harmonics'][0])
    drift=abs(fs[1]-fs[0])/np.mean(fs)*1e6
    coarse=all(np.all(d[f'XP.b{i}']>.9) if 23&(1<<i) else np.all(d[f'XP.b{i}']<.3) for i in range(8))
    clamp=float(max(abs(d['XP.ctrl']-item['control_v'])));supply=max(float(max(abs(d[k]-1.2))) for k in ['XP.vco_vdd','XP.rx_vdd','XP.rt_vdd'])
    row.update(rf_fit=rf,output_fit=of,rf_last_two_windows_hz=fs,output_pm_last_two_windows=pm,
        loop_filter_memory=dict(final_control_v=float(d['XP.ctrl'][-1]),final_vc1_v=float(d['XP.vc1'][-1]),
            final_vc1_minus_control_v=float(d['XP.vc1'][-1]-d['XP.ctrl'][-1]),
            note='Frequency curve uses the external clamp; its final state is not automatically a matched closed-loop seed. Physically precharge or settle the loop filter before release.'),
        last_two_window_difference_ppm=float(drift),coarse23_held=bool(coarse),control_clamp_max_error_v=clamp,supply_max_error_v=supply,
        rf_differential_swing_pp_v=float(np.ptp(d['XP.vp']-d['XP.vn'])),reference_and_cp_timing=loading_timing(t,d),
        valid=bool(coarse and clamp<1e-9 and supply<1e-9 and drift<100 and abs(of['carrier_hz']*4/rf['carrier_hz']-1)<.001))
out=dict(scope=__doc__,condition=p['condition'],cases=rows,complete=len(rows)==3,full_pll_acceptance=False,random_jitter_measured=False,main_dut_modified=False)
if out['complete'] and all(x['valid'] for x in rows):
    a=sorted(rows,key=lambda x:x['control_v']);v=np.array([x['control_v'] for x in a]);f=np.array([x['rf_fit']['carrier_hz'] for x in a]);target=p['target_rf_hz']
    monotonic=bool(np.all(np.diff(f)>0) or np.all(np.diff(f)<0));bracket=bool(monotonic and min(f)<target<max(f))
    out['curve']=dict(control_v=v.tolist(),rf_hz=f.tolist(),monotonic=monotonic,target_rf_hz=target,target_bracketed=bracket,
        predicted_control_v=float(np.interp(target,f if f[0]<f[-1] else f[::-1],v if f[0]<f[-1] else v[::-1])) if bracket else None,
        note='Interpolation inside actual measured range only; a clamped point is not a PLL lock or jitter result.')
(H/'results/sampler_tuning_validation.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(dict(complete=out['complete'],curve=out.get('curve'),cases=[dict(case=x['case'],valid=x['valid'],control_v=x['control_v'],rf_mhz=x.get('rf_fit',{}).get('carrier_hz',0)/1e6) for x in rows]),indent=2))
