"""Replay only the clean prefix to obtain a full intermediate transistor state."""
from pathlib import Path
import datetime,hashlib,json
H=Path(__file__).resolve().parent; ROOT=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    pp=H/'results/full_pll_precision_ramp_protocol.json'; p=json.loads(pp.read_text())
    failure=H/'results/full_pll_precision_ramp_failure.json'; v=json.loads(failure.read_text())
    assert not v['completed'] and v['recovery']['lte_relaxations_reported']==1
    src=H/'tb'/(p['case']+'.scs'); assert sha(src)==p['tb_sha256']
    original=src.read_text(); removed='1.6e-05 5e-13 1e-06 1e-09 1e-12 0\n'
    assert original.count(removed)==1 and original.count('stop=20u')==1
    body=original.replace(removed,'').replace('stop=20u','stop=15.9u')
    # Exactly these two changes; all physical sources, device dependencies and observations stay identical.
    assert body.replace('stop=15.9u','stop=20u').replace('}\ntran tran',removed+'}\ntran tran')==original
    case='full_pll_rt4_precision_stage_tt'; tb=H/'tb'/(case+'.scs')
    dst=H/'results/full_pll_precision_stage_protocol.json'
    assert not tb.exists() and not dst.exists()
    tb.write_text(body,encoding='utf-8',newline='\n')
    stage=dict(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),run='pllprecisionstage01',case=case,
        tb_sha256=sha(tb),source_protocol_sha256=sha(pp),failure_diagnosis_sha256=sha(failure),
        text_state=p['text_state'],text_state_sha256=p['text_state_sha256'],schedule=p['schedule'][:-1],stop_s=15.9e-6,
        physical_dut_modified=False,noise_enabled=False,full_pll_acceptance=False,
        condition='RT4/newbank complete actual transistor PLL,TT27/1.2V/24MHz/K41/M4/10fF/Q5RLC/CF10. Ideal external supply and reference.',
        terminal_precision='0.5ps/reltol1e-5/vabstol100nV/iabstol1pA from15 to15.9us; not the final jitter precision.',
        differences=['Remove the16us tolerance transition.','Stop at15.9us and collect all-node writefinal IC.'],
        gates=['Actual successful terminal log and all input/output hashes.','No numerical recovery.','No reacquisition; observed controls held.',
               'Compare sparse prefix against prior run, excluding its invalid post16us segment.','Complete final IC required; preserve reference phase in the follow-on.'],
        deployment_rule='Guard owns cancellation. No noise launch from this stage. A subsequent distinct constant-fine dense test must pass original numerical, initialization, logic and stationarity gates.',
        limitations=p['limitations'])
    dst.write_text(json.dumps(stage,indent=2)+'\n')
    print(json.dumps(stage,indent=2))

if __name__=='__main__':main()
