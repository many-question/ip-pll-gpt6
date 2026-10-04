"""Model-assisted sensitivity of unmeasured sub-Hz flicker-pole centres.

Measured samples define the spectrum everywhere used directly. An explicit
B + A / distance**alpha fit is extrapolated only inside each unmeasured 1 Hz
half-window. Swept cutoffs are assumptions, never asserted device physics.
"""
from pathlib import Path
import hashlib,json
import numpy as np
from analyze_rt4_harmonic_neighbours import load
from analyze_vco_bias_band import integral
H=Path(__file__).resolve().parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def fit(delta,s):
    scale=max(s);y=s/scale;best=None
    for alpha in np.linspace(.5,2,6001):
        X=np.column_stack([np.ones(len(delta)),delta**(-alpha)])
        coef=np.linalg.lstsq(X,y,rcond=None)[0]
        if min(coef)<0:continue
        estimate=X@coef;loss=float(np.sum((estimate-y)**2))
        if best is None or loss<best[0]:best=(loss,alpha,coef,estimate)
    assert best is not None
    loss,alpha,coef,estimate=best
    return dict(background_s2_per_hz=float(coef[0]*scale),excess_coefficient=float(coef[1]*scale),
        exponent=float(alpha),max_relative_fit_error=float(max(abs(estimate/y-1))),
        exponent_search_bounds=[.5,2.],fit_at_search_boundary=bool(alpha in [.5,2.]),
        fitted_timing_psd_s2_per_hz=(estimate*scale).tolist())

def main():
    pp=H/'results/rt4_harmonic_neighbour_validation.json';p=json.loads(pp.read_text());assert p['same_fresh_pss_verified']
    a=load('pn');b=load('pnnear');assert a['manifest_sha256']==p['main_snapshot_sha256'] and b['manifest_sha256']==p['near_snapshot_sha256']
    f=np.concatenate([a['f'],b['f']]);s=np.concatenate([a['st'],b['st']]);order=np.argsort(f);f=f[order];s=s[order]
    assert np.all(np.diff(f)>0)
    # Integrate disjoint measured regions. No trapezoid bridges an unknown centre.
    intervals=[[1e4,164e6-1],[164e6+1,328e6-1],[328e6+1,492e6-1]]
    measured=sum(integral(f,s,lo,hi) for lo,hi in intervals);models=[]
    for side in p['sides']:
        delta=np.asarray(side['distance_hz']);spec=np.asarray(side['timing_psd_s2_per_hz']);q=fit(delta,spec)
        assert q['max_relative_fit_error']<.01 and not q['fit_at_search_boundary']
        models.append(dict(harmonic_hz=side['harmonic_hz'],side=side['side'],measured_distance_hz=delta.tolist(),**q))
    sweep=[]
    for cutoff in [1.,1e-3,1e-6,1e-9]:
        variances=[]
        for q in models:
            alpha=q['exponent'];power=np.log(1/cutoff) if abs(alpha-1)<1e-12 else (1-cutoff**(1-alpha))/(1-alpha)
            variances.append(q['background_s2_per_hz']*(1-cutoff)+q['excess_coefficient']*power)
        central=sum(variances);rms=float(np.sqrt(measured+central)*1e15)
        sweep.append(dict(assumed_minimum_distance_hz=cutoff,modelled_centre_variance_s2=central,
            modelled_centre_rms_fs=float(np.sqrt(central)*1e15),conditional_total_rms_fs=rms,
            change_from_measured_regions_fs=rms-float(np.sqrt(measured)*1e15)))
    out=dict(scope=__doc__,source_validation_sha256=sha(pp),condition=p['condition'],measured_intervals_hz=intervals,
        measured_regions_rms_fs=float(np.sqrt(measured)*1e15),
        original_log_grid_rms_fs=p['provisional_main_log_grid_rms_fs'],models=models,assumption_sweep=sweep,
        sensitivity_range_hz=[1e-9,1],max_conditional_total_change_fs=max(x['change_from_measured_regions_fs'] for x in sweep),
        physical_cutoff_verified=False,model_extrapolation_is_measurement=False,qualified_full_band_jitter_fs=None,full_pll_acceptance=False,
        interpretation='Finite neighbour scans plus this explicit extrapolation sensitivity do not suggest a material hidden central contribution at the tested assumptions. Prioritize actualLC/closedloop work; keep the model boundary visible.',
        limitations=['B+A/delta**alpha is fitted over measured1..10000Hz distance and extrapolated over up to9decades; no such sub-Hz measurement was made.',
            'A constant PSD saturation below a physical cutoff is not implied; the swept cutoff is a lower integration bound.',
            'This calculation does not establish an absolute mathematical bound or justify calling continuous noise a discrete spur.',
            'Sparse near-pole quadrature, all-band numerical precision and genuine six-edge cyclostationary covariance remain distinct checks.'])
    (H/'results/rt4_pole_sensitivity.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k!='models'},indent=2))

if __name__=='__main__':main()
