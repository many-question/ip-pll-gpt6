"""Separate the numerical effects of output strobes and the high-impedance observer."""
from pathlib import Path
import datetime,hashlib,json
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
vp=H/'results/core_gear_dense_validation.json';v=json.loads(vp.read_text())
assert not v['ready_for_pss_review'] and v['branch_counts_passed'] and v['carrier_screen_passed']
source=H/'tb/core_gear_dense_period_tt.scs';body=source.read_text()
assert 'strobeperiod' not in body and 'XOBS' not in body
assert 'stop=750n outputstart=250n' in body
basep=H/'results/core_gear_dense_protocol.json';p=json.loads(basep.read_text())
assert sha(H/'state_inputs/core_gear_dense_period_tt.ic')==p['seed_sha256']
rows=[]
for tag,observer,strobe in [('strobe',False,True),('observer',True,False),('both',True,True)]:
    case=f'core_gear_mesh_{tag}_tt';tb=H/'tb'/(case+'.scs');assert not tb.exists()
    b=body
    if strobe:b=b.replace('stop=750n outputstart=250n','stop=750n outputstart=250n strobeperiod=2n strobeoutput=all')
    if observer:
        b+='\n// Observer has no electrical input loading; its cross events can change the numerical mesh.\n'
        b+='ahdl_include "lc_loop_observer.va"\n'
        b+='XOBS (XP.vp XP.vn XP.refb XP.ctrl out 0 obsphase obscycles obsctrl obsdivcycles) lc_loop_observer\n'
        b+='save obsphase obscycles obsctrl obsdivcycles\n'
    tb.write_text(b)
    rows.append(dict(case=case,observer=observer,strobe=strobe,tb_sha256=sha(tb)))
out=dict(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),status='prepared_not_run',run='coremesh01',cases=rows,
    baseline_run='coregeardense01',baseline_case='core_gear_dense_period_tt',source_validation_sha256=sha(vp),
    baseline_protocol_sha256=sha(basep),seed_sha256=p['seed_sha256'],physical_state_units=p['physical_state_units'],
    expected_rising_edges_per_period=p['expected_rising_edges_per_period'],limits=p['limits'],
    condition='Same612actualwarmstates,physicalDUT,750ns/1psGear2,tolerances,250nsdenseperiods; no physical voltage/current/state changes. Three serial runs add2ns forcedstrobes,observercross events,orboth; compare against completedneither baseline.',
    source_documentation=dict(path='research/spectre_help/tran.txt',sha256=sha(ROOT/'research/spectre_help/tran.txt'),lines=[652,657],finding='Spectre forces a step at each strobe point; outputstrobing can therefore change numerical integration.'),
    hypothesis='The first dense restart also removed the observer and forced strobes from its warm source. Common clock advance~.114ps/250ns may include a mesh-induced operating-point change; this is a hypothesis, not a proved cause.',
    launch_gate='One released6threadlongslot,3serialcases,total<=18/fourlong+oneshort; no PSS or native-state claim.',
    limitations=['Allcases use the same text restore; this control cannot independently isolate missing hidden charge/history from ordinary post-restore settling.',
        'Observer inputs draw no current but cross events affect timestep selection. The observer is not part of the physical PLL.',
        'One-mV working gates remain unchanged; deterministic displacement is not random jitter.'],
    main_dut_modified=False,full_pll_acceptance=False)
(H/'results/core_mesh_protocol.json').write_text(json.dumps(out,indent=2)+'\n')
print(' '.join(x['case'] for x in rows))
