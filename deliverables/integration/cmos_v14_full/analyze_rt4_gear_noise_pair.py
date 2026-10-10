"""Apply the existing unchanged PLL gates only after checking the actual Gear method."""
import json,sys
from pathlib import Path
from transient_diagnostics import effective
import analyze_full_pll_direct_noise_pair as base

if __name__=='__main__':
    name=sys.argv[sys.argv.index('--protocol')+1]
    assert name=='full_pll_rt4_gear_quarter_pair_protocol.json'
    protocol=json.loads((base.H/'results'/name).read_text())
    assert protocol['method']=='gear2only'
    for case in protocol['cases']:
        directory=base.R/case['run']/case['case']
        if (directory/'result.json').exists():
            assert effective((directory/'spectre.out').read_text())['method']=='gear2only'
    base.main()
