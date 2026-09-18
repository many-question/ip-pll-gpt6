"""Check delivered TB references and positional module interfaces before reruns."""
from pathlib import Path
import re,json
HERE=Path(__file__).resolve().parent
TX=HERE.parents[1]/'blocks/transistor_v1';VA=HERE.parents[1]/'blocks/behavioral_va'
sources=list(TX.glob('*.scs'))+list(TX.glob('*.va'))+list(VA.glob('*.va'))
modules={}
for p in sources:
    s=p.read_text(encoding='utf-8')
    for name,ports in re.findall(r'\bmodule\s+(\w+)\s*\(([^)]*)\)',s):modules[name]=len(ports.split(','))
    for name,ports in re.findall(r'\bsubckt\s+(\w+)\s*\(([^)]*)\)',s):modules[name]=len(ports.split())
available={p.name for p in sources};errors=[];count=0
for p in sources+list((HERE/'tb').glob('*.scs')):
    s=p.read_text(encoding='utf-8')
    for dep in re.findall(r'^(?:ahdl_include|include)\s+"([^"]+)"',s,re.M):
        if not dep.startswith('/home/process/') and dep not in available:errors.append(f'{p.name}: missing include {dep}')
    for inst,nets,model in re.findall(r'^(\w+)\s+\(([^)\n]+)\)\s+(\w+)',s,re.M):
        if model in modules:
            count+=1
            if len(nets.split())!=modules[model]:errors.append(f'{p.name}: {inst} {model}: {len(nets.split())} pins, expected {modules[model]}')
print(json.dumps({'checked_instances':count,'testbenches':len(list((HERE/'tb').glob('*.scs'))),'errors':errors},indent=2))
if errors:raise SystemExit(1)
