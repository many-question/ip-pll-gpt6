"""Gate-graph candidate check only, with asynchronous RF phase and range endpoints."""
from analyze_fll_async_quantization import Graph,simulate,H
import json,time
g=Graph('fll_center128_v14');rows=[];start=time.monotonic()
for k in range(9,42):
 for i in range(8):rows.append(dict(initial_rf4_phase=i/8,**simulate(g,k,i/8)))
valid=[c for c in rows if c['enable'] and not c['range_error']]
extra=[]
# Reachable code-zero case, above maximum, and below minimum are distinct tests.
for label,f0,expected_error in [('code_zero',3939e6,False),('too_slow',3900e6,True),('too_fast',5400e6,True)]:
 for i in range(8):
  r=simulate(g,41,i/8,f0=f0);r.update(label=label,f0_hz=f0,initial_rf4_phase=i/8,expected_range_error=expected_error)
  r['passed']=r['range_error']==expected_error and r['enable']!=expected_error and (label!='code_zero' or r['code']==0)
  extra.append(r)
summary=dict(controller='fll_center128_v14',scope=__doc__,not_integrated=True,range_error_cases=len(rows)-len(valid),rf_error_range_mhz=[min(c['rf_error_mhz'] for c in valid),max(c['rf_error_mhz'] for c in valid)],acquisition_ref_cycles=sorted(set(c['cycles'] for c in rows)),nominal_cases=rows,endpoint_cases=extra,endpoint_passed=all(c['passed'] for c in extra),runtime_s=time.monotonic()-start)
(H/'results/fll_center_candidate_validation.json').write_text(json.dumps(summary,indent=2)+'\n')
print({k:v for k,v in summary.items() if k not in ['nominal_cases','endpoint_cases']},flush=True)
