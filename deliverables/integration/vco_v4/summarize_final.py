"""Recompute R2 channel acceptance from immutable waveforms, not batch flags."""
from analyze import *
import csv

def main():
    selected=[];missing=[];rejected=[]
    targets=json.loads((H/'results/required_channels.json').read_text())
    for corner in ['tt','ss','ff']:
        for target in targets:
            k=target['k'];candidates=[]
            for p in sorted(R.glob(f'r2_{corner}_k{k}_c*/r2_{corner}_k{k}_c*')):
                if not (p/'result.json').exists():continue
                rec=json.loads((p/'result.json').read_text())
                if not rec['ok'] or not rec.get('remote_inputs_match'):continue
                tb=(p/'inputs'/f'{p.name}.scs').read_text()
                # These values define the R2 recipe; reject accidentally mixed revisions.
                assert 'fixed_c=1e-14' in tb and 'fine_w=4.5e-06' in tb,(p,'wrong revision')
                assert 'series_r=6.822430344006' in tb and 'core_w=0.00012' in tb
                windows=endpoint_windows(tb);lo=measure(p,windows[0]);hi=measure(p,windows[1])
                assert all(x['window_s'][1]-x['window_s'][0]>.99*(w[1]-w[0]) for x,w in zip([lo,hi],windows))
                a,b=sorted([lo['f_ghz']*1e9,hi['f_ghz']*1e9]);margin=min(target['fvco_hz']-a,b-target['fvco_hz'])
                log=(p/'spectre.out').read_text(errors='replace')
                status=re.findall(r'spectre completes with (\d+) errors?, (\d+) warnings?',log)
                assert status and int(status[-1][0])==0
                assert rec['remote_inputs_match']
                assert re.search(r'maxstep\s*=\s*2 ps',log) and re.search(r'method\s*=\s*trap\b',log)
                assert '-preset_override=maxstep' in rec['metadata']['spectre_command']
                code=sum(2**i for i in range(8) if f'VB{i} (b{i} 0) vsource dc=1.2' in tb)
                good=bool(lo['divide_valid'] and hi['divide_valid'] and margin>2e6)
                row=dict(**target,corner=corner,run=p.parent.name,case=p.name,code=code,low=lo,high=hi,
                         margin_hz=margin,numeric_guard_hz=2e6,pass_check=good,
                         effective_maxstep_s=2e-12,effective_solver='Spectre X AX; maxstep override; trap; reltol=1e-3')
                (candidates if good else rejected).append(row)
            if candidates:selected.append(max(candidates,key=lambda x:x['margin_hz']))
            else:missing.append(dict(corner=corner,**target))
    report=dict(revision='R2',conditions=dict(vdd_v=1.2,paired_corners=dict(tt=27,ss=60,ff=0),inductor_q_at_3p3ghz=5,
                fine_control_v=[.2,1.0],load='Actual selected transistor divider, sampler, CP, reference buffer and timing; CP output clamped; 10 fF divider output.',
                scope='Frequency coverage and correct division; not closed-loop capture, PLL jitter or total PLL power.'),
                target_points=99,passed_points=len(selected),all_pass=not missing,missing=missing,selected=selected,rejected_attempts=rejected)
    if selected:
        report['minimum_margin_hz']=min(x['margin_hz'] for x in selected)
        report['minimum_diff_pp_v']=min(x[y]['diff_pp_v'] for x in selected for y in ['low','high'])
        report['vco_power_range_mw']=[min(x[y]['vco_mw'] for x in selected for y in ['low','high']),max(x[y]['vco_mw'] for x in selected for y in ['low','high'])]
        report['measured_branch_power_range_mw']=[min(x[y]['total_mw'] for x in selected for y in ['low','high']),max(x[y]['total_mw'] for x in selected for y in ['low','high'])]
    (H/'results/final_validation.json').write_text(json.dumps(report,indent=2)+'\n')
    with (H/'results/channel_map.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['corner','K','M','target_vco_MHz','code','frequency_at_0p2V_MHz','frequency_at_1V_MHz','nearest_endpoint_margin_MHz','vco_power_max_mW','measured_branch_power_max_mW'])
        for x in selected:w.writerow([x['corner'],x['k'],x['m'],x['fvco_hz']/1e6,x['code'],x['low']['f_ghz']*1000,x['high']['f_ghz']*1000,x['margin_hz']/1e6,max(x[y]['vco_mw'] for y in ['low','high']),max(x[y]['total_mw'] for y in ['low','high'])])
    print('R2 passed',len(selected),'/ 99;', {c:sum(x['corner']==c for x in selected) for c in ['tt','ss','ff']})
    if len(missing)<10:print('Missing',[(x['corner'],x['k']) for x in missing])
if __name__=='__main__':main()
