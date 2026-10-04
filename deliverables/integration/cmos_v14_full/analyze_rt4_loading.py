"""Measure actualLC RT4 clamped-control curve; never claim PLL noise acceptance."""
from pathlib import Path
import hashlib,json
import numpy as np
from noise_utils import cross
from reference_modulation_utils import fit_edges
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
p=json.loads((H/'results/rt4_loading_protocol.json').read_text());R=ROOT/'research/runs/spectre_cmos_v14_full';rows=[]
items=[dict(**x,run=p['run']) for x in p['cases']]
extra=H/'results/rt4_loading_limit_protocol.json'
if extra.exists():
    ep=json.loads(extra.read_text());assert ep['rt4_core_sha256']==p['rt4_core_sha256']
    items += [dict(**x,run=ep['run']) for x in ep['cases']]
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
for case in items:
    j=R/case['run']/case['case'];rp=j/'result.json'
    if not rp.exists():continue
    r=json.loads(rp.read_text())
    if not r.get('local_outputs_sha256'):continue
    row=dict(case=case['case'],control_v=case['control_v'],valid=False,source=rp.relative_to(ROOT).as_posix(),source_sha256=sha(rp));rows.append(row)
    if not r['ok'] or 'spectre completes with 0 errors' not in (j/'spectre.out').read_text():continue
    assert r['remote_inputs_match'] and r['inputs_sha256']['pll_noise_rt4_core_v14.scs']==p['rt4_core_sha256']
    assert r['inputs_sha256'][case['case']+'.ic']==case['seed_sha256']
    assert sha(j/'waveforms.npz')==r['local_outputs_sha256']['waveforms.npz']
    with np.load(j/'waveforms.npz') as z:d={k:z[k] for k in z.files}
    t=d['time'];assert abs(t[0]-250e-9)<1e-14 and abs(t[-1]-750e-9)<1e-14
    re=cross(t,d['XP.vp']-d['XP.vn'],0);oe=cross(t,d['out']);fr=fit_edges(re);fo=fit_edges(oe)
    coarse=all(np.all(d[f'XP.b{i}']>.9) if 23&(1<<i) else np.all(d[f'XP.b{i}']<.3) for i in range(8))
    clamp=float(max(abs(d['XP.ctrl']-case['control_v'])))
    fs=[]
    for first,last in [(250e-9,500e-9),(500e-9,750e-9)]:
        e=re[(re>=first)&(re<last)];fs.append(float(1/np.mean(np.diff(e))))
    drift=abs(fs[1]-fs[0])/np.mean(fs)*1e6
    row.update(rf_fit=fr,output_fit=fo,coarse23_held=bool(coarse),control_clamp_max_error_v=clamp,
        loop_filter_memory=dict(final_control_v=float(d['XP.ctrl'][-1]),final_vc1_v=float(d['XP.vc1'][-1]),
            final_vc1_minus_control_v=float(d['XP.vc1'][-1]-d['XP.ctrl'][-1]),
            note='External clamp makes this valid for frequency measurement, but releasing it with unsettled C1 can create a large transient. Prepare a physical precharge/settling handoff before judging loop capture.'),
        last_two_window_rf_hz=fs,last_two_window_difference_ppm=float(drift),
        valid=bool(coarse and clamp<1e-9 and drift<100 and abs(fo['carrier_hz']*4/fr['carrier_hz']-1)<.001))
out=dict(scope=__doc__,cases=rows,expected_cases=len(items),complete=len(rows)==len(items),main_dut_modified=False,full_pll_acceptance=False,random_jitter_measured=False)
base=json.loads((H/'results/sampler_loading_validation.json').read_text())
bc=next((x for x in base['cases'] if x['case']=='samplerload_clocked_tt' and x['valid_for_diagnosis']),None)
nominal=next((x for x in rows if x['case']=='rt4load_nominal_tt' and x['valid']),None)
if bc and nominal:
    out['same_control_loading_comparison']=dict(rf_frequency_pull_hz=nominal['rf_fit']['carrier_hz']-bc['rf_fit']['carrier_hz'],
        output_pm24_ratio=nominal['output_fit']['harmonics'][0]['pm_peak_rad']/bc['output_fit']['harmonics'][0]['pm_peak_rad'],
        note='Sameexternalcontrol, actualLC loopclamped, only outputchainRT4 scaling. Not lockednoise performance.')
if len(rows)>=3 and all(x['valid'] for x in rows):
    ordered=sorted(rows,key=lambda x:x['control_v']);v=np.array([x['control_v'] for x in ordered]);f=np.array([x['rf_fit']['carrier_hz'] for x in ordered])
    target=3936e6;monotonic=bool(np.all(np.diff(f)>0) or np.all(np.diff(f)<0));bracket=bool(monotonic and min(f)<target<max(f))
    fit=np.polyfit(v,f,1)
    out['curve']=dict(controls_v=v.tolist(),rf_frequencies_hz=f.tolist(),secant_kvco_hz_per_v=float((f[-1]-f[0])/(v[-1]-v[0])),
        linear_fit_max_residual_hz=float(max(abs(np.polyval(fit,v)-f))),target_hz=target,target_bracketed=bracket,
        predicted_control_v=float(np.interp(target,f if f[0]<f[-1] else f[::-1],v if f[0]<f[-1] else v[::-1])) if bracket else None,
        note='Piecewise linear interpolation inside measured range only; verify the predicted point and actualloop capture. Static curve does not establish capture range.')
(H/'results/rt4_loading_validation.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(dict(complete=out['complete'],curve=out.get('curve'),cases=[dict(case=x['case'],valid=x['valid'],control_v=x['control_v'],rf_mhz=x.get('rf_fit',{}).get('carrier_hz',0)/1e6) for x in rows]),indent=2))
