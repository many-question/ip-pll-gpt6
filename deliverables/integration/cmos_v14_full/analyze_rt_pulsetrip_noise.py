"""Validate updated-divider local-chain noise and compare matched old-bank offsets."""
from pathlib import Path
import hashlib,json
import numpy as np
from noise_utils import parse,header,devices,cross
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
p=json.loads((H/'results/rt_pulsetrip_noise_protocol.json').read_text());sha=lambda x:hashlib.sha256(x.read_bytes()).hexdigest()
def noise(path):
    pn=parse(path);f=pn['freq'];slope=header(path,'slew rate event_1');sv=pn['out']**2
    assert slope>0 and np.all(np.diff(f)>0) and np.all(np.isfinite(sv)) and np.all(sv>=0)
    dev=devices(path,len(f));err=float(max(abs(sum(dev.values())/sv-1)));assert err<1e-7
    return f,sv/slope**2,slope,err,{k:v/slope**2 for k,v in dev.items()}
rows=[]
for item in p['cases']:
    j=R/item['run']/item['case'];rp=j/'result.json'
    if not rp.exists():continue
    r=json.loads(rp.read_text())
    if not r.get('local_outputs_sha256'):continue
    row=dict(factor=item['factor'],grade=item['grade'],source_result=rp.relative_to(ROOT).as_posix(),source_sha256=sha(rp),periodic_passed=False);rows.append(row)
    log=(j/'spectre.out').read_text()
    if not r['ok'] or 'spectre completes with 0 errors' not in log:continue
    assert r['remote_inputs_match'] and not r.get('periodic_state') and 'The steady-state solution was achieved' in log
    assert r['inputs_sha256']['bank_pulsetrip_v14.scs']==p['current_bank_sha256']
    old=R/item['old_fine_run']/item['old_fine_case'];oldr=json.loads((old/'result.json').read_text())
    # The changed bank still includes the same latch dependencies; exactly one physical file changes.
    current={k:v for k,v in r['inputs_sha256'].items() if k not in [item['case']+'.scs','bank_pulsetrip_v14.scs']}
    previous={k:v for k,v in oldr['inputs_sha256'].items() if k not in [item['old_fine_case']+'.scs','cmos_even_bank_acq_v14.scs']}
    assert current==previous
    raw=j/(item['case']+'.raw');td=parse(raw/'pss.td.pss');fd=parse(raw/'pss.fd.pss');t=td['time'];T=t[-1]-t[0]
    expected={'vp':24,'clk':24,'q1':12,'data':6,'out':6,'acqclk':6,'XD.d8':3,'XD.d12':2}
    actual={k:int(round(fd['freq'][1+np.argmax(abs(fd[k][1:]))]/164e6)) for k in expected}
    edges=cross(t,td['out']);end=max(float(abs(td[k][-1]-td[k][0])) for k in expected)
    periodic=bool(abs(T*164e6-1)<1e-7 and actual==expected and len(edges)==6 and end<1e-3)
    if periodic:periodic=bool(max(abs(np.diff(np.r_[edges,edges[0]+T])*984e6-1))<.02)
    row.update(periodic_passed=periodic,harmonics=actual,output_edges=len(edges),endpoint_max_v=end,physical_change_verified=True)
    if not periodic:continue
    path=raw/'pnMedge.0.sample.pnoise';f,st,slew,err,dev=noise(path)
    row.update(offsets_hz=f.tolist(),timing_psd_s2_per_hz=st.tolist(),slew_v_per_s=slew,device_sum_relative_error=err,
        raw_noise_sha256=sha(path),exact_harmonic_flicker_warning='SPCRTRF-15037' in log)
    groups={}
    for name,values in dev.items():
        group='.'.join(name.split('.')[:2]) if name.startswith('XR.') else name.split('.')[0]
        groups[group]=groups.get(group,0)+values
    row['group_timing_psd_s2_per_hz']={k:v.tolist() for k,v in groups.items()}
    if item['grade']=='probe':
        bf,bst,_,_,_=noise(old/(item['old_fine_case']+'.raw')/'pnMedge.0.sample.pnoise')
        assert np.allclose(f,p['matched_offsets_hz'],rtol=1e-10,atol=0) and np.allclose(f,bf,rtol=1e-10,atol=0)
        row.update(repaired_minus_old_bank_psd_db=(10*np.log10(st/bst)).tolist(),old_result_sha256=sha(old/'result.json'),fullband_rms_measured=False)
    else:
        assert len(f)>=90 and abs(f[0]/1e4-1)<1e-9 and abs(f[-1]/492e6-1)<1e-9
        row.update(provisional_log_grid_rms_fs=float(np.sqrt(np.trapezoid(st,f))*1e15),
            group_provisional_rms_fs={k:float(np.sqrt(np.trapezoid(v,f))*1e15) for k,v in groups.items()},fullband_rms_measured=True,
            physical_pole_integral_closed=False)
out=dict(scope=__doc__,cases=rows,probe_complete=sum(x['grade']=='probe' for x in rows)==2,
    full_pll_acceptance=False,old_noise_only_gates_apply=False,main_dut_modified=False,limitations=p['limitations'])
(H/'results/rt_pulsetrip_noise_validation.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
