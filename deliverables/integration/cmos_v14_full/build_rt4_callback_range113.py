"""Build one two-point callback110 VCO diagnostic, preserving all device sizes."""
from pathlib import Path
import datetime
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[4]
H = ROOT / 'share/deliverables/integration/cmos_v14_full'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    case = 'rt4_callback_range113_tt'
    tb = H / 'tb' / (case + '.scs')
    pp = H / 'results/rt4_callback_range113_protocol.json'
    assert not tb.exists() and not pp.exists()
    source = H / 'tb/pdkcb110_vco_after.scs'
    net = ROOT / 'share/deliverables/blocks/cmos_v14_full/rt4_callback110_after.scs'
    assert sha(net) == '260a50e7e62d0d25cfdfb21d6004a22f31ca38544632329448bea811dcd38f62'
    s = source.read_text()
    s = s.replace('VC (ctrl 0) vsource dc=.48',
                  'VC (ctrl 0) vsource type=pwl wave=[0 .20 1u .20 1.00001u 1.00 2u 1.00]')
    for bit in range(8):
        s, count = re.subn(rf'VB{bit} \(b{bit} 0\) vsource dc=[^\n]+',
                          f'VB{bit} (b{bit} 0) vsource type=pwl wave=[0 1.2 1u 1.2 1.00001u 0 2u 0]', s)
        assert count == 1
    assert 'stop=4e-07 start=0 strobeperiod=5e-12' in s
    s = s.replace('stop=4e-07 start=0 strobeperiod=5e-12', 'stop=2e-06 start=0 strobeperiod=1e-11')
    s = '// Conditional local tuning endpoints; fixed codes are diagnostic stimuli only.\n' + s
    tb.write_text(s, encoding='utf-8')
    c = dict(run='rt4cbrange113ssd01', case=case, kind='diagnostic', stop_s=2e-6,
             strobe_s=1e-11, expected_points=200001, requested_threads=2)
    p = dict(time=datetime.datetime.now().astimezone().isoformat(), cases=[c], threads=2,
             mode='ax', maxstep_s=8e-12, reltol=.001, method='traponly', noise=False,
             condition='TT27/1.2V/24MHz/10fF, callback110 geometry, unchanged4.8fF bank and actual RF/4/RT4 load.',
             purpose='After original109 recovery, check whether callback-induced frequency reduction prevents conditional endpoint coverage before any long full-PLL capture.',
             segments=[dict(start_s=0, end_s=1e-6, coarse=255, control_V=.20, window_s=[.7e-6, 1e-6], target_MHz=2688),
                       dict(start_s=1.00001e-6, end_s=2e-6, coarse=0, control_V=1.00, window_s=[1.7e-6, 2e-6], target_MHz=3936)],
             initialization='Real1Mohm/10pF bias network, nfilt initial .728V released at t0; no DC bias clamp.',
             unchanged='callback110 MOS dimensions and all derived parameters; no controller or adopted baseline edit.',
             source_tb=source.relative_to(ROOT).as_posix(), source_tb_sha256=sha(source),
             physical_inputs_sha256={str(v.relative_to(ROOT)).replace('\\', '/'): sha(v) for v in [net, tb]},
             completion='Two terminal observations >=60s apart, exit0/zero errors, PSF END, input/raw/log/final.ic hashes,200001 finite points0..2us.',
             evidence_boundary='Local externally selected two-point warm-bias transient; no all-code overlap, asymptotic steady state, full PLL capture, noise or PVT claim. Original109 remains a different parameter version.',
             resource_cap=dict(threads=18, long_jobs=4, short_jobs=1))
    pp.write_text(json.dumps(p, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(p, indent=2))


if __name__ == '__main__':
    main()
