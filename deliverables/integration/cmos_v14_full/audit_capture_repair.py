"""Bind MOS unit evidence and the reset experiment to one repair revision."""
from pathlib import Path
import json,hashlib,re
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
boundary=json.loads((H/'results/boundary_pll_capture_v14.json').read_text())
expected=boundary['source_hashes'];units=json.loads((H/'results/capture_repair_units.json').read_text())
assert units['passed'] and units['completed']
rows=[];sources={}
for row in units['cases']:
    p=ROOT/row['source_result'];rec=json.loads(p.read_text())
    assert rec['remote_inputs_match']
    circuit={k:v for k,v in rec['inputs_sha256'].items() if k!=p.parent.name+'.scs'}
    assert all(expected[k]==v for k,v in circuit.items())
    rows.append(dict(case=row['case'],matched_circuit_files=list(circuit),passed=row['passed']))
    for src in row['source_segments']:
        rp=ROOT/src;r=json.loads(rp.read_text());assert r['remote_inputs_match']
        sources[Path(src).as_posix()]=dict(result_sha256=sha(rp),inputs_sha256=r['inputs_sha256'],
            local_outputs_sha256=r['local_outputs_sha256'],native_state=r.get('native_state'))
job=R/'repaircold01/repair_capture_tt';tb=(job/'inputs/repair_capture_tt.scs').read_text()
assert all(sha(job/'inputs'/k)==v for k,v in expected.items())
assert 'readic=' not in tb and 'recover=' not in tb
assert 'maxstep=4p' in tb and 'reltol=1e-4' in tb and 'stop=64u' in tb
assert re.search(r'^XP .*\) pll_capture_v14\s*$',tb,re.M)
capture=json.loads((H/'results/capture_repaircold01.json').read_text())
rec=json.loads((job/'result.json').read_text())
assert rec['remote_inputs_match'] and rec['local_outputs_sha256']
assert 'spectre completes with 0 errors' in (job/'spectre.out').read_text(errors='replace')
assert capture['final_simulator_completed'] and capture['circuit_hashes_identical']
sources[(job/'result.json').relative_to(ROOT).as_posix()]=dict(result_sha256=sha(job/'result.json'),
    inputs_sha256=rec['inputs_sha256'],local_outputs_sha256=rec['local_outputs_sha256'],native_state=None)
out=dict(scope=__doc__,top='pll_capture_v14',design_identity_sha256=hashlib.sha256(json.dumps(expected,sort_keys=True).encode()).hexdigest(),
    circuit_files=expected,unit_cases=rows,raw_manifest=sources,
    full_reset=dict(run='repaircold01',case='repair_capture_tt',local_dependency_match=True,
        constructed_nearlock_state=False,native_continuation=False,scheduled_stop_us=64,
        completed=True,functional_capture_screen_passed=capture['functional_capture_screen_passed'],
        capture_result_sha256=sha(H/'results/capture_repaircold01.json'),
        status='64us completed and recovered with verified input/output hashes. TT functional reset capture passed; strict numerical and retention checks are separate.'),
    limitations='Units use ideal stimuli and20fF output loads. Full PLL uses real circuit interconnect/loading. No fullPVT, MC, noise, power or supply-ramp acceptance.')
(H/'results/capture_repair_consistency.json').write_text(json.dumps(out,indent=2)+'\n')
print('All six MOS unit cases match the full reset DUT:',out['design_identity_sha256'])
