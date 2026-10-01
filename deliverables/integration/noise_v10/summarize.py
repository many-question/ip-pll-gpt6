"""Produce a compact, condition-qualified summary of the measured experiments."""
import json
from analyze import H

def main():
 def read(name):return json.loads((H/'results'/name).read_text())
 gate=read('gating_validation.json');opt=read('optimization_validation.json');noise=read('noise_validation.json');val=read('validation.json')
 by={r['case']:r for r in noise['cases']};base=by['noise_gate_all_coarse'];rows=[]
 for r in opt['cases']:
  row={k:r[k] for k in ['case','group','function_pass','change']}
  for mode in ['only','all']:
   if mode in r:row[mode]=r[mode]
  if r.get('all',{}).get('valid_noise'):
   a=by[r['all']['case']]
   row['all_on_contributions_fs']={k:x['jitter_fs'] for k,x in a['noise_by_subblock'].items() if k.startswith('XRT.')}
   row['all_on_contributions_fs']['XD']=a['noise_by_instance']['XD']['jitter_fs']
   row['all_on_group_relative_changes']={k:x/base['noise_by_subblock'][k]['jitter_fs']-1 for k,x in row['all_on_contributions_fs'].items() if k!='XD'}
   row['all_on_group_relative_changes']['XD']=row['all_on_contributions_fs']['XD']/base['noise_by_instance']['XD']['jitter_fs']-1
   key=a['case'].removesuffix('_coarse');row['precision']=noise['precision'].get(key)
   fine=by.get(key+'_fine')
   if fine and fine['valid_noise']:row['fine']=dict(jitter_fs=fine['numeric_jitter_fs'],power_mw=fine['periodic']['power_mw'])
  rows.append(row)
 full=[r for r in rows if r.get('all',{}).get('valid_noise')]
 qualified=[r for r in full if r.get('precision',{}).get('pass_precision') and 'fine' in r]
 best=min(qualified,key=lambda r:r['fine']['jitter_fs']) if qualified else None
 out=dict(scope='TT27/1.2V/984MHz/10fF output-chain fixture; ideal noiseless3.936GHz RF voltage shape.10kHz–492MHz,out0.6V rising. Not fullPLL.',
  baseline=dict(jitter_fs=base['numeric_jitter_fs'],power_mw=base['periodic']['power_mw'],gate_pass=gate['pass_gating'],variance_closure=gate['variance_closure'],contributions=[{k:r[k] for k in ['group','jitter_fs','variance_fraction']} for r in gate['cases'] if r['group'] not in ['all','off']]),
  run_counts=dict(completed=len(val),simulator_success=sum(bool(r['sim_ok']) for r in val),physical_transient_cases=sum('transient' in r and not r['diagnostic_only'] for r in val),physical_transient_pass=sum(r.get('transient',{}).get('pass_function',False) and not r['diagnostic_only'] for r in val),timing_diagnostic_cases=sum(r['diagnostic_only'] for r in val),noise_cases=len(noise['cases']),valid_noise=sum(r['valid_noise'] for r in noise['cases'])),
  single_module_changes=rows,best_qualified_single_module_candidate=best,
  limitations=['200fs wholePLL requirement remains unchanged and unmet by output chain.','WholePLL power cannot be obtained by adding this fixture to old core power.','No new full-frequency,PVT,VCO-loading,physicalRC/area or FLL capture qualification.','Limited deterministic timing replay does not qualify general setup/hold or divider-noise suppression.','Added ideal1pF must later use actual PDK capacitor; bias/reference generator is still deferred.'])
 (H/'results/summary.json').write_text(json.dumps(out,indent=2,allow_nan=False)+'\n')
 print(json.dumps(dict(run_counts=out['run_counts'],best=best),indent=2))

if __name__=='__main__':main()
