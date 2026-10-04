"""Compare deterministic drift with independently toggled strobes and event observer."""
from pathlib import Path
import hashlib,json,re
import numpy as np
from noise_utils import cross
from reference_modulation_utils import fit_edges
from psf_trace_units import trace_units
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=json.loads((H/'results/core_mesh_protocol.json').read_text())
basej=R/p['baseline_run']/p['baseline_case'];baser=json.loads((basej/'result.json').read_text())
specs=[dict(case=p['baseline_case'],run=p['baseline_run'],observer=False,strobe=False)]+[dict(x,run=p['run']) for x in p['cases']]
baseunits=trace_units(basej/(basej.name+'.raw')/'tran.tran.tran')
grid=np.linspace(250e-9,500e-9,250001);T=250e-9;rows=[]
def canonical(body):
    body=re.sub(r'(readic|writefinal)="[^"]+"',r'\1="__PATH__"',body)
    body=body.replace(' strobeperiod=2n strobeoutput=all','')
    return '\n'.join(line.strip() for line in body.splitlines() if line.strip() and not line.strip().startswith('//') and not line.startswith(('ahdl_include "lc_loop_observer.va"','XOBS (','save obsphase ')))
basebody=canonical((basej/'inputs'/(basej.name+'.scs')).read_text())
def states(path):
    out={}
    for line in path.read_text().splitlines():
        z=line.split()
        if z and z[0] in p['physical_state_units']:
            u='A' if re.search(r'#unit\s+A\s*$',line) else 'V'
            assert u==p['physical_state_units'][z[0]];out[z[0]]=float(z[1])
    assert set(out)==set(p['physical_state_units']);return out
