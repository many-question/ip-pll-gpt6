"""Conditional mapped-gate checks after the physical coarse6/DAC32/49 pair.

These are abstract count plants, NOT new TT transistor simulations or a fit to
the two physical measurements. Only the two endpoint counts are observations.
"""
from pathlib import Path
import datetime, hashlib, json
from verify_rt4_recenter109 import verify

H = Path(__file__).resolve().parent
B = H.parents[1] / 'blocks/cmos_v14_full'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    out = H / 'results/rt4_callback_budget120.json'
    assert not out.exists()
    lo = json.loads((H / 'results/rt4_callback_start119_review120.json').read_text())
    hi = json.loads((H / 'results/rt4_callback_edge118_review119.json').read_text())
    assert lo['coarse'] == hi['coarse'] == 6
    assert (lo['dac'], hi['dac']) == (32, 49)
    assert (lo['physical_snapshot_count'], hi['physical_snapshot_count']) == (5243, 5265)
    rows = []
    # Unknown interior codes are alternatives, not measured/predicted lock codes.
    # Under the explicit stationary monotone hypothesis, put a single acceptable
    # integer DAC at each possible interior location and exercise the actual gates.
    for acceptable in range(33, 49):
        def plant(c, d, i, q=acceptable):
            assert c == 6
            return -5 if d <= 32 else 17 if d >= 49 else (0 if d == q else -2 if d < q else 2)
        row = verify('hypothetical_single_good_dac_' + str(acceptable), plant, True,
                     coarse=6, expected_coarse=6)
        assert row['checks'][0]['dac'] == 32 and row['checks'][0]['error_count'] == -5
        assert row['checks'][1]['dac'] == 43
        rows.append(row)
    # A physical endpoint bracket alone does not imply a representable +/-1-count
    # code, and does not guarantee the count signs persist as bias evolves.
    def skipped_deadband(c, d, i):
        return -5 if d <= 32 else 17 if d >= 49 else (-2 if d <= 40 else 2)
    failures = [
        verify('hypothetical_bracket_without_acceptable_integer_code', skipped_deadband,
               False, coarse=6, expected_coarse=6),
        verify('hypothetical_count_sign_changes_after_first_check',
               lambda c, d, i: -5 if i == 0 else 17,
               False, coarse=6, expected_coarse=6),
    ]
    result = dict(time=datetime.datetime.now().astimezone().isoformat(), passed=True,
        category='Actual mapped digital gates with conditional artificial count inputs; not MOS/TT capture.',
        observed_endpoints=dict(coarse=6, dac=[32,49], count=[5243,5265], error=[-5,17]),
        assumptions='Stationary monotone response with exactly one acceptable integer DAC in33..48; all unmeasured counts are abstract +/-2 or0. The physical measurements do not establish these assumptions.',
        conditional_success_cases=rows, counterexamples=failures,
        maximum_checks=max(len(x['checks']) for x in rows), minimum_checks=min(len(x['checks']) for x in rows),
        original_budget=8, source_sha256={p.name:sha(p) for p in [
            B/'fll_recenter109_v14_mapped.json', B/'fll_recenter109_v14.v',
            H/'verify_rt4_recenter109.py', H/'analyze_fll_async_quantization.py', Path(__file__)]},
        boundary='Verification registers are initialized only in this DIGITAL unit test. No analog state was loaded, no PLL instance was forced, and no autonomous selection/handoff/capture is claimed. Successful cases need no coarse change; the automatic coarse-recenter branch is not physically validated.',
        conclusion='The unchanged eight-check budget covers all16 stationary single-good-code alternatives tested. Counterexamples preserve safe error rather than false enable. No measured lock code or guarantee follows; do not widen the budget or scan more fixed codes from this result.')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(dict(passed=True, conditional_cases=len(rows), counterexamples=len(failures),
                         checks=[result['minimum_checks'],result['maximum_checks']])))

if __name__ == '__main__': main()
