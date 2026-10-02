"""Build candidate-only64/128-ref fine measurements; currentDUT unchanged.

Coarse SAR keeps32 references. Fine comparator uses>=target instead of>target
to avoid deliberately keeping an above-target count bin before the final+1DAC.
Asynchronous window quantization is separately swept; no analog capture claim.
"""
from pathlib import Path
import subprocess,sys,json,collections
H=Path(__file__).resolve().parent;ROOT=H.parents[3];B=H.parents[1]/'blocks/cmos_v14_full'
for window in [64,128]:
 name=f'fll_accuracy{window}_v14';s=(B/'fll_controller_rf4_v14.v').read_text().replace('fll_controller_rf4_v14',name)
 s=s.replace('wire [13:0] target =','wire [13:0] coarse_target =')
 s=s.replace('wire high_freq = measured > target;',f'wire [13:0] target = fine ? (coarse_target << {1 if window==64 else 2}) : coarse_target;\n wire high_freq = fine ? (measured >= target) : (measured > target);')
 s=s.replace('if(tick==31) begin tick<=0; state<=DRAIN; end',f'if(tick==(fine ? {window-1} : 31)) begin tick<=0; state<=DRAIN; end')
 assert f'fine ? {window-1}' in s
 (B/(name+'.v')).write_text('// Candidate only; not yet selected for completeDUT.\n'+s)
 out=B/(name+'_mapped.json');cmd=f'read_verilog "{(B/(name+".v")).as_posix()}"; hierarchy -top {name}; proc; flatten; opt; techmap; opt; dffunmap; opt_clean; setundef -zero; opt_clean; write_json "{out.as_posix()}"'
 p=subprocess.run([sys.executable,str(ROOT/'research/run_yosys.py'),'-p',cmd],capture_output=True,text=True)
 (ROOT/'research'/(name+'_synthesis.log')).write_text(p.stdout+p.stderr);assert p.returncode==0,p.stderr
 m=json.loads(out.read_text())['modules'][name];names={};ports=[]
 for n,info in m['ports'].items():
  for i,bit in enumerate(info['bits']):
   label=n if len(info['bits'])==1 else f'{n}{i}';names[bit]=label;ports.append(label)
 def node(bit):return {'0':'vss','1':'vdd'}.get(bit,names.get(bit,f'n{bit}'))
 mapping={'$_AND_':('tx_and','ABY'),'$_OR_':('tx_or','ABY'),'$_NOT_':('pll_inv','AY'),'$_XOR_':('tx_xor','ABY'),'$_XNOR_':('tx_xnor','ABY'),'$_MUX_':('tx_mux','ABSY'),'$_DFF_PP0_':('tx_dff_r0','DCRQ'),'$_DFF_PP1_':('tx_dff_r1','DCRQ')}
 lines=['simulator lang=spectre','// Candidate only; no integration or analog-capture acceptance.','subckt tx_'+name+' ('+' '.join(ports)+' vdd vss)']
 for i,(_,c) in enumerate(sorted(m['cells'].items())):
  sub,order=mapping[c['type']];nets=' '.join(node(c['connections'][k][0]) for k in order);lines.append(f'X{i} ({nets} vdd vss) {sub}')
 lines.append('ends tx_'+name);(B/(name+'.scs')).write_text('\n'.join(lines)+'\n')
 print(name,len(m['cells']),'cells',dict(collections.Counter(c['type'] for c in m['cells'].values())))
