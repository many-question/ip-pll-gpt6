"""Extend the successful buffer-period calibration to the actual RT4 TSPC retimer."""
from pathlib import Path
import datetime,hashlib,json
H=Path(__file__).resolve().parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    proof=H/'results/mos_period_noise_validation.json';v=json.loads(proof.read_text());assert v['passed']
    pp=H/'results/mos_period_noise_protocol.json';p=json.loads(pp.read_text());cases=[]
    for old in p['cases']:
        body=(H/'tb'/(old['case']+'.scs')).read_text()
        body=body.replace('include "cells.scs"','include "cells.scs"\ninclude "rtcomb_v13.scs"\ninclude "rt_noise_scale4_v14.scs"')
        body=body.replace('rise=10p fall=10p\n','rise=10p fall=10p delay=30p\n',1)
        original='X0 (in ob vdd 0) pll_inv wn=12u wp=2u\nX1 (ob out vdd 0) pll_inv wn=3.2u wp=12u'
        assert body.count(original)==1
        body=body.replace(original,f'VCLK (clk 0) vsource type=pulse val0=0 val1=1.2 period={1/3.936e9:.17g} width={.5/3.936e9-10e-12:.17g} rise=10p fall=10p\nXR (in clk out vdd 0) rt_noise_scale4_v14')
        body=body.replace('// Same two final CMOS stages as RT4; ideal input isolates the measurement.','// Actual RT4 retimer and output stages; ideal data/RF clock isolate measurement.')
        body=body.replace('save in ob out VDD:p','save in clk XR.ob XR.qb XR.XFF.a XR.XFF.b out VDD:p')
        case=old['case'].replace('mos_period','retimer_period');dest=H/'tb'/(case+'.scs');assert not dest.exists();dest.write_text(body,encoding='utf-8',newline='\n')
        cases.append(dict(old,case=case,run='rtperiod01',tb_sha256=sha(dest)))
    p.update(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),cases=cases,
        source_buffer_validation_sha256=sha(proof),source_protocol_sha256=sha(pp),
        condition='TT27/1.2V/actualRT4 TSPC+twoinverters/10fF; ideal984MHz data delayed30ps and3.936GHz clock,10ps edges. FreshPSS ratio1vs6/.5ps/maxac504GHz.',
        waveform_nodes=['XR.qb','XR.ob','XR.XFF.a','XR.XFF.b','out'],clock_node='clk',clock_ratio=4,
        required_mode='ax +mt=1 -preset_override',dispatch_failures=[],
        reason='Buffer-only calibration does not cover the dynamic/regenerative TSPC stages that dominate the measured digital-chain noise.')
    p['limitations']+=['Ideal clock/data exclude input jitter, realRF receiver, programmable-divider loading and fullPLL.']
    dest=H/'results/retimer_period_noise_protocol.json';assert not dest.exists();dest.write_text(json.dumps(p,indent=2)+'\n')
    print([x['case'] for x in cases])

if __name__=='__main__':main()
