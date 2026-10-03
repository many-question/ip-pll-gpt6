"""Prepare fresh-PSS full-band numerical checks; no launch or adoption.

The original 10kHz..492MHz logarithmic grid and exact endpoint are retained.
Additional finite harmonic-neighbour points expose, rather than hide, the
known shifted flicker poles. No physical low-frequency cutoff is assumed.
"""
from pathlib import Path
import hashlib,json,re
H=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
offsets=sorted({int(center+sign*distance) for center in [164e6,328e6,492e6]
                for distance in [1,10,100,1000,10000] for sign in [-1,1]
                if 1e4<=center+sign*distance<=492e6})
rows=[]
for factor in [2,4]:
    source=H/f'tb/chain_rtscale{factor}_tt.scs';body=source.read_text()
    assert 'start=10k stop=492M dec=20' in body and 'readpss=' not in body
    body=body.replace('harms=383','harms=767').replace('maxstep=1p','maxstep=0.5p maxacfreq=504G').replace('maxsideband=383','maxsideband=767')
    body+='\n// Finite harmonic-neighbour diagnostic, same fresh PSS and event.\n'
    body+='pnnear pnoise values=['+' '.join(map(str,offsets))+'] pnoisemethod=fullspectrum noisetype=sampled measurement=[edge] sampleratio=6 maxsideband=767\n'
    target=H/f'tb/chain_rt{factor}_fullband_fine_tt.scs';assert not target.exists();target.write_text(body)
    rows.append(dict(factor=factor,case=target.stem,run=f'rt{factor}fullband01',
        source_case=source.stem,source_run='chainrtscale01',source_tb_sha256=sha(source),tb_sha256=sha(target)))
out=dict(scope=__doc__,status='prepared_not_run',cases=rows,band_hz=[1e4,492e6],
    harmonic_neighbour_offsets_hz=offsets,pointwise_limit_db=.2,integrated_rms_relative_limit=.02,
    condition='TT27/1.2V/984MHz/10fF, same noiseless RF replay and MOS dependencies as own scaling result; .5ps/767sidebands/maxacfreq504GHz vs1ps/383.',
    launch_gate='Review and complete the corresponding five fresh noise-on groups first; reuse its released one-thread long slot. No automatic launch or duplicate jobs.',
    acceptance='Identical frequency grid, physical hashes, branch periods/endpoints, device sums, finite PSD values and convergence log must pass. Full-grid numerical agreement is not physical closure of exact-harmonic flicker singularities.',
    unchanged_requirement='Random RMS<200fs from10kHz to492MHz at984MHz output; exclude discrete spurs, not continuous device noise.',
    limitations=['A logarithmic-grid RMS remains provisional until the harmonic-pole treatment is physically justified.',
        'Finite neighbours down to1Hz distance do not integrate through zero distance or establish a physical cutoff.',
        'This local chain excludes the noisy actualLC, PLL transfer and external source/supply noise.',
        'Only the first edge is integrated; previous six-edge three-point screens do not establish all-edge full-band equality.'],
    main_dut_modified=False,full_pll_acceptance=False)
(H/'results/rt_fullband_precision_protocol.json').write_text(json.dumps(out,indent=2)+'\n')
print([x['case'] for x in rows])
