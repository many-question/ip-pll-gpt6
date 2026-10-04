"""Read controlled CP operating trials with verified gate-current branches."""
from pathlib import Path
import argparse,hashlib,json,re
import numpy as np
from analyze_frontend_gain import measurement
from noise_utils import stream_selected,cross
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
normal=lambda s:re.sub(r'\b(writefinal|writepss)="[^"]+"',r'\1="STATE"',s).strip()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--mid70',action='store_true');args=ap.parse_args()
    stem='cp_mid70_probe' if args.mid70 else 'cp_fasttail_branch'
    pp=H/'results'/(stem+'_protocol.json');p=json.loads(pp.read_text())
    j=ROOT/'research/runs/spectre_cmos_v14_full'/p['run']/p['case'];m=measurement(j,p['phase_deg'])
    out=dict(scope=__doc__,protocol_sha256=sha(pp),condition=p['condition'],physical_change=p['only_physical_change'],periodic=m,
        operating_data_valid=False,node_balances_verified=False,measured_center_rebalanced=False,
        main_dut_modified=False,noise_measured=False,full_pll_acceptance=False,limitations=p['limitations'])
    if m.get('periodic_passed'):
        r=json.loads((j/'result.json').read_text());assert not r.get('periodic_state')
        assert {k:v for k,v in r['inputs_sha256'].items() if k!=j.name+'.scs'}==p['dependencies_sha256']
        tb=H/'tb'/(j.name+'.scs');assert sha(tb)==p['tb_sha256'] and normal(tb.read_text())==normal((j/'inputs'/tb.name).read_text())
        bp=H/'results/cp_gate_branch_validation.json';assert sha(bp)==p['branch_validation_sha256'];bv=json.loads(bp.read_text())
        dp=H/'results/cp_dynamic_timing_validation.json';assert sha(dp)==p['dynamic_validation_sha256'];base=json.loads(dp.read_text())
        raw=j/(j.name+'.raw')/'pss.td.pss';cache=j/'cp_operating_trial_traces.npz'
        nodes={'tail':['XCP.MT:d','XCP.MIP:s','XCP.MIN:s'],
            'mirror':['XCP.MIN:d','XCP.MPD:d','XCP.MPD:g','XCP.MPO:g'],
            'tail_gate':['XCP.VTG:p','XCP.VOFF:p','XCP.VMT:p']}
        names=set(['XCP.gate','XCP.ng','XCP.ng_tg','XCP.ng_off','XCP.ng_mt','XCP.tail','XCP.mir','hp','hn','vmid','sp','sn','refb',
            'XCP.MT:id','XCP.MIP:id','XCP.MIN:id'])
        names.update(n for terms in nodes.values() for n in terms)
        if cache.exists():
            with np.load(cache) as z:
                assert str(z['source_sha256'])==sha(raw);d={n:z[n] for n in ['time']+sorted(names)}
        else:
            d,dups=stream_selected(raw,sorted(names));assert dups==0
            np.savez_compressed(cache,**d,source_sha256=sha(raw))
        t=d['time'];T=t[-1]-t[0];mean=lambda y:float(np.trapezoid(y,t)/T)
        rows=[]
        for node,terms in nodes.items():
            signed=[(-1 if node=='tail_gate' and n=='XCP.VTG:p' else 1)*d[n] for n in terms]
            rel=mean(abs(sum(signed)))/sum(mean(abs(x)) for x in signed)
            rows.append(dict(node=node,relative_mean_absolute_residual=rel,passed=rel<p['diagnostic_limits']['relative_mean_absolute_kcl']))
        voltage=max(float(max(abs(d[n]-d['XCP.ng']))) for n in ['XCP.ng_tg','XCP.ng_off','XCP.ng_mt'])
        gate=d['XCP.gate']>.6;rise=cross(t,d['XCP.gate']);fall=cross(t,-d['XCP.gate'],-.6);assert len(rise)==len(fall)==1
        pair=d['XCP.MIP:id']+d['XCP.MIN:id'];tail=d['XCP.MT:id'];qp=mean(pair)*T;qt=mean(tail)*T;assert qp>0 and qt>0
        outside=1-mean(pair*gate)*T/qp
        out.update(operating_data_valid=True,node_balances=rows,node_balances_verified=all(x['passed'] for x in rows),
            probe_voltage_max_v=voltage,probe_voltages_verified=voltage<p['diagnostic_limits']['max_probe_voltage_v'],
            gate_high_duration_ns=float((fall[0]-rise[0])*1e9),input_pair_resistive_charge_c=qp,
            input_pair_charge_outside_gate_high_fraction=outside,baseline_outside_fraction=base['input_pair_charge_outside_gate_high_fraction'],
            tail_resistive_charge_c=qt,tail_gate_high_charge_c=mean(tail*gate)*T,
            gate_high_gate_branch_charge_c=mean(d['XCP.VMT:p']*gate)*T,
            baseline_mean_clamp_current_a=bv['periodic']['mean_clamp_current_a'],
            settling_improved=bool(outside<base['input_pair_charge_outside_gate_high_fraction']),td_sha256=sha(raw),
            voltage_ranges_v={n:[float(min(d[n])),mean(d[n]),float(max(d[n]))] for n in ['vmid','sp','sn','hp','hn','XCP.tail']},
            samples=[dict(after_gate_rise_ns=s['after_gate_rise_ns'],values={n:float(np.interp(rise[0]+s['after_gate_rise_ns']*1e-9,t,d[n])) for n in s['values']}) for s in base['samples']])
    (H/'results'/(stem+'_validation.json')).write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k!='samples'},indent=2))

if __name__=='__main__':main()
