"""Match the local noise chain's divider to the current actualLC candidate.

The earlier scaling/audit runs used cmos_even_bank_acq_v14. ActualLC preflights
use bank_pulsetrip_v14, with a continuous ring clock and a changed PB1. Keep
all other local fixture circuitry unchanged and solve PSS afresh.
"""
from pathlib import Path
import hashlib,json,re
H=Path(__file__).resolve().parent;B=H.parents[1]/'blocks/cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();rows=[]
for factor in [2,4]:
    src=H/f'tb/chain_rt{factor}_precision_fine_tt.scs';old=src.read_text()
    assert old.count('cmos_even_bank_acq_v14')==2 and 'readpss=' not in old
    body=old.replace('cmos_even_bank_acq_v14','bank_pulsetrip_v14')
    assert body.replace('bank_pulsetrip_v14','cmos_even_bank_acq_v14')==old
    for grade in ['probe','band']:
        case=f'chain_rt{factor}_pulsetrip_{grade}_tt';tb=body
        if grade=='band':tb=tb.replace('values=[10k 100k 1M 10M 100M 491.99M]','start=10k stop=492M dec=20')
        p=H/'tb'/(case+'.scs');assert not p.exists();p.write_text(tb)
        rows.append(dict(factor=factor,grade=grade,case=case,run='rtpulsetripprobe01' if grade=='probe' else f'rt{factor}pulsetripband01',
            tb_sha256=sha(p),old_fine_case=src.stem,old_fine_run=f'rt{factor}precision01',
            change='Only divider include and instance type differ from own original fine six-point source.' if grade=='probe' else 'Same repaired divider; replace six-offset probe with original full-band grid.'))
out=dict(scope=__doc__,status='prepared_not_run',cases=rows,
    old_bank_sha256=sha(B/'cmos_even_bank_acq_v14.scs'),current_bank_sha256=sha(B/'bank_pulsetrip_v14.scs'),
    actual_core_sha256=sha(B/'pll_noise_pulsetrip_core_v14.scs'),
    matched_offsets_hz=[1e4,1e5,1e6,1e7,1e8,491.99e6],
    condition='TT27/1.2V/984MHz/10fF, noiseless zeroimpedance measuredRF replay, .5ps/767sidebands/maxacfreq504GHz, freshPSS. Quiet counter retained. RealLC excluded.',
    reason='Old divider noise does not establish the noise of the repaired continuous-clock divider now used in actualLC integration.',
    launch_gate='Complete and review existingRT2 audit, then reuse its released one-thread long slot for two probe cases. Review both probes before selecting any full-band run. No automatic band run.',
    limitations=['Retimer-loading interaction with the noisy actualLC is still excluded.',
        'Five noise-only gates validated on the old divider must not be labeled validation of this new circuit.',
        'Six offsets compare spectra, not integratedRMS.',
        'Exact harmonic flicker, numerical allband/edges and PVT remain.'],
    main_dut_modified=False,full_pll_acceptance=False)
(H/'results/rt_pulsetrip_noise_protocol.json').write_text(json.dumps(out,indent=2)+'\n')
print([x['case'] for x in rows])
