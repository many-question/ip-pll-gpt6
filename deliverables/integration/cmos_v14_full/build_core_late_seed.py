"""Prepare an IC-only freshPSS comparison from the newly settled physical baseline.

No launch is implied. Same4MHz period, tstart, tstab, tolerances, defaultitres
and device circuit as coretripsupply01; only the saved physical state changes.
"""
from pathlib import Path
import hashlib,json
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
j=ROOT/'research/runs/spectre_cmos_v14_full/corenoisecand01/core_noisecand_base_tt'
r=json.loads((j/'result.json').read_text());source=j/'final.ic'
proof=json.loads((H/'results/core_noise_candidates_validation.json').read_text())
base=next(x for x in proof['cases'] if x['variant']=='base');assert base['passed']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(j/'result.json')==base['source_sha256'] and sha(source)==r['local_outputs_sha256']['final.ic']
assert r['remote_inputs_match'] and 'spectre completes with 0 errors' in (j/'spectre.out').read_text()
lines=[line for line in source.read_text().splitlines() if line.strip() and
       (line.split()[0].startswith('XP.') or line.split()[0] in ['out','ref','vdd'])]
values={line.split()[0]:float(line.split()[1]) for line in lines}
supplies={k:values[k] for k in ['XP.vco_vdd','XP.rx_vdd','XP.rt_vdd']}
assert all(abs(v-1.2)<1e-12 for v in supplies.values())
state=H/'state_inputs/core_pulsetrip_late_seed_tt.ic';assert not state.exists()
state.write_text('# Actual baseline additional3us final state; observer states excluded. Text seed, not native continuation.\n'+'\n'.join(lines)+'\n')
source_tb=H/'tb/core_pulsetrip_supply_noise_tt.scs';body=source_tb.read_text()
assert body.count('core_pulsetrip_supply_seed_tt.ic')==1
body=body.replace('core_pulsetrip_supply_seed_tt.ic',state.name)
target=H/'tb/core_pulsetrip_late_noise_tt.scs';assert not target.exists();target.write_text(body)
assert body.replace(state.name,'core_pulsetrip_supply_seed_tt.ic')==source_tb.read_text()
out=dict(scope=__doc__,status='prepared_not_run',run='coretriplate01',case=target.stem,
    source_result=base['source'],source_result_sha256=base['source_sha256'],source_final_ic_sha256=sha(source),
    seed_sha256=sha(state),source_tb_sha256=sha(source_tb),candidate_tb_sha256=sha(target),
    retained_state_nodes=len(lines),actual_saved_supply_values_v=supplies,
    source_stationarity=base['stationarity'],
    phase_alignment='Source baseline localtime3us is12 complete250ns branch periods. Candidate tstart3us and reference waveform identical modulo250ns. Source itself started from the prior3us physical seed; not native6us continuation.',
    change='Onlyreadic changes to a newly simulated state. No manual analog/digital node correction, no tolerance/period/itres/circuit changes.',
    launch_gate='First review actualLC four-way loading comparison; use a released long-job slot. No automatic dispatch; do not overlap existing6threadbatch.',
    acceptance='ActualPSS convergence, branch/endpoint checks, fresh noise and device sums required; sixoffsetsareonlyaprobenotRMS.',
    main_dut_modified=False,full_pll_acceptance=False)
(H/'results/core_late_seed_protocol.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(dict(case=target.stem,supply_values=supplies,retained_nodes=len(lines),status=out['status']),indent=2))
