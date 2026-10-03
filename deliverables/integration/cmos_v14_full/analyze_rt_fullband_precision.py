"""Compare the full log grid and audit finite neighbours of shifted flicker poles."""
from pathlib import Path
import hashlib,json
import numpy as np
from noise_utils import parse,header,devices,cross
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
protocol=json.loads((H/'results/rt_fullband_precision_protocol.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def read_noise(path):
    d=parse(path);f=d['freq'];slew=header(path,'slew rate event_1');sv=d['out']**2
    assert slew>0 and np.all(np.isfinite(sv)) and np.all(sv>=0) and np.all(np.diff(f)>0)
    contrib=devices(path,len(f));error=float(max(abs(sum(contrib.values())/sv-1)));assert error<1e-7
    return f,sv/slew**2,slew,error
rows=[]
for item in protocol['cases']:
    j=R/item['run']/item['case'];rp=j/'result.json'
    if not rp.exists():continue
    r=json.loads(rp.read_text())
    if not r.get('local_outputs_sha256'):continue
    row=dict(factor=item['factor'],source_result=rp.relative_to(ROOT).as_posix(),source_sha256=sha(rp),numerical_grid_passed=False);rows.append(row)
    log=(j/'spectre.out').read_text();assert r['remote_inputs_match'] and not r.get('periodic_state')
    if not r['ok'] or 'spectre completes with 0 errors' not in log:continue
    assert 'The steady-state solution was achieved' in log
    raw=j/(item['case']+'.raw');old=R/item['source_run']/item['source_case'];br=json.loads((old/'result.json').read_text())
    assert {k:v for k,v in r['inputs_sha256'].items() if k!=item['case']+'.scs'}=={k:v for k,v in br['inputs_sha256'].items() if k!=item['source_case']+'.scs'}
    td=parse(raw/'pss.td.pss');fd=parse(raw/'pss.fd.pss');t=td['time'];T=t[-1]-t[0]
    expected={'vp':24,'clk':24,'q1':12,'data':6,'out':6,'acqclk':6,'XD.d8':3,'XD.d12':2}
    harmonic={k:int(round(fd['freq'][1+np.argmax(abs(fd[k][1:]))]/164e6)) for k in expected}
    edges=cross(t,td['out']);endpoint=max(float(abs(td[k][-1]-td[k][0])) for k in expected)
    assert abs(T*164e6-1)<1e-7 and harmonic==expected and len(edges)==6 and endpoint<1e-3
    assert max(abs(np.diff(np.r_[edges,edges[0]+T])*984e6-1))<.02
    f,st,slew,error=read_noise(raw/'pnMedge.0.sample.pnoise')
    bf,bst,_,_=read_noise(old/(item['source_case']+'.raw')/'pnMedge.0.sample.pnoise')
    assert len(f)>=90 and np.allclose(f,bf,rtol=1e-10,atol=0)
    assert abs(f[0]/1e4-1)<1e-9 and abs(f[-1]/492e6-1)<1e-9
    delta=10*np.log10(st/bst);coarse=float(np.sqrt(np.trapezoid(bst,bf))*1e15);fine=float(np.sqrt(np.trapezoid(st,f))*1e15)
    nf,nst,_,_=read_noise(raw/'pnnearMedge.0.sample.pnoise')
    assert np.allclose(nf,protocol['harmonic_neighbour_offsets_hz'],rtol=1e-12,atol=0)
    smooth=np.exp(np.interp(np.log(nf),np.log(f),np.log(st)))
    near_db=10*np.log10(nst/smooth)
    row.update(physical_dependencies_match=True,endpoint_max_v=endpoint,slew_v_per_s=slew,
        analyzed_raw_sha256={name:sha(raw/name) for name in ['pss.td.pss','pss.fd.pss','pnMedge.0.sample.pnoise','pnnearMedge.0.sample.pnoise']},
        original_noise_file_sha256=sha(old/(item['source_case']+'.raw')/'pnMedge.0.sample.pnoise'),
        device_sum_relative_error=error,grid_offsets_hz=f.tolist(),fine_timing_psd_s2_per_hz=st.tolist(),
        fine_minus_coarse_db=delta.tolist(),max_grid_difference_db=float(max(abs(delta))),
        coarse_log_grid_provisional_rms_fs=coarse,fine_log_grid_provisional_rms_fs=fine,rms_relative_change=fine/coarse-1,
        numerical_grid_passed=bool(max(abs(delta))<protocol['pointwise_limit_db'] and abs(fine/coarse-1)<protocol['integrated_rms_relative_limit']),
        finite_neighbours=dict(offsets_hz=nf.tolist(),timing_psd_s2_per_hz=nst.tolist(),relative_to_log_interpolated_psd_db=near_db.tolist(),
            max_difference_db=float(max(abs(near_db))),note='No area across the unmeasured harmonic centre is asserted.'),
        exact_harmonic_flicker_warning='SPCRTRF-15037' in log,
        physical_pole_integral_closed=False,full_pll_acceptance=False)
out=dict(scope=__doc__,cases=rows,complete=len(rows)==len(protocol['cases']),
    physical_pole_integral_closed=False,full_pll_acceptance=False,limitations=protocol['limitations'])
(H/'results/rt_fullband_precision_validation.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
