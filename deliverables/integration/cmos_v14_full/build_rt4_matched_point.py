"""Measure the in-bracket RT4 control prediction from its own physical code24 state."""
from pathlib import Path
import datetime,hashlib,json,re
H=Path(__file__).resolve().parent;ROOT=H.parents[3];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
v=json.loads((H/'results/rt4_code24_tuning_validation.json').read_text());assert v['valid'] and v['curve']['target_bracketed']
control=v['curve']['interpolated_control_v'];assert min(v['curve']['control_v'])<control<max(v['curve']['control_v'])
j=(ROOT/v['source_result']).parent;r=json.loads((j/'result.json').read_text());assert sha(j/'result.json')==v['source_sha256'] and r['ok'] and r['remote_inputs_match']
source=j/'final.ic';assert sha(source)==r['local_outputs_sha256']['final.ic']
lines=[];changed=[];values={}
for line in source.read_text().splitlines():
    z=line.split()
    if not z or not(z[0].startswith('XP.') or z[0] in ['ref','out','vdd']):continue
    values[z[0]]=float(z[1])
    if z[0]=='XP.ctrl':lines.append(f'XP.ctrl {control:.16g}');changed.append(z[0])
    else:lines.append(line)
assert changed==['XP.ctrl'] and len(lines)==612
assert all(values[f'XP.b{i}']>.9 if 24&(1<<i) else values[f'XP.b{i}']<.3 for i in range(8))
case='rt4c24_match1_tt';seed=H/'state_inputs'/(case+'.ic');assert not seed.exists()
seed.write_text('# Actual code24/0.75V750ns final DUT state; only prescribed VCTRL initial voltage changed. Not a closed-loop or native continuation.\n'+'\n'.join(lines)+'\n')
tbsource=H/'tb/rt4c24_v750_tt.scs';body=tbsource.read_text().replace('rt4c24_v750_tt.ic',seed.name)
body=re.sub(r'^VCTRL .*$',f'VCTRL (XP.ctrl 0) vsource dc={control:.16g}',body,flags=re.M)
tb=H/'tb'/(case+'.scs');assert not tb.exists();tb.write_text(body)
p=dict(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),status='prepared_not_run',run='rt4match01',case=case,
    source_validation_sha256=sha(H/'results/rt4_code24_tuning_validation.json'),source_result=v['source_result'],source_result_sha256=v['source_sha256'],
    source_final_ic_sha256=sha(source),seed_sha256=sha(seed),tb_sha256=sha(tb),control_v=control,target_rf_hz=3936e6,
    source_c1_v=values['XP.vc1'],initial_c1_minus_control_v=values['XP.vc1']-control,
    condition='SameTT27/1.2V/Q5/CF10/RT4/repairedbank/code24/10fF,750ns/1ps/traponly,last500ns dense. Externalcontrolclamped; own measured750ns finalstate has matching forcingphase modulo250ns.',
    change='Only forced control changes to the measured-bracket interpolation. All612 physicalDUT entries come from the preceding actualsimulation;601voltages/11currents. C1 and inductors are not overwritten.',
    limits=dict(window_rf_drift_ppm=100,divider_relative=.001,clamp_error_v=1e-9,desired_target_error_hz=100e3,desired_filter_alignment_v=1e-4),
    launch_gate='One short750ns point after noisecorr01two cases complete; verify18threads/fourlong+oneshort. No automatic clamp release.',
    limitations=['Frequency-matching diagnostic only; no noise, coldcapture or validPLLperiodicstate.',
        '100kHz frequency and100uV C1 diagnostic targets are working handoff screens, not new project requirements.',
        'If either handoff target is unmet, refine/physicallysettle before release; no dynamic-state correction.'],main_dut_modified=False,full_pll_acceptance=False)
(H/'results/rt4_matched_point_protocol.json').write_text(json.dumps(p,indent=2)+'\n');print(case,control)
