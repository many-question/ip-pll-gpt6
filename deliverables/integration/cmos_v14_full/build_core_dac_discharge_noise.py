"""Evaluate a physically discharged DAC island in the actual periodic core."""
from pathlib import Path
import datetime,hashlib,json,re
H=Path(__file__).resolve().parent;ROOT=H.parents[3];B=H.parents[1]/'blocks/cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
unit=H/'results/dac_discharge_all_validation.json';u=json.loads(unit.read_text())
assert u['complete'] and u['all_completed_checks_passed'] and all(x['checks']['off_internal_discharged'] for x in u['cases'])
base=H/'results/core_native_noise_protocol.json';p=json.loads(base.read_text())
old=B/'pll_noise_pulsetrip_core_v14.scs';name='pll_noise_dacdischarge_core_v14'
body=old.read_text().replace('pll_noise_pulsetrip_core_v14',name)
body=body.replace('include "fll_circuit.scs"','include "fll_circuit.scs"\ninclude "dac_discharge_all_v14.scs"')
body=body.replace('XDAC (d0 d1 d2 d3 d4 d5 acquired preset vdd vss) tx_fll_dac','XDAC (d0 d1 d2 d3 d4 d5 acquired preset vdd vss) dac_discharge_all_v14')
restored=body.replace(name,'pll_noise_pulsetrip_core_v14').replace('\ninclude "dac_discharge_all_v14.scs"','').replace(') dac_discharge_all_v14',') tx_fll_dac')
assert restored==old.read_text()
new=B/(name+'.scs');assert not new.exists();new.write_text(body)
run='coredacnoise01';case='core_dac_discharge_noise_tt';tb=H/'tb'/(case+'.scs');assert not tb.exists()
body=(H/'tb/core_native_noise_tt.scs').read_text().replace('pll_noise_pulsetrip_core_v14',name)
body=body.replace('tstab=250n','tstab=2u').replace('maxperiods=6','maxperiods=10')
save='/home/jielu/TSMC180/MP/IP-PLL-GPT6/simulation/cmos_v14_full/'+run+'_'+case+'.srf'
body=re.sub(r'^(pss pss .*)$',lambda m:m[0]+f' skipcount=2000 skipstop=5.25u savetime=[5.25u 5.75u] savefile="{save}"',body,flags=re.M)
assert 'readic="core_native_noise_tt.ic"' in body and 'recover=' not in body and 'readpss=' not in body
tb.write_text(body)
physical=dict(p['physical_dependencies_sha256']);del physical[old.name];physical[new.name]=sha(new);physical['dac_discharge_all_v14.scs']=sha(B/'dac_discharge_all_v14.scs')
p.update(scope=__doc__,run=run,case=case,time=datetime.datetime.now().astimezone().isoformat(),
    source_protocol_sha256=sha(base),unit_validation_sha256=sha(unit),tb_sha256=sha(tb),physical_dependencies_sha256=physical,
    initial_state_file='core_native_noise_tt.ic',native_savefile=save,native_checkpoint_times_s=[5.25e-6,5.75e-6],
    condition=p['condition']+' PhysicalDAC off-state clamp candidate:seven1um/1umNMOS. Original main andcompleteRT4candidateunchanged.',
    rationale='Rail-onlyunit leaves internal b nodes floating. Rail+sixb clamps establishoffstate atthreepairedcorners with<1mVadditionalheldctrlperturbation. Evaluateactualclosedloop/freshPSS; do notpresumeclampfixesNewton.',
    numerical_change='Increase own PSS tstab250ns->2us, maxperiods6->10; skipsavingearlypointsuntil5.25us,savealllast500ns. Same1psGear2/tolerances; noforcedstrobes. Physicalandsettlingchangesarebothdeclared; successwouldnotisolatewhichcausedimprovement.',
    main_dut_modified=False,full_pll_acceptance=False)
p['timing'].update(tstab_s=2e-6,maxperiods=10)
p['limitations']+=['Previouswaveformdifferencesdo notidentifythecauseofnonconvergence.','UnitDAC38/threepairedcornersis not all64DACcodes/fullFLLhandoff/PVT.','Earlyinitializationis sparselysaved;onlylast500nsisavailableforadenseperiodcomparison.']
(H/'results/core_dac_discharge_noise_protocol.json').write_text(json.dumps(p,indent=2)+'\n');print(case)
