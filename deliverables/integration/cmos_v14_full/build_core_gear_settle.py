"""Prepare a physically evolving Gear2 warm preflight with every available state observed."""
from pathlib import Path
import datetime,hashlib,json,re
H=Path(__file__).resolve().parent;ROOT=H.parents[3];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
drift=json.loads((H/'results/core_gear_initial_period_drift.json').read_text())
assert not drift['periodic_state_valid']
vc1=next(x for x in drift['rows'] if x['node']=='XP.vc1');assert abs(vc1['endpoint_difference'])>1e-4
src=H/'tb/coremethod_gear_1ps_tt.scs';body=src.read_text()
seed=H/'state_inputs/core_pulsetrip_late_seed_tt.ic';names=[];units={}
for line in seed.read_text().splitlines():
    if not line.strip() or line.startswith('#'):continue
    name,value=line.split('#',1)[0].split();float(value);assert re.fullmatch(r'[A-Za-z0-9_.:]+',name)
    names.append(name)
    # MOS internal voltage names also contain colons; use the IC unit marker.
    units[name]='A' if re.search(r'#unit\s+A\s*$',line) else 'V'
assert len(names)==612 and len(set(names))==612
assert list(units.values()).count('V')==601 and list(units.values()).count('A')==11
assert body.count('stop=20n outputstart=5n')==1
body=body.replace('stop=20n outputstart=5n','stop=6u strobeperiod=2n strobeoutput=strobeonly')
body+='\n// Testbench observer only: draws no current and does not control the PLL.\n'
body+='ahdl_include "lc_loop_observer.va"\nXOBS (XP.vp XP.vn XP.refb XP.ctrl out 0 obsphase obscycles obsctrl obsdivcycles) lc_loop_observer\n'
body+='save obsphase obscycles obsctrl obsdivcycles\n'
already=set()
for line in body.splitlines():
    if line.startswith('save '):already.update(line.split()[1:])
for start in range(0,len(names),12):
    extra=[x for x in names[start:start+12] if x not in already]
    if extra:body+='save '+' '.join(extra)+'\n'
case='core_gear_settle6_tt';target=H/'tb'/(case+'.scs');assert not target.exists();target.write_text(body)
method=json.loads((H/'results/core_method_probe_protocol.json').read_text());assert sha(seed)==method['seed_sha256']
p=dict(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),status='prepared_not_run',run='coregearsettle01',case=case,
    source_tb_sha256=sha(src),tb_sha256=sha(target),seed_sha256=sha(seed),
    source_drift_result_sha256=sha(H/'results/core_gear_initial_period_drift.json'),
    physical_state_names=names,physical_state_units=units,voltage_state_count=list(units.values()).count('V'),current_state_count=list(units.values()).count('A'),
    condition='TT27/1.2V/Q5/CF10/originalRT/repairedbank/coarse23/M4/10fF; same actual late3us state and1ps Gear2/tolerances. Localtime0 forcing phase equals source3us modulo250ns.',
    change='Compared with existing20ns Gear2 method control: duration to6us;2ns strobes; testbench-only high-impedance observer and all612 available physical-state probes. No physical circuit/source/initial voltage/current edits.',
    reason='Method-only PSS initialization retains deterministic output advance~.868ps/250ns andC1endpoint change+.7394mV. Check actual Gear2 loop settling and internal drift before another PSS seed.',
    limits=dict(phase_pp_rad=.02,phase_drift_rad_per_us=.01,cycle_error=.001,control_v=[.2,1.],additional_sampled_voltage_screen_v=.001),
    launch_gate='Prepared only. Review current coretripgear01 and release its exact long slot before dispatch; at most6threads with18total/fourlong+oneshort. No automatic PSS follow-up.',
    limitations=['Warm functional preflight; not coldstart, nativecheckpoint, validPSS or randomnoise.',
        '2ns sampled state differences at250ns separation expose observed drift but cannot establish all-time periodic accuracy or GHz spectra.',
        'All612 saved circuit voltage/current entries are covered, not every unexported MOS internal charge state.',
        'Switching from trap-produced source state to Gear2 can shift operating point. Settling alone does not establish numerical accuracy; finer-method/noise comparisons remain necessary.'],
    main_dut_modified=False,full_pll_acceptance=False)
(H/'results/core_gear_settle_protocol.json').write_text(json.dumps(p,indent=2)+'\n');print(case,len(names))
