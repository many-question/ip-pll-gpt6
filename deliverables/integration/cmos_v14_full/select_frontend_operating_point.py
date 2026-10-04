"""Select the smallest measured negative-slope bracket, retaining failed probes.

Each invocation creates an immutable search record. It can generate one fresh
PSS point; it does not submit a job or accept an interpolated operating point.
"""
from pathlib import Path
import argparse,datetime,hashlib,json,re
import numpy as np
from analyze_frontend_gain import measurement

H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def canonical(s):
    s=re.sub(r'\bphase_deg=\S+','phase_deg=PHASE',s)
    return re.sub(r'\b(writefinal|writepss)="[^"]+"',r'\1="STATE"',s)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--iteration',type=int,required=True);ap.add_argument('--build-point',action='store_true');a=ap.parse_args();assert 1<=a.iteration<=10
    base=R/'frontendgain01/frontend_gain_p0_tt';bm=json.loads((base/'result.json').read_text());dep={k:v for k,v in bm['inputs_sha256'].items() if k!=base.name+'.scs'}
    bt=canonical((base/'inputs'/(base.name+'.scs')).read_text());rows=[];failed=[]
    for rp in sorted(R.glob('frontend*/*/result.json')):
        j=rp.parent
        if not re.match(r'frontend_(gain_p|local\d+_|root\d+_)',j.name):continue
        r=json.loads(rp.read_text())
        if not r.get('local_outputs_sha256'):continue
        s=(j/'inputs'/(j.name+'.scs')).read_text();phase=float(re.search(r'\bphase_deg=(\S+)',s)[1])
        assert {k:v for k,v in r['inputs_sha256'].items() if k!=j.name+'.scs'}==dep
        assert canonical(s)==bt
        row=measurement(j,phase);row['run']=j.parent.name
        if row['periodic_passed']:rows.append(row)
        else:
            if (j/'cancellation.json').exists():row['intentional_cancellation']=json.loads((j/'cancellation.json').read_text())
            failed.append(row)
    rows.sort(key=lambda x:x['phase_deg']);assert len(rows)>=2 and len(set(x['phase_deg'] for x in rows))==len(rows)
    bracket=[]
    for lo,hi in zip(rows[:-1],rows[1:]):
        if lo['mean_clamp_current_a']>0>hi['mean_clamp_current_a']:
            slope=(hi['mean_clamp_current_a']-lo['mean_clamp_current_a'])/np.deg2rad(hi['phase_deg']-lo['phase_deg'])
            phase=lo['phase_deg']-np.rad2deg(lo['mean_clamp_current_a']/slope)
            bracket.append(dict(lo=lo,hi=hi,secant_a_per_rad=float(slope),interpolated_phase_deg=float(phase)))
    assert len(bracket)==1,('Ambiguous measured branch',len(bracket))
    pair=bracket[0];closest=min([pair['lo'],pair['hi']],key=lambda x:abs(x['mean_clamp_current_a']))
    target=1e-10;balanced=abs(closest['mean_clamp_current_a'])<target
    proposal=closest['phase_deg'] if balanced else pair['interpolated_phase_deg']
    method='measured point' if balanced else 'bracketing secant'
    local_model=None
    # Use a third nearby measured point to reduce slow false-position progress
    # on a curved I(phi) branch. A fit is only a proposal for a fresh PSS run.
    endpoints=[pair['lo'],pair['hi']]
    other=[r for r in rows if r['phase_deg'] not in [x['phase_deg'] for x in endpoints]]
    nearby=endpoints+sorted(other,key=lambda x:abs(x['phase_deg']-pair['interpolated_phase_deg']))[:1]
    nearby.sort(key=lambda x:x['phase_deg'])
    if not balanced and len(nearby)==3 and nearby[-1]['phase_deg']-nearby[0]['phase_deg']<=45:
        origin=closest['phase_deg'];x=np.array([r['phase_deg']-origin for r in nearby])
        y=np.array([r['mean_clamp_current_a'] for r in nearby]);coef=np.polyfit(x,y,2)
        roots=np.roots(coef)
        candidates=[float(z.real+origin) for z in roots if abs(z.imag)<1e-9 and
                    pair['lo']['phase_deg']<z.real+origin<pair['hi']['phase_deg'] and
                    np.polyval(np.polyder(coef),z.real)<0]
        local_model=dict(measured_points=[dict(case=r['case'],phase_deg=r['phase_deg'],current_a=r['mean_clamp_current_a']) for r in nearby],
                         origin_deg=origin,coefficients_a_per_degree_powers=coef.tolist(),admissible_roots_deg=candidates)
        if len(candidates)==1 and np.all(np.polyval(np.polyder(coef),x)<0):
            proposal=candidates[0];method='quadratic interpolation within measured negative-slope bracket'
    p0=json.loads((H/'results/frontend_gain_protocol.json').read_text())
    out=dict(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),iteration=a.iteration,
             condition=p0['condition'],control_clamp_v=p0['control_clamp_v'],cases=rows,failed_or_stopped_cases=failed,
             complete=True,periodic_all_passed=True,unique_negative_feedback_branch=True,measured_bracket=pair,
             proposed_phase_deg=proposal,proposed_phase_method=method,local_model=local_model,
             closest_measured_point=closest,search_current_target_a=target,
             current_search_target_met=balanced,proposed_phase_is_measured=balanced,local_gain_verified=False,
             integrated_jitter_fs=None,full_pll_acceptance=False,limitations=p0['limitations']+
             ['The current search target is an engineering precheck; local gain and phase-error acceptance still need actual measurements.'])
    if a.build_point:
        assert not balanced,'Use the measured point for local slope verification instead of duplicating it'
        assert all(abs(proposal-x['phase_deg'])>1e-7 for x in rows),'Proposed point duplicates evidence'
        case=f'frontend_root{a.iteration}_tt';run=f'frontendroot0{a.iteration}';dst=H/'tb'/(case+'.scs');assert not dst.exists()
        source=H/'tb/frontend_gain_p0_tt.scs';tb,n=re.subn(r'\bphase_deg=\S+',f'phase_deg={proposal:.17g}',source.read_text());assert n==1
        dst.write_text(tb,encoding='utf-8',newline='\n');out['next_point']=dict(run=run,case=case,phase_deg=proposal,tb_sha256=sha(dst))
    dst=H/'results'/f'frontend_op_search_{a.iteration}.json';assert not dst.exists();dst.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(dict(record=dst.name,bracket_deg=[pair['lo']['phase_deg'],pair['hi']['phase_deg']],proposal=proposal,current_target_met=balanced,next_point=out.get('next_point')),indent=2))

if __name__=='__main__':main()
