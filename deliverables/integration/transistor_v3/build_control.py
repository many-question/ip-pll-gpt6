"""Synthesize project-owned RTL and map generic cells to real PDK MOS wrappers."""
import sys,subprocess,json,collections,shutil
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parents[1]/'blocks/transistor_v3'
D=H.parents[2]
ROOT=D.parent if D.name=='share' and (D.parent/'AGENTS.md').exists() else D
MAP={'$_AND_':('tx_and','ABY'),'$_OR_':('tx_or','ABY'),'$_NOT_':('pll_inv','AY'),
     '$_XOR_':('tx_xor','ABY'),'$_XNOR_':('tx_xnor','ABY'),'$_MUX_':('tx_mux','ABSY'),
     '$_DFF_PP0_':('tx_dff_r0','DCRQ'),'$_DFF_PP1_':('tx_dff_r1','DCRQ')}

def map_module(name):
 out=B/(name+'_mapped.json')
 command=f'read_verilog "{B.as_posix()}/pll_control.v"; hierarchy -top {name}; proc; flatten; opt; techmap; opt; dffunmap; opt_clean; write_json "{out.as_posix()}"'
 local=ROOT/'research/run_yosys.py'
 entry=[sys.executable,str(local)] if local.exists() else [shutil.which('yosys') or shutil.which('yowasp-yosys') or 'yowasp-yosys']
 (ROOT/'research').mkdir(exist_ok=True)
 p=subprocess.run(entry+['-p',command],capture_output=True,text=True)
 (ROOT/'research'/f'{name}_synthesis.log').write_text(p.stdout+p.stderr)
 if p.returncode:raise RuntimeError(p.stderr)
 m=json.loads(out.read_text())['modules'][name]
 names={};ports=[]
 for n,info in m['ports'].items():
  for i,b in enumerate(info['bits']):
   port=n if len(info['bits'])==1 else f'{n}{i}'
   names[b]=port;ports.append(port)
 def node(b):return {'0':'vss','1':'vdd'}.get(b,names.get(b,f'n{b}'))
 lines=['simulator lang=spectre',f'// From pll_control.v: {len(m["cells"])} generic cells mapped to MOS.',
        'subckt tx_'+name+' ('+' '.join(ports)+' vdd vss)']
 for i,(_,c) in enumerate(sorted(m['cells'].items())):
  sub,order=MAP[c['type']];nets=' '.join(node(c['connections'][n][0]) for n in order)
  lines.append(f'X{i} ({nets} vdd vss) {sub}')
 lines.append('ends tx_'+name)
 (B/(name+'.scs')).write_text('\n'.join(lines)+'\n')
 return {'name':name,'cells':len(m['cells']),'types':dict(collections.Counter(c['type'] for c in m['cells'].values())),'ports':ports}

if __name__=='__main__':
 result=[map_module(n) for n in ['pll_config','pll_supervisor']]
 (H/'results/control_mapping.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(result,indent=2))
