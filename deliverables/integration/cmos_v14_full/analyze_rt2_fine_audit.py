"""Audit fresh-PSS edge dependence and five independent device-noise gates."""
from pathlib import Path
import argparse,hashlib,json
import numpy as np
from noise_utils import parse,header,devices,cross
H=Path(__file__).resolve().parent; ROOT=H.parents[3]
parser=argparse.ArgumentParser()
parser.add_argument('--factor',type=int,choices=[2,4],default=2)
factor=parser.parse_args().factor
protocol=json.loads((H/f'results/rt{factor}_fine_audit_protocol.json').read_text())
R=ROOT/'research/runs/spectre_cmos_v14_full'/protocol['run']; freq=np.array(protocol['offsets_hz'])
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def read(case):
    j=R/case; p=j/'result.json'
    if not p.exists(): return None
    r=json.loads(p.read_text())
    if not r.get('local_outputs_sha256'): return None
    assert r['ok'] and r['remote_inputs_match'] and not r.get('periodic_state')
    assert 'spectre completes with 0 errors' in (j/'spectre.out').read_text()
    raw=j/(case+'.raw');td=parse(raw/'pss.td.pss');fd=parse(raw/'pss.fd.pss')
    t=td['time'];T=t[-1]-t[0];e=cross(t,td['out'])
    h={k:int(round(fd['freq'][1+np.argmax(abs(fd[k][1:]))]/164e6)) for k in ['vp','clk','q1','data','out']}
    assert h==dict(vp=24,clk=24,q1=12,data=6,out=6) and len(e)==6 and abs(T*164e6-1)<1e-7
    assert max(abs(np.diff(np.r_[e,e[0]+T])*984e6-1))<.02
    assert max(abs(td[k][-1]-td[k][0]) for k in h)<1e-3
    return j,r,raw
def noise(p):
    d=parse(p); assert np.allclose(d['freq'],freq,rtol=1e-10,atol=0)
    slope=header(p,'slew rate event_1'); dev=devices(p,len(freq)); sv=d['out']**2
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
        out['edge_rows'].append(dict(edge=edge,psd_s2_per_hz=st.tolist(),relative_to_edge1_db=(10*np.log10(st/ref)).tolist(),slew_v_per_s=slope))
    spread=np.ptp(10*np.log10(np.array([x['psd_s2_per_hz'] for x in out['edge_rows']])),axis=0)
    out['edge_spread_db']=spread.tolist();out['edge_passed']=bool(max(spread)<protocol['edge_spread_limit_db'])
    for group,names in protocol['groups'].items():
        info=read(f'chain_rt{factor}_fine_only_{group}_tt')
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
(H/f'results/rt{factor}_fine_audit_validation.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k not in ['edge_rows','gate_rows']},indent=2))
