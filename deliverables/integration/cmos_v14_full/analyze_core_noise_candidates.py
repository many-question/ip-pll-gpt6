"""Compare completed near-lock real-LC preflights; never derive jitter from them."""
from pathlib import Path
import hashlib,json
import numpy as np
from analyze import loop
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
protocol=json.loads((H/'results/core_noise_candidates_protocol.json').read_text())
R=ROOT/'research/runs/spectre_cmos_v14_full'/protocol['run']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rows=[]
for item in protocol['cases']:
    j=R/item['case'];p=j/'result.json'
    if not p.exists():continue
    r=json.loads(p.read_text())
    if not r.get('local_outputs_sha256'):continue
    row=dict(variant=item['variant'],case=item['case'],source=p.relative_to(ROOT).as_posix(),source_sha256=sha(p),passed=False)
    rows.append(row)
    if not r['ok'] or 'spectre completes with 0 errors' not in (j/'spectre.out').read_text():continue
    assert r['remote_inputs_match']
    assert r['inputs_sha256'][item['core']+'.scs']==item['core_sha256']
    assert r['inputs_sha256']['core_pulsetrip_supply_seed_tt.ic']==protocol['seed_sha256']
    assert sha(j/'waveforms.npz')==r['local_outputs_sha256']['waveforms.npz']
    with np.load(j/'waveforms.npz') as z:d={k:z[k] for k in z.files}
    t=d['time'];assert abs(t[0])<1e-15 and abs(t[-1]-3e-6)<1e-12
    v=loop(d)
    bits={f'b{i}':[float(min(d[f'XP.b{i}'])),float(max(d[f'XP.b{i}']))] for i in range(8)}
    coarse=all((lo>.9 if 23&(1<<i) else hi<.3) for i,(lo,hi) in enumerate(bits.values()))
    supplies={k:[float(min(d[k])),float(max(d[k]))] for k in ['XP.vco_vdd','XP.rx_vdd','XP.rt_vdd']}
    supply_ok=all(abs(lo-1.2)<1e-9 and abs(hi-1.2)<1e-9 for lo,hi in supplies.values())
    ix=t>2e-6;bias=d['XP.XV.XL.nfilt'][ix]
    row.update(stationarity=v,coarse23_held=bool(coarse),supply_ranges_v=supplies,
        bias_filter_last1us_range_v=[float(min(bias)),float(max(bias))],
        bias_filter_last1us_drift_v_per_us=float(np.polyfit((t[ix]-t[ix][0])*1e6,bias,1)[0]),
        passed=bool(v['passed'] and coarse and supply_ok))
out=dict(scope=__doc__,cases=rows,complete=len(rows)==4,passed=None,
    full_pll_acceptance=False,noise_acceptance=False,power_up_acceptance=False,
    limitations=protocol['limitations'])
if len(rows)==4:out['passed']=all(x['passed'] for x in rows)
baseline=next((x for x in rows if x['variant']=='base' and 'stationarity' in x),None)
if baseline:
    for row in rows:
        if 'stationarity' not in row:continue
        row['output_change_from_base_mhz']=row['stationarity']['mean_output_mhz']-baseline['stationarity']['mean_output_mhz']
        row['mean_sampled_control_change_v']=float(np.mean(row['stationarity']['ctrl_range_v'])-np.mean(baseline['stationarity']['ctrl_range_v']))
(H/'results/core_noise_candidates_validation.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
