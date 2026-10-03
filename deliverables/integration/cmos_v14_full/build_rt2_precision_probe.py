"""Prepare fresh-PSS, matched-offset numerical checks of the 2x or 4x local chain.

This is a numerical screen, not an integrated-jitter measurement. The point
491.99 MHz deliberately avoids the exact third harmonic of the 164 MHz PSS.
"""
from pathlib import Path
import hashlib
import json
import re
import argparse

H = Path(__file__).resolve().parent
parser=argparse.ArgumentParser();parser.add_argument('--factor',type=int,choices=[2,4],default=2)
args=parser.parse_args();factor=args.factor
source = H / f'tb/chain_rtscale{factor}_tt.scs'
body = source.read_text()
body = body.replace('start=10k stop=492M dec=20',
                    'values=[10k 100k 1M 10M 100M 491.99M]')
cases = []
for grade in ['coarse', 'fine']:
    case = f'chain_rt{factor}_precision_{grade}_tt'
    tb = body
    if grade == 'fine':
        tb = tb.replace('harms=383', 'harms=767')
        tb = tb.replace('maxstep=1p', 'maxstep=0.5p maxacfreq=504G')
        tb = tb.replace('maxsideband=383', 'maxsideband=767')
    target = H / 'tb' / (case + '.scs')
    assert not target.exists(), target
    target.write_text(tb, encoding='utf-8', newline='\n')
    assert 'readpss=' not in tb
    cases.append(dict(case=case, sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
                      pss=re.search(r'^pss .*$', tb, re.M)[0],
                      pnoise=re.search(r'^pn .*$', tb, re.M)[0]))
out = dict(scope=__doc__, source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
           run=f'rt{factor}precision01', factor=factor, cases=cases, full_pll_acceptance=False,
           offsets_hz=[1e4, 1e5, 1e6, 1e7, 1e8, 491.99e6],
           pointwise_pass_limit_db=0.2,
           condition='TT27/1.2V/984MHz/10fF, noiseless measured RF replay; all device noise; fresh PSS in both cases.',
           limitation='Combined step/sideband/maxacfreq screen. A failure needs individual-parameter diagnosis; six points do not establish a full-band RMS value.')
(H / f'results/rt{factor}_precision_protocol.json').write_text(json.dumps(out, indent=2)+'\n')
print(' '.join(x['case'] for x in cases))
