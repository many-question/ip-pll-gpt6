"""Measure current balance and local gain; retain failed brackets or nonlinearity."""
from pathlib import Path
import argparse,hashlib,json,re
import numpy as np
from analyze_frontend_gain import measurement

H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--round',type=int,choices=[1,2,3],default=1);a=ap.parse_args()
    pp=H/'results'/f'frontend_local_gain{a.round}_protocol.json'
    if not pp.exists():print('Local gain protocol pending');return
    p=json.loads(pp.read_text());proof=H/'results'/p['source_validation'];assert sha(proof)==p['source_validation_sha256']
    rows=[];dependencies=[];nets=[]
    for c in p['cases']:
        j=R/c['run']/c['case'];row=measurement(j,c['phase_deg']);rows.append(row)
        if not row['completed']:continue
        r=json.loads((j/'result.json').read_text());dependencies.append({k:v for k,v in r['inputs_sha256'].items() if k!=j.name+'.scs'})
        s=(j/'inputs'/(j.name+'.scs')).read_text();s=re.sub(r'\bphase_deg=\S+','phase_deg=PHASE',s)
        nets.append(re.sub(r'\b(writefinal|writepss)="[^"]+"',r'\1="STATE"',s))
    if dependencies:
        base=R/'frontendgain01/frontend_gain_p0_tt';r=json.loads((base/'result.json').read_text())
        expected={k:v for k,v in r['inputs_sha256'].items() if k!=base.name+'.scs'}
        assert all(x==expected for x in dependencies) and all(x==nets[0] for x in nets)
        s=(base/'inputs'/(base.name+'.scs')).read_text();s=re.sub(r'\bphase_deg=\S+','phase_deg=PHASE',s)
        assert nets[0]==re.sub(r'\b(writefinal|writepss)="[^"]+"',r'\1="STATE"',s)
    complete=all(x['completed'] for x in rows);passed=complete and all(x['periodic_passed'] for x in rows)
    out=dict(scope=__doc__,round=a.round,condition=p['condition'],protocol_sha256=sha(pp),control_clamp_v=p['control_clamp_v'],
             cases=rows,complete=complete,periodic_all_passed=bool(passed),unique_negative_feedback_branch=False,
             proposed_phase_deg=None,local_gain_verified=False,balanced_center_verified=False,
             integrated_jitter_fs=None,full_pll_acceptance=False,limitations=p['limitations'])
    if passed:
        x=np.deg2rad([r['phase_deg'] for r in rows]);y=np.array([r['mean_clamp_current_a'] for r in rows])
        slopes=np.diff(y)/np.diff(x);gain=(y[-1]-y[0])/(x[-1]-x[0])
        curvature=float(abs(slopes[1]-slopes[0])/abs(gain)) if gain else None
        bracket=bool(y[0]>0>y[-1] and np.all(slopes<0))
        root=None;secant_root=None;root_method=None
        if bracket:
            index=0 if y[1]<0 else 1
            secant_root=float(np.rad2deg(x[index]-y[index]/slopes[index]));root=secant_root;root_method='bracketing secant'
            coeff=np.polyfit(x-x[1],y,2)
            roots=np.roots(coeff)
            admissible=[float(z.real) for z in roots if abs(z.imag)<1e-10 and x[0]-x[1]<=z.real<=x[-1]-x[1] and np.polyval(np.polyder(coeff),z.real)<0]
            if len(admissible)==1:
                root=float(np.rad2deg(x[1]+admissible[0]));root_method='quadratic interpolation of three measured points'
        valid=bool(bracket and curvature<p['engineering_gates']['local_half_slope_relative_difference'])
        residual=float(y[1]/gain) if gain else None
        balanced=bool(valid and abs(residual)<p['engineering_gates']['residual_phase_rad'])
        out.update(unique_negative_feedback_branch=bracket,proposed_phase_deg=root,
                   proposed_phase_method=root_method,proposed_phase_unverified=True,bracket_secant_phase_deg=secant_root,
                   signed_gain_a_per_rf_rad=float(gain),kphi_magnitude_a_per_rf_rad=float(abs(gain)),
                   half_slopes_a_per_rf_rad=slopes.tolist(),half_slope_relative_difference=curvature,
                   center_residual_current_a=float(y[1]),linearized_center_phase_error_rad=residual,
                   local_gain_verified=valid,balanced_center_verified=balanced,
                   engineering_gates=p['engineering_gates'])
    (H/'results'/f'frontend_local_gain{a.round}_validation.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2))

if __name__=='__main__':main()
