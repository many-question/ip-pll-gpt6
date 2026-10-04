"""Audit fresh-PSS edge dependence and five independent device-noise gates."""
from pathlib import Path
import argparse,hashlib,json,re
import numpy as np
from noise_utils import parse,header,devices,cross
H=Path(__file__).resolve().parent; ROOT=H.parents[3]
parser=argparse.ArgumentParser()
parser.add_argument('--factor',type=int,choices=[2,4],default=2)
parser.add_argument('--bank',choices=['original','pulsetrip'],default='original')
args=parser.parse_args();factor=args.factor
if args.bank=='pulsetrip':assert factor==4
name=f'rt{factor}_'+('fine' if args.bank=='original' else 'pulsetrip')+'_audit'
protocol=json.loads((H/f'results/{name}_protocol.json').read_text())
R=ROOT/'research/runs/spectre_cmos_v14_full'/protocol['run']; freq=np.array(protocol['offsets_hz'])
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
case_checks=[]
def read(case):
    j=R/case; p=j/'result.json'
    if not p.exists(): return None
    r=json.loads(p.read_text())
    if not r.get('local_outputs_sha256'): return None
    assert r['ok'] and r['remote_inputs_match'] and not r.get('periodic_state')
    log=(j/'spectre.out').read_text()
    assert 'spectre completes with 0 errors' in log and not re.search(r'^\s*ERROR\s*\(',log,re.M)
    assert r['metadata']['returncode']==0
    if args.bank=='pulsetrip':
        assert 'The steady-state solution was achieved' in log
        assert r['inputs_sha256']['bank_pulsetrip_v14.scs']==protocol['bank_sha256']
        tb=H/'tb'/(case+'.scs');assert sha(tb)==protocol['tb_sha256'][case]
        def canonical(s):
            s=re.sub(r'writefinal="[^"]+"','writefinal="__FINAL_STATE__"',s)
            return re.sub(r'writepss="[^"]+"','writepss="__PERIODIC_STATE__"',s)
        assert canonical(tb.read_text())==canonical((j/'inputs'/tb.name).read_text())
    raw=j/(case+'.raw');td=parse(raw/'pss.td.pss');fd=parse(raw/'pss.fd.pss')
    t=td['time'];T=t[-1]-t[0];e=cross(t,td['out'])
    expected=dict(vp=24,clk=24,q1=12,data=6,out=6)
    if args.bank=='pulsetrip':expected.update({'acqclk':6,'XD.d8':3,'XD.d12':2})
    h={k:int(round(fd['freq'][1+np.argmax(abs(fd[k][1:]))]/164e6)) for k in expected}
    assert h==expected and len(e)==6 and abs(T*164e6-1)<1e-7
    assert max(abs(np.diff(np.r_[e,e[0]+T])*984e6-1))<.02
    endpoint=float(max(abs(td[k][-1]-td[k][0]) for k in h));assert endpoint<1e-3
    case_checks.append(dict(case=case,expected_harmonics=expected,actual_harmonics=h,endpoint_max_v=endpoint,
        simulator_returncode=r['metadata']['returncode'],simulator_zero_errors=True,pss_achieved='The steady-state solution was achieved' in log,
        wrapper_error_labels=r['errors'],log_sha256=sha(j/'spectre.out'),
        diagnostic_note='Wrapper error labels are retained. Acceptance uses actual completed Spectre log, periodic waveform and finite PSD checks; no source manifest is edited.'))
    return j,r,raw
def noise(p):
    d=parse(p); assert np.allclose(d['freq'],freq,rtol=1e-10,atol=0)
    assert header(p,'sample ratio factor')==6
    slope=header(p,'slew rate event_1'); dev=devices(p,len(freq)); sv=d['out']**2
    assert np.all(np.isfinite(sv)) and np.all(sv>0)
    assert slope>0 and max(abs(sum(dev.values())/sv-1))<1e-7
    return sv/slope**2,{k:v/slope**2 for k,v in dev.items()},slope
out=dict(scope=__doc__,offsets_hz=freq.tolist(),edge_rows=[],gate_rows=[],complete=False,passed=None,
         full_band_integral=False,full_pll_acceptance=False)
