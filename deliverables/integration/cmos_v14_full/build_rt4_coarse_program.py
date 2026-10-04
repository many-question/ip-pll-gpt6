"""Physically clock a requested coarse code into existing MOS flops; keep a code23 control."""
from pathlib import Path
import datetime,hashlib,json
H=Path(__file__).resolve().parent;ROOT=H.parents[3];B=H.parents[1]/'blocks/cmos_v14_full';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
v=json.loads((H/'results/rt4_loading_validation.json').read_text())
assert v['complete'] and len(v['cases'])==4 and all(x['valid'] for x in v['cases']) and not v['curve']['target_bracketed']
oldname='pll_noise_rt4_core_v14';newname='pll_noise_rt4_program_core_v14'
src=B/(oldname+'.scs');body=src.read_text();body=body.replace(oldname,newname)
oldports=f'subckt {newname} (ref out vdd vss)';assert body.count(oldports)==1
body=body.replace(oldports,f'subckt {newname} (ref out '+' '.join(f'cd{i}' for i in range(8))+' vdd vss)')
for i in range(8):
    old=f'XCOARSE{i} (b{i} refb vss b{i} vdd vss)';assert body.count(old)==1
    body=body.replace(old,f'XCOARSE{i} (cd{i} refb vss b{i} vdd vss)')
body=body.replace('// Diagnostic acquired state: coarse23, DAC38, M4; ideal static controls.','// Diagnostic acquired boundary: coarse D inputs are testbench pins, clocked by actual reference buffer.\n// Remaining static controls unchanged. Not a full-PLL configuration implementation.')
dst=B/(newname+'.scs');assert not dst.exists();dst.write_text(body)
tbsource=H/'tb/rt4load_nominal_tt.scs';template=tbsource.read_text().replace(oldname,newname);rows=[]
for code in [23,24]:
    case=f'rt4program_c{code}_tt';pins=' '.join('vdd' if code&(1<<i) else '0' for i in range(8))
    tb=template.replace(f'XP (ref out vdd 0) {newname}',f'XP (ref out {pins} vdd 0) {newname}')
    target=H/'tb'/(case+'.scs');assert not target.exists();target.write_text(tb)
    rows.append(dict(case=case,coarse_code=code,tb_sha256=sha(target)))
out=dict(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),status='prepared_not_run',run='rt4program01',cases=rows,
    original_core_sha256=sha(src),program_core_sha256=sha(dst),source_seed_sha256=sha(H/'state_inputs/rt4load_nominal_tt.ic'),
    source_curve_sha256=sha(H/'results/rt4_loading_validation.json'),control_v=.6579988674567703,
    condition='TT27/1.2V/Q5/CF10/RT4/newbank/10fF,750ns/1ps/traponly,last500nsdense, externalcontrolclamp. Same actual source IC in both cases; no dynamic voltage/state editing.',
    change='Expose eight coarse-D inputs instead of self-feedback. Testbench connects constant code23/24 levels; actual tx_dff_r0 instances clock them into b0..b7. Code23 control checks interface loading before attributing a change to the code.',
    launch_gate='Use the released one-thread short control slot only; four existing long jobs total17threads, plus this one gives18. Sequential two-case batch; no automatic next batch.',
    limits=['Not autonomous FLL, cold capture, periodic noise or jitter.','Changing D interface can alter coarse-Q load; code23 control must match previous nominal RF within250kHz and swing within0.5percent.','Do not interpolate RF versus discrete coarse code as if it were a continuous control.','Before releasing the external clamp, physically settle/precharge C1 and check phase capture.'],
    main_dut_modified=False,full_pll_acceptance=False)
(H/'results/rt4_coarse_program_protocol.json').write_text(json.dumps(out,indent=2)+'\n');print(' '.join(x['case'] for x in rows))
