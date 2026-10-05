"""Validate activation of actual native device noise in the complete original PLL."""
from pathlib import Path
import hashlib,json,math,re
import numpy as np
from transient_diagnostics import effective,recovery
from noise_utils import cross
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def noise_band_diagnostic(protocol,log):
    """Separate strict protocol agreement from a documented duration floor.

    This diagnosis only supports the activation test. It never establishes
    stationarity, observable low-offset coverage, or integrated jitter.
    """
    e=effective(log);requested=protocol['noisefmin_hz']
    floor=1/protocol['stop_s'];expected=max(requested,floor)
    actual=e.get('noisefmin');maximum=e.get('noisefmax')
    notices=re.findall(r"Specified 'noisefmin' is smaller than 1/stop time\.\s*"
                       r"'noisefmin' has been changed to [^\n]+",log)
    same=lambda a,b:isinstance(a,(int,float)) and math.isclose(a,b,rel_tol=1e-12,abs_tol=0)
    matched=same(actual,requested) and same(maximum,protocol['noisefmax_hz'])
    documented_floor=(requested<floor and same(actual,expected) and bool(notices)
                      and same(maximum,protocol['noisefmax_hz']))
    return dict(requested_min_hz=requested,effective_min_hz=actual,
                requested_max_hz=protocol['noisefmax_hz'],effective_max_hz=maximum,
                duration_floor_hz=floor,requested_configuration_matched=matched,
                documented_duration_floor_applied=documented_floor,
                activation_configuration_understood=matched or documented_floor,
                adjustment_notices=notices,
                low_offset_coverage_established=False,integrated_jitter_fs=None)

def main():
    pp=H/'results/full_pll_noise_activation_probe_protocol.json';p=json.loads(pp.read_text())
    j=R/p['run']/p['case'];rp=j/('completed_result.json' if (j/'completed_result.json').exists() else 'result.json');r=json.loads(rp.read_text());log=(j/'spectre.out').read_text()
    out=dict(scope=__doc__,protocol_sha256=sha(pp),source_result=rp.relative_to(ROOT).as_posix(),source_result_sha256=sha(rp),
        log_sha256=sha(j/'spectre.out'),completed=r['ok'],recovery=recovery(log),effective=effective(log),
        noise_activation_log_times_s=[float(s) for s in re.findall(r'tran noise is turning ON on time ([0-9.eE+-]+)\.',log)],
        noise_band=noise_band_diagnostic(p,log),
        passed=False,activation_method_passed=False,full_pll_acceptance=False,integrated_jitter_fs=None,limitations=p['limitations'])
    if not out['noise_band']['requested_configuration_matched']:
        out['limitations'].append('Effective native-noise band differs from the requested protocol; strict protocol pass remains false. The separate activation-method result cannot establish noise-band or jitter acceptance.')
    if r['ok']:
        cache=j/'waveforms.npz';assert sha(cache)==r['local_outputs_sha256'][cache.name]
        with np.load(cache) as z:d={k:z[k] for k in z.files if k!='units'}
        t=d['time'];sel=t>p['noise_start_s']+1e-12
        initial={}
        for line in (j/'inputs'/p['text_state']).read_text().splitlines():
            if line.strip() and not line.startswith('#'):
                z=line.split();initial[z[0]]=float(z[1])
        deltas={k:abs(float(d[k][0])-initial[k]) for k in d if k in initial and ':' not in k}
        logic={k:dict(min_v=float(min(d[k][sel])),max_v=float(max(d[k][sel]))) for k in ['qualified','frequency_good','amp_good','XP.XC.phase_held','XP.XC.acquired','XP.en','XP.restart','range_error']}
        e=cross(t[sel],d['out'][sel],.6)
        checks=dict(completed=t[-1]>=p['stop_s']-1e-15,clean=out['recovery']['numerically_clean'],
            initialized=t[0]==0 and max(deltas.values())<1e-9,
            activated=out['noise_activation_log_times_s']==[p['noise_start_s']],
            states_held=all(logic[k]['min_v']>1 for k in ['qualified','frequency_good','amp_good','XP.XC.phase_held','XP.XC.acquired','XP.en']) and all(max(abs(logic[k]['min_v']),abs(logic[k]['max_v']))<.2 for k in ['XP.restart','range_error']),
            provenance=r['remote_inputs_match'] and not r.get('native_state'),
            noise_configuration=out['noise_band']['requested_configuration_matched'],
            no_replaced_functional_modules=all(not k.endswith('.va') for k in r['inputs_sha256']))
        checks={k:bool(v) for k,v in checks.items()}
        activation_checks={k:v for k,v in checks.items() if k!='noise_configuration'}
        activation_checks['understood_effective_noise_configuration']=out['noise_band']['activation_configuration_understood']
        out.update(cache_sha256=sha(cache),logic=logic,checks=checks,passed=all(checks.values()),
            activation_method_checks=activation_checks,activation_method_passed=all(activation_checks.values()),
            initial_compared_nodes=len(deltas),initial_max_delta_v=max(deltas.values()),noise_output_edges=len(e),
            period_range_ps=[float(min(np.diff(e))*1e12),float(max(np.diff(e))*1e12)])
    else:out['errors']=r['errors']
    (H/'results/full_pll_noise_activation_probe_validation.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
if __name__=='__main__':main()
