"""Extend the clean initialization trial at its verified original tolerances."""
from pathlib import Path
import datetime,hashlib,json
H=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    pp0=H/'results/full_pll_noise_settling_protocol.json';p=json.loads(pp0.read_text())
    source=H/'tb/full_pll_warm_noise_method_tt.scs';body=source.read_text()
    body=body.replace('stop=300n maxstep=1p','stop=2u maxstep=.5p').replace('param_vec=[0 0 1u 1]','param_vec=[0 0 3u 1]')
    case='full_pll_noise_moderate_settling_tt';tb=H/'tb'/(case+'.scs');assert not tb.exists();tb.write_text(body)
    p.update(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),run='pllnoisesettle02',case=case,
        source_tb_sha256=sha(source),tb_sha256=sha(tb),method='traponly',reltol=1e-5,vabstol=1e-6,iabstol=1e-12,
        reason='The300ns warm trial and both native step controls were clean at these tolerances. Extend to2us with.5ps. This is a separate moderate-tolerance settling track, not a one-variable comparison against strict Gear2.')
    pp=H/'results/full_pll_noise_moderate_settling_protocol.json';assert not pp.exists();pp.write_text(json.dumps(p,indent=2)+'\n')
    print(json.dumps(dict(run=p['run'],case=case,protocol_sha256=sha(pp)),indent=2))

if __name__=='__main__':main()
