"""Prepare a dense period check only from a completed, screened Gear2 warm state."""
from pathlib import Path
import datetime,hashlib,json,re
H=Path(__file__).resolve().parent;ROOT=H.parents[3];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
validation=H/'results/core_gear_settle_validation.json'
if not validation.exists():print('pending completed Gear2 warm validation; no netlist prepared');raise SystemExit(0)
v=json.loads(validation.read_text());assert v['warm_preflight_passed'] and v['sampled_voltage_screen_passed'], 'Warm state needs review; no follow-up generated'
wp=json.loads((H/'results/core_gear_settle_protocol.json').read_text())
j=(ROOT/v['source_result']).parent;r=json.loads((j/'result.json').read_text())
assert sha(j/'result.json')==v['source_sha256'] and r['ok'] and r['remote_inputs_match']
final=j/'final.ic';assert sha(final)==r['local_outputs_sha256']['final.ic']
states={}
for line in final.read_text().splitlines():
    z=line.split()
    if z and z[0] in wp['physical_state_names']:
        states[z[0]]=(float(z[1]),line,'A' if re.search(r'#unit\s+A\s*$',line) else 'V')
assert set(states)==set(wp['physical_state_names'])
assert {k:x[2] for k,x in states.items()}==wp['physical_state_units']
assert all(states[f'XP.b{i}'][0]>.9 if 23&(1<<i) else states[f'XP.b{i}'][0]<.3 for i in range(8))
case='core_gear_dense_period_tt';seed=H/'state_inputs'/(case+'.ic');assert not seed.exists()
seed.write_text('# Exact612 DUT voltage/current entries from completed6us Gear2 warm simulation. No analog or digital state correction.\n'+'\n'.join(states[k][1] for k in wp['physical_state_names'])+'\n')
body=(H/'tb/coremethod_gear_1ps_tt.scs').read_text()
assert 'stop=20n outputstart=5n' in body and 'readic="core_pulsetrip_late_seed_tt.ic"' in body
body=body.replace('stop=20n outputstart=5n','stop=750n outputstart=250n').replace('readic="core_pulsetrip_late_seed_tt.ic"',f'readic="{seed.name}"')
selected=set()
for line in body.splitlines():
    if line.startswith('save '):selected.update(line.split()[1:])
extra=set(x['node'] for x in v['largest_sampled_voltage_mismatches'][:12])
extra.update(k for k,u in wp['physical_state_units'].items() if u=='A')
extra.update(['XP.XV.XL.nfilt','XP.XV.XL.nb','XP.XV.XL.tail','XP.vco_vdd','XP.rx_vdd','XP.rt_vdd'])
extra=sorted(extra-selected);body+='\n// Highest warm-state drift nodes and every physical branch-current state.\n'
for i in range(0,len(extra),10):body+='save '+' '.join(extra[i:i+10])+'\n'
tb=H/'tb'/(case+'.scs');assert not tb.exists();tb.write_text(body)
p=dict(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),status='prepared_not_run',run='coregeardense01',case=case,
    source_validation_sha256=sha(validation),source_result=v['source_result'],source_result_sha256=v['source_sha256'],
    source_final_ic_sha256=sha(final),seed_sha256=sha(seed),tb_sha256=sha(tb),physical_state_units=wp['physical_state_units'],
    dense_observations=sorted(selected|set(extra)),period_s=250e-9,intervals_s=[[250e-9,500e-9],[500e-9,750e-9]],
    expected_rising_edges_per_period={'ref':6,'XP.refb':6,'out':246,'XP.clk':984,'XP.q1':492,'XP.data':246,'XP.acqclk':246,'XP.XD.d8':123,'XP.XD.d12':82,'XP.XD.d6':164,'XP.XD.ck':492},
    condition='SameactualLC/originalRT/CF10/repairedbank/coarse23/M4/TT27/1.2V/Q5/10fF.1ps Gear2/tolerances unchanged.6us source and0ns restart share forcingphase modulo250ns.250ns settling then500ns dense output.',
    limits=dict(dense_voltage_difference_peak_v=.001,all_state_voltage_endpoint_difference_v=.001,carrier_relative_error=1e-5),
    launch_gate='Prepared only after warm preflight and sampled voltage screen pass. Reuse released coregearsettle01 longslot, atmost6threads within18/fourlong+oneshort. No automatic PSS launch.',
    limitations=['Dense check covers selected nodes; endpoint comparisons cover612 exported physical states, not unexported MOS charge/history.',
        'Text-state restoration is not native checkpoint recovery. Initial250ns is excluded to allow restoration to evolve.',
        'Deterministic waveform mismatch and edge displacement are not random jitter.',
        'The1mV and10ppm screens are diagnostic gates, not project acceptance criteria. No tolerance relaxation or physical circuit change.'],
    main_dut_modified=False,full_pll_acceptance=False)
(H/'results/core_gear_dense_protocol.json').write_text(json.dumps(p,indent=2)+'\n');print(case,len(p['dense_observations']))
