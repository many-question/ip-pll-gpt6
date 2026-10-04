"""Verify expected bus counts after gated pauses, including 14-bit carry/wrap."""
from pathlib import Path
import hashlib,json
import numpy as np
from noise_utils import parse
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    pp=H/'results/reset_clear_counter_protocol.json'
    if not pp.exists():print('Reset-clear counter protocol pending');return
    p=json.loads(pp.read_text());rows=[]
    for c in p['cases']:
        j=R/c['run']/c['case'];rp=j/'result.json';row=dict(case=c['case'],completed=False)
        if not rp.exists() or not json.loads(rp.read_text()).get('local_outputs_sha256'):rows.append(row);continue
        r=json.loads(rp.read_text());log=(j/'spectre.out').read_text()
        row.update(completed=True,source_result=rp.relative_to(ROOT).as_posix(),source_sha256=sha(rp),
                   simulation_passed=bool(r['ok'] and 'spectre completes with 0 errors' in log))
        if not row['simulation_passed']:rows.append(row);continue
        assert r['remote_inputs_match'] and all(sha(j/'inputs'/k)==v for k,v in r['inputs_sha256'].items())
        for k,v in p['dependencies_sha256'].items():assert r['inputs_sha256'][k]==v
        traces=list((j/(j.name+'.raw')).glob('tran*.tran'));assert len(traces)==1;tp=traces[0];d=parse(tp);t=d['time']
        assert t[-1]>=p['stop_s']-2.1e-9
        checks=[]
        for spec in p['checks']:
            when=spec['time_s'];interp=lambda name:float(np.interp(when,t,d[name]));item=dict(spec)
            item.update(gate_v=interp('gate'),reset_v=interp('reset'));assert item['gate_v']<.3
            assert item['reset_v']>.9 if spec.get('reset_check') else item['reset_v']<.3
            for label,prefix in [('original','o'),('candidate','n')]:
                bits=[interp(prefix+str(i)) for i in range(14)];rail=all(v<.3 or v>.9 for v in bits)
                count=sum((int(v>.6)<<i) for i,v in enumerate(bits))
                item[label]=dict(count=count,rail_valid=rail,passed=bool(rail and count==spec['expected']))
            checks.append(item)
        mask=(t>=4e-9)&(t<=8e-9);assert sum(mask)>=3
        stack={variant:max(float(max(abs(d[f'X{variant}.XF{i}.XF.XS.XN.x'][mask]))) for i in range(14)) for variant in ['O','N']}
        row.update(corner=c['corner'],temperature_c=c['temp_c'],td_sha256=sha(tp),count_checks=checks,
                   sampled_initial_reset_slave_stack_max_v=stack,
                   passed=all(x['original']['passed'] and x['candidate']['passed'] for x in checks))
        rows.append(row)
    out=dict(scope=__doc__,protocol_sha256=sha(pp),condition=p['condition'],cases=rows,complete=all(x['completed'] for x in rows),
             passed=all(x.get('passed',False) for x in rows),main_dut_modified=False,noise_measured=False,full_pll_acceptance=False,limitations=p['limitations'])
    (H/'results/reset_clear_counter_validation.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({**{k:v for k,v in out.items() if k!='cases'},'cases':[{k:v for k,v in x.items() if k!='count_checks'} for x in rows]},indent=2))

if __name__=='__main__':main()
