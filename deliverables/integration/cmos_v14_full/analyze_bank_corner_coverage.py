"""Count proven endpoint cases without interpreting them as continuous PLL coverage."""
from pathlib import Path
import hashlib,json
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
high=json.loads((H/'results/ss_settled_pulse_validation.json').read_text())['cases']
extra=json.loads((H/'results/bank_pulsetrip_corner_validation.json').read_text())['cases']
protocol=json.loads((H/'results/bank_pulsetrip_corner_protocol.json').read_text())
expected={x['case']:x for x in protocol['cases']}
assert len(expected)==17 and all(x['case'] in expected for x in extra)
reference_hash=None;rows=[]
for r in high+extra:
    manifest=ROOT/r['source'];rec=json.loads(manifest.read_text())
    assert hashlib.sha256(manifest.read_bytes()).hexdigest()==r['source_sha256']
    assert rec['remote_inputs_match']
    bank=rec['inputs_sha256']['bank_pulsetrip_v14.scs']
    if reference_hash is None:reference_hash=bank
    assert bank==reference_hash
    rows.append(dict(case=r['case'],corner=r['corner'],temperature_c=r['temperature_c'],m=r['output']['m'],
        rf_mhz=r['nominal_rf_mhz'],target_output_mhz=r['nominal_rf_mhz']/r['output']['m'],
        actual_output_mhz=r['output']['output_mhz'],passed=r['passed'],source=r['source'],source_sha256=r['source_sha256']))
lo={4:2688,6:2736,8:2688,10:2880,12:2880,14:3024}
hi={4:3936,6:3888,8:3456,10:3120,12:3168,14:3024}
coverage=[]
for m in lo:
    endpoints=[]
    for f in sorted(set([lo[m],hi[m]])):
        found=[x for x in rows if x['corner']=='ss' and x['m']==m and x['rf_mhz']==f]
        assert len(found)<=1
        endpoints.append(dict(rf_mhz=f,target_output_mhz=f/m,passed=bool(found and found[0]['passed']),case=found[0]['case'] if found else None))
    coverage.append(dict(m=m,endpoints=endpoints,ss_endpoints_passed=all(x['passed'] for x in endpoints)))
out=dict(scope=__doc__,candidate_sha256=reference_hash,cases=rows,ss_endpoint_coverage=coverage,
    all_ss_planned_endpoints_passed=all(x['ss_endpoints_passed'] for x in coverage),
    additional_cases_expected=17,additional_cases_completed=len(extra),additional_cases_passed=sum(x['passed'] for x in extra),
    pending_additional_cases=[x for x in expected if x not in {r['case'] for r in extra}],
    fixed_window_ns=[400,600],condition='1.2V/10fF;actualcornerMOSRX/bank/baselineRT/quietcounterinput;sameSSmeasuredshape,zeroimpedanceRFreplay.',
    limitations=['SS endpoints do not prove every intermediate channel, reset duration, or mode change.',
                 'Fixed SS-shaped stimulus across corners does not simulate actual corner VCO loading.',
                 'Not fullPVT, actualLC, mismatch, noise, or fullPLL acceptance.'],full_pll_acceptance=False)
(H/'results/bank_pulsetrip_coverage.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k not in ['cases','ss_endpoint_coverage']},indent=2))
