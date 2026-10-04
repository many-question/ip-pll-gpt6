"""Validate physical coarse loading and its matched control; no closed-loop/noise claim."""
from pathlib import Path
import hashlib,json
import numpy as np
from noise_utils import cross
from reference_modulation_utils import fit_edges
H=Path(__file__).resolve().parent;ROOT=H.parents[3];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=json.loads((H/'results/rt4_coarse_program_protocol.json').read_text());rows=[];deps=None
for item in p['cases']:
    j=ROOT/'research/runs/spectre_cmos_v14_full'/p['run']/item['case'];rp=j/'result.json'
    if not rp.exists():continue
    r=json.loads(rp.read_text())
    if not r.get('local_outputs_sha256'):continue
    row=dict(case=item['case'],coarse_code=item['coarse_code'],source_result=rp.relative_to(ROOT).as_posix(),source_sha256=sha(rp),valid=False);rows.append(row)
    if not r['ok'] or 'spectre completes with 0 errors' not in (j/'spectre.out').read_text():continue
    assert r['remote_inputs_match'] and r['inputs_sha256']['pll_noise_rt4_program_core_v14.scs']==p['program_core_sha256']
    assert r['inputs_sha256']['rt4load_nominal_tt.ic']==p['source_seed_sha256']
    current={k:v for k,v in r['inputs_sha256'].items() if k!=item['case']+'.scs'}
    if deps is None:deps=current
    assert current==deps and sha(j/'waveforms.npz')==r['local_outputs_sha256']['waveforms.npz']
    with np.load(j/'waveforms.npz') as z:d={k:z[k] for k in z.files}
    t=d['time'];assert abs(t[0]-250e-9)<1e-14 and abs(t[-1]-750e-9)<1e-14
    code=item['coarse_code'];held=all(np.all(d[f'XP.b{i}']>.9) if code&(1<<i) else np.all(d[f'XP.b{i}']<.3) for i in range(8))
    edges=cross(t,d['XP.vp']-d['XP.vn'],0);rf=fit_edges(edges);of=fit_edges(cross(t,d['out']))
    fs=[]
    for lo,hi in [(250e-9,500e-9),(500e-9,750e-9)]:
        a=edges[(edges>=lo)&(edges<hi)];fs.append(float(1/np.mean(np.diff(a))))
    drift=abs(fs[1]-fs[0])/np.mean(fs)*1e6;clamp=float(max(abs(d['XP.ctrl']-p['control_v'])))
    row.update(valid=bool(held and clamp<1e-9 and drift<100 and abs(of['carrier_hz']*4/rf['carrier_hz']-1)<.001),
        coarse_held=bool(held),rf_fit=rf,output_fit=of,control_clamp_error_v=clamp,window_rf_drift_ppm=float(drift),
        rf_swing_pp_v=float(np.ptp(d['XP.vp']-d['XP.vn'])),final_c1_minus_control_v=float(d['XP.vc1'][-1]-d['XP.ctrl'][-1]))
out=dict(scope=__doc__,cases=rows,complete=len(rows)==2,main_dut_modified=False,full_pll_acceptance=False,random_jitter_measured=False)
same=next((x for x in rows if x['coarse_code']==23 and x['valid']),None)
if same:
    oldj=ROOT/'research/runs/spectre_cmos_v14_full/rt4load01/rt4load_nominal_tt';old=json.loads((oldj/'result.json').read_text())
    with np.load(oldj/'waveforms.npz') as z:
        oldf=fit_edges(cross(z['time'],z['XP.vp']-z['XP.vn'],0))['carrier_hz'];swing=np.ptp(z['XP.vp']-z['XP.vn'])
    df=same['rf_fit']['carrier_hz']-oldf;ds=same['rf_swing_pp_v']/swing-1
    out['program_interface_control']=dict(rf_delta_hz=df,swing_fraction_delta=float(ds),passed=bool(abs(df)<250e3 and abs(ds)<.005))
    out['source_nominal_result_sha256']=sha(oldj/'result.json')
if len(rows)==2 and all(x['valid'] for x in rows) and out.get('program_interface_control',{}).get('passed'):
    a,b=sorted(rows,key=lambda x:x['coarse_code']);out['measured_one_code_rf_delta_hz']=b['rf_fit']['carrier_hz']-a['rf_fit']['carrier_hz']
(H/'results/rt4_coarse_program_validation.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(dict(complete=out['complete'],control=out.get('program_interface_control'),rows=[dict(case=x['case'],valid=x['valid'],rf_mhz=x.get('rf_fit',{}).get('carrier_hz',0)/1e6) for x in rows]),indent=2))
