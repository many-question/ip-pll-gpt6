"""Expand project-owned subcircuits and audit physical DUT boundaries."""
from pathlib import Path
from collections import Counter
import re,json,hashlib,argparse
H=Path(__file__).resolve().parent;D=H.parents[1]
def audit(top,includes=()):
    available={p.name:p for p in (D/'blocks').rglob('*.scs')}
    files={};defs={}
    def read(name):
        if name in files:return
        p=available[name];s=p.read_text();files[name]=p
        for inc in re.findall(r'^include\s+"([^"]+)"',s,re.M):
            if not inc.startswith('/'):read(inc)
        current=None;lines=[]
        for no,line in enumerate(s.splitlines(),1):
            line=line.strip()
            if line.startswith('subckt '):current=line.split()[1];lines=[]
            elif line.startswith('ends '):
                assert current not in defs,('Duplicate definition',current,name)
                defs[current]=(p,lines);current=None
            elif current is not None:lines.append((no,line))
    for name in includes:read(name)
    read(top+'.scs');counts=Counter();seen=Counter();probes=[];violations=[]
    def expand(name,path):
        seen[name]+=1
        p,lines=defs[name]
        for no,line in lines:
            if not line or line.startswith(('//','parameters')):continue
            mt=re.match(r'(\S+)\s+\([^)]*\)\s+(\S+)(.*)',line)
            if not mt:
                violations.append(dict(path=path,file=str(p),line=no,text=line));continue
            instance,kind,params=mt.groups();node=path+'.'+instance
            if kind in defs:expand(kind,node)
            else:
                counts[kind]+=1
                if kind=='vsource' and params.strip()=='dc=0':probes.append(node)
                elif kind not in ['nch','pch','nmoscap','resistor','capacitor','inductor']:
                    violations.append(dict(path=node,kind=kind,file=str(p),line=no,text=line))
    expand(top,'DUT')
    result=dict(top=top,physical_primitive_counts=dict(counts),expanded_subcircuit_counts=dict(seen),
                zero_volt_current_probes=probes,violations=violations,physical_boundary_pass=not violations,
                source_hashes={k:hashlib.sha256(p.read_bytes()).hexdigest() for k,p in files.items()},
                scope='Structural audit only, not function/noise/reliability signoff. PDK nmoscap treated as a physical PDK primitive. RLC Q and passive geometry remain provisional. External supply/reference/config and testbench-only observer lie outside DUT.')
    (H/'results'/f'boundary_{top}.json').write_text(json.dumps(result,indent=2)+'\n')
    print(top,dict(counts),'violations',violations)
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('top');p.add_argument('--include',nargs='*',default=[])
    a=p.parse_args();audit(a.top,a.include)
