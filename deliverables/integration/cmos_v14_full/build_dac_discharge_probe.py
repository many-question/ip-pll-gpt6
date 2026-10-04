"""Test a physical switched DAC rail discharge against the unchanged original."""
from pathlib import Path
import datetime,hashlib,json,re
H=Path(__file__).resolve().parent;ROOT=H.parents[3];B=H.parents[1]/'blocks/cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
src=B.parent/'transistor_v2/fll_circuit.scs';s=src.read_text()
chunk=re.search(r'^subckt tx_fll_dac .*?^ends tx_fll_dac$',s,re.M|re.S)[0]
name='dac_discharge_v14';new=chunk.replace('tx_fll_dac',name)
new=new.replace('XI0 (d0 b0 vd vss)', '// Physical off-state discharge; on only when the header PMOS is off.\nMDIS (vd enable vss vss) nch w=1u l=1u ad=1u*240n as=1u*240n pd=2*(1u+240n) ps=2*(1u+240n)\nXI0 (d0 b0 vd vss)')
dest=B/(name+'.scs');assert not dest.exists();dest.write_text('simulator lang=spectre\n'+new+'\n')
cases=[]
for corner,temp in [('tt',27),('ss',60),('ff',0)]:
    case='dac_discharge_'+corner
    body=f'''simulator lang=spectre
global 0
include "/home/process/tsmc180bcd_gen2_2022/PDK/TSMC180BCD/models/spectre/c018bcd_gen2_v1d6.scs" section={corner}
include "cells.scs"
include "digital_cells_v2.scs"
include "fll_circuit.scs"
include "dac_discharge_v14.scs"
include "loop_filter_v5.scs"
simulatorOptions options temp={temp} reltol=1e-5 vabstol=1e-7 iabstol=1e-13
VDD (vdd 0) vsource dc=1.2
VEN (en 0) vsource type=pwl wave=[0 0 1u 0 1.0001u 1.2 4u 1.2 4.0001u 0 5u 0]
// DAC38, as used by the current periodic-core diagnostic.
V1 (d1 0) vsource dc=1.2
V2 (d2 0) vsource dc=1.2
V5 (d5 0) vsource dc=1.2
XO (0 d1 d2 0 0 d5 en original vdd 0) tx_fll_dac
XN (0 d1 d2 0 0 d5 en candidate vdd 0) dac_discharge_v14
XLO (ctrl_o vc1_o en original vdd 0) tx_loop_filter_v5
XLN (ctrl_n vc1_n en candidate vdd 0) tx_loop_filter_v5
save en original candidate ctrl_o ctrl_n vc1_o vc1_n XO.vd XN.vd XO.b0 XN.b0 XO.b3 XN.b3 XO.b4 XN.b4 VDD:p
saveOptions options save=selected
tran tran stop=5u maxstep=10p method=gear2only errpreset=conservative writefinal="__FINAL_STATE__"
'''
    tb=H/'tb'/(case+'.scs');assert not tb.exists();tb.write_text(body)
    cases.append(dict(case=case,corner=corner,temp_c=temp,tb_sha256=sha(tb)))
p=dict(scope=__doc__,run='dacdischarge01',time=datetime.datetime.now().astimezone().isoformat(),cases=cases,
    hypothesis='The powered-off DAC rail and low-input inverter nodes drift because no intentional discharge path exists. A small enable-controlled NMOS may provide a definite off state without changing active DAC behavior.',
    source_file=src.relative_to(ROOT).as_posix(),source_sha256=sha(src),candidate_sha256=sha(dest),
    physical_change='One1um/1um PDK NMOS from vd to ground, gate=enable. Original DAC and paired physical loopfilter retained in the same TB.',
    conditions='1.2V,DAC38,TT27/SS60/FF0,actual7.162pF+.477pF loopfilter and20u/40u prechargeTGs; acquired rises at1us/falls4us with100ps edges,5us/10ps/Gear2.',
    working_limits=dict(active_output_difference_v=.001,off_rail_max_v=.001,additional_held_ctrl_difference_v=.001),
    limitations=['Unit functional and loading test only; no proof this fixes corePSS.','Ideal enable/data stimuli; complete FLL/CP/reference loading and capture must be checked before adoption.','Three paired corners do not establish allPVT, MonteCarlo or noise.','No change to original main or currently running complete RT4 candidate.'],
    main_dut_modified=False,full_pll_acceptance=False)
(H/'results/dac_discharge_protocol.json').write_text(json.dumps(p,indent=2)+'\n');print(' '.join(x['case'] for x in cases))
