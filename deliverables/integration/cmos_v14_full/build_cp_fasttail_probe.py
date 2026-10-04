"""Build a one-change CP settling trial; no noise benefit is presumed.

Only MT changes from W/L=10um/1um to 1.8um/0.18um. Nominal aspect
ratio is retained, but current matching and device noise must be remeasured.
"""
from pathlib import Path
import datetime,hashlib,json
H=Path(__file__).resolve().parent;ROOT=H.parents[3];B=H.parents[1]/'blocks/cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    dst=H/'results/cp_fasttail_probe_protocol.json';assert not dst.exists()
    dp=H/'results/cp_dynamic_timing_validation.json';d=json.loads(dp.read_text())
    assert d['input_pair_charge_outside_gate_high_fraction']>.9
    pp=H/'results/cp_terminal_balance_protocol.json';p=json.loads(pp.read_text())
    original=B/'cp_physical_v14.scs';block=B/'cp_fasttail_v14.scs';assert not block.exists()
    old='MT (tail ng vss vss) nch w=10u l=1u ad=2.4p as=2.4p pd=20.48u ps=20.48u'
    new='MT (tail ng vss vss) nch w=1.8u l=180n ad=.432p as=.432p pd=4.08u ps=4.08u'
    body=original.read_text();assert body.count(old)==1
    body=body.replace('cp_physical_v14','cp_fasttail_v14').replace(old,new)
    body='// Settling experiment: only tail MT geometry changes; original main is unchanged.\n'+body
    block.write_text(body,encoding='utf-8',newline='\n')
    src=H/'tb'/(p['case']+'.scs');assert sha(src)==p['tb_sha256']
    case='cp_fasttail_operating_tt';tb=H/'tb'/(case+'.scs');assert not tb.exists()
    body=src.read_text();assert body.count('cp_physical_v14')==2
    tb.write_text(body.replace('cp_physical_v14','cp_fasttail_v14'),encoding='utf-8',newline='\n')
    source_result=ROOT/p['source_result'];assert sha(source_result)==p['source_result_sha256']
    deps=json.loads(source_result.read_text())['inputs_sha256'].copy();deps.pop(p['source_case']+'.scs')
    assert deps.pop(original.name)==sha(original);deps[block.name]=sha(block)
    out=dict(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),run='cpfasttailprobe01',case=case,
        phase_deg=p['phase_deg'],condition=p['condition'],tb_sha256=sha(tb),candidate_block_sha256=sha(block),
        baseline_block_sha256=sha(original),dependencies_sha256=deps,
        dynamic_diagnosis_sha256=sha(dp),terminal_protocol_sha256=sha(pp),
        source_case=p['case'],source_run=p['run'],source_tb_sha256=sha(src),
        original_geometry=dict(w_um=10,l_um=1),candidate_geometry=dict(w_um=1.8,l_um=.18),
        launch_gate='Baseline terminal-current probe must pass first; one fresh PSS, one thread, 1200s guard, verified free long slot.',
        measured_center_rebalanced=False,main_dut_modified=False,noise_measured=False,full_pll_acceptance=False,
        limitations=['Same phase is deliberately retained to isolate settling behavior; output-current balance may change.',
            'Same W/L does not mean the same current, output resistance, flicker noise or PVT behavior.',
            'This experiment is not adopted unless later rebalanced gain, noise and closed-loop checks justify it.',
            'The established ideal RF replay and control-voltage clamp remain diagnostic boundaries.'])
    dst.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(dict(run=out['run'],case=case,launched=False),indent=2))

if __name__=='__main__':main()
