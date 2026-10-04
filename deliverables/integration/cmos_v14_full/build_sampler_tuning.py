"""Measure whether fine tuning can recover the MOS-dummy candidate's RF target.

Two new control points plus the completed40fF nominal point. Physical circuit
and coarse23 remain unchanged; only an external clamp and its matching IC vary.
"""
from pathlib import Path
import datetime,hashlib,json,re
H=Path(__file__).resolve().parent;ROOT=H.parents[3];B=H.parents[1]/'blocks/cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
v=json.loads((H/'results/sampler_dummy_validation.json').read_text())
assert v['complete'] and len(v['cases'])==3 and all(x['valid_for_diagnosis'] for x in v['cases'])
base=next(x for x in v['cases'] if x['case']=='samplerdummy_c40_tt')
assert v['lowest_output24_pm_diagnostic_case']==base['case']
rp=ROOT/base['source_result'];r=json.loads(rp.read_text());assert sha(rp)==base['source_sha256']
source=H/'tb/samplerdummy_c40_tt.scs';body=source.read_text();seed=H/'state_inputs/samplerload_clocked_tt.ic'
nominal=float(re.search(r'^VCTRL .* dc=([^\s]+)',body,re.M)[1]);rows=[]
for voltage in [.85,1.0]:
    case=f'samplertune_c40_v{round(voltage*1000)}_tt';lines=[];changed=[]
    for line in seed.read_text().splitlines():
        fields=line.split()
        if fields and fields[0]=='XP.ctrl':lines.append(f'XP.ctrl {voltage:.16g}');changed.append(fields[0])
        else:lines.append(line)
    assert changed==['XP.ctrl']
    state=H/'state_inputs'/(case+'.ic');assert not state.exists();state.write_text('\n'.join(lines)+'\n')
    tb=re.sub(r'^VCTRL .*$',f'VCTRL (XP.ctrl 0) vsource dc={voltage:.16g}',body,flags=re.M).replace(seed.name,state.name)
    target=H/'tb'/(case+'.scs');assert not target.exists();target.write_text(tb)
    rows.append(dict(case=case,control_v=voltage,tb_sha256=sha(target),seed_sha256=sha(state)))
out=dict(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),status='prepared_not_run',run='samplertune01',cases=rows,
    baseline=dict(case=base['case'],source_result=base['source_result'],source_sha256=base['source_sha256'],control_v=nominal),
    core_sha256=sha(B/'pll_noise_dummy_core_v14.scs'),sampler_sha256=sha(B/'sampler_dummy_v14.scs'),source_seed_sha256=sha(seed),
    target_rf_hz=3936e6,selection='40fF has the lowest measured24MHzPM of three nominal-control cases, but11%window amplitude spread and frequency mismatch remain; not a final optimum.',
    condition='TT27/1.2V/Q5/coarse23/CF10/originalRT/10fF, actualMOS complementary sampler40fF.750ns/1ps/reltol1e-5/traponly,last500nsdense. Externalcontrolclamp.',
    hypothesis='Fine control may recover the22.186MHz deficit to3.936GHz. Its nonlinear curve must be measured; baseline staticKVCO is not extrapolated.',
    launch_gate='Allthree dummy results complete and reviewed; reuse that released one-thread short slot. Existing16+1=17requestedthreads,4long+1short.',
    acceptance='Only interpolate inside a measured monotonic bracket, then simulate the predicted point and actualclosedloop. If target not bracketed, measure a physical coarse retune or isolate loading; no extrapolated locked result.',
    limitations=['ReferencePM changes are deterministic and exclude randomnoise.','ExtraMOSnoise, mismatch, closedloop capture, PVT and frequency coverage remain.','No main-DUT adoption or automatic follow-up batch.'],
    main_dut_modified=False,full_pll_acceptance=False)
(H/'results/sampler_tuning_protocol.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(dict(run=out['run'],cases=rows,baseline_rf_mhz=base['rf_hz']/1e6),indent=2))
