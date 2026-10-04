"""Check actual reset-node settling and guarded DFF functionality by corner."""
from pathlib import Path
import argparse,hashlib,json,re
import numpy as np
from noise_utils import parse,cross
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def transitions(t,v):return np.sort(np.r_[cross(t,v),cross(t,-v,-.6)])

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--quiet',action='store_true');a=ap.parse_args()
    label='reset_clear_quiet' if a.quiet else 'reset_clear_unit';pp=H/'results'/(label+'_protocol.json')
    if not pp.exists():print('Reset-clear unit protocol pending');return
    p=json.loads(pp.read_text());rows=[]
    for c in p['cases']:
        j=R/c['run']/c['case'];rp=j/'result.json';row=dict(case=c['case'],completed=False)
        if not rp.exists() or not json.loads(rp.read_text()).get('local_outputs_sha256'):rows.append(row);continue
        r=json.loads(rp.read_text());log=(j/'spectre.out').read_text()
        row.update(completed=True,source_result=rp.relative_to(ROOT).as_posix(),source_sha256=sha(rp),
                   simulation_passed=bool(r['ok'] and 'spectre completes with 0 errors' in log))
        if not row['simulation_passed']:rows.append(row);continue
        assert r['remote_inputs_match'] and all(sha(j/'inputs'/k)==v for k,v in r['inputs_sha256'].items())
        assert r['inputs_sha256']['reset_clear_cells_v14.scs']==p['candidate_sha256']
        for path,digest in p['original_sources_sha256'].items():assert r['inputs_sha256'][Path(path).name]==digest
        raw=j/(j.name+'.raw');traces=list(raw.glob('tran*.tran'));assert len(traces)==1
        tp=traces[0];d=parse(tp);t=d['time'];assert t[0]==0 and t[-1]>=40e-9*.999999
        clk=cross(t,d['clk']);reset_trans=transitions(t,d['reset']);data_trans=transitions(t,d['d'])
        interp=lambda n,x:np.interp(x,t,d[n]);samples=[]
        for edge in clk:
            sample=edge+p['sample_delay_s']
            if sample>=t[-1]:continue
            if interp('reset',sample)>.9:
                previous=reset_trans[reset_trans<sample];since=sample-(previous[-1] if len(previous) else 0)
                if since<p['engineering_reset_deadline_s']:continue
                expected=0
            else:
                if np.any((reset_trans>edge-p['input_guard_s'])&(reset_trans<sample)):continue
                if len(data_trans) and min(abs(data_trans-edge))<p['input_guard_s']:continue
                expected=int(interp('d',edge)>.6)
            vo=float(interp('qo',sample));vn=float(interp('qn',sample));good=lambda v:v>.9 if expected else v<.3
            samples.append(dict(edge_s=float(edge),sample_s=float(sample),expected=expected,old_v=vo,new_v=vn,old_passed=bool(good(vo)),new_passed=bool(good(vn))))
        assert len(samples)>=20
        mask=(t>=1e-9)&(t<=2e-9)
        stack={variant:{stage:dict(mean_v=float(np.trapezoid(d[f'X{variant}.{stage}.XN.x'][mask],t[mask])/(t[mask][-1]-t[mask][0])),peak_abs_v=float(max(abs(d[f'X{variant}.{stage}.XN.x'][mask])))) for stage in ['XM','XS']} for variant in ['OLD','NEW']}
        reset_mask=d['reset']>.9
        for change in np.r_[0,reset_trans]:reset_mask &= ~((t>=change)&(t<change+p['engineering_reset_deadline_s']))
        qreset={n:float(max(abs(d[n][reset_mask]))) for n in ['qo','qn']}
        checks=dict(original_guarded_function=all(x['old_passed'] for x in samples),candidate_guarded_function=all(x['new_passed'] for x in samples),
                    reset_outputs_low=max(qreset.values())<.3,
                    candidate_stack_cleared=all(x['peak_abs_v']<p['engineering_stack_clear_limit_v'] for x in stack['NEW'].values()))
        row.update(corner=c['corner'],temperature_c=c['temp_c'],td_sha256=sha(tp),guarded_samples=samples,
                   initial_reset_stack_nodes=stack,reset_output_peak_abs_v=qreset,checks=checks,passed=bool(all(checks.values())))
        rows.append(row)
    out=dict(scope=__doc__,protocol_sha256=sha(pp),condition=p['condition'],cases=rows,complete=all(x['completed'] for x in rows),
             passed=all(x.get('passed',False) for x in rows),main_dut_modified=False,whole_core_pss_cause_identified=False,
             full_pll_acceptance=False,limitations=p['limitations'])
    (H/'results'/(label+'_validation.json')).write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({**{k:v for k,v in out.items() if k!='cases'},'cases':[{k:v for k,v in x.items() if k!='guarded_samples'} for x in rows]},indent=2))

if __name__=='__main__':main()
