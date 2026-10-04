"""Compare independent zero-volt branch currents with saved CP MOS terminals."""
from pathlib import Path
import hashlib,json,re
import numpy as np
from analyze_frontend_gain import measurement
from noise_utils import stream_selected
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
normal=lambda s:re.sub(r'\b(writefinal|writepss)="[^"]+"',r'\1="STATE"',s).strip()

def main():
    pp=H/'results/cp_gate_branch_protocol.json';p=json.loads(pp.read_text())
    j=ROOT/'research/runs/spectre_cmos_v14_full'/p['run']/p['case'];m=measurement(j,p['phase_deg'])
    out=dict(scope=__doc__,protocol_sha256=sha(pp),condition=p['condition'],periodic=m,
        branch_kcl_verified=False,operating_point_unchanged=False,terminal_reporting_consistent=False,
        main_dut_modified=False,noise_measured=False,full_pll_acceptance=False,limitations=p['limitations'])
    if m.get('periodic_passed'):
        r=json.loads((j/'result.json').read_text());assert not r.get('periodic_state')
        assert {k:v for k,v in r['inputs_sha256'].items() if k!=j.name+'.scs'}==p['dependencies_sha256']
        tb=H/'tb'/(j.name+'.scs');assert sha(tb)==p['tb_sha256']
        assert normal((j/'inputs'/tb.name).read_text())==normal(tb.read_text())
        vp=H/'results/cp_terminal_balance_validation.json';assert sha(vp)==p['prior_validation_sha256'];v=json.loads(vp.read_text())
        raw=j/(j.name+'.raw')/'pss.td.pss';cache=j/'branch_probe_traces.npz'
        physical_nodes=['ref','refb','vp','vn','sp','sn','hp','hn','vmid','pulse','out','amp_good','phase_good',
            'XCP.ng','XCP.nb','XCP.tail','XCP.mir','XCP.gate','XCP.gateb']
        names=list(dict.fromkeys(['XCP.ng','XCP.XT.MN:s','XCP.XT.MP:s','XCP.MOFF:d','XCP.MT:g']+p['extra_observations']+physical_nodes))
        if cache.exists():
            with np.load(cache) as z:
                assert str(z['source_sha256'])==sha(raw);d={n:z[n] for n in ['time']+names}
        else:
            d,dups=stream_selected(raw,names);assert dups==0
            np.savez_compressed(cache,**d,source_sha256=sha(raw))
        t=d['time'];T=t[-1]-t[0];mean=lambda y:float(np.trapezoid(y,t)/T)
        a=-d['XCP.VTG:p'];b=d['XCP.VOFF:p'];c=d['XCP.VMT:p']
        rel=mean(abs(a+b+c))/(mean(abs(a))+mean(abs(b))+mean(abs(c)))
        voltage=max(float(max(abs(d[n]-d['XCP.ng']))) for n in ['XCP.ng_tg','XCP.ng_off','XCP.ng_mt'])
        change=m['mean_clamp_current_a']-v['periodic']['mean_clamp_current_a']
        source=ROOT/v['periodic']['source_result'];assert sha(source)==v['periodic']['source_sha256']
        base_raw=source.parent/(source.parent.name+'.raw')/'pss.td.pss';assert sha(base_raw)==v['td_sha256']
        original,dups=stream_selected(base_raw,physical_nodes);assert dups==0
        assert t[0]==original['time'][0] and t[-1]==original['time'][-1]
        differences={n:float(max(abs(d[n]-np.interp(t,original['time'],original[n])))) for n in physical_nodes}
        ports=dict(tg=d['XCP.XT.MN:s']+d['XCP.XT.MP:s'],off=d['XCP.MOFF:d'],tail_gate=d['XCP.MT:g'])
        branches=dict(tg=a,off=b,tail_gate=c);rows=[]
        for name in ports:
            x,y=ports[name],branches[name];scale=mean(abs(x))+mean(abs(y));err=mean(abs(x-y))/scale
            rows.append(dict(branch=name,relative_mean_absolute_difference=err,mean_signed_difference_a=mean(x-y),
                max_absolute_difference_a=float(max(abs(x-y))),passed=err<p['diagnostic_limits']['relative_mean_absolute_kcl']))
        out.update(branch_kcl_relative_mean_absolute_residual=rel,
            branch_kcl_verified=rel<p['diagnostic_limits']['relative_mean_absolute_kcl'],
            maximum_probe_voltage_v=voltage,clamp_current_change_a=change,
            operating_point_unchanged=voltage<p['diagnostic_limits']['max_probe_voltage_v'] and abs(change)<p['diagnostic_limits']['max_clamp_current_change_a'],
            terminal_reporting_consistent=all(x['passed'] for x in rows),branch_port_comparison=rows,td_sha256=sha(raw),
            physical_waveform_max_abs_changes_v=differences,
            waveform_comparison_note='Additional diagnostic comparison, not a retrospective relaxation of any protocol gate.')
    (H/'results/cp_gate_branch_validation.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))

if __name__=='__main__':main()
