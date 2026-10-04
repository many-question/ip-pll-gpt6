"""Settle the actual core on the observer-free mesh used by PSS; retain a native state."""
from pathlib import Path
import datetime,hashlib,json,re
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
mp=H/'results/core_mesh_validation.json';m=json.loads(mp.read_text())
a=next(x for x in m['cases'] if not x['observer'] and not x['strobe'])
b=next(x for x in m['cases'] if x['observer'] and not x['strobe'])
assert not a['working_checks_passed'] and b['working_checks_passed']
dp=json.loads((H/'results/core_gear_dense_protocol.json').read_text())
j=(ROOT/a['source_result']).parent;r=json.loads((j/'result.json').read_text())
assert sha(j/'result.json')==a['source_sha256'] and r['ok'] and r['remote_inputs_match']
final=j/'final.ic';assert sha(final)==r['local_outputs_sha256']['final.ic']
entries={}
for line in final.read_text().splitlines():
    z=line.split()
    if z and z[0] in dp['physical_state_units']:
        assert ('A' if re.search(r'#unit\s+A\s*$',line) else 'V')==dp['physical_state_units'][z[0]]
        entries[z[0]]=line
assert len(entries)==612
case='core_plain_warm_tt';seed=H/'state_inputs'/(case+'.ic');assert not seed.exists()
seed.write_text('# Exact612 states from the completed observer-free dense transient; no correction.\n'+'\n'.join(entries[n] for n in dp['physical_state_units'])+'\n')
body=(H/'tb/core_gear_dense_period_tt.scs').read_text()
assert 'XOBS' not in body and 'strobeperiod' not in body and 'stop=750n outputstart=250n' in body
body=body.replace('core_gear_dense_period_tt.ic',seed.name).replace('stop=750n outputstart=250n','stop=3u skipcount=2000')
native='/home/jielu/TSMC180/MP/IP-PLL-GPT6/simulation/cmos_v14_full/coreplainwarm01_'+case+'.srf'
body=re.sub(r'^(tran tran .*)$',lambda m:m[0]+f' savetime=[3u] savefile="{native}"',body,flags=re.M)
tb=H/'tb'/(case+'.scs');assert not tb.exists();tb.write_text(body)
p=dict(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),status='prepared_not_run',run='coreplainwarm01',case=case,
    source_result=a['source_result'],source_result_sha256=a['source_sha256'],source_final_ic_sha256=sha(final),
    mesh_evidence_sha256=sha(mp),seed_sha256=sha(seed),tb_sha256=sha(tb),physical_state_units=dp['physical_state_units'],
    expected_rising_edges_per_period=dp['expected_rising_edges_per_period'],limits=dp['limits'],native_savefile=native,native_save_time_s=3e-6,
    condition='ActualLC/originalRT/CF10/newbank/coarse23/M4/TT27/1.2V/Q5/10fF;1psGear2,tolerances unchanged. No eventobserver or forcedstrobes; save every2000th accepted step to reduce output withoutforcingtimes.',
    reason='Observer-only matched-seed control passes.601mV while neither/strobeonly fail9.458/9.738mV. A warm state generated withtightRF/outputcross events is not interchangeable with the observer-free numerical mesh. Evolve from its own actual observer-free endpoint and retain hiddencharge/history for a native continuation.',
    followup='After completed raw/log/input validation, collect and hash the native3uscheckpoint. Continue the identical physical snapshot for500ns withdenseoutput and compare two250nsperiods plusall612exported endpoint states. No automaticPSS.',
    launch_gate='Reuse the released strict64us longslot with6threads; fourlong+oneshort,total<=18. Finite3uswarmonly.',
    limitations=['Sparse skipcount output is not a periodic or RF-noise measurement.','Native checkpoint existence and contents must be checked afteractualcompletion.','Observer-control evidence does not establish numerical convergence ofGear2 or fullPLL noise.'],main_dut_modified=False,full_pll_acceptance=False)
(H/'results/core_plain_warm_protocol.json').write_text(json.dumps(p,indent=2)+'\n');print(case)
