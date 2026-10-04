"""Verify actual CP node-current balances before assigning dynamic charge."""
from pathlib import Path
import hashlib,json,re
import numpy as np
from noise_utils import parse,cross
from analyze_frontend_gain import measurement
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
normal=lambda s:re.sub(r'\b(writefinal|writepss)="[^"]+"',r'\1="STATE"',s).strip()

def main():
    pp=H/'results/cp_terminal_balance_protocol.json';p=json.loads(pp.read_text())
    assert sha(H/'results'/p['source_validation'])==p['source_validation_sha256']
    j=ROOT/'research/runs/spectre_cmos_v14_full'/p['run']/p['case'];m=measurement(j,p['phase_deg'])
    out=dict(scope=__doc__,protocol_sha256=sha(pp),condition=p['condition'],periodic=m,
        terminal_balances_verified=False,main_dut_modified=False,noise_measured=False,full_pll_acceptance=False,limitations=p['limitations'])
    if m.get('periodic_passed'):
        rp=j/'result.json';r=json.loads(rp.read_text());src=ROOT/p['source_result'];assert sha(src)==p['source_result_sha256']
        old=json.loads(src.read_text());dep=lambda r,n:{k:v for k,v in r['inputs_sha256'].items() if k!=n+'.scs'}
        assert dep(r,j.name)==dep(old,src.parent.name) and not r.get('periodic_state')
        extra='\n// Observation-only terminal and charge balance probe.\nsave '+' '.join(p['extra_observations'])+'\n'
        body=(j/'inputs'/(j.name+'.scs')).read_text();assert body.count(extra)==1
        assert normal(body.replace(extra,''))==normal((src.parent/'inputs'/(p['source_case']+'.scs')).read_text())
        assert abs(m['mean_clamp_current_a']-json.loads((H/'results'/p['source_validation']).read_text())['periodic']['mean_clamp_current_a'])<p['diagnostic_limits']['max_mean_clamp_current_change_a']
        raw=j/(j.name+'.raw')/'pss.td.pss';d=parse(raw);assert set(p['extra_observations'])<=set(d)
        t=d['time'];T=t[-1]-t[0];mean=lambda y:float(np.trapezoid(y,t)/T)
        gate=d['XCP.gate']>.6;fall=cross(t,-d['XCP.gate'],-.6);assert len(fall)==1
        age=(t-fall[0])%T;masks=dict(gate_on=gate,gate_off=~gate,late_off=(~gate)&(age>=5e-9))
        nodes=[]
        for node,terms in p['kcl_nodes'].items():
            current=sum(d[n] for n in terms);scale=sum(mean(abs(d[n])) for n in terms);assert scale>0
            relative=mean(abs(current))/scale
            windows={}
            for label,mask in masks.items():
                z=mask.astype(float);windows[label]=dict(duration_s=mean(z)*T,
                    signed_terminal_charge_c={n:mean(d[n]*z)*T for n in terms},
                    signed_kcl_residual_c=mean(current*z)*T)
            nodes.append(dict(node=node,terminal_terms=terms,relative_mean_absolute_residual=relative,
                max_abs_residual_a=float(max(abs(current))),passed=relative<p['diagnostic_limits']['relative_mean_absolute_kcl'],windows=windows))
        # The hypotheses use separately labelled resistive and terminal current integrals.
        on=gate.astype(float);drain_terms=['XCP.MT','XCP.MIP','XCP.MIN']
        out.update(terminal_balances_verified=all(n['passed'] for n in nodes),node_balances=nodes,
            gate_high_resistive_drain_charge_c={n:mean(d[n+':id']*on)*T for n in drain_terms},
            gate_high_tail_terminal_charge_c={n:mean(d[n]*on)*T for n in p['kcl_nodes']['tail']},
            td_sha256=sha(raw),physical_observation_only_change_verified=True)
    (H/'results/cp_terminal_balance_validation.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2))

if __name__=='__main__':main()
