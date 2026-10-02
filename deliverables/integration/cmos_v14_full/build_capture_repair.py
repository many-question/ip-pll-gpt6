"""Generate a separately named V14 repair; baseline input files stay unchanged."""
from pathlib import Path
import subprocess,sys,json,collections,hashlib,datetime
H=Path(__file__).resolve().parent;ROOT=H.parents[3];B=H.parents[1]/'blocks/cmos_v14_full'
MAP={'$_AND_':('tx_and','ABY'),'$_OR_':('tx_or','ABY'),'$_NOT_':('pll_inv','AY'),
     '$_XOR_':('tx_xor','ABY'),'$_XNOR_':('tx_xnor','ABY'),'$_MUX_':('tx_mux','ABSY'),
     '$_DFF_PP0_':('tx_dff_r0','DCRQ'),'$_DFF_PP1_':('tx_dff_r1','DCRQ')}
def map_module(name):
 out=B/(name+'_mapped.json')
 cmd=f'read_verilog "{(B/(name+".v")).as_posix()}"; hierarchy -top {name}; proc; flatten; opt; techmap; opt; dffunmap; opt_clean; setundef -zero; opt_clean; write_json "{out.as_posix()}"'
 p=subprocess.run([sys.executable,str(ROOT/'research/run_yosys.py'),'-p',cmd],capture_output=True,text=True)
 (ROOT/'research'/(name+'_synthesis.log')).write_text(p.stdout+p.stderr)
 assert p.returncode==0,p.stderr
 m=json.loads(out.read_text())['modules'][name];names={};ports=[]
 for n,info in m['ports'].items():
  for i,bit in enumerate(info['bits']):
   label=n if len(info['bits'])==1 else f'{n}{i}';names[bit]=label;ports.append(label)
 def node(bit):return {'0':'vss','1':'vdd'}.get(bit,names.get(bit,f'n{bit}'))
 lines=['simulator lang=spectre','// Project RTL mapped to actual MOS cells.',
        'subckt tx_'+name+' ('+' '.join(ports)+' vdd vss)']
 for i,(_,c) in enumerate(sorted(m['cells'].items())):
  sub,order=MAP[c['type']]
  nets=' '.join(node(c['connections'][k][0]) for k in order)
  lines.append(f'X{i} ({nets} vdd vss) {sub}')
 lines.append('ends tx_'+name)
 (B/(name+'.scs')).write_text('\n'.join(lines)+'\n')
 return dict(name=name,cells=len(m['cells']),types=dict(collections.Counter(c['type'] for c in m['cells'].values())),rtl_sha256=hashlib.sha256((B/(name+'.v')).read_bytes()).hexdigest())

if __name__=='__main__':
 name='fll_best128_v14'
 s=(B/'fll_center128_v14.v').read_text().replace('fll_center128_v14',name)
 s=s.replace('// Candidate only; not yet selected for completeDUT.',
   '// Capture repair: coarse32/fine128 references, actual measured-best fine DAC.\n// Select a tested fine code; do not add one to an already rejected last bit.')
 s=s.replace('reg [7:0] bitmask;','reg [7:0] bitmask;\n reg [13:0] best_error;\n reg [5:0] best_dac;')
 s=s.replace('assign state_out=state;',"""wire [13:0] trial_error = (measured>=target) ? measured-target : target-measured;
 wire better = (trial_error<best_error) || ((trial_error==best_error) && (dac<best_dac));
 wire [5:0] selected_dac = better ? dac : best_dac;
 assign state_out=state;""")
 s=s.replace('state<=SETTLE; tick<=0; count_gate<=0; count_reset<=1;',
   "state<=SETTLE; tick<=0; count_gate<=0; count_reset<=1; best_error<=14'h3fff;best_dac<=32;")
 s=s.replace('end else begin\n           if(bitmask==1)',"""end else begin
           if(better) begin best_error<=trial_error;best_dac<=dac;end
           if(bitmask==1)""")
 old="""if(fine_keep<11) begin dac<=11; range_error<=1; end
             else if(fine_keep>52) begin dac<=53; range_error<=1; end
             else dac<=fine_keep+1'b1;"""
 assert old in s
 s=s.replace(old,"""dac<=selected_dac;
             if(selected_dac<11 || selected_dac>53) range_error<=1;""")
 assert "if(better)" in s and "dac<=fine_keep+1" not in s
 (B/(name+'.v')).write_text(s)
 mapped=[map_module(name),map_module('pll_supervisor_capture_v14')]
 wrap=(B/'pll_control_rf4_v14.scs').read_text()
 wrap=wrap.replace('pll_control_rf4_v14','pll_control_capture_v14').replace('tx_fll_controller_rf4_v14','tx_'+name).replace('tx_pll_supervisor','tx_pll_supervisor_capture_v14')
 (B/'pll_control_capture_v14.scs').write_text(wrap)
 top=(B/'pll_complete_v14.scs').read_text().replace('pll_complete_v14','pll_capture_v14').replace('pll_control_rf4_v14','pll_control_capture_v14').replace('fll_controller_rf4_v14',name).replace('"pll_supervisor.scs"','"pll_supervisor_capture_v14.scs"')
 (B/'pll_capture_v14.scs').write_text(top)
 for corner in ['tt','ss','ff']:
  tb=(H/'tb'/f'complete_k41_{corner}.scs').read_text().replace('pll_complete_v14','pll_capture_v14')
  tb=tb.replace('stop=36u','stop=64u')
  (H/'tb'/f'repair_capture_{corner}.scs').write_text(tb)
 protocol=dict(created=datetime.datetime.now().astimezone().isoformat(),scope=__doc__,mapped=mapped,
  changes=['32-reference coarse SAR retained; coarse floor+2 headroom from previously screened candidate.',
   '128-reference fine windows; choose the actually tested DAC with minimum absolute count error. Equal errors prefer lower code. Remove unconditional final+1.',
   'First unqualified capture gets512reference clocks (21.333us), then an8-reference restart. Original32-good/4-bad qualification rules retained.'],
  unchanged='VCO/bias/Q5RLC, receiver, six-mode divider, retimer/output, sampler/CP/filter, phase/amplitude detector, configuration, watchdog and reference.',
  validation_order=['asynchronous gate-graph sweep and supervisor directed tests','MOS controller timing and supervisor TT/SS/FF','complete-DUT DC-supply reset capture, then stricter numerical/retention checks'],
  not_claimed='No complete capture result yet; no state recovery across modified circuits; no supply-ramp/fullPVT/noise/power improvement claim.')
 (H/'results/capture_repair_protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
 print(json.dumps(mapped,indent=2))
