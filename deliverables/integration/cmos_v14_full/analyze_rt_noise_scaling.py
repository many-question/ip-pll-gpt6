"""Conditional local-chain jitter comparison, not full-PLL acceptance."""
from pathlib import Path
import json,hashlib
import numpy as np
from noise_utils import parse,header,devices,cross
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
rows=[];spectra={}
baseline=json.loads((H/'results/chain_noise_validation.json').read_text())
b=next(x for x in baseline['cases'] if x['case']=='chain_noise_fine_tt' and x.get('single_case_valid'))
baseline_record=json.loads((ROOT/b['source_result']).read_text())
for factor in [2,4]:
    case=f'chain_rtscale{factor}_tt';j=R/'chainrtscale01'/case;rp=j/'result.json'
    if not rp.exists():continue
    rec=json.loads(rp.read_text())
    if not rec.get('local_outputs_sha256'):continue
    log=(j/'spectre.out').read_text(errors='replace')
    row=dict(case=case,factor=factor,source_result=rp.relative_to(ROOT).as_posix(),source_sha256=hashlib.sha256(rp.read_bytes()).hexdigest(),simulator_completed='spectre completes with 0 errors' in log,full_pll_acceptance=False);rows.append(row)
    if not row['simulator_completed']:continue
    assert rec['ok'] and rec['remote_inputs_match']
    old={k:v for k,v in baseline_record['inputs_sha256'].items() if k not in ['chain_noise_fine_tt.scs','rt_light24s12_out083_v14.scs']}
    new={k:v for k,v in rec['inputs_sha256'].items() if k not in [case+'.scs',f'rt_noise_scale{factor}_v14.scs']}
    assert old==new,'A physical dependency besides the retimer/output candidate changed'
    row['other_physical_dependencies_match_baseline']=True
    raw=j/(case+'.raw');td=parse(raw/'pss.td.pss');fd=parse(raw/'pss.fd.pss');t=td['time'];T=t[-1]-t[0]
    expected={'vp':24,'clk':24,'q1':12,'data':6,'out':6,'acqclk':6,'XD.d8':3,'XD.d12':2}
    harmonic={k:int(round(fd['freq'][1+np.argmax(abs(fd[k][1:]))]/164e6)) for k in expected}
    e=cross(t,td['out']);period=np.diff(np.r_[e,e[0]+T]) if len(e) else np.array([0.])
    endpoint=max(float(abs(td[k][-1]-td[k][0])) for k in expected)
    periodic=bool(abs(T*164e6-1)<1e-7 and harmonic==expected and len(e)==6 and max(abs(period*984e6-1))<.02 and endpoint<1e-3)
    row.update(periodic_passed=periodic,dominant_harmonics=harmonic,output_edges=len(e),endpoint_max_v=endpoint,
        output_range_v=[float(min(td['out'])),float(max(td['out']))],power_mw={k:float(-1.2*np.trapezoid(td[k],t)/T*1e3) for k in ['VDD:p','VRX:p','VRT:p']})
    p=raw/'pnMedge.0.sample.pnoise';pn=parse(p);f=pn['freq'];slew=header(p,'slew rate event_1');sv=pn['out']**2;st=sv/slew**2
    assert slew>0 and np.all(np.isfinite(st)) and np.all(st>=0) and np.all(np.diff(f)>0)
    assert len(f)>=90 and abs(f[0]/1e4-1)<1e-9 and abs(f[-1]/492e6-1)<1e-9
    dev=devices(p,len(f));err=float(max(abs(sum(dev.values())-sv)/np.maximum(sv,1e-300)))
    groups={}
    for name,v in dev.items():
        group='.'.join(name.split('.')[:2]) if name.startswith('XR.') else name.split('.')[0]
        groups[group]=groups.get(group,0)+v/slew**2
    jfs=float(np.sqrt(np.trapezoid(st,f))*1e15)
    row.update(provisional_jitter_fs=jfs,vs_baseline_ratio=jfs/b['jitter_fs'],slew_v_per_s=slew,
        device_sum_relative_error=err,noise_consistent=err<1e-7,
        provisional_group_jitter_fs={k:float(np.sqrt(np.trapezoid(v,f))*1e15) for k,v in groups.items()},
        exact_harmonic_flicker_warning='SPCRTRF-15037' in log,
        noise_consistent_scope='Device PSD sum agrees with output PSD only; not an independent noise-on or reuse validation.',
        pending='Finite-offset harmonic integration, all-edge, full-band numerical convergence, fresh-PSS noise-on and full-PLL/PVT checks remain.')
    precision_path=H/f'results/rt{factor}_precision_validation.json'
    if precision_path.exists():
        precision=json.loads(precision_path.read_text())
        row['matched_offset_precision_passed']=precision.get('passed')
        row['matched_offset_precision_evidence']=precision_path.relative_to(ROOT).as_posix()
        if precision.get('passed'):
            deps={k:v for k,v in rec['inputs_sha256'].items() if k!=case+'.scs'}
            assert all(p['physical_inputs']==deps for p in precision['cases'])
            row['matched_offset_max_psd_delta_db']=precision['max_absolute_delta_db']
    row['full_band_numerical_convergence_proven']=False
    spectra[case+'_f']=f;spectra[case+'_st']=st
    for k,v in groups.items():spectra[case+'_'+k+'_st']=v
out=dict(scope=__doc__,condition='TT27/1.2V/984MHz/10fF; external noiseless measured3.936GHz RF replay; actual RX, full divider and quiet counter load.1ps/383sidebands,20points/dec.',
    baseline_provisional_fs=b['jitter_fs'],baseline_slew_v_per_s=b['slew_v_per_s'],baseline_source=b['source_result'],band_hz=[1e4,492e6],cases=rows,main_dut_modified=False,
    selection_rule='Noise/performance first; recorded power is not an optimization gate. No automatic main-DUT adoption.',
    reuse_caution='This MOS circuit currently fails fresh-vs-readpss noise consistency. Original full-band sizing runs solve PSS fresh. See rt_noise_controls.json; RC calibration alone is insufficient.')
(H/'results/rt_noise_scaling_validation.json').write_text(json.dumps(out,indent=2)+'\n')
if spectra:np.savez_compressed(H/'results/rt_noise_scaling_spectra.npz',**spectra)
for row in rows:print(row['case'],row.get('periodic_passed'),row.get('provisional_jitter_fs'),row.get('provisional_group_jitter_fs'))
