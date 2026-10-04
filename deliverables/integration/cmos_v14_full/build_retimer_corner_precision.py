"""Refine the SS60/FF0 standalone RT4 full-band noise cases without circuit edits."""
from pathlib import Path
import datetime, hashlib, json
H=Path(__file__).resolve().parent
ROOT=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
CHANGES={'harms=256':'harms=512','maxstep=0.25p':'maxstep=0.125p',
         'maxacfreq=1008G':'maxacfreq=2016G','maxsideband=256':'maxsideband=512'}

def main():
    proof=H/'results/retimer_standalone_pvt_validation.json';v=json.loads(proof.read_text())
    assert v['function_all_passed'] and v['noise_all_valid']
    pp=H/'results/retimer_corner_precision_protocol.json';assert not pp.exists();rows=[]
    for old in v['cases']:
        rp=ROOT/old['source_result'];assert sha(rp)==old['source_sha256']
        r=json.loads(rp.read_text());src=H/'tb'/(old['case']+'.scs');body=src.read_text()
        for before,after in CHANGES.items():
            assert body.count(before)==1
            body=body.replace(before,after)
        case='retimer_standalone_refined_'+old['corner'];tb=H/'tb'/(case+'.scs');assert not tb.exists()
        tb.write_text(body,encoding='utf-8',newline='\n')
        rows.append(dict(run='rtcornerprecision01',case=case,corner=old['corner'],temp_c=old['temp_c'],
                         source_result=old['source_result'],source_sha256=old['source_sha256'],
                         source_tb_sha256=sha(src),tb_sha256=sha(tb),
                         physical_dependencies_sha256={k:x for k,x in r['inputs_sha256'].items() if k!=old['case']+'.scs'}))
    p=dict(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),cases=rows,
           source_validation=proof.name,source_validation_sha256=sha(proof),numerical_changes=CHANGES,
           condition='ActualRT4+two buffers, SS60/FF0,1.2V/984MHz/10fF,ideal3.936GHzclock and984MHzdata/10psedges/delay30ps;freshPSS,10kHz-492MHz95point noise.',
           precision_limits=dict(max_psd_change_db=.1,max_relative_rms_change=.01),
           integration_band_hz=[1e4,492e6],main_dut_modified=False,full_pll_acceptance=False,
           limitations=['Two paired corners, not all process/temperature/voltage/frequency/load combinations.',
                        'Ideal clock/data exclude RF receiver, divider, LC and closed-loop correlations.',
                        'Numerical precision within this fixture is not complete PLL jitter acceptance.'])
    pp.write_text(json.dumps(p,indent=2)+'\n');print(json.dumps(rows,indent=2))

if __name__=='__main__':main()