for item in specs:
    j=R/item['run']/item['case'];rp=j/'result.json'
    if not rp.exists():continue
    r=json.loads(rp.read_text())
    if not r.get('local_outputs_sha256'):continue
    assert r['ok'] and r['remote_inputs_match'] and sha(j/'waveforms.npz')==r['local_outputs_sha256']['waveforms.npz']
    assert r['inputs_sha256']['core_gear_dense_period_tt.ic']==p['seed_sha256']
    ex={j.name+'.scs',basej.name+'.scs','lc_loop_observer.va'}
    assert {k:v for k,v in r['inputs_sha256'].items() if k not in ex}=={k:v for k,v in baser['inputs_sha256'].items() if k not in ex}
    log=(j/'spectre.out').read_text();assert 'spectre completes with 0 errors' in log
    body=(j/'inputs'/(j.name+'.scs')).read_text()
    assert ('XOBS (' in body)==item['observer'] and ('strobeperiod=2n' in body)==item['strobe']
    assert canonical(body)==basebody
    assert re.search(r'^\s*method\s*=\s*gear2only\s*$',log,re.M)
    with np.load(j/'waveforms.npz') as z:d={k:z[k] for k in z.files}
    t=d['time'];assert abs(t[0]-250e-9)<1e-14 and abs(t[-1]-750e-9)<1e-14
    units=trace_units(j/(j.name+'.raw')/'tran.tran.tran')
    assert {k:units[k] for k in baseunits}==baseunits
    voltages=[];branches=[]
    for k,u in baseunits.items():
        if u=='V':
            dy=np.interp(grid+T,t,d[k])-np.interp(grid,t,d[k])
            voltages.append(dict(node=k,peak_v=float(max(abs(dy))),rms_v=float(np.sqrt(np.mean(dy**2)))))
        if k in p['expected_rising_edges_per_period']:
            e=cross(t,d[k]);a=e[(e>=250e-9)&(e<500e-9)];b=e[(e>=500e-9)&(e<750e-9)]
            target=p['expected_rising_edges_per_period'][k];br=dict(node=k,first_edges=len(a),second_edges=len(b),expected=target,passed=len(a)==len(b)==target)
            if br['passed']:
                dt=(b-a-T)*1e12
                br.update(mean_displacement_ps=float(np.mean(dt)),max_displacement_ps=float(max(abs(dt))),
                    early_quarter_mean_ps=float(np.mean(dt[:max(1,len(dt)//4)])),late_quarter_mean_ps=float(np.mean(dt[-max(1,len(dt)//4):])))
            branches.append(br)
    voltages.sort(key=lambda x:x['peak_v'],reverse=True)
    assert sha(j/'final.ic')==r['local_outputs_sha256']['final.ic']
    seed=states(j/'inputs/core_gear_dense_period_tt.ic');final=states(j/'final.ic')
    ends=sorted([dict(node=k,change_v=final[k]-seed[k]) for k,u in p['physical_state_units'].items() if u=='V'],key=lambda x:abs(x['change_v']),reverse=True)
    rf=fit_edges(cross(t,d['XP.vp']-d['XP.vn'],0));outfit=fit_edges(cross(t,d['out']))
    held=all(np.all(d[f'XP.b{i}']>.9) if 23&(1<<i) else np.all(d[f'XP.b{i}']<.3) for i in range(8))
    carrier=abs(rf['carrier_hz']/3936e6-1)<p['limits']['carrier_relative_error'] and abs(outfit['carrier_hz']/984e6-1)<p['limits']['carrier_relative_error']
    dense=voltages[0]['peak_v']<p['limits']['dense_voltage_difference_peak_v'];endpoint=abs(ends[0]['change_v'])<p['limits']['all_state_voltage_endpoint_difference_v']
    assert len(branches)==len(p['expected_rising_edges_per_period'])
    row=dict(case=j.name,observer=item['observer'],strobe=item['strobe'],source_result=rp.relative_to(ROOT).as_posix(),source_sha256=sha(rp),
        physical_dependencies_match=True,coarse23_held=bool(held),carrier_screen_passed=bool(carrier),dense_periods_passed=bool(dense),all_state_endpoint_screen_passed=bool(endpoint),
        branch_counts_passed=all(x['passed'] for x in branches),rf_fit=rf,output_fit=outfit,branches=branches,
        largest_dense_voltage_mismatches=voltages[:12],largest_endpoint_voltage_mismatches=ends[:12],
        all_dense_voltage_rows=voltages,step_count=len(t)-1,mean_dense_step_ps=float(np.mean(np.diff(t))*1e12))
    row['working_checks_passed']=bool(held and carrier and dense and endpoint and row['branch_counts_passed'])
    if item['observer']:
        row['observer_last_counts']=dict(rf=float(d['obscycles'][-1]),out=float(d['obsdivcycles'][-1]))
    rows.append(row)
out=dict(scope=__doc__,complete=len(rows)==4,cases=rows,periodic_state_valid=False,random_jitter_measured=False,full_pll_acceptance=False,
    interpretation='Changes in matched-seed deterministic drift distinguish strobe/observer numerical effects. Allcases still text-restore the same warm state; no control independently proves hidden-state restoration error or fullperiodicaccuracy.',limitations=p['limitations'])
if len(rows)==4:
    # Factorial effects report RF frequency at the fitted observation midpoint;
    # each individual result also retains its residual frequency drift.
    f={(r['observer'],r['strobe']):r['rf_fit']['carrier_hz'] for r in rows}
    out['rf_frequency_factorial_effects_hz']=dict(strobe_without_observer=f[False,True]-f[False,False],observer_without_strobe=f[True,False]-f[False,False],interaction=f[True,True]-f[True,False]-f[False,True]+f[False,False])
(H/'results/core_mesh_validation.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(dict(complete=out['complete'],cases=[dict(case=r['case'],observer=r['observer'],strobe=r['strobe'],rf_hz=r['rf_fit']['carrier_hz'],rf_drift_hz_per_us=r['rf_fit']['frequency_drift_hz_per_us'],max_dense_mv=r['largest_dense_voltage_mismatches'][0]['peak_v']*1e3,working_checks_passed=r['working_checks_passed']) for r in rows]),indent=2))
