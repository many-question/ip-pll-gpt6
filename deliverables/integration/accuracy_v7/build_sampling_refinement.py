"""Predeclare joint bandwidth/grid refinement after the scalar-Jee discrepancy."""
import datetime,json
from analyze import H

def main():
    for old,new in [('984','984_fine'),('24ratio41','24ratio41_fine')]:
        p=H/'tb'/f'sampling_{new}.scs';assert not p.exists()
        s=(H/'tb'/f'sampling_{old}.scs').read_text().replace('maxacfreq=100G','maxacfreq=1T').replace('maxstep=1p','maxstep=250f')
        p.write_text(s,encoding='utf-8',newline='\n')
    r=dict(time=datetime.datetime.now().astimezone().isoformat(),reason='Original predeclared combined check fails: auto Jee differs from the full10kHz-492MHz spectral integral for fund24MHz/ratio41. The scalar matches integration only through the last grid point below12MHz. Preserve the failure.',
        cases={'sampling_984_fine':dict(fund_hz=984e6,sampleratio=1),'sampling_24ratio41_fine':dict(fund_hz=24e6,sampleratio=41)},
        changed='Joint maxacfreq100GHz->1THz and maxstep1ps->0.25ps; same RC/circuit, temperature, band and noise settings.',
        new_diagnostic_limits=dict(psd_integral_vs_analytic=.005,between_fundamental_psd_integrals=.005,auto_jee_vs_actual_grid_clipped_integral=.015),
        scope='Separate PSD normalization and integration-band diagnostic, not a relaxed pass for the original auto-Jee check or PLL jitter signoff. Values beyond nominal bandwidth are solver accuracy controls, not a physical1THz circuit claim.')
    (H/'results/sampling_refinement_protocol.json').write_text(json.dumps(r,indent=2)+'\n')

if __name__=='__main__':main()
