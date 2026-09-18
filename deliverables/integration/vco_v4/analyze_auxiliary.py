"""Summarize public defaults, loss sensitivity and Pnoise numerical checks."""
from analyze import *

def main():
    a=measure(R/'r2_checks/r2_public_defaults');b=measure(R/'r2_checks/r2_explicit_defaults')
    defaults=dict(public=a,explicit=b,frequency_difference_hz=(a['f_ghz']-b['f_ghz'])*1e9,
                  pass_check=abs(a['f_ghz']-b['f_ghz'])<1e-6 and abs(a['vco_mw']-b['vco_mw'])<1e-4)
    sensitivity=[]
    for q in [3,8]:
        for code in [6,243]:
            p=R/'r2_checks'/f'r2_sensitivity_q{q}_c{code}'
            if (p/'result.json').exists():sensitivity.append(dict(q_at_3p3ghz=q,code=code,corner='SS60',**measure(p)))
    noise=json.loads((H/'results/noise_summary.json').read_text());by_case={x['case']:x for x in noise}
    comparisons=[]
    spectra=np.load(H/'results/noise_spectra.npz')
    pairs=[(f'r2_noise_tt_c{c}',f'r2_noise_tight_c{c}') for c in [6,243]]
    pairs.append(('r2_noise_divider','r2_noise_divider_refined'))
    for first,second in pairs:
        if first not in by_case or second not in by_case:continue
        a=by_case[first];b=by_case[second]
        ka=a['run']+'__'+first;kb=b['run']+'__'+second
        fa=spectra[ka+'_f'];fb=spectra[kb+'_f'];la=10*np.log10(spectra[ka+'_L']);lb=10*np.log10(spectra[kb+'_L'])
        mask=(fb>=fa[0])&(fb<=fa[-1]);diff=lb[mask]-np.interp(np.log(fb[mask]),np.log(fa),la)
        # 0.1 dB is an internal numerical consistency screen, not a design spec.
        maxchange=float(max(abs(diff)))
        comparisons.append(dict(baseline=first,refinement=second,frequencies_hz=fb[mask].tolist(),phase_noise_change_db=diff.tolist(),maximum_absolute_change_db=maxchange,
            carrier_frequency_change_hz=b['frequency_hz']-a['frequency_hz'],vco_power_change_mw=b['vco_power_mw']-a['vco_power_mw'],
            pass_check=bool(maxchange<.1 and abs(b['frequency_hz']-a['frequency_hz'])<1e6)))
    (H/'results/auxiliary_validation.json').write_text(json.dumps(dict(public_defaults=defaults,q_sensitivity=sensitivity,noise_precision=comparisons),indent=2)+'\n')
    print('Public defaults equal:',defaults['pass_check'])
    for x in sensitivity:print('Q',x['q_at_3p3ghz'],'code',x['code'],'GHz',x.get('f_ghz'),'Vpp',x.get('diff_pp_v'))
    for x in comparisons:print(x['refinement'],'max PN change dB',x['maximum_absolute_change_db'],'pass',x['pass_check'])

if __name__=='__main__':main()
