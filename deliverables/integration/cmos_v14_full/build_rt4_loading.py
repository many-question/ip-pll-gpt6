"""Prepare actualLC RT4 loading/control probes after its near-lock failure.

No dispatch or adoption is implied. Three clamped control values measure the
loaded frequency curve before choosing a new physical handoff operating point.
"""
from pathlib import Path
import hashlib,json,re
H=Path(__file__).resolve().parent;ROOT=H.parents[3];B=H.parents[1]/'blocks/cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
measured=json.loads((H/'results/core_noise_candidates_validation.json').read_text())
rt4=next(x for x in measured['cases'] if x['variant']=='rt4');assert not rt4['passed'] and 'stationarity' in rt4
fixed=json.loads((H/'results/sampler_loading_protocol.json').read_text())
baseline=next(x for x in fixed['cases'] if x['reference']=='clocked');v=baseline['control_v']
body=(H/'tb/samplerload_clocked_tt.scs').read_text()
assert body.count('pll_noise_pulsetrip_core_v14')==2
body=body.replace('pll_noise_pulsetrip_core_v14','pll_noise_rt4_core_v14')
seed=H/'state_inputs/samplerload_clocked_tt.ic';rows=[]
for name,delta in [('nominal',0.),('minus25m',-.025),('minus50m',-.05)]:
    case='rt4load_'+name+'_tt';control=v+delta;lines=[];changed=[]
    for line in seed.read_text().splitlines():
        fields=line.split()
        if fields and fields[0]=='XP.ctrl':
            lines.append(f'XP.ctrl {control:.16g}');changed.append(fields[0])
        else:lines.append(line)
    assert changed==['XP.ctrl']
    target=H/'state_inputs'/(case+'.ic');assert not target.exists();target.write_text('\n'.join(lines)+'\n')
    tb=re.sub(r'^VCTRL .*$',f'VCTRL (XP.ctrl 0) vsource dc={control:.16g}',body,flags=re.M)
    tb=tb.replace('samplerload_clocked_tt.ic',target.name)
    p=H/'tb'/(case+'.scs');assert not p.exists();p.write_text(tb)
    rows.append(dict(case=case,control_v=control,delta_from_baseline_v=delta,tb_sha256=sha(p),seed_sha256=sha(target)))
out=dict(scope=__doc__,run='rt4load01',status='prepared_not_run',cases=rows,
    baseline_clamped_run='samplerload01',baseline_clamped_case='samplerload_clocked_tt',
    original_seed_sha256=sha(seed),original_core_sha256=sha(B/'pll_noise_pulsetrip_core_v14.scs'),rt4_core_sha256=sha(B/'pll_noise_rt4_core_v14.scs'),
    triggering_result=rt4,condition='TT27/1.2V/coarse23/CF10/RT4/continuousclockbank/10fF/Q5.750ns/1ps/traponly/reltol1e-5,24MHz normalreference, last500ns dense. IdealexternalVCTRL clamp.',
    hypothesis='Retimer scaling changes actualRF receiver loading and possibly LC operating frequency. Correct M4 but ~+8MHz RF mismatch from the old seed requires matching operating point before accepting/rejecting RT4 in the real loop.',
    interpretation='Nominal control compares directly against the completed baseline clamp. Two lowercontrols measure the RT4loaded curve; infer a possible frequency-matched control only when the target is bracketed, then verify in a released actualclosedloop trial.',
    launch_gate='Review samplerload01 and actualLC four-way first. Use a released slot within18threads and4long+1short. No automatic launch; do not overlap a finite pipeline replacement.',
    limitations=['Not a closed-loop locking result or a random-jitter measurement.','Common inherited voltages are near-lock test seeds, not native state continuation.','Changing control alone may not recover phase capture; an FLL retune or clock-loading isolation may still be needed.'],
    main_dut_modified=False,full_pll_acceptance=False)
(H/'results/rt4_loading_protocol.json').write_text(json.dumps(out,indent=2)+'\n');print([x['case'] for x in rows])
