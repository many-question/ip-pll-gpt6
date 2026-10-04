"""Measure one physical fine-control point after admitting coarse-code24."""
from pathlib import Path
import datetime,hashlib,json,re
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
v=json.loads((H/'results/rt4_coarse_program_validation.json').read_text())
assert v['complete'] and v['program_interface_control']['passed']
row=next(x for x in v['cases'] if x['coarse_code']==24)
assert row['valid'] and row['rf_fit']['carrier_hz']<3936e6
case='rt4c24_v750_tt';control=.75
source=H/'tb/rt4program_c24_tt.scs';body=source.read_text()
original_seed=H/'state_inputs/rt4load_nominal_tt.ic'
lines=[];changed=[]
for line in original_seed.read_text().splitlines():
    fields=line.split()
    if fields and fields[0]=='XP.ctrl':
        lines.append(f'XP.ctrl {control:.16g}');changed.append(fields[0])
    else:lines.append(line)
assert changed==['XP.ctrl']
seed=H/'state_inputs'/(case+'.ic');assert not seed.exists();seed.write_text('\n'.join(lines)+'\n')
body=re.sub(r'^VCTRL .*$',f'VCTRL (XP.ctrl 0) vsource dc={control}',body,flags=re.M).replace(original_seed.name,seed.name)
tb=H/'tb'/(case+'.scs');assert not tb.exists();tb.write_text(body)
p=dict(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),status='prepared_not_run',
    run='rt4c24tune01',case=case,control_v=control,tb_sha256=sha(tb),seed_sha256=sha(seed),
    original_seed_sha256=sha(original_seed),source_validation_sha256=sha(H/'results/rt4_coarse_program_validation.json'),
    baseline_result=row['source_result'],baseline_result_sha256=row['source_sha256'],
    target_rf_hz=3936e6,coarse_code=24,
    condition='TT27/1.2V/Q5/CF10/RT4/repaired divider/10fF;750ns/1ps traponly,last500ns dense. Actual MOS flops program code24.',
    change='Only prescribed external-control clamp and its own initial voltage change to .75V. All other dynamic state entries, including C1 and coarse flops, remain from the common physical source.',
    limits=dict(window_rf_drift_ppm=100,divider_relative=.001,clamp_error_v=1e-9),
    launch_gate='One short control after both corecal01 calibration simulations terminate and are collected. Reuse the one-thread short slot;18-thread/four-long-plus-one-short cap.',
    limitations=['Frequency bracket only; no closed-loop capture or random-noise result.',
        'C1 is not artificially precharged. Its physical settling must be checked before releasing the clamp.',
        'Interpolation is only allowed inside measured same-code control bounds and is not a simulated operating point.'],
    main_dut_modified=False,full_pll_acceptance=False)
(H/'results/rt4_code24_tuning_protocol.json').write_text(json.dumps(p,indent=2)+'\n');print(case)
