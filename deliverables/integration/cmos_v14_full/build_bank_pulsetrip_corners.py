"""Check corner and low-RF coverage before adopting the repaired physical bank.

Hold the measured SS waveform shape fixed while changing device corner and
frequency. These are controlled receiver/bank interface tests, not simulations
of each corner's actual VCO. All use a predeclared 400-600 ns acceptance window.
"""
from pathlib import Path
import hashlib,json,re
H=Path(__file__).resolve().parent
proof=json.loads((H/'results/ss_settled_pulse_validation.json').read_text())['cases']
assert len(proof)==6 and all(x['passed'] for x in proof)
hi={4:3936,6:3888,8:3456,10:3120,12:3168,14:3024}
lo={4:2688,6:2736,8:2688,10:2880,12:2880}
specs=[('ss',60,m,rf,'lo') for m,rf in lo.items()]
specs += [(corner,temp,m,rf,'hi') for corner,temp in [('tt',27),('ff',0)] for m,rf in hi.items()]
cases=[]
for corner,temp,m,rf,end in specs:
    src=H/'tb'/f'banktripsettled_m{m}_ss.scs'
    tb=src.read_text().replace('section=ss',f'section={corner}').replace('temp=60',f'temp={temp}')
    tb=re.sub(r'(?<=frequency=)[0-9.]+M',f'{rf}M',tb)
    case=f'banktripcorner_m{m}_{corner}_{end}'
    p=H/'tb'/(case+'.scs');assert not p.exists();p.write_text(tb)
    cases.append(dict(case=case,corner=corner,temp_c=temp,m=m,rf_mhz=rf,expected_output_mhz=rf/m,
                      endpoint=end,source_tb_sha256=hashlib.sha256(src.read_bytes()).hexdigest()))
out=dict(scope=__doc__,run='banktripcorner01',cases=cases,candidate='bank_pulsetrip_v14',
         condition='1.2V/10fF, actual MOS RX/bank/baselineRT/quietcounter load, noiseless zero-impedance SS-shaped RF replay.',
         solver='600ns, fixed400-600ns window,1ps/reltol1e-5',
         full_pll_acceptance=False,main_dut_modified=False,
         limitations=['Same replay shape is not proof of each corner VCO amplitude/common-mode/loading.',
                      'Three paired corners and selected endpoints do not establish fullPVT or all33PLLchannels.',
                      'No reset/mode-change or random-jitter result from these steady windows.'])
(H/'results/bank_pulsetrip_corner_protocol.json').write_text(json.dumps(out,indent=2)+'\n')
print(' '.join(x['case'] for x in cases))
