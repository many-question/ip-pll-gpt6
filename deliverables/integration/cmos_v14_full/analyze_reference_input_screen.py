"""Validate finite-input reference transients; no noise/jitter inference."""
from pathlib import Path
import hashlib,json,re
import numpy as np
from noise_utils import parse,cross
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
normal=lambda s:re.sub(r'\bwritefinal="[^"]+"','writefinal="STATE"',s).strip()

def transitions(t,y):
    r=[cross(t,y,v) for v in [.12,.6,1.08]]
    f=[cross(t,-y,-v) for v in [1.08,.6,.12]]
    assert all(len(x)==3 for x in r+f),[len(x) for x in r+f]
    return dict(rise_10_90_ps=float(np.mean(r[2]-r[0])*1e12),fall_90_10_ps=float(np.mean(f[2]-f[0])*1e12)),r[1],f[1]

def main():
    pp=H/'results/reference_input_screen_protocol.json';p=json.loads(pp.read_text());rows=[]
    for c in p['cases']:
        j=ROOT/'research/runs/spectre_cmos_v14_full'/c['run']/c['case'];rp=j/'result.json'
        item=dict(case=c['case'],precision=c['precision'],completed=False)
        if not rp.exists() or not json.loads(rp.read_text()).get('local_outputs_sha256'):rows.append(item);continue
        r=json.loads(rp.read_text());log=(j/'spectre.out').read_text()
        item.update(completed=True,source_result=rp.relative_to(ROOT).as_posix(),source_sha256=sha(rp),simulator_passed=bool(r['ok'] and 'spectre completes with 0 errors' in log))
        if item['simulator_passed']:
            assert r['remote_inputs_match'] and not r.get('periodic_state')
            assert {k:v for k,v in r['inputs_sha256'].items() if k!=c['case']+'.scs'}==p['dependencies_sha256']
            tb=H/'tb'/(c['case']+'.scs');assert sha(tb)==c['tb_sha256']
            assert normal((j/'inputs'/tb.name).read_text())==normal(tb.read_text())
            # run_spectre names this analysis tran.tran; Spectre appends .tran.
            raw=j/(j.name+'.raw')/'tran.tran.tran';assert raw.is_file()
            # The runner already parsed the complete 0.8--1.6 GB ASCII source.
            # Verify its saved cache, rather than parsing it a second time.
            cache=j/'waveforms.npz';assert sha(cache)==r['local_outputs_sha256']['waveforms.npz']
            with np.load(cache) as z:d={k:z[k] for k in z.files}
            t=d['time'];assert len(t)==r['signals']['time'] and np.all(np.diff(t)>0)
            keep=(t>=p['measurement_window_s'][0])&(t<=p['measurement_window_s'][1]);t=t[keep]
            assert t[0]<=375.01e-9 and t[-1]>=499.99e-9 and max(np.diff(t))<=c['maxstep_ps']*1e-12*1.001
            branches=[]
            for b in p['branches']:
                src=d[b['source_node']][keep];inp=d[b['input_node']][keep];out=d[b['output_node']][keep]
                sm,sr,sf=transitions(t,src);im,ir,iff=transitions(t,inp);om,orr,of=transitions(t,out)
                assert min(out)<.2 and max(out)>1.0
                assert abs(sm['rise_10_90_ps']/b['source_10_90_ps']-1)<.01
                branches.append(dict(b,source=sm,input=im,output=om,source_to_output_rise_delay_ps=float(np.mean(orr-sr)*1e12),
                    source_to_output_fall_delay_ps=float(np.mean(of-sf)*1e12),input_to_output_rise_delay_ps=float(np.mean(orr-ir)*1e12),
                    output_range_v=[float(min(out)),float(max(out))],input_range_v=[float(min(inp)),float(max(inp))],functional_passed=True))
            item.update(functional_passed=True,branches=branches,raw_sha256=sha(raw))
        rows.append(item)
    out=dict(scope=__doc__,protocol_sha256=sha(pp),condition=p['condition'],cases=rows,
             complete=all(x['completed'] for x in rows),functional_all_passed=all(x.get('functional_passed',False) for x in rows),
             precision_verified=False,input_requirements_confirmed=False,noise_measured=False,full_pll_acceptance=False)
    if out['functional_all_passed']:
        comparison=[]
        for a,b in zip(rows[0]['branches'],rows[1]['branches']):
            assert a['tag']==b['tag']
            delay=max(abs(b[k]-a[k]) for k in ['source_to_output_rise_delay_ps','source_to_output_fall_delay_ps','input_to_output_rise_delay_ps'])
            edge=max(abs(b[n][k]/a[n][k]-1) for n in ['input','output'] for k in ['rise_10_90_ps','fall_90_10_ps'])
            comparison.append(dict(tag=a['tag'],max_abs_delay_change_ps=delay,max_relative_transition_change=edge,
                passed=delay<p['numerical_limits']['max_abs_delay_change_ps'] and edge<p['numerical_limits']['max_relative_transition_change']))
        out.update(precision=comparison,precision_verified=all(x['passed'] for x in comparison))
    (H/'results/reference_input_screen_validation.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k!='cases'},indent=2))

if __name__=='__main__':main()
