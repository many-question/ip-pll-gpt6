"""Tie all 18 completed divider/retimer TBs to the current complete DUT."""
from pathlib import Path
import json

H = Path(__file__).resolve().parent
ROOT = H.parents[3]
R = ROOT / 'research/runs/spectre_cmos_v14_full'
baseline = json.loads((R / 'completestrict01/complete_strict_tt/result.json').read_text())
shared = ['cells.scs', 'cmos_even_bank_acq_v14.scs', 'digital_cells_v2.scs',
          'ff_fbdelay50_v14.scs', 'ring_inv_static_v14.scs',
          'rt_light24s12_out083_v14.scs', 'rtcomb_v13.scs']
validation = json.loads((H / 'results/validation.json').read_text())
rows = []
for m in [4, 6, 8, 10, 12, 14]:
    cases = []
    for corner, temp in [('tt', 27), ('ss', 60), ('ff', 0)]:
        name = f'bankrt_m{m}_{corner}'
        v = next(x for x in validation if x['run'] == 'bankrt01' and x['case'] == name)
        result_path = R / 'bankrt01' / name / 'result.json'
        rec = json.loads(result_path.read_text())
        assert rec['remote_inputs_match'] and rec['local_outputs_sha256']
        assert all(rec['inputs_sha256'][f] == baseline['inputs_sha256'][f] for f in shared)
        log = (result_path.parent / 'spectre.out').read_text(errors='replace')
        assert 'spectre completes with 0 errors' in log
        d = v['divider']
        cases.append(dict(corner=corner,temperature_c=temp,passed=d['passed'],
                          measured_output_mhz=d['output_mhz'],
                          source_result=str(result_path.relative_to(ROOT)),
                          same_seven_circuit_dependencies=True))
    rows.append(dict(m=m,rf_mhz=d['rf_mhz'],target_output_mhz=d['rf_mhz']/m,cases=cases))
out = dict(scope=__doc__,conditions='1.2V, ideal rail RF with20ps rise/fall,10fF;100ns transient, final40ns measured. Six-mode divider bank plus retimer and acquisition RF/4 buffer; no RF analog receiver or VCO.',
           reference_full_dut='completestrict01/complete_strict_tt',
           identical_dependencies={f:baseline['inputs_sha256'][f] for f in shared},
           rows=rows,limitation='Six selected RF frequencies, not all33 channels or all PVT combinations. Functional tests only; no mismatch, supply/load sweep, layout/PEX or noise acceptance.')
(H / 'results/bank_tb_consistency.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
