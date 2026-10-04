"""Add one measured low-control endpoint after the first RT4 curve misses target."""
from pathlib import Path
import datetime,hashlib,json,re
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
v=json.loads((H/'results/rt4_loading_validation.json').read_text())
assert v['complete'] and all(x['valid'] for x in v['cases']) and not v['curve']['target_bracketed']
p=json.loads((H/'results/rt4_loading_protocol.json').read_text())
source=H/'tb/rt4load_minus250m_tt.scs';seed=H/'state_inputs/rt4load_minus250m_tt.ic'
case='rt4load_v200_tt';control=.2;lines=[];changed=[]
for line in seed.read_text().splitlines():
    fields=line.split()
    if fields and fields[0]=='XP.ctrl':lines.append(f'XP.ctrl {control:.16g}');changed.append(fields[0])
    else:lines.append(line)
assert changed==['XP.ctrl']
state=H/'state_inputs'/(case+'.ic');assert not state.exists();state.write_text('\n'.join(lines)+'\n')
body=re.sub(r'^VCTRL .*$',f'VCTRL (XP.ctrl 0) vsource dc={control}',source.read_text(),flags=re.M).replace(seed.name,state.name)
tb=H/'tb'/(case+'.scs');assert not tb.exists();tb.write_text(body)
out=dict(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),status='prepared_not_run',run='rt4loadlimit01',
    cases=[dict(case=case,control_v=control,tb_sha256=sha(tb),seed_sha256=sha(state))],rt4_core_sha256=p['rt4_core_sha256'],
    basis_result_sha256=sha(H/'results/rt4_loading_validation.json'),
    reason='All three original points valid; lowest .407999V gives3.938568GHz, above3.936GHz. Measure .2V rather than extrapolate nonlinear tuning.',
    condition=p['condition'],launch_gate='Only released rt4load01 one-thread long slot; no automatic subsequent batch.',
    limitations=['Clamped frequency boundary only, no closed-loop lock or jitter.','C1 is not precharged; do not release this clamp state as a matched loop seed.','If .2V still misses target, physically change coarse setting before another lock attempt.'],
    main_dut_modified=False,full_pll_acceptance=False)
(H/'results/rt4_loading_limit_protocol.json').write_text(json.dumps(out,indent=2)+'\n');print(case)
