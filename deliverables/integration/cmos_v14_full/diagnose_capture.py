"""Separate observed FLL decisions from hypotheses about the capture failure."""
from pathlib import Path
import json,hashlib
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
p=H/'results/capture_completecold05.json';d=json.loads(p.read_text())
assert d['final_simulator_completed'] and not d['functional_capture_screen_passed']
fine=[x for x in d['fll_measurements'] if x['eval_time_us']>18]
first,last=fine[0],fine[-1]
assert first['dac']==32 and first['captured_count']==first['target_count']==1312
assert last['dac']==33 and last['captured_count']==1313
assert d['pre_handoff']['dac']==33 and d['pre_handoff']['coarse']==22
src=ROOT/'share/deliverables/blocks/cmos_v14_full/fll_controller_rf4_v14.v'
s=src.read_text();assert 'wire high_freq = measured > target;' in s and "else dac<=fine_keep+1'b1;" in s
result=dict(condition=d['condition'],source_capture_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
 controller_source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),
 observed=dict(first_fine_trial=first,last_fine_trial=last,handoff=d['pre_handoff'],
               final_mean_output_mhz=d['stationarity']['mean_output_mhz'],qualified_ever_high=d['logic']['qualified']['first_rising_us'] is not None,
               restart_ever_high=d['logic']['XP.restart']['first_rising_us'] is not None),
 static_controller_facts=['RF/4 counted for32 reference cycles gives3MHz RF count resolution.',
  'An equality measured==target is classified as not high; DAC32 was retained despite a late-window RF estimate above3936MHz.',
  'At the finalbit, DAC33 measured1313>1312 and fine_keep clears bit0 to32. The unconditionalfine_keep+1 selects33 again for handoff.',
  'The existing supervisor only requests restart after a previously qualified state loses qualification. There is no initial-capture timeout in the current controller.'],
 inference='FLL quantization, equality handling and the final ceiling choice leave a measured+3.156MHz RF error before handoff. Mainloop phase keeps slipping for the remaining6.415us. This establishes an observed failed handoff at this condition; it does not prove a unique cause, a global capture range, or failure at all initial phases/corners.',
 next_experiment='Validate the retained128-reference-window/coarse-headroom proposal with actual MOS timing and actualVCO, then rerun reset capture in a separately named DUT revision. Do not reuse a native checkpoint across modified circuits. Mainloop capture range and bias-settling memory should be checked alongside the FLL change.',
 limitation='No circuit modification or performance optimization is adopted by this diagnostic. The128-window candidate remains only gate-graph/linear-plant evidence.')
(H/'results/capture_diagnosis.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
