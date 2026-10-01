"""Summarize verified records, preserving failed function/PSS/replay cases."""
import json,datetime
from analyze import H

def main():
 v=json.loads((H/'results/validation.json').read_text());n=json.loads((H/'results/noise_validation.json').read_text());t=json.loads((H/'results/timing_validation.json').read_text())
 func=[x for x in v if not x['case'].startswith(('noise_','timing_'))]
 timing=[x for x in v if x['case'].startswith('timing_')]
 rows=[]
 for r in n['cases']:
  w=r.get('periodic',{});p=w.get('power_mw',{});precision=n['precision'].get(r['case'].removesuffix('_coarse').removesuffix('_fine'),{})
  rows.append(dict(case=r['case'],valid_noise=r.get('valid_noise',False),noise_fs=r.get('numeric_jitter_fs'),chain_power_mw=p.get('VDD:p'),retimer_output_power_mw=p.get('VRT:p'),noise_by_subblock=r.get('noise_by_subblock'),noise_by_instance=r.get('noise_by_instance'),pass_joint_precision=precision.get('pass_precision',False)))
 out=dict(time=datetime.datetime.now().astimezone().isoformat(),scope='TT27/1.2V,984MHz,/4 physical raw differential divider;ideal noiseless shaped3.936GHz RF,10fF. No fullPLL/VCO source impedance or generators. Functional tests, PSS/noise qualification, and finite timing replay are distinct.',
  total_completed_records=len(v),functional_trials=len(func),functional_pass=sum(x.get('transient',{}).get('pass_function',False) for x in func),timing_diagnostic_trials=len(timing),noise_trials=len(n['cases']),valid_noise_count=sum(x.get('valid_noise',False) for x in n['cases']),noise=rows,precision=n['precision'],timing=t['cases'],
  limitations=['Only/4 and984MHz TT27;noPVT/allmodes/actualVCOintegration.','Bias current generators deferred; resistors/capacitors ideal concentrated elements, resistor noise on.','Joint timestep/harmonic/colored-sideband refinement does not separate their individual effects.','Replay qualification failure means its timing gain is not interpretable as physical circuit sensitivity.','Different fixtures overlap the divider and change loading; no direct addition to core power.','No new team adoption or specification changes.'])
 (H/'results/summary.json').write_text(json.dumps(out,indent=2,allow_nan=False)+'\n')
 lines=['| Case | Valid PSS/noise | RMS (fs) | Chain power (mW) | Joint refinement |','|---|---|---:|---:|---|']
 for r in rows:
  f=lambda x:'—' if x is None else f'{x:.3f}'
  lines.append(f"| {r['case']} | {r['valid_noise']} | {f(r['noise_fs'])} | {f(r['chain_power_mw'])} | {r['pass_joint_precision']} |")
 (H/'results/noise_table.md').write_text('\n'.join(lines)+'\n')
 lines=['| Case | Function screen | Output MHz | Output min/max V | Measured chain mW |','|---|---|---:|---|---:|']
 for r in func:
  w=r.get('transient',{});o=w.get('signals',{}).get('out',{});limits=o.get('range_v',[0,0])
  lines.append(f"| {r['case']} | {w.get('pass_function',False)} | {o.get('frequency_hz',0)/1e6:.6f} | {limits[0]:.4f}/{limits[1]:.4f} | {w.get('power_mw',{}).get('VDD:p',0):.6f} |")
 (H/'results/function_table.md').write_text('\n'.join(lines)+'\n')
 lines=['| Replay | Zero-replay qualification | Rise timing gain | Fall timing gain | Internal target |','|---|---|---:|---:|---|']
 for r in t['cases']:
  gain=r['output_to_input_timing_gain'];ok=r['qualified_replay']
  a=f"{gain['out_rise']:.4f}" if ok else 'unqualified';b=f"{gain['out_fall']:.4f}" if ok else 'unqualified'
  lines.append(f"| {r['phase']} | {ok} | {a} | {b} | {r['pass_internal_timing_target']} |")
 (H/'results/timing_table.md').write_text('\n'.join(lines)+'\n')
 print(json.dumps({k:out[k] for k in ['total_completed_records','functional_trials','functional_pass','timing_diagnostic_trials','noise_trials','valid_noise_count']},indent=2))

if __name__=='__main__':main()
