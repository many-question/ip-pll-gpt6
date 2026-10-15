"""Build one two-point K41 tuning diagnostic; frozen callback geometry stays unchanged."""
from pathlib import Path
import datetime, hashlib, json, re

ROOT = Path(__file__).resolve().parents[4]
H = ROOT / 'share/deliverables/integration/cmos_v14_full'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    case = 'rt4_callback_k41_114_tt'
    tb = H / 'tb' / (case + '.scs')
    pp = H / 'results/rt4_callback_k41_114_protocol.json'
    assert not tb.exists() and not pp.exists()
    source = H / 'tb/pdkcb110_vco_after.scs'
    net = ROOT / 'share/deliverables/blocks/cmos_v14_full/rt4_callback110_after.scs'
    assert sha(net) == '260a50e7e62d0d25cfdfb21d6004a22f31ca38544632329448bea811dcd38f62'
    s = source.read_text()
    assert 'VC (ctrl 0) vsource dc=.48' in s
    s = s.replace('VC (ctrl 0) vsource dc=.48',
                  'VC (ctrl 0) vsource type=pwl wave=[0 .20 1u .20 1.00001u .84 2u .84]')
    for bit in range(8):
        s, count = re.subn(rf'VB{bit} \(b{bit} 0\) vsource dc=[^\n]+',
                          f'VB{bit} (b{bit} 0) vsource dc={1.2 if (9 >> bit) & 1 else 0}', s)
        assert count == 1
    assert 'stop=4e-07 start=0 strobeperiod=5e-12' in s
    s = s.replace('stop=4e-07 start=0 strobeperiod=5e-12', 'stop=2e-06 start=0 strobeperiod=1e-11')
    s = s.replace('save vp vn ctrl ', 'save b0 b1 b2 b3 b4 b5 b6 b7 vp vn ctrl ')
    tb.write_text('// Same externally fixed code9 at both control voltages: local diagnostic only.\n'+s, encoding='utf-8')
    c = dict(run='rt4cbk41114ssd01', case=case, kind='diagnostic', stop_s=2e-6,
             strobe_s=1e-11, expected_points=200001, requested_threads=2)
    p = dict(time=datetime.datetime.now().astimezone().isoformat(), cases=[c], threads=2,
             mode='ax', maxstep_s=8e-12, reltol=.001, method='traponly', noise=False,
             condition='TT27/1.2V/24MHz/10fF, callback110 geometry, unchanged4.8fF bank and real RF/4/RT4 load.',
             purpose='Check whether one estimated K41 coarse code has conditional analog tuning around3936MHz before considering full-PLL capture.',
             code_selection_hypothesis='Code9 is a diagnostic estimate: callback110 code20 at.48V gave3824.248MHz; previous approximate10MHz/code sensitivity suggests moving about11 codes. This cross-version estimate selects a test only, not a tuning or control guarantee. Callback113 separately showed target endpoint coverage but different bias conditions.',
             segments=[dict(start_s=0, end_s=1e-6, coarse=9, control_V=.20, window_s=[.7e-6, 1e-6], target_MHz=3936),
                       dict(start_s=1.00001e-6, end_s=2e-6, coarse=9, control_V=.84, window_s=[1.7e-6, 2e-6], target_MHz=3936)],
             initialization='Real1Mohm/10pF bias network, nfilt initial .728V released at t0; no DC bias clamp. Same coarse code throughout to avoid a coarse-switch transient between the two measurements.',
             unchanged='callback110 MOS W/L/NF/M and all derived parameters, logic and passives; no controller or adopted baseline edit.',
             source_tb=source.relative_to(ROOT).as_posix(), source_tb_sha256=sha(source),
             physical_inputs_sha256={v.relative_to(ROOT).as_posix():sha(v) for v in [net,tb]},
             completion='Two terminal observations >=60s apart; exit0/zero errors, PSF END, input/raw/log/final.ic hashes,200001 finite points0..2us.',
             evidence_boundary='Two externally fixed-code points at warm bias, not hardware-selected code, full-PLL capture, all-code overlap, asymptotic steady state or noise. Failure to bracket in.20..84V does not prove no solution over the full legal control range.',
             resource_cap=dict(threads=18, long_jobs=4, short_jobs=1))
    pp.write_text(json.dumps(p, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(case=case, protocol_sha256=sha(pp), input_sha256=sha(tb), segments=p['segments']),indent=2))


if __name__ == '__main__':
    main()
