"""Compare actual tail/input-pair settling at the unchanged diagnostic phase."""
from pathlib import Path
import hashlib,json,re
import numpy as np
from noise_utils import parse,cross
from analyze_frontend_gain import measurement
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
normal=lambda s:re.sub(r'\b(writefinal|writepss)="[^"]+"',r'\1="STATE"',s).strip()

def main():
    pp=H/'results/cp_fasttail_probe_protocol.json';p=json.loads(pp.read_text())
    j=ROOT/'research/runs/spectre_cmos_v14_full'/p['run']/p['case'];m=measurement(j,p['phase_deg'])
    out=dict(scope=__doc__,protocol_sha256=sha(pp),condition=p['condition'],periodic=m,
        operating_data_valid=False,measured_center_rebalanced=False,noise_measured=False,
        full_pll_acceptance=False,main_dut_modified=False,limitations=p['limitations'])
    if m.get('periodic_passed'):
        r=json.loads((j/'result.json').read_text());assert not r.get('periodic_state')
        assert {k:v for k,v in r['inputs_sha256'].items() if k!=j.name+'.scs'}==p['dependencies_sha256']
        src=H/'tb'/(p['source_case']+'.scs');assert sha(src)==p['source_tb_sha256']
        assert normal((j/'inputs'/(j.name+'.scs')).read_text())==normal(src.read_text().replace('cp_physical_v14','cp_fasttail_v14'))
        raw=j/(j.name+'.raw')/'pss.td.pss';d=parse(raw);t=d['time'];T=t[-1]-t[0]
        mean=lambda y:float(np.trapezoid(y,t)/T)
        gate=d['XCP.gate']>.6;rise=cross(t,d['XCP.gate']);fall=cross(t,-d['XCP.gate'],-.6)
        assert len(rise)==len(fall)==1
        pair=d['XCP.MIP:id']+d['XCP.MIN:id'];tail=d['XCP.MT:id'];qp=mean(pair)*T;qt=mean(tail)*T
        assert qp>0 and qt>0
        source=H/'results/cp_dynamic_timing_validation.json';assert sha(source)==p['dynamic_diagnosis_sha256'];base=json.loads(source.read_text())
        bp=H/'results/cp_terminal_balance_protocol.json';assert sha(bp)==p['terminal_protocol_sha256'];b=json.loads(bp.read_text())
        balances=[]
        for node,terms in b['kcl_nodes'].items():
            residual=sum(d[n] for n in terms);relative=mean(abs(residual))/sum(mean(abs(d[n])) for n in terms)
            balances.append(dict(node=node,relative_mean_absolute_residual=relative,passed=relative<b['diagnostic_limits']['relative_mean_absolute_kcl']))
        outside=1-mean(pair*gate)*T/qp
        out.update(operating_data_valid=True,td_sha256=sha(raw),node_balances=balances,
            terminal_balances_verified=all(x['passed'] for x in balances),
            gate_high_duration_ns=float((fall[0]-rise[0])*1e9),input_pair_resistive_charge_c=qp,
            input_pair_charge_outside_gate_high_fraction=outside,baseline_outside_fraction=base['input_pair_charge_outside_gate_high_fraction'],
            tail_resistive_charge_c=qt,tail_gate_high_charge_c=mean(tail*gate)*T,
            baseline_mean_clamp_current_a=json.loads((H/'results/frontend_operating_probe_validation.json').read_text())['periodic']['mean_clamp_current_a'],
            settling_improved=bool(outside<base['input_pair_charge_outside_gate_high_fraction']),
            samples=[dict(after_gate_rise_ns=s['after_gate_rise_ns'],values={n:float(np.interp(rise[0]+s['after_gate_rise_ns']*1e-9,t,d[n])) for n in s['values']}) for s in base['samples']])
    (H/'results/cp_fasttail_probe_validation.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k!='samples'},indent=2))

if __name__=='__main__':main()
