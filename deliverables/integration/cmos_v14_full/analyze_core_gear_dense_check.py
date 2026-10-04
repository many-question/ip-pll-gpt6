"""Audit dense deterministic periods and all exported endpoint states before PSS."""
from pathlib import Path
import hashlib,json,re
import numpy as np
from noise_utils import cross
from reference_modulation_utils import fit_edges
from psf_trace_units import trace_units
H=Path(__file__).resolve().parent;ROOT=H.parents[3];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=json.loads((H/'results/core_gear_dense_protocol.json').read_text());j=ROOT/'research/runs/spectre_cmos_v14_full'/p['run']/p['case'];rp=j/'result.json'
if not rp.exists():print('pending');raise SystemExit(0)
r=json.loads(rp.read_text())
if not r.get('local_outputs_sha256'):print('collection incomplete');raise SystemExit(0)
assert r['ok'] and r['remote_inputs_match'] and sha(j/'waveforms.npz')==r['local_outputs_sha256']['waveforms.npz']
source=ROOT/p['source_result'];old=json.loads(source.read_text());assert sha(source)==p['source_result_sha256']
excluded={j.name+'.scs',j.name+'.ic',source.parent.name+'.scs','core_pulsetrip_late_seed_tt.ic','lc_loop_observer.va'}
assert {k:v for k,v in r['inputs_sha256'].items() if k not in excluded}=={k:v for k,v in old['inputs_sha256'].items() if k not in excluded}
assert r['inputs_sha256'][j.name+'.ic']==p['seed_sha256']
log=(j/'spectre.out').read_text();assert 'spectre completes with 0 errors' in log and re.search(r'^\s*method\s*=\s*gear2only\s*$',log,re.M)
with np.load(j/'waveforms.npz') as z:d={k:z[k] for k in z.files}
t=d['time'];assert abs(t[0]-250e-9)<1e-14 and abs(t[-1]-750e-9)<1e-14 and np.all(np.diff(t)>0)
units=trace_units(j/(j.name+'.raw')/'tran.tran.tran')
period=p['period_s'];grid=np.linspace(250e-9,500e-9,250001);rows=[]
for name,u in units.items():
    a=np.interp(grid,t,d[name]);b=np.interp(grid+period,t,d[name]);delta=b-a
    row=dict(node=name,unit=u,difference_peak=float(max(abs(delta))),difference_rms=float(np.sqrt(np.mean(delta**2))),endpoint_difference=float(delta[-1]))
    if name in p['expected_rising_edges_per_period']:
        e=cross(t,d[name]);ea=e[(e>=250e-9)&(e<500e-9)];eb=e[(e>=500e-9)&(e<750e-9)]
        row.update(first_period_edges=len(ea),second_period_edges=len(eb),expected_edges=p['expected_rising_edges_per_period'][name])
        row['edge_count_passed']=len(ea)==len(eb)==row['expected_edges']
        if row['edge_count_passed']:
            shift=(eb-ea-period)*1e12;row['deterministic_edge_displacement_ps']=dict(mean=float(np.mean(shift)),peak_abs=float(max(abs(shift))),pp=float(np.ptp(shift)))
    rows.append(row)
def state(path):
    result={}
    for line in path.read_text().splitlines():
        z=line.split()
        if z and z[0] in p['physical_state_units']:result[z[0]]=float(z[1])
    assert set(result)==set(p['physical_state_units']);return result
first=state(j/'inputs'/(j.name+'.ic'));final=state(j/'final.ic');assert sha(j/'final.ic')==r['local_outputs_sha256']['final.ic']
endpoints=[dict(node=n,unit=u,initial=first[n],final=final[n],difference=final[n]-first[n]) for n,u in p['physical_state_units'].items()]
volts=sorted([x for x in rows if x['unit']=='V'],key=lambda x:x['difference_peak'],reverse=True)
ev=sorted([x for x in endpoints if x['unit']=='V'],key=lambda x:abs(x['difference']),reverse=True)
rf=fit_edges(cross(t,d['XP.vp']-d['XP.vn'],0));outfit=fit_edges(cross(t,d['out']))
counts=all(x['edge_count_passed'] for x in rows if 'edge_count_passed' in x);assert sum('edge_count_passed' in x for x in rows)==len(p['expected_rising_edges_per_period'])
limits=p['limits'];dense=volts[0]['difference_peak']<limits['dense_voltage_difference_peak_v'];ends=abs(ev[0]['difference'])<limits['all_state_voltage_endpoint_difference_v']
carrier=abs(rf['carrier_hz']/3936e6-1)<limits['carrier_relative_error'] and abs(outfit['carrier_hz']/984e6-1)<limits['carrier_relative_error']
out=dict(scope=__doc__,source_result=rp.relative_to(ROOT).as_posix(),source_sha256=sha(rp),
    dense_periods_passed=bool(dense),all_state_endpoint_screen_passed=bool(ends),branch_counts_passed=bool(counts),carrier_screen_passed=bool(carrier),
    ready_for_pss_review=bool(dense and ends and counts and carrier),rf_fit=rf,output_fit=outfit,
    largest_dense_voltage_mismatches=volts[:12],all_dense_rows=rows,all_state_endpoint_rows=endpoints,largest_endpoint_voltage_mismatches=ev[:12],
    periodic_state_valid=False,random_jitter_measured=False,full_pll_acceptance=False,limitations=p['limitations'])
(H/'results/core_gear_dense_validation.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k not in ['all_dense_rows','all_state_endpoint_rows','rf_fit','output_fit']},indent=2))
