"""Compare accepted PSS against the continued1ps orbit at the same reference edge."""
import json
import numpy as np
from analyze import H,R,parse,cross
def main():
    validation=json.loads((H/'results/validation.json').read_text());rows=[]
    sample=H/'results/settle_1ps_continue_1ps_samples.npz'
    if not sample.exists():return
    with np.load(sample) as z:
        keep=z['time']>3e-6;cp=float(np.mean(z['obsctrl'][keep]));phase=float(np.angle(np.mean(np.exp(1j*z['obsphase'][keep]))))
    for x in validation:
        if not x['case'].startswith('clamp8_') or not (x.get('periodic') or {}).get('pass_loop_periodic'):continue
        d=parse(R/x['run']/x['case']/(x['case']+'.raw')/'pss.td.pss');t=d['time'];T=t[-1]-t[0]
        ve=cross(t,d['vp']-d['vn']);ve=np.r_[ve-T,ve,ve+T];re=cross(t,d['refb'],.6)
        assert len(re)==1
        idx=np.searchsorted(ve,re[0])-1
        ph=2*np.pi*(re[0]-ve[idx])/(ve[idx]-ve[idx-1]);cv=float(np.interp(re[0],t,d['ctrl']))
        dp=float(np.angle(np.exp(1j*(ph-phase))));dv=cv-cp
        rows.append(dict(case=x['case'],pss_phase_at_reference_rad=float(ph),pss_control_at_reference_v=cv,transient_phase_mean_rad=phase,transient_control_mean_v=cp,
            phase_difference_rad=dp,control_difference_v=dv,pass_orbit_agreement=bool(abs(dp)<.02 and abs(dv)<.005),
            criteria='Additional orbit comparison: wrapped reference-sampled phase difference<0.02rad, sampled control difference<5mV. Compare PSS to cumulative7-8us1ps continuation; no stability/noise/capture signoff.'))
    (H/'results/periodic_orbit_comparison.json').write_text(json.dumps(rows,indent=2)+'\n')
    pairs=[]
    for i,a in enumerate(rows):
        for b in rows[i+1:]:
            dp=float(np.angle(np.exp(1j*(a['pss_phase_at_reference_rad']-b['pss_phase_at_reference_rad']))))
            dv=a['pss_control_at_reference_v']-b['pss_control_at_reference_v']
            pairs.append(dict(a=a['case'],b=b['case'],reference_phase_delta_rad=dp,reference_control_delta_v=dv,
                note='Descriptive comparison at the same reference edge. Both runs use1ps maxstep; boundary phase/stabilization time and absolute tolerances may differ. Not independent timestep refinement or a single-factor causal test.'))
    (H/'results/accepted_pss_comparison.json').write_text(json.dumps(pairs,indent=2)+'\n')
    print(json.dumps(rows,indent=2))
if __name__=='__main__':main()
