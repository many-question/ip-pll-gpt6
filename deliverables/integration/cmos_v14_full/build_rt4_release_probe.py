"""Release the physical RT4 loop to test capture from a measured, slightly detuned state."""
from pathlib import Path
import datetime,hashlib,json,re
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
vp=H/'results/rt4_refined_point_validation.json';v=json.loads(vp.read_text())
assert v['valid'] and v['filter_memory_screen_passed']
assert not v['rf_matching_passed'] and -125e3<v['rf_error_hz']<-100e3
j=(ROOT/v['source_result']).parent;r=json.loads((j/'result.json').read_text())
assert sha(j/'result.json')==v['source_sha256'] and r['ok'] and r['remote_inputs_match']
final=j/'final.ic';assert sha(final)==r['local_outputs_sha256']['final.ic']
entries={};units={}
for line in final.read_text().splitlines():
    z=line.split()
    if not z or not (z[0].startswith('XP.') or z[0] in ['ref','out','vdd']):continue
    entries[z[0]]=line;units[z[0]]='A' if re.search(r'#unit\s+A\s*$',line) else 'V'
assert len(entries)==612 and list(units.values()).count('A')==11
assert all(float(entries[f'XP.b{i}'].split()[1])>.9 if 24&(1<<i) else float(entries[f'XP.b{i}'].split()[1])<.3 for i in range(8))
case='rt4c24_release_tt';seed=H/'state_inputs'/(case+'.ic');assert not seed.exists()
seed.write_text('# Exact612 physical RT4 states from the measured3us clamped run. No control,C1,inductor or bit correction.\n'+'\n'.join(entries.values())+'\n')
body=(H/'tb/rt4c24_match2_settle_tt.scs').read_text()
assert body.count('\nVCTRL ')==1
body=re.sub(r'^VCTRL .*\n','',body,flags=re.M).replace(' VCTRL:p','')
body=body.replace('// External diagnostic control clamp; not an accepted PLL implementation.','// Control clamp removed for a physical closed-loop capture experiment.')
body=body.replace('rt4c24_match2_settle_tt.ic',seed.name).replace('outputstart=2.5u','outputstart=2u')
native='/home/jielu/TSMC180/MP/IP-PLL-GPT6/simulation/cmos_v14_full/rt4release01_'+case+'.srf'
body=re.sub(r'^(tran tran .*)$',lambda m:m[0]+f' savetime=[3u] savefile="{native}"',body,flags=re.M)
tb=H/'tb'/(case+'.scs');assert not tb.exists();tb.write_text(body)
p=dict(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),status='prepared_not_run',run='rt4release01',case=case,
    source_result=v['source_result'],source_result_sha256=v['source_sha256'],source_validation_sha256=sha(vp),
    source_final_ic_sha256=sha(final),seed_sha256=sha(seed),tb_sha256=sha(tb),physical_state_units=units,
    source_rf_error_hz=v['rf_error_hz'],source_c1_minus_control_v=v['final_c1_minus_control_v'],
    source_rf_matching_screen_passed=False,source_filter_memory_screen_passed=True,
    decision='The100kHz open-loop frequency handoff screen remains FAILED at-121.128kHz. Proceed as an explicit near-lock capture experiment, not as a passed handoff: the C1alignment screen passed, and actual closed-loop evolution is more informative than extrapolating another arbitrary-phase clamped tune point. No requirement or acceptance threshold is relaxed.',
    condition='TT27/1.2V/Q5/CF10/RT4/newbank/coarse24/M4/10fF.3us/1ps/traponly/tolerances unchanged; final1us dense, no event observer. Real source time3us and restart0 share forcingphase modulo250ns.',
    change='Remove only the external ideal VCTRL clamp and its current probe; preserve all612 physical state entries. Save final native state for possible continuation.',
    native_savefile=native,native_save_time_s=3e-6,
    limits=dict(phase_pp_rad=.02,phase_drift_rad_per_us=.01,rf_cycles_error=.001,out_cycles_error=.001,control_v=[.2,1.]),
    launch_gate='Reuse released RT4refinement one-thread diagnostic slot, total<=18 and fourlong+oneshort. No automatic adoption or PSS.',
    limitations=['Warm capture experiment only; not coldstart/fullPLL/PVT/randomnoise.','Text restoration still omits hidden device charge/history; the resulting transient is measured, never assumed settled.','Knowntraponly mesh artifacts remain a numerical limitation; successful function must later be compared with Gear2/finer step.'],
    main_dut_modified=False,full_pll_acceptance=False)
(H/'results/rt4_release_protocol.json').write_text(json.dumps(p,indent=2)+'\n');print(case)
