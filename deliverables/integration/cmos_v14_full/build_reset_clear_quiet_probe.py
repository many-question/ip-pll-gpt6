"""Separate quiet-reset settling from the already measured clock kickback.

The failed 1mV peak gate under a running clock remains in the original unit
record. This changes only clock start time, never the device or that gate.
"""
from pathlib import Path
import datetime,hashlib,json
H=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    source=H/'results/reset_clear_unit_protocol.json';p=json.loads(source.read_text())
    proof=H/'results/reset_clear_unit_validation.json';v=json.loads(proof.read_text());assert v['complete'] and not v['passed']
    assert all(c['checks']['candidate_guarded_function'] and c['checks']['original_guarded_function'] and c['checks']['reset_outputs_low'] for c in v['cases'])
    rows=[]
    for c in p['cases']:
        src=H/'tb'/(c['case']+'.scs');s=src.read_text();assert s.count('delay=200p')==1
        s=s.replace('delay=200p','delay=3.2n');case=c['case'].replace('dff','quiet');dst=H/'tb'/(case+'.scs');assert not dst.exists()
        dst.write_text(s,encoding='utf-8',newline='\n');rows.append(dict(c,case=case,run='resetclearquiet01',tb_sha256=sha(dst),source_case=c['case'],source_tb_sha256=sha(src)))
    p.update(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),cases=rows,
        source_protocol_sha256=sha(source),source_running_clock_validation_sha256=sha(proof),
        condition=p['condition']+' Clock held low until3.2ns; reset held high until3.0ns. Stack settling measured1..2ns before clock starts.',
        controlled_fixture_change=dict(clock_delay_s=[200e-12,3.2e-9]))
    p['limitations']+=['Quiet-reset settling is a different measurement condition from the preserved running-clock peak failure. Both remain relevant.',
                        'This does not reproduce every capacitively coupled input in the whole PLL.']
    dst=H/'results/reset_clear_quiet_protocol.json';assert not dst.exists();dst.write_text(json.dumps(p,indent=2)+'\n');print(json.dumps(rows,indent=2))

if __name__=='__main__':main()
