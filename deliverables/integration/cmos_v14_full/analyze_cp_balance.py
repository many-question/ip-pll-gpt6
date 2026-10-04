"""Measure the phase/current zero and local gain of a physical CP candidate."""
from pathlib import Path
import argparse,hashlib,json,re
import numpy as np
from analyze_frontend_gain import measurement
from build_cp_balance import normal,operating_body
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
without_phase=lambda s:re.sub(r'\bphase_deg=\S+','phase_deg=PHASE',normal(s))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--variant',choices=['fasttail','mid70'],required=True)
    ap.add_argument('--round',type=int,choices=[1,2,3],default=1);a=ap.parse_args();prefix='cp_'+a.variant
    pp=H/'results'/f'{prefix}_balance{a.round}_protocol.json';p=json.loads(pp.read_text())
    assert sha(H/'results'/p['source_validation'])==p['source_validation_sha256']
    assert sha(H/'results'/p['operating_validation'])==p['operating_validation_sha256']
    src=ROOT/p['source_result'];assert sha(src)==p['source_result_sha256']
    original=src.parent/'inputs'/(src.parent.name+'.scs');assert sha(original)==p['source_input_sha256']
    expected=without_phase(operating_body(original.read_text()));rows=[]
    for c in p['cases']:
        j=ROOT/'research/runs/spectre_cmos_v14_full'/c['run']/c['case'];m=measurement(j,c['phase_deg']);rows.append(m)
        if not m['completed']:continue
        r=json.loads((j/'result.json').read_text());assert not r.get('periodic_state') and not r.get('native_state')
        assert {k:v for k,v in r['inputs_sha256'].items() if k!=j.name+'.scs'}==p['dependencies_sha256']
        tb=H/'tb'/(j.name+'.scs');assert sha(tb)==c['tb_sha256']
        actual=(j/'inputs'/tb.name).read_text();assert normal(actual)==normal(tb.read_text()) and without_phase(actual)==expected
        m['physical_trial_verified']=True
    complete=all(x['completed'] for x in rows);passed=complete and all(x['periodic_passed'] for x in rows)
    out=dict(scope=__doc__,variant=a.variant,round=a.round,condition=p['condition'],protocol_sha256=sha(pp),
        control_clamp_v=p['control_clamp_v'],cases=rows,complete=complete,periodic_all_passed=bool(passed),
        unique_negative_feedback_branch=False,proposed_phase_deg=None,local_gain_verified=False,balanced_center_verified=False,
        noise_measured=False,integrated_jitter_fs=None,full_pll_acceptance=False,main_dut_modified=False,limitations=p['limitations'])
    if passed:
        x=np.deg2rad([z['phase_deg'] for z in rows]);y=np.array([z['mean_clamp_current_a'] for z in rows]);slopes=np.diff(y)/np.diff(x)
        gain=(y[-1]-y[0])/(x[-1]-x[0]);curvature=float(abs(slopes[1]-slopes[0])/abs(gain)) if gain else None
        bracket=bool(y[0]>0>y[-1] and np.all(slopes<0));phase=None;method=None
        if bracket:
            k=0 if y[1]<0 else 1;phase=float(np.rad2deg(x[k]-y[k]/slopes[k]));method='Bracketing secant from measured currents.'
            coeff=np.polyfit(x-x[1],y,2);roots=np.roots(coeff)
            admissible=[float(z.real) for z in roots if abs(z.imag)<1e-10 and x[0]-x[1]<=z.real<=x[-1]-x[1] and np.polyval(np.polyder(coeff),z.real)<0]
            if len(admissible)==1:phase=float(np.rad2deg(x[1]+admissible[0]));method='Quadratic interpolation of three measured currents.'
        valid=bool(bracket and curvature<p['engineering_gates']['local_half_slope_relative_difference'])
        residual=float(y[1]/gain) if gain else None
        balanced=bool(valid and abs(residual)<p['engineering_gates']['residual_phase_rad'] and rows[1]['amplitude_good_fraction']>.999 and rows[1]['phase_good_fraction']>.999)
        out.update(unique_negative_feedback_branch=bracket,proposed_phase_deg=phase,proposed_phase_method=method,proposed_phase_unverified=True,
            signed_gain_a_per_rf_rad=float(gain),kphi_magnitude_a_per_rf_rad=float(abs(gain)),half_slopes_a_per_rf_rad=slopes.tolist(),
            half_slope_relative_difference=curvature,center_residual_current_a=float(y[1]),linearized_center_phase_error_rad=residual,
            local_gain_verified=valid,balanced_center_verified=balanced,engineering_gates=p['engineering_gates'])
    (H/'results'/f'{prefix}_balance{a.round}_validation.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))

if __name__=='__main__':main()
