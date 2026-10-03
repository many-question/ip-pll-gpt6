"""Validate isolated device-noise attribution on a completed sizing candidate.

Three frequencies are attribution tests, not jitter integrals. Physical circuit,
stimulus, PSS settings and source state are checked before each isolated run.
"""
from pathlib import Path
import argparse,hashlib,json,re,subprocess,sys
import numpy as np
from noise_utils import parse,header,devices
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
parser=argparse.ArgumentParser();parser.add_argument('--factor',type=int,choices=[2,4],required=True);parser.add_argument('--run-id',required=True)
a=parser.parse_args();assert a.run_id.replace('_','').isalnum()
sourcecase=f'chain_rtscale{a.factor}_tt';j=R/'chainrtscale01'/sourcecase
subprocess.run([sys.executable,str(H/'analyze_rt_noise_scaling.py')],check=True)
v=next(x for x in json.loads((H/'results/rt_noise_scaling_validation.json').read_text())['cases'] if x['case']==sourcecase)
assert v['periodic_passed'] and v['noise_consistent'] and v['simulator_completed']
rec=json.loads((j/'result.json').read_text());state=j/'periodic.state';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert rec['ok'] and rec['remote_inputs_match'] and rec['periodic_state_file']['collected']
assert sha(state)==rec['local_outputs_sha256']['periodic.state']
assert json.loads((H/'results/pss_reuse_validation.json').read_text())['passed']
available={p.name:p for p in (H.parents[1]/'blocks').glob('*/*') if p.suffix in ('.scs','.va')}
for name,digest in rec['inputs_sha256'].items():
    if name!=sourcecase+'.scs':assert name in available and sha(available[name])==digest,name
groups={'ff':['XR.XFF'],'buffers':['XR.X0','XR.X1'],'rx':['XRX'],'divider':['XD'],'aux':['XACQ0','XACQ1','XACB0','XACB1','XCOUNT']}
base=(j/'inputs'/(sourcecase+'.scs')).read_text()
base=re.sub(r'writefinal="[^"]+"','writefinal="__FINAL_STATE__"',base)
# No need to save another periodic.state for each three-point diagnostic.
base=re.sub(r'\s+writepss="[^"]+"','',base)
assert 'start=10k stop=492M dec=20' in base
base=base.replace('start=10k stop=492M dec=20','values=[1M 10M 100M]')
assert not (R/a.run_id).exists(),'Never repeat an existing run id'
cases=[]
for group,names in groups.items():
    case=f'chain_rt{a.factor}_only_{group}_tt'
    s=re.sub(r'^(simulatorOptions options .*)$',lambda m:m[0]+' noiseon_inst=['+' '.join(names)+'] noiseon_type=all',base,flags=re.M)
    (H/'tb'/(case+'.scs')).write_text(s);cases.append(case)
# run_spectre currently accepts exactly one case with a reused PSS state.
source_raw=j/(sourcecase+'.raw')/'pnMedge.0.sample.pnoise'
source_pn=parse(source_raw);source_dev=devices(source_raw,len(source_pn['freq']));source_slew=header(source_raw,'slew rate event_1')
rows=[]
for group,case in zip(groups,cases):
    run=a.run_id+'_'+group
    assert not (R/run).exists(),run
    subprocess.run([sys.executable,str(H/'run_spectre.py'),'--run-id',run,'--cases',case,'--mode','ax','--threads','1','--preset-override','all','--timeout','7200','--pss-state',str(state)],check=True)
    job=R/run/case;r=json.loads((job/'result.json').read_text());log=(job/'spectre.out').read_text(errors='replace')
    assert r['ok'] and r['remote_inputs_match'] and 'spectre completes with 0 errors' in log
    p=job/(case+'.raw')/'pnMedge.0.sample.pnoise';pn=parse(p);freq=pn['freq'];slew=header(p,'slew rate event_1');dev=devices(p,len(freq))
    wanted=lambda name:any(name.startswith(prefix+'.') for prefix in groups[group])
    sv=pn['out']**2;selected=sum(x for k,x in dev.items() if wanted(k));excluded=sum(x for k,x in dev.items() if not wanted(k))
    ref_sv=sum(x for k,x in source_dev.items() if wanted(k))
    ref_st=np.interp(freq,source_pn['freq'],ref_sv)/source_slew**2;st=sv/slew**2
    err=float(max(abs(st/ref_st-1)));ex=float(max(np.asarray(excluded)/np.maximum(sv,1e-300)))
    totalerr=float(max(abs(sum(dev.values())/sv-1)))
    row=dict(group=group,source_result=(job/'result.json').relative_to(ROOT).as_posix(),source_sha256=sha(job/'result.json'),offsets_hz=freq.tolist(),timing_psd_s2_per_hz=st.tolist(),reference_group_psd=ref_st.tolist(),max_relative_error=err,max_excluded_noise_fraction=ex,device_sum_relative_error=totalerr,passed=bool(err<1e-3 and ex<1e-8 and totalerr<1e-7),full_band_integral=False)
    rows.append(row)
    (H/'results'/f'rt_noise_gate{a.factor}_validation.json').write_text(json.dumps(dict(scope=__doc__,source_case=sourcecase,groups=groups,cases=rows,completed=len(rows)==len(groups),passed=len(rows)==len(groups) and all(x['passed'] for x in rows),full_pll_acceptance=False),indent=2)+'\n')
    print(group,err,ex,row['passed'],flush=True)
