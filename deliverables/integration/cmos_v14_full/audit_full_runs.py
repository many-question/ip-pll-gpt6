"""Check that current fullPLL tests use one physical DUT revision, not mixed parts."""
from pathlib import Path
import hashlib,json,re
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
boundary=json.loads((H/'results/boundary_pll_complete_v14.json').read_text());expected=boundary['source_hashes']
cases=[('completewarm01','complete_warm_tt'),('completedense01','complete_warm_tt'),('completestrict01','complete_strict_tt'),('completequal01','complete_qual_tt'),('completess01','complete_near_ss')]
cases += [('completecold'+str(i).zfill(2),'complete_k41_tt') for i in range(1,6)]
cases += [('handoffprobe01','handoff_probe_'+phase+'_tt') for phase in ['p0','p180']]
rows=[]
for run,case in cases:
 job=R/run/case;ip=job/'inputs'
 if not ip.exists():continue
 actual={k:hashlib.sha256((ip/k).read_bytes()).hexdigest() for k in expected}
 assert actual==expected,(run,case,'Physical DUT dependency mismatch')
 tb=(ip/(case+'.scs')).read_text();m=re.search(r'^XP[ \t]+\([^\n]+\)[ \t]+pll_complete_v14[ \t]*([^\n]*)$',tb,re.M);assert m
 assert not m[1].strip(),'Top parameter overrides must be audited explicitly'
 rec=json.loads((job/'result.json').read_text()) if (job/'result.json').exists() else None
 if rec:assert rec['remote_inputs_match'] and all(rec['inputs_sha256'][k]==v for k,v in expected.items())
 rows.append(dict(run=run,case=case,local_dut_dependencies_match=True,remote_input_hash_verification_complete=rec['remote_inputs_match'] if rec else False,simulation_result_recovered=rec is not None,corner=re.search(r'section=(tt|ss|ff)\b',tb)[1],constructed_state='readic=' in tb,native_continuation='recover=' in tb,top_parameter_overrides=None))
result=dict(scope=__doc__,top='pll_complete_v14',design_identity_sha256=hashlib.sha256(json.dumps(expected,sort_keys=True).encode()).hexdigest(),circuit_files=expected,cases=rows,limitation='Design consistency only. Initial conditions, corner, numerical precision, reference phase and test duration differ as documented. Pending or failed runs do not become functional evidence from this audit.')
(H/'results/full_dut_consistency.json').write_text(json.dumps(result,indent=2)+'\n');print('Consistent physical DUT in',len(rows),'local snapshots;',result['design_identity_sha256'])
