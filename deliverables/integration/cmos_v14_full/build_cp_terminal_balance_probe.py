"""Instrument actual CP terminal currents to test the dynamic-storage hypothesis.

No physical device, forcing waveform or solver setting changes. Fresh PSS
must be accepted before node-current balances and gate-window charge are read.
"""
from pathlib import Path
import datetime,hashlib,json
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    dest=H/'results/cp_terminal_balance_protocol.json';assert not dest.exists()
    proof=H/'results/frontend_operating_probe_validation.json';v=json.loads(proof.read_text())
    assert v['operating_data_valid'] and v['balanced'] and v['periodic']['periodic_passed']
    pp=H/'results/frontend_operating_probe_protocol.json';p=json.loads(pp.read_text());assert v['protocol_sha256']==sha(pp)
    src=H/'tb'/(p['case']+'.scs');assert sha(src)==p['tb_sha256']
    extra=['XCP.MIP:s','XCP.MIN:s','XCP.MT:g','XCP.MPD:g','XCP.MPO:g',
        'XCP.XT.MN:s','XCP.XT.MP:s','XCP.MOFF:d']
    for dev in ['MIP','MIN','MT','MPD','MPO']:
        extra += ['XCP.'+dev+':'+q for q in ['qs','qg','qb']]
    body=src.read_text()+'\n// Observation-only terminal and charge balance probe.\nsave '+' '.join(extra)+'\n'
    case='cp_terminal_balance_tt';tb=H/'tb'/(case+'.scs');assert not tb.exists()
    tb.write_text(body,encoding='utf-8',newline='\n')
    result=dict(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),run='cpterminalbalance01',case=case,
        source_validation=proof.name,source_validation_sha256=sha(proof),source_protocol_sha256=sha(pp),
        source_case=p['case'],source_run=p['run'],source_tb_sha256=sha(src),tb_sha256=sha(tb),
        source_result=v['periodic']['source_result'],source_result_sha256=v['periodic']['source_sha256'],
        phase_deg=p['phase_deg'],condition=p['condition'],extra_observations=extra,
        kcl_nodes=dict(tail=['XCP.MT:d','XCP.MIP:s','XCP.MIN:s'],
            mirror=['XCP.MIN:d','XCP.MPD:d','XCP.MPD:g','XCP.MPO:g'],
            tail_gate=['XCP.XT.MN:s','XCP.XT.MP:s','XCP.MOFF:d','XCP.MT:g']),
        diagnostic_limits=dict(relative_mean_absolute_kcl=1e-3,max_mean_clamp_current_change_a=1e-10),
        launch_scope='One one-thread fresh PSS;1200s guard; await a verified free resource slot, not submitted.',
        main_dut_modified=False,noise_measured=False,full_pll_acceptance=False,
        limitations=['This is the established ideal-RF/control-clamp frontend fixture, not a complete PLL.',
            'Terminal currents include displacement; retained intrinsic drain currents are separately labelled.',
            'Charge boundary conventions must be verified against terminal currents before identifying storage capacitance.'])
    dest.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(run=result['run'],case=case,added_observations=len(extra),launched=False),indent=2))

if __name__=='__main__':main()
