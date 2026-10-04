"""Use the measured smaller bracket and physical RC settling for RT4 code24."""
from pathlib import Path
import datetime,hashlib,json,re,math
H=Path(__file__).resolve().parent;ROOT=H.parents[3];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
lowpath=H/'results/rt4_matched_point_validation.json';highpath=H/'results/rt4_code24_tuning_validation.json'
lo=json.loads(lowpath.read_text());hi=json.loads(highpath.read_text());assert lo['valid'] and hi['valid']
target=3936e6;fl=lo['rf_fit']['carrier_hz'];fh=hi['rf_fit']['carrier_hz'];vl=lo['control_v'];vh=hi['control_v']
assert fl<target<fh and vl<vh
control=vl+(target-fl)/(fh-fl)*(vh-vl);assert vl<control<vh
j=(ROOT/lo['source_result']).parent;r=json.loads((j/'result.json').read_text());assert sha(j/'result.json')==lo['source_sha256'] and r['ok'] and r['remote_inputs_match']
source=j/'final.ic';assert sha(source)==r['local_outputs_sha256']['final.ic']
lines=[];units={};values={};changes=[]
for line in source.read_text().splitlines():
    z=line.split()
    if not z or not(z[0].startswith('XP.') or z[0] in ['ref','out','vdd']):continue
    name=z[0];values[name]=float(z[1]);units[name]='A' if re.search(r'#unit\s+A\s*$',line) else 'V'
    if name=='XP.ctrl':lines.append(f'XP.ctrl {control:.16g}');changes.append(name)
    else:lines.append(line)
assert changes==['XP.ctrl'] and len(lines)==612 and list(units.values()).count('A')==11
assert all(values[f'XP.b{i}']>.9 if 24&(1<<i) else values[f'XP.b{i}']<.3 for i in range(8))
case='rt4c24_match2_settle_tt';seed=H/'state_inputs'/(case+'.ic');assert not seed.exists()
seed.write_text('# Actual code24 matched-point final DUT state; only externally prescribed control changes. No C1/inductor/bit correction.\n'+'\n'.join(lines)+'\n')
tbsource=H/'tb/rt4c24_match1_tt.scs';body=tbsource.read_text().replace('rt4c24_match1_tt.ic',seed.name)
body=re.sub(r'^VCTRL .*$',f'VCTRL (XP.ctrl 0) vsource dc={control:.16g}',body,flags=re.M)
assert 'stop=750n outputstart=250n' in body
body=body.replace('stop=750n outputstart=250n','stop=3u outputstart=2.5u')
tb=H/'tb'/(case+'.scs');assert not tb.exists();tb.write_text(body)
tau=100e3*7.1619724391353e-12;memory=values['XP.vc1']-control
oldp=json.loads((H/'results/rt4_matched_point_protocol.json').read_text())
p=dict(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),status='prepared_not_run',run='rt4match02',case=case,
    source_result=lo['source_result'],source_result_sha256=lo['source_sha256'],source_final_ic_sha256=sha(source),
    bracket_evidence=[dict(path=x.relative_to(ROOT).as_posix(),sha256=sha(x)) for x in [lowpath,highpath]],
    bracket_control_v=[vl,vh],bracket_rf_hz=[fl,fh],control_v=control,target_rf_hz=target,
    seed_sha256=sha(seed),tb_sha256=sha(tb),dense_start_s=2.5e-6,stop_s=3e-6,
    initial_c1_minus_control_v=memory,nominal_clamped_rc_tau_s=tau,nominal_rc_residual_prediction_v=memory*math.exp(-3e-6/tau),
    condition='SameTT27/1.2V/Q5/CF10/RT4/repairedbank/coarse24/10fF.3us/1ps/traponly,final500ns dense. Source750ns and newtime0 share forcingphase modulo250ns.',
    change='Only forced control changed; all612 actual DUT state entries retained.3us permits physical C1 relaxation; RC prediction omits leakage and is not acceptance evidence.',
    limits=oldp['limits'],launch_gate='Prepared pending completion/collection of noisecorr246_01 in the single shortslot. No automatic clamp release.',
    limitations=oldp['limitations'],main_dut_modified=False,full_pll_acceptance=False)
(H/'results/rt4_refined_point_protocol.json').write_text(json.dumps(p,indent=2)+'\n')
print(json.dumps(dict(case=case,control_v=control,initial_c1_minus_control_v=memory,rc_prediction_v=p['nominal_rc_residual_prediction_v']),indent=2))