base=read(protocol['cases'][0])
if base:
    j,r,raw=base; deps={k:v for k,v in r['inputs_sha256'].items() if k!=j.name+'.scs'}
    out['source_result']=(j/'result.json').relative_to(ROOT).as_posix(); out['source_sha256']=sha(j/'result.json')
    ref,dev,_=noise(raw/'pnMedge1.0.sample.pnoise')
    for edge in range(1,7):
        st,_,slope=noise(raw/f'pnMedge{edge}.0.sample.pnoise')
        out['edge_rows'].append(dict(edge=edge,psd_s2_per_hz=st.tolist(),relative_to_edge1_db=(10*np.log10(st/ref)).tolist(),slew_v_per_s=slope,raw_noise_sha256=sha(raw/f'pnMedge{edge}.0.sample.pnoise')))
    spread=np.ptp(10*np.log10(np.array([x['psd_s2_per_hz'] for x in out['edge_rows']])),axis=0)
    out['edge_spread_db']=spread.tolist();out['edge_passed']=bool(max(spread)<protocol['edge_spread_limit_db'])
    if args.bank=='pulsetrip':
        probe=ROOT/protocol['source_probe_result'];assert sha(probe)==protocol['source_probe_sha256']
        pr=json.loads(probe.read_text());assert pr['ok'] and pr['remote_inputs_match'] and not pr.get('periodic_state')
        assert deps=={k:v for k,v in pr['inputs_sha256'].items() if k!=probe.parent.name+'.scs'}
        path=probe.parent/(probe.parent.name+'.raw')/'pnMedge.0.sample.pnoise';pn=parse(path)
        indices=[int(np.flatnonzero(np.isclose(pn['freq'],f,rtol=1e-10,atol=0))[0]) for f in freq]
        previous=pn['out'][indices]**2/header(path,'slew rate event_1')**2
        difference=10*np.log10(ref/previous)
        out['fresh_probe_repeat']=dict(source_result=protocol['source_probe_result'],source_sha256=sha(probe),raw_noise_sha256=sha(path),
            edge1_minus_probe_db=difference.tolist(),max_difference_db=float(max(abs(difference))),passed=bool(max(abs(difference))<.1))
        assert out['fresh_probe_repeat']['passed']
    for group,names in protocol['groups'].items():
        info=read(protocol.get('gate_cases',{}).get(group,f'chain_rt{factor}_fine_only_{group}_tt'))
        if info is None:continue
        gj,gr,graw=info
        assert deps=={k:v for k,v in gr['inputs_sha256'].items() if k!=gj.name+'.scs'}
        st,gdev,slope=noise(graw/'pnMedge.0.sample.pnoise')
        expect=sum(v for k,v in dev.items() if any(k.startswith(n+'.') for n in names))
        err=float(max(abs(st/expect-1)))
        excluded=float(max(np.asarray(sum(v for k,v in gdev.items() if not any(k.startswith(n+'.') for n in names)))/st))
        out['gate_rows'].append(dict(group=group,source_result=(gj/'result.json').relative_to(ROOT).as_posix(),source_sha256=sha(gj/'result.json'),
            timing_psd_s2_per_hz=st.tolist(),max_relative_difference=err,excluded_fraction=excluded,
            passed=bool(err<protocol['noise_gate_relative_limit'] and excluded<1e-8)))
    out['complete']=len(out['gate_rows'])==5
    if out['complete']:
        isolated_sum=np.sum([x['timing_psd_s2_per_hz'] for x in out['gate_rows']],axis=0)
        closure=float(max(abs(isolated_sum/ref-1)))
        out['isolated_sum_to_all_noise_ratio']=(isolated_sum/ref).tolist()
        out['isolated_sum_max_relative_error']=closure
        out['passed']=bool(out['edge_passed'] and all(x['passed'] for x in out['gate_rows']) and closure<protocol['noise_gate_relative_limit'])
out['periodic_case_checks']=case_checks
(H/f'results/{name}_validation.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k not in ['edge_rows','gate_rows']},indent=2))
