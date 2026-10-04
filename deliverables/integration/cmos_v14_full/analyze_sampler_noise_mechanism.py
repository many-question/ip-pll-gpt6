"""Separate independently verified sampler noise into clock inverter and switches."""
from pathlib import Path
import hashlib, json
import numpy as np

H = Path(__file__).resolve().parent
ROOT = H.parents[3]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    pp = H/'results/frontend_noise_r2_sampler_validation.json'
    ap = H/'results/frontend_noise_r2_all_validation.json'
    v, allv = json.loads(pp.read_text()), json.loads(ap.read_text())
    assert v['noise_valid'] and v['isolated_vs_all_group_check']['passed'] and v['excluded_noise_fraction']==0
    assert sha(ap)==v['isolated_vs_all_group_check']['all_result_sha256']
    src = ROOT/v['periodic']['source_result']; assert sha(src)==v['periodic']['source_sha256']
    assert sha(src.parent/(src.parent.name+'.raw')/'pn.pnoise')==v['noise_sha256']
    d = v['top_device_components_a2_per_hz']
    assert set(d)=={'XS.XI.MN','XS.XI.MP','XS.XSP.MN','XS.XSP.MP','XS.XSN.MN','XS.XSN.MP'}
    group = dict(clock_inverter=['XS.XI.MN','XS.XI.MP'], nmos_switches=['XS.XSP.MN','XS.XSN.MN'],
                 pmos_switches=['XS.XSP.MP','XS.XSN.MP'])
    psd = np.asarray(v['current_psd_a2_per_hz'])
    gp = {g:sum(np.asarray(d[n]['total']) for n in names) for g,names in group.items()}
    assert max(abs(sum(gp.values())/psd-1))<1e-7
    component = {}
    for g, names in group.items():
        terms = dict(flicker=np.zeros(3), channel_thermal=np.zeros(3), other=np.zeros(3))
        for n in names:
            for k,value in d[n].items():
                if k=='total':continue
                terms['flicker' if k=='fn' else 'channel_thermal' if k=='id' else 'other'] += np.asarray(value)
        assert max(abs(sum(terms.values())/gp[g]-1))<1e-7
        component[g] = {k:(val/gp[g]).tolist() for k,val in terms.items()}
    clock_fraction = gp['clock_inverter']/np.asarray(allv['current_psd_a2_per_hz'])
    out = dict(scope=__doc__, condition=v['condition'], isolated_source_sha256=sha(pp), all_source_sha256=sha(ap),
        offsets_hz=v['offsets_hz'], sampler_current_asd_pa_per_sqrt_hz=(np.sqrt(psd)*1e12).tolist(),
        group_fraction_of_sampler={g:(val/psd).tolist() for g,val in gp.items()},
        component_fraction_within_group=component,
        clock_inverter_fraction_of_all_frontend_variance=clock_fraction.tolist(),
        conditional_noiseless_clock_inverter_total_asd_change=(np.sqrt(1-clock_fraction)-1).tolist(),
        full_pll_acceptance=False, main_dut_modified=False,
        interpretation='This fixes the measured physical operating point and suppresses only clock-inverter noise as a mathematical diagnostic. It is not a sizing prediction or integrated jitter.',
        next_priority='Keep the already running reference-buffer and CP candidate comparisons ahead of a new sampler branch; their actual system benefit must be measured first.',
        limitations=['Only10kHz/1MHz/10MHz points; no RMS integration or dominant-contributor claim across the full band.',
            'Resizing the inverter changes load, timing, coupling and balance. It must not be represented by removing its noise at unchanged gain.',
            'Ideal RF replay/control clamp still exclude the actual LC and closed-loop noise transfer.'])
    dst=H/'results/sampler_noise_mechanism_validation.json'; assert not dst.exists()
    dst.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))


if __name__=='__main__':main()
