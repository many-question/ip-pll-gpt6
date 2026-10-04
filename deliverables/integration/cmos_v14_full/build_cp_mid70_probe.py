"""Isolate CP input headroom by shifting only the resistive sampler midpoint.

Use the original tail MOS and the already verified measurement branches.
The nominal midpoint moves from 0.60 to 0.70 V at 1.2 V, while the divider's
Thevenin resistance and bypass capacitance remain 50 kohm and 10 pF.
"""
from pathlib import Path
import datetime,hashlib,json
H=Path(__file__).resolve().parent;ROOT=H.parents[3];B=H.parents[1]/'blocks/cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    dst=H/'results/cp_mid70_probe_protocol.json';assert not dst.exists()
    vp=H/'results/cp_gate_branch_validation.json';v=json.loads(vp.read_text())
    assert v['branch_kcl_verified'] and v['operating_point_unchanged'] and v['periodic']['periodic_passed']
    pp=H/'results/cp_gate_branch_protocol.json';p=json.loads(pp.read_text());assert sha(pp)==v['protocol_sha256']
    rp=ROOT/v['periodic']['source_result'];assert sha(rp)==v['periodic']['source_sha256']
    original=rp.parent/'inputs/sampler_bias_v5.scs';assert sha(original)==p['dependencies_sha256'][original.name]
    block=B/'sampler_bias_mid70_v14.scs';assert not block.exists()
    block.write_text('''simulator lang=spectre
// Diagnostic headroom candidate. Same nominal Thevenin R and bypass C as baseline.
subckt sampler_bias_mid70_v14 (vdd vss vmid)
parameters rtop=85714.28571428571 rbot=120000 cmid=10p
R0 (vdd vmid) resistor r=rtop
R1 (vmid vss) resistor r=rbot
C0 (vmid vss) capacitor c=cmid
ends sampler_bias_mid70_v14
''',encoding='utf-8',newline='\n')
    src=H/'tb'/(p['case']+'.scs');assert sha(src)==p['tb_sha256']
    s=src.read_text();assert s.count('include "sampler_bias_v5.scs"')==1 and s.count('tx_bias_mid_v5')==1
    s=s.replace('include "sampler_bias_v5.scs"','include "sampler_bias_mid70_v14.scs"').replace('tx_bias_mid_v5','sampler_bias_mid70_v14')
    case='cp_mid70_operating_tt';tb=H/'tb'/(case+'.scs');assert not tb.exists();tb.write_text(s,encoding='utf-8',newline='\n')
    deps=p['dependencies_sha256'].copy();deps.pop(original.name);deps[block.name]=sha(block)
    out=dict(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),run='cpmid70probe01',case=case,
        phase_deg=p['phase_deg'],condition=p['condition'],tb_sha256=sha(tb),block_sha256=sha(block),dependencies_sha256=deps,
        baseline_block_sha256=sha(original),baseline_tb_sha256=sha(src),baseline_case=p['case'],
        branch_validation_sha256=sha(vp),dynamic_validation_sha256=sha(H/'results/cp_dynamic_timing_validation.json'),
        only_physical_change='Sampler bias resistor pair:100k/100k ->85.7142857k/120k. Original tail10um/1um and same three zero-volt probes.',
        predicted_nominal_midpoint_v=.7,nominal_thevenin_resistance_ohm=50000,bypass_capacitance_f=10e-12,
        diagnostic_limits=dict(relative_mean_absolute_kcl=1e-3,max_probe_voltage_v=1e-8),
        launch_scope='One fresh PSS,1thread,1200s guard, only after actual resource slot is free.',
        main_dut_modified=False,noise_measured=False,full_pll_acceptance=False,
        limitations=['0.70V is the unloaded divider prediction, not the measured sampled voltage or a changed project requirement.',
            'RF coupling, sampler loading, reference sensitivity, CP gain, balance and noise all require measurement after this change.',
            'The same-phase operating trial cannot be treated as a balanced noise comparison.',
            'The original fasttail change is not included; this isolates midpoint/headroom from tail geometry.',
            'No extrapolation to full PVT, voltage margin, full PLL or PEX.'])
    dst.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(dict(run=out['run'],case=case,launched=False),indent=2))

if __name__=='__main__':main()
