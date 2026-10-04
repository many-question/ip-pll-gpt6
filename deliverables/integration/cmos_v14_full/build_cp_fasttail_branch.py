"""Test reduced tail-MOS loading using the independently verified branch probes."""
from pathlib import Path
import datetime,hashlib,json
H=Path(__file__).resolve().parent;ROOT=H.parents[3];B=H.parents[1]/'blocks/cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    dst=H/'results/cp_fasttail_branch_protocol.json';assert not dst.exists()
    vp=H/'results/cp_gate_branch_validation.json';v=json.loads(vp.read_text())
    assert v['branch_kcl_verified'] and v['operating_point_unchanged'] and v['periodic']['periodic_passed']
    assert max(v['physical_waveform_max_abs_changes_v'].values())<1e-6
    pp=H/'results/cp_gate_branch_protocol.json';p=json.loads(pp.read_text());assert sha(pp)==v['protocol_sha256']
    original=B/'cp_gate_probe_v14.scs';block=B/'cp_fasttail_probe_v14.scs';assert not block.exists() and sha(original)==p['block_sha256']
    old='MT (tail ng_mt vss vss) nch w=10u l=1u ad=2.4p as=2.4p pd=20.48u ps=20.48u'
    new='MT (tail ng_mt vss vss) nch w=1.8u l=180n ad=.432p as=.432p pd=4.08u ps=4.08u'
    s=original.read_text();assert s.count(old)==1
    block.write_text(s.replace(old,new).replace('cp_gate_probe_v14','cp_fasttail_probe_v14'),encoding='utf-8',newline='\n')
    case='cp_fasttail_branch_tt';tb=H/'tb'/(case+'.scs');assert not tb.exists()
    src=H/'tb'/(p['case']+'.scs');assert sha(src)==p['tb_sha256']
    tb.write_text(src.read_text().replace('cp_gate_probe_v14','cp_fasttail_probe_v14'),encoding='utf-8',newline='\n')
    deps=p['dependencies_sha256'].copy();assert deps.pop(original.name)==sha(original);deps[block.name]=sha(block)
    dyn=H/'results/cp_dynamic_timing_validation.json'
    out=dict(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),run='cpfasttailbranch01',case=case,
        phase_deg=p['phase_deg'],condition=p['condition'],tb_sha256=sha(tb),block_sha256=sha(block),
        dependencies_sha256=deps,baseline_block_sha256=sha(original),baseline_tb_sha256=sha(src),baseline_case=p['case'],
        branch_validation_sha256=sha(vp),dynamic_validation_sha256=sha(dyn),
        only_physical_change='Tail MT 10um/1um -> 1.8um/0.18um, same nominal W/L; preserve the same three zero-volt branch probes.',
        diagnostic_limits=dict(relative_mean_absolute_kcl=1e-3,max_probe_voltage_v=1e-8),
        launch_scope='One fresh PSS,1thread,1200s guard, verified free long slot. No balance or noise claim.',
        old_direct_port_failure_preserved=True,main_dut_modified=False,noise_measured=False,full_pll_acceptance=False,
        limitations=['The original unprobed fasttail trial remains unlaunched; this is a separate controlled pair with verified measurement branches.',
            'TG/MOFF reported MOS currents disagreed with independent branch currents in the baseline. Gate KCL must use the branches, without changing signs to fit.',
            'The exact simulator/model-internal reason for the terminal-report disagreement is not established.',
            'Equal nominal W/L does not guarantee equal current, output resistance, noise, mismatch or PVT.',
            'This same-phase operating trial is not rebalanced; improved settling must be followed by actual gain, balance and device-noise measurements.'])
    dst.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(dict(run=out['run'],case=case),indent=2))

if __name__=='__main__':main()
