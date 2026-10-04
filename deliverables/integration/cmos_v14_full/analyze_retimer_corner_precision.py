"""Check full-band SS60/FF0 RT4 noise against independently refined simulations."""
from pathlib import Path
import hashlib,json,re
import numpy as np
from noise_utils import parse,header,devices,cross
from analyze_vco_bias_band import integral
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
normal=lambda s:re.sub(r'\b(writefinal|writepss)="[^"]+"',r'\1="STATE"',s)

def measure(j):
    raw=j/(j.name+'.raw');td=parse(raw/'pss.td.pss');fd=parse(raw/'pss.fd.pss');t=td['time']
    assert abs((t[-1]-t[0])*984e6-1)<1e-7
    nodes=['out','XR.qb','XR.ob','XR.XFF.a','XR.XFF.b']
    endpoint=max(float(abs(td[n][-1]-td[n][0])) for n in nodes)
    rails=np.quantile(td['out'],[.1,.9]);edges=len(cross(t,td['out']));clocks=len(cross(t,td['clk']))
    harmonic=int(1+np.argmax(abs(fd['out'][1:])))
    assert edges==1 and clocks==4 and harmonic==1 and endpoint<1e-3 and rails[0]<.2 and rails[1]>1
    path=raw/'pnMedge.0.sample.pnoise';pn=parse(path);f=pn['freq'];sv=pn['out']**2
    slew=header(path,'slew rate event_1');assert slew>0 and header(path,'sample ratio factor')==1
    assert len(f)>=90 and abs(f[0]/1e4-1)<1e-9 and abs(f[-1]/492e6-1)<1e-9
    assert np.all(np.diff(f)>0) and np.all(np.isfinite(sv)) and np.all(sv>0)
    dev=devices(path,len(f));closure=float(max(abs(sum(dev.values())/sv-1)));assert closure<1e-7
    st=sv/slew**2;groups={k:np.zeros(len(f)) for k in ['retimer_ff','first_buffer','last_buffer']}
    for name,value in dev.items():
        group='retimer_ff' if name.startswith('XR.XFF.') else 'first_buffer' if name.startswith('XR.X0.') else 'last_buffer' if name.startswith('XR.X1.') else None
        assert group,name
        groups[group]+=value/slew**2
    variance=integral(f,st,1e4,492e6);parts={k:integral(f,x,1e4,492e6) for k,x in groups.items()}
    assert abs(sum(parts.values())/variance-1)<1e-7
    return dict(rms_fs=float(np.sqrt(variance)*1e15),frequency_points=len(f),slew_v_per_s=slew,
                endpoint_peak_v=endpoint,rails_v=rails.tolist(),output_edges=edges,clock_edges=clocks,
                group_rms_fs={k:float(np.sqrt(v)*1e15) for k,v in parts.items()},device_sum_relative_error=closure,
                noise_sha256=sha(path),td_sha256=sha(raw/'pss.td.pss'),fd_sha256=sha(raw/'pss.fd.pss')),f,st

def main():
    pp=H/'results/retimer_corner_precision_protocol.json';p=json.loads(pp.read_text())
    proof=H/'results'/p['source_validation'];assert sha(proof)==p['source_validation_sha256']
    old={x['corner']:x for x in json.loads(proof.read_text())['cases']};rows=[]
    for c in p['cases']:
        j=R/c['run']/c['case'];rp=j/'result.json';row=dict(case=c['case'],corner=c['corner'],completed=False)
        if not rp.exists() or not json.loads(rp.read_text()).get('local_outputs_sha256'):rows.append(row);continue
        r=json.loads(rp.read_text());log=(j/'spectre.out').read_text()
        row.update(completed=True,source_result=rp.relative_to(ROOT).as_posix(),source_sha256=sha(rp),
                   simulator_passed=bool(r['ok'] and 'spectre completes with 0 errors' in log and 'The steady-state solution was achieved' in log))
        if row['simulator_passed']:
            assert r['remote_inputs_match'] and not r.get('periodic_state')
            assert all(sha(j/'inputs'/k)==v for k,v in r['inputs_sha256'].items())
            assert c['physical_dependencies_sha256']=={k:v for k,v in r['inputs_sha256'].items() if k!=j.name+'.scs'}
            src=(ROOT/c['source_result']).parent;assert sha(src/'result.json')==c['source_sha256']
            body=(j/'inputs'/(j.name+'.scs')).read_text()
            for before,after in p['numerical_changes'].items():
                assert body.count(after)==1
                body=body.replace(after,before)
            assert normal(body)==normal((src/'inputs'/(src.name+'.scs')).read_text())
            assert re.search(r'maxstep\s*=\s*125 fs',log)
            baseline,f0,s0=measure(src);candidate,f1,s1=measure(j)
            assert baseline['noise_sha256']==old[c['corner']]['noise_sha256']
            assert abs(baseline['rms_fs']/old[c['corner']]['integrated_jitter_fs']-1)<1e-12
            assert np.array_equal(f0,f1)
            delta=10*np.log10(s1/s0);relative=candidate['rms_fs']/baseline['rms_fs']-1
            checks=dict(psd=bool(max(abs(delta))<p['precision_limits']['max_psd_change_db']),
                        rms=bool(abs(relative)<p['precision_limits']['max_relative_rms_change']))
            row.update(baseline=baseline,candidate=candidate,offsets_hz=f1.tolist(),psd_change_db=delta.tolist(),
                       max_absolute_psd_change_db=float(max(abs(delta))),relative_rms_change=relative,
                       checks=checks,passed=all(checks.values()),physical_comparison_verified=True)
        rows.append(row)
    out=dict(scope=__doc__,condition=p['condition'],protocol_sha256=sha(pp),cases=rows,
             complete=all(x['completed'] for x in rows),passed=all(x.get('passed',False) for x in rows),
             main_dut_modified=False,full_pll_acceptance=False,full_pll_jitter_fs=None,limitations=p['limitations'])
    (H/'results/retimer_corner_precision_validation.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({**{k:v for k,v in out.items() if k!='cases'},'cases':[{k:v for k,v in x.items() if k not in ['offsets_hz','psd_change_db']} for x in rows]},indent=2))

if __name__=='__main__':main()
