"""Read current physical frontend gain probes; bracket a negative-feedback zero."""
from pathlib import Path
import hashlib,json,re
import numpy as np
from noise_utils import parse,cross
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def measurement(j,phase):
    rp=j/'result.json'
    if not rp.exists() or not json.loads(rp.read_text()).get('local_outputs_sha256'):return dict(case=j.name,phase_deg=phase,completed=False)
    r=json.loads(rp.read_text());log=(j/'spectre.out').read_text();assert r['remote_inputs_match'] and all(sha(j/'inputs'/k)==v for k,v in r['inputs_sha256'].items())
    out=dict(case=j.name,phase_deg=phase,completed=True,source_result=rp.relative_to(ROOT).as_posix(),source_sha256=sha(rp),
        simulator_completed=bool(r['ok'] and 'spectre completes with 0 errors' in log),pss_converged='The steady-state solution was achieved' in log,periodic_passed=False)
    if not out['simulator_completed'] or not out['pss_converged']:return out
    raw=j/(j.name+'.raw');td=parse(raw/'pss.td.pss');fd=parse(raw/'pss.fd.pss');t=td['time'];T=t[-1]-t[0]
    names=['ref','refb','vp','vn','sp','sn','hp','hn','vmid','pulse','out','amp_good','phase_good']
    endpoint=max(float(abs(td[n][-1]-td[n][0])) for n in names)
    rf=td['vp']-td['vn'];rf_edges=len(cross(t,rf,0));ref_edges=len(cross(t,td['refb']));pulse_edges=len(cross(t,td['pulse']))
    rf_harm=int(1+np.argmax(abs((fd['vp']-fd['vn'])[1:])))
    mean=lambda y:float(np.trapezoid(y,t)/T)
    out.update(period_s=float(T),endpoint_peak_v=endpoint,rf_rising_edges=rf_edges,ref_rising_edges=ref_edges,pulse_rising_edges=pulse_edges,rf_dominant_harmonic=rf_harm,
        mean_clamp_current_a=mean(td['VO:p']),pulse_duty=mean((td['pulse']>.6).astype(float)),
        mean_held_difference_v=mean(td['hp']-td['hn']),hold_range_v={n:[float(min(td[n])),float(max(td[n]))] for n in ['hp','hn']},
        amplitude_good_fraction=mean((td['amp_good']>.6).astype(float)),phase_good_fraction=mean((td['phase_good']>.6).astype(float)),
        td_sha256=sha(raw/'pss.td.pss'),fd_sha256=sha(raw/'pss.fd.pss'))
    out['periodic_passed']=bool(abs(T*24e6-1)<1e-7 and endpoint<1e-3 and rf_edges==164 and rf_harm==164 and ref_edges==1 and pulse_edges==1)
    return out

def main():
    pp=H/'results/frontend_gain_protocol.json';p=json.loads(pp.read_text());rows=[];dependencies=[];nets=[]
    for c in p['cases']:
        j=R/c['run']/c['case'];row=measurement(j,c['phase_deg']);rows.append(row)
        if not row['completed']:continue
        r=json.loads((j/'result.json').read_text());dependencies.append({k:v for k,v in r['inputs_sha256'].items() if k!=j.name+'.scs'})
        tb=(j/'inputs'/(j.name+'.scs')).read_text();tb=re.sub(r'\bphase_deg=\S+','phase_deg=PHASE',tb)
        nets.append(re.sub(r'\b(writefinal|writepss)="[^"]+"',r'\1="RUN_LOCAL_PATH"',tb))
    if dependencies:assert all(x==dependencies[0] for x in dependencies) and all(x==nets[0] for x in nets)
    complete=all(x['completed'] for x in rows);passed=complete and all(x['periodic_passed'] for x in rows);brackets=[]
    if passed:
        extended=rows+[dict(rows[0],phase_deg=rows[0]['phase_deg']+360)]
        for a,b in zip(extended[:-1],extended[1:]):
            ia=a['mean_clamp_current_a'];ib=b['mean_clamp_current_a'];slope=(ib-ia)/np.deg2rad(b['phase_deg']-a['phase_deg'])
            if ia*ib<0:
                phase=a['phase_deg']+(b['phase_deg']-a['phase_deg'])*(-ia)/(ib-ia)
                brackets.append(dict(phase_range_deg=[a['phase_deg'],b['phase_deg']],endpoint_current_a=[ia,ib],secant_a_per_rad=slope,
                    negative_feedback_candidate=bool(slope<0),interpolated_phase_deg=phase,interpolated_phase_unverified=True))
    selected=[x for x in brackets if x['negative_feedback_candidate']]
    out=dict(scope=__doc__,condition=p['condition'],protocol_sha256=sha(pp),control_clamp_v=p['control_clamp_v'],cases=rows,
        complete=complete,periodic_all_passed=bool(passed),zero_brackets=brackets,unique_negative_feedback_branch=bool(len(selected)==1),
        proposed_phase_deg=selected[0]['interpolated_phase_deg'] if len(selected)==1 else None,
        local_gain_verified=False,integrated_jitter_fs=None,full_pll_acceptance=False,limitations=p['limitations'])
    (H/'results/frontend_gain_validation.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2))

if __name__=='__main__':main()
