"""Small analytic RC fixture to verify multi-cycle sampled-noise normalization."""
import datetime,json
from analyze import H

def main():
    for tag, fund, ratio in [('984',984e6,1),('24ratio41',24e6,41),('24ratio1',24e6,1)]:
        p=H/'tb'/f'sampling_{tag}.scs';assert not p.exists()
        p.write_text(f'''simulator lang=spectre
global 0
// Verification fixture only: no PLL performance is represented by this RC.
simulatorOptions options temp=27 reltol=1e-5 vabstol=1e-7 iabstol=1e-13
VI (inp 0) vsource type=sine dc=0.6 ampl=0.5 freq=984M
R (inp out) resistor r=1k
C (out 0) capacitor c=20f
pss pss fund={fund:.15g} harms=64 maxacfreq=100G tstab=5n maxstep=1p method=traponly errpreset=conservative maxperiods=10 saveinit=yes
pn pnoise start=10k stop=492M dec=40 pnoisemethod=fullspectrum noisetype=sampled measurement=[edge] sampleratio={ratio} maxsideband=100
edge jitterevent trigger=[out] triggerthresh=0.6 triggernum=1 triggerdir=rise target=[out] jittercal=[Jee]
save inp out
saveOptions options save=selected
''',encoding='utf-8',newline='\n')
    r=dict(time=datetime.datetime.now().astimezone().isoformat(),question='Does a24MHz PSS superperiod with sampleratio41 reproduce the984MHz RC clock sampled-noise result?',
        circuit='LTI R1kohm/C20fF, noiseless984MHz sine0.6Vdc/0.5Vpeak,27C; not PLL devices.',
        cases={'sampling_984':dict(fund_hz=984e6,sampleratio=1), 'sampling_24ratio41':dict(fund_hz=24e6,sampleratio=41), 'sampling_24ratio1':dict(fund_hz=24e6,sampleratio=1,negative_control=True)},
        analytic='For the matched984MHz sampling rate, integrate sampled thermal PSD from10kHz to492MHz. Total variance approaches k*T/C; edge-time variance is voltage variance divided by squared sinusoidal crossing slew. Account for finite10kHz lower cutoff using the exact alias sum of the RC PSD.',
        limits=dict(correct_cases_relative_jitter_difference=.01,numeric_vs_spectre_jee=.015,numeric_vs_analytic=.02),
        scope='Tool/measurement verification only. Identical edges in an LTI fixture do not validate phase-dependent noise or all41 edge phases of the actual PLL. Deliberate ratio1 at24MHz integrated past12MHz is invalid bandwidth and must not become a performance result.',
        sources=['research/spectre_help/pnoise.txt: sampleratio definition', 'https://community.cadence.com/cadence_technology_forums/f/rf-design/47558/phase-noise-and-jitter-simulation/1372822'])
    (H/'results/sampling_fixture_protocol.json').write_text(json.dumps(r,indent=2)+'\n')

if __name__=='__main__':main()
