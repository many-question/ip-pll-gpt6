"""Cross-check reported MOS port currents with independent zero-volt branches.

The initial gate-node sum failed 1e-3 while tail/mirror sums passed. Preserve
that result and measure which saved terminal quantity differs from a branch.
"""
from pathlib import Path
import datetime,hashlib,json
H=Path(__file__).resolve().parent;ROOT=H.parents[3];B=H.parents[1]/'blocks/cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    dst=H/'results/cp_gate_branch_protocol.json';assert not dst.exists()
    vp=H/'results/cp_terminal_balance_validation.json';v=json.loads(vp.read_text())
    assert v['periodic']['periodic_passed'] and not v['terminal_balances_verified']
    assert [x['passed'] for x in v['node_balances']]==[True,True,False]
    pp=H/'results/cp_terminal_balance_protocol.json';p=json.loads(pp.read_text());assert sha(pp)==v['protocol_sha256']
    original=B/'cp_physical_v14.scs';block=B/'cp_gate_probe_v14.scs';assert not block.exists()
    s=original.read_text()
    changes={'XT (nb ng gate gateb':'XT (nb ng_tg gate gateb',
             'MOFF (ng gateb':'MOFF (ng_off gateb',
             'MT (tail ng vss':'MT (tail ng_mt vss'}
    for old,new in changes.items():assert s.count(old)==1;s=s.replace(old,new)
    s=s.replace('cp_physical_v14','cp_gate_probe_v14').replace('ends cp_gate_probe_v14',
        'VTG (ng_tg ng) vsource dc=0\nVOFF (ng ng_off) vsource dc=0\nVMT (ng ng_mt) vsource dc=0\nends cp_gate_probe_v14')
    block.write_text(s,encoding='utf-8',newline='\n')
    src=H/'tb'/(p['case']+'.scs');assert sha(src)==p['tb_sha256']
    case='cp_gate_branch_tt';tb=H/'tb'/(case+'.scs');assert not tb.exists()
    extra=['XCP.VTG:p','XCP.VOFF:p','XCP.VMT:p','XCP.ng_tg','XCP.ng_off','XCP.ng_mt']
    tb.write_text(src.read_text().replace('cp_physical_v14','cp_gate_probe_v14')+'\nsave '+' '.join(extra)+'\n',encoding='utf-8',newline='\n')
    rp=ROOT/v['periodic']['source_result'];assert sha(rp)==v['periodic']['source_sha256']
    deps=json.loads(rp.read_text())['inputs_sha256'].copy();deps.pop(p['case']+'.scs')
    assert deps.pop(original.name)==sha(original);deps[block.name]=sha(block)
    out=dict(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),run='cpgatebranch01',case=case,
        phase_deg=p['phase_deg'],condition=p['condition'],tb_sha256=sha(tb),block_sha256=sha(block),
        baseline_block_sha256=sha(original),dependencies_sha256=deps,prior_validation_sha256=sha(vp),
        baseline_tb_sha256=sha(src),baseline_case=p['case'],extra_observations=extra,
        diagnostic_limits=dict(relative_mean_absolute_kcl=1e-3,max_probe_voltage_v=1e-8,max_clamp_current_change_a=1e-10),
        launch_scope='One fresh PSS,1thread,1200s guard, verified free long slot.',
        no_physical_MOS_geometry_or_excitation_change=True,main_dut_modified=False,noise_measured=False,full_pll_acceptance=False,
        limitations=['Three zero-volt current probes add simulator unknowns; verify unchanged operating point before interpreting them.',
            'A branch/port disagreement is a measurement/model diagnostic, not evidence that physical KCL is violated.',
            'No gate-current correction or sign reversal may be selected simply to minimize the residual.'])
    dst.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(dict(run=out['run'],case=case),indent=2))

if __name__=='__main__':main()
