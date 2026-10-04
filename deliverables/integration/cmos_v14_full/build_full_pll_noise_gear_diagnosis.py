"""Isolate integration method after noise-OFF strict Trap exhibited recovery."""
from pathlib import Path
import datetime,hashlib,json
H=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    source=H/'tb/full_pll_noise_settling_tt.scs';body=source.read_text()
    assert 'method=traponly' in body
    case='full_pll_noise_gear_diagnosis_tt';tb=H/'tb'/(case+'.scs');assert not tb.exists()
    tb.write_text(body.replace('method=traponly','method=gear2only'))
    pp0=H/'results/full_pll_noise_settling_protocol.json';p=json.loads(pp0.read_text())
    p.update(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),run='pllnoisegear01',case=case,
        source_tb_sha256=sha(source),tb_sha256=sha(tb),method='gear2only',
        superseded_protocol=pp0.name,superseded_protocol_sha256=sha(pp0),
        reason='Noise remains OFF. Strict Trap generated XP.data ringing and repeated Newton disaster recoveries starting935.6ps. Change only integration method; do not treat those events as physical jitter.')
    p['limitations']+=['Gear2 can introduce numerical damping; a clean settled solution still needs step and noise cross-checks.']
    pp=H/'results/full_pll_noise_gear_diagnosis_protocol.json';assert not pp.exists();pp.write_text(json.dumps(p,indent=2)+'\n')
    print(json.dumps(dict(run=p['run'],case=case,protocol_sha256=sha(pp)),indent=2))

if __name__=='__main__':main()
