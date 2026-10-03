"""Two causal SS checks at the prescaler-to-clock-tree interface.

The original dynamic prescaler remains unchanged. At SS/3.888GHz, qb0 reaches
only about0.907V, q1 high time is322ps/514ps, and the first clock-tree inverter
cannot restore a full pulse. Test qb0 pull-up and q1 switching threshold
separately, using the same ungated balanced tree and actual receiver/load.
"""
from pathlib import Path
import hashlib, json

H = Path(__file__).resolve().parent
B = H.parents[1] / 'blocks/cmos_v14_full'
source = B / 'bank_ungatedbal_v14.scs'
base = source.read_text()
edits = {
    'pulsepull': ('XPB0 (q0 qb0 vdd vss) pll_inv wn=0.8u wp=0.5u',
                  'XPB0 (q0 qb0 vdd vss) pll_inv wn=0.8u wp=1u'),
    'pulsetrip': ('XPB1 (qb0 q1 vdd vss) pll_inv wn=2u wp=4u',
                  'XPB1 (qb0 q1 vdd vss) pll_inv wn=3u wp=3u'),
}
cases = []
for tag, (old, new) in edits.items():
    name = 'bank_' + tag + '_v14'
    assert base.count(old) == 1
    s = base.replace('bank_ungatedbal_v14', name).replace(old, new)
    p = B / (name + '.scs')
    assert not p.exists(), p
    p.write_text(s)
    case = 'bank' + tag + '_m6_ss'
    cases.append(case)
    tb = (H / 'tb/bankungatedbal_m6_ss.scs').read_text().replace('bank_ungatedbal_v14', name)
    (H / 'tb' / (case + '.scs')).write_text(tb)
(H / 'results/ss_pulse_restore_protocol.json').write_text(json.dumps(dict(
    scope=__doc__, source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
    cases=cases, run='bankpulse01', main_dut_modified=False,
    condition='Actual MOS receiver with measured SS RF waveform replay;3.888GHz,M6,SS60/1.2V/10fF,200ns,last80ns,1ps/reltol1e-5.',
    changes={k: list(v) for k,v in edits.items()},
    not_acceptance=['No LC backaction','No noise','No full PVT or mode/reset regression']), indent=2) + '\n')
print(' '.join(cases))
