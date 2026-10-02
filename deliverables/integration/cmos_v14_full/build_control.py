"""Map a32-reference-cycle physical acquisition controller; record changed window."""
from pathlib import Path
import json,subprocess,sys,collections
H=Path(__file__).resolve().parent;D=H.parents[1];B=D/'blocks/cmos_v14_full';ROOT=D.parent.parent
src=(D/'blocks/transistor_v2/fll_controller.v').read_text()
src=src.replace('256 reference periods','32 reference periods').replace('module fll_controller(', 'module fll_controller_full_v14(')
src=src.replace("{target_k,8'b0}","{3'b0,target_k,5'b0}").replace('tick==255','tick==31')
src='// Internal acquisition-window choice:32 reference periods,0.75MHz output count quantum.\n// This is synthesized hardware, not a simulator shortcut; all counters remain MOS.\n'+src
(B/'fll_controller_full_v14.v').write_text(src)
out=B/'fll_controller_full_v14_mapped.json'
command=f'read_verilog "{(B/"fll_controller_full_v14.v").as_posix()}"; hierarchy -top fll_controller_full_v14; proc; flatten; opt; techmap; opt; dffunmap; opt_clean; setundef -zero; opt_clean; write_json "{out.as_posix()}"'
p=subprocess.run([sys.executable,str(ROOT/'research/run_yosys.py'),'-p',command],capture_output=True,text=True)
(ROOT/'research/v14_full_synthesis.log').write_text(p.stdout+p.stderr)
if p.returncode:raise RuntimeError(p.stderr)
m=json.loads(out.read_text())['modules']['fll_controller_full_v14'];names={};ports=[]
for n,info in m['ports'].items():
 for i,bit in enumerate(info['bits']):
  name=n if len(info['bits'])==1 else f'{n}{i}';names[bit]=name;ports.append(name)
def node(bit):return {'0':'vss','1':'vdd'}.get(bit,names.get(bit,f'n{bit}'))
mapping={'$_AND_':('tx_and','ABY'),'$_OR_':('tx_or','ABY'),'$_NOT_':('pll_inv','AY'),'$_XOR_':('tx_xor','ABY'),'$_XNOR_':('tx_xnor','ABY'),'$_MUX_':('tx_mux','ABSY'),'$_DFF_PP0_':('tx_dff_r0','DCRQ'),'$_DFF_PP1_':('tx_dff_r1','DCRQ')}
s=['simulator lang=spectre','subckt tx_fll_controller_full_v14 ('+' '.join(ports)+' vdd vss)']
for i,(_,c) in enumerate(sorted(m['cells'].items())):
 sub,order=mapping[c['type']];nets=' '.join(node(c['connections'][k][0]) for k in order);s.append(f'X{i} ({nets} vdd vss) {sub}')
s.append('ends tx_fll_controller_full_v14');(B/'fll_controller_full_v14.scs').write_text('\n'.join(s)+'\n')
wrap=(D/'blocks/transistor_v3/pll_control_monitored.scs').read_text().replace('tx_pll_control_monitored','pll_control_full_v14').replace(' tx_fll_controller\n',' tx_fll_controller_full_v14\n')
wrap=wrap.replace('phase_good remains a sensing input.','phase_good is driven by the physical phase/envelope detector in the top DUT.')
(B/'pll_control_full_v14.scs').write_text(wrap)
verify=(D/'integration/transistor_v2/verify_fll_logic.py').read_text().replace("blocks/transistor_v2","blocks/cmos_v14_full").replace("fll_mapped.json","fll_controller_full_v14_mapped.json").replace("['fll_controller']","['fll_controller_full_v14']").replace('[256]*expected_windows','[32]*expected_windows').replace('ratio*24e6/256','ratio*24e6/32')
(H/'verify_fll_logic.py').write_text(verify)
(H/'results/control_mapping.json').write_text(json.dumps({'cells':len(m['cells']),'types':dict(collections.Counter(c['type'] for c in m['cells'].values())),'count_window_ref_periods':32,'resolution_output_hz':750000,'note':'Internal working parameter, not a change to output or jitter requirements; actual acquisition residual and handoff must pass physical tests.'},indent=2)+'\n')
print('Mapped',len(m['cells']),'cells')
