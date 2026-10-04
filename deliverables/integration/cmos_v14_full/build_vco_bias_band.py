"""Quantify the measured CF40 VCO candidate over a dense grid with an independent finer run."""
from pathlib import Path
import datetime,hashlib,json
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
proof=H/'results/vco_bias_noise_validation.json';v=json.loads(proof.read_text())
assert v['baseline']['periodic_passed'] and v['candidate']['periodic_passed']
cases=[]
for tag,source,step,sides in [('cf10_fine','vco_noise_check6_tt',.5,255),('cf40_fine','vco_bias_cf40_tt',.5,255),('cf40_finer','vco_bias_cf40_tt',.25,511)]:
    case='vco_band_'+tag+'_tt';src=H/'tb'/(source+'.scs');body=src.read_text()
    assert 'values=[10k 100k 1M 10M 100M 492M]' in body and 'maxstep=0.5p' in body and 'maxsideband=255' in body
    body=body.replace('values=[10k 100k 1M 10M 100M 492M]','start=10k stop=492M dec=20')
    body=body.replace('maxstep=0.5p',f'maxstep={step:g}p').replace('maxsideband=255',f'maxsideband={sides}')
    tb=H/'tb'/(case+'.scs');assert not tb.exists();tb.write_text(body)
    cases.append(dict(case=case,variant=tag,source_tb=src.name,source_tb_sha256=sha(src),tb_sha256=sha(tb),maxstep_ps=step,maxsideband=sides))
p=dict(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),status='prepared_not_run',run='vcobiasband01',cases=cases,
    prior_six_point_validation_sha256=sha(proof),
    condition='TT27/1.2V/Q5/coarse23/control.679V/actualfixedM4chain10fF/referenceDC0tracksampler/onlyXVnoise. Samephysicalcircuitasvalidatedsixpointcases. IndependentfreshautonomousPSSforeachcase; no readpss.',
    frequency_grid=dict(start_hz=1e4,stop_hz=492e6,points_per_decade=20),
    high_offset_integrals=dict(lower_bounds_hz=[1e6,2e6,5e6,10e6,100e6],upper='Common minimum of measuredRFcarrier/8 across completed cases; neverextrapolate.'),
    numerical_limits=dict(max_phase_noise_delta_db=.1,max_relative_rf_frequency_change=1e-4,max_high_band_rms_relative_change=.01),
    launch_gate='Three serial one-threadcases in releasedmesh longslot;<=18/fourlong+oneshort. Existingobserver-free corewarm andRT4releasecontinueindependently.',
    limitations=['Free-running PM linearization near linewidth is not a totaljitterestimate. Integrals onlyat>=1MHz withactualcarrier normalizations.',
        'Static-reference/fixedM4load, not active sampling/programmablebank/RT4/fullPLL.',
        'CF40 nominalbiasRCtimeconstant40us versus10us; coldstart/power-up notproven byPSS orwarmtests.',
        'No adoption into mainDUT; candidates needactualclosed-loop/noise/PVTverification.'],main_dut_modified=False,full_pll_acceptance=False)
(H/'results/vco_bias_band_protocol.json').write_text(json.dumps(p,indent=2)+'\n');print(' '.join(x['case'] for x in cases))
