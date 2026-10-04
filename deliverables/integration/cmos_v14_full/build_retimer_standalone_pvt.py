"""Paired SS/60C and FF/0C device-noise checks of the standalone RT4 module."""
from pathlib import Path
import datetime,hashlib,json
H=Path(__file__).resolve().parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    proof=H/'results/retimer_standalone_band_validation.json';v=json.loads(proof.read_text());assert v['precision_passed']
    source=H/'tb/retimer_standalone_band_finer_tt.scs';body=source.read_text();rows=[]
    for corner,temp in [('ss',60),('ff',0)]:
        assert body.count('section=tt\n')==1 and body.count('temp=27 ')==1
        b=body.replace('section=tt\n','section='+corner+'\n').replace('temp=27 ',f'temp={temp} ')
        case=f'retimer_standalone_band_finer_{corner}';dest=H/'tb'/(case+'.scs');assert not dest.exists();dest.write_text(b,encoding='utf-8',newline='\n')
        rows.append(dict(case=case,corner=corner,temp_c=temp,run='rtstandalonepvt01',tb_sha256=sha(dest)))
    p=dict(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),cases=rows,
        source_validation_sha256=sha(proof),source_tb_sha256=sha(source),
        condition='1.2V/984MHzoutput/10fF/actualRT4; ideal3.936GHzclock+984MHzdata delayed30ps/10psedges. SS60 andFF0 pairings, freshPSSfund984MHz/.25ps/256sidebands/maxac1008GHz.',
        integration_band_hz=[1e4,492e6],launch_scope='Two sequential one-thread cases; no automatic additional sweep.',
        limits=dict(endpoint_peak_v=.001,low_max_v=.2,high_min_v=1.0),
        limitations=['Only SS60/TT27/FF0 at1.2V/984MHz/10fF. Not all nine process-temperature combinations or voltage/load/frequency corners.',
            'Ideal clock/data exclude receiver/divider/LC and PLL interactions.',
            'Independent numerical precision comparison completed at TT only; SS/FF precision not separately established.'],
        full_pll_acceptance=False,main_dut_modified=False)
    dest=H/'results/retimer_standalone_pvt_protocol.json';assert not dest.exists();dest.write_text(json.dumps(p,indent=2)+'\n')
    print([x['case'] for x in rows])

if __name__=='__main__':main()
