"""Unintegrated FLL candidate: extra coarse step supplies fine-search headroom.

Uses the128-reference fine-window candidate, preserving all earlier variants.
This is a model-level functional proposal, not a selected full-DUT revision.
"""
from pathlib import Path
import subprocess,sys,json,collections
H=Path(__file__).resolve().parent;ROOT=H.parents[3];B=H.parents[1]/'blocks/cmos_v14_full'
name='fll_center128_v14'
s=(B/'fll_accuracy128_v14.v').read_text().replace('fll_accuracy128_v14',name)
old="(coarse_keep==255) ? 255 : coarse_keep+1'b1"
assert old in s
s=s.replace(old,"(coarse_keep>=254) ? 255 : coarse_keep+2'd2")
(B/(name+'.v')).write_text(s)
out=B/(name+'_mapped.json')
cmd=f'read_verilog "{(B/(name+".v")).as_posix()}"; hierarchy -top {name}; proc; flatten; opt; techmap; opt; dffunmap; opt_clean; setundef -zero; opt_clean; write_json "{out.as_posix()}"'
p=subprocess.run([sys.executable,str(ROOT/'research/run_yosys.py'),'-p',cmd],capture_output=True,text=True)
(ROOT/'research'/(name+'_synthesis.log')).write_text(p.stdout+p.stderr);assert p.returncode==0,p.stderr
m=json.loads(out.read_text())['modules'][name];names={};ports=[]
for n,info in m['ports'].items():
 for i,bit in enumerate(info['bits']):
  label=n if len(info['bits'])==1 else f'{n}{i}';names[bit]=label;ports.append(label)
def node(bit):return {'0':'vss','1':'vdd'}.get(bit,names.get(bit,f'n{bit}'))
mapping={'$_AND_':('tx_and','ABY'),'$_OR_':('tx_or','ABY'),'$_NOT_':('pll_inv','AY'),'$_XOR_':('tx_xor','ABY'),'$_XNOR_':('tx_xnor','ABY'),'$_MUX_':('tx_mux','ABSY'),'$_DFF_PP0_':('tx_dff_r0','DCRQ'),'$_DFF_PP1_':('tx_dff_r1','DCRQ')}
lines=['simulator lang=spectre','// Unintegrated candidate; no analog validation.','subckt tx_'+name+' ('+' '.join(ports)+' vdd vss)']
for i,(_,c) in enumerate(sorted(m['cells'].items())):
 sub,order=mapping[c['type']];nets=' '.join(node(c['connections'][k][0]) for k in order);lines.append(f'X{i} ({nets} vdd vss) {sub}')
lines.append('ends tx_'+name);(B/(name+'.scs')).write_text('\n'.join(lines)+'\n')
print(name,len(m['cells']),'cells',dict(collections.Counter(c['type'] for c in m['cells'].values())))
