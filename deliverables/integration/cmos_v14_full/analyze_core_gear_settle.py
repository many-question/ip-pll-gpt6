"""Check Gear2 warm stationarity and sampled physical-state drift; no noise inference."""
from pathlib import Path
import hashlib,json,re
import numpy as np
from analyze import loop
H=Path(__file__).resolve().parent;ROOT=H.parents[3];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=json.loads((H/'results/core_gear_settle_protocol.json').read_text());j=ROOT/'research/runs/spectre_cmos_v14_full'/p['run']/p['case'];rp=j/'result.json'
if not rp.exists():print('pending');raise SystemExit(0)
r=json.loads(rp.read_text())
if not r.get('local_outputs_sha256'):print('collection incomplete');raise SystemExit(0)
assert r['ok'] and r['remote_inputs_match'] and sha(j/'waveforms.npz')==r['local_outputs_sha256']['waveforms.npz']
log=(j/'spectre.out').read_text();assert 'spectre completes with 0 errors' in log and re.search(r'^\s*method\s*=\s*gear2only\s*$',log,re.M)
assert r['inputs_sha256']['core_pulsetrip_late_seed_tt.ic']==p['seed_sha256']
source=ROOT/'research/runs/spectre_cmos_v14_full/coremethod01/coremethod_gear_1ps_tt/result.json';old=json.loads(source.read_text())
excluded={p['case']+'.scs','coremethod_gear_1ps_tt.scs','lc_loop_observer.va'}
assert {k:v for k,v in r['inputs_sha256'].items() if k not in excluded}=={k:v for k,v in old['inputs_sha256'].items() if k not in excluded}
with np.load(j/'waveforms.npz') as z:d={k:z[k] for k in z.files}
t=d['time'];assert abs(t[0])<1e-15 and abs(t[-1]-6e-6)<1e-12 and set(p['physical_state_names'])<=set(d)
units={}
with (j/(j.name+'.raw')/'tran.tran.tran').open() as f:
    active=False
    for line in f:
        if line.strip()=='TRACE':active=True;continue
        if line.strip()=='VALUE':break
        if active:
            m=re.fullmatch(r'"([^"]+)" "([VI])"\s*',line);assert m,line
            units[m[1]]='A' if m[2]=='I' else 'V'
assert {n:units[n] for n in p['physical_state_names']}==p['physical_state_units']
windows=[]
for end_us in range(1,7):
    part={k:v[t<=end_us*1e-6+1e-15] for k,v in d.items() if v.ndim==1 and len(v)==len(t)}
    windows.append(loop(part))
coarse=all(np.all(d[f'XP.b{i}']>.9) if 23&(1<<i) else np.all(d[f'XP.b{i}']<.3) for i in range(8))
supplies={k:[float(min(d[k])),float(max(d[k]))] for k in ['XP.vco_vdd','XP.rx_vdd','XP.rt_vdd']}
supply_ok=all(abs(lo-1.2)<1e-9 and abs(hi-1.2)<1e-9 for lo,hi in supplies.values())
period=250e-9;ix=np.flatnonzero((t>=t[-1]-2*period-1e-15)&(t<=t[-1]-period+1e-15));rows=[]
assert len(ix)>=125
for name in p['physical_state_names']:
    a=d[name][ix];b=np.interp(t[ix]+period,t,d[name]);delta=b-a
    rows.append(dict(node=name,unit=units[name],difference_peak=float(max(abs(delta))),
        difference_rms=float(np.sqrt(np.mean(delta**2))),difference_mean=float(np.mean(delta)),endpoint_difference=float(delta[-1])))
vr=sorted([x for x in rows if x['unit']=='V'],key=lambda x:x['difference_peak'],reverse=True)
ir=sorted([x for x in rows if x['unit']=='A'],key=lambda x:x['difference_peak'],reverse=True)
warm=bool(windows[-1]['passed'] and coarse and supply_ok)
screen=bool(vr[0]['difference_peak']<p['limits']['additional_sampled_voltage_screen_v'])
out=dict(scope=__doc__,source_result=rp.relative_to(ROOT).as_posix(),source_sha256=sha(rp),windows=windows,
    physical_state_count=len(rows),coarse23_held=bool(coarse),supply_ranges_v=supplies,
    sampled_period_intervals_us=[[5.5,5.75],[5.75,6.]],sampled_voltage_screen_passed=screen,
    largest_sampled_voltage_mismatches=vr[:20],largest_sampled_current_mismatches=ir,all_state_rows=rows,
    warm_preflight_passed=warm,ready_for_dense_period_check=bool(warm and screen),
    first_window_note='Observer starts cycle counters atzero until secondreference; first-window countfailure is retained, not interpreted as a physical frequency drop.',
    random_jitter_measured=False,periodic_state_valid=False,full_pll_acceptance=False,limitations=p['limitations'])
(H/'results/core_gear_settle_validation.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(dict(warm_preflight_passed=warm,sampled_voltage_screen_passed=screen,last_window=windows[-1],largest_voltage_mismatches=vr[:6]),indent=2))
