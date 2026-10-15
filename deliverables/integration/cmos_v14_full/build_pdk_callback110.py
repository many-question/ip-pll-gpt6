"""Independent pre-layout callback candidate; never edits frozen capture inputs.

The unified skill CLI is the parameter authority. Every distinct actual
W/L/model is evaluated numerically; narrow-width geometry must not be replaced
with a generic symbolic normal-diffusion formula. The hierarchy is specialized
at the unchanged existing W/L/NF/M and component values.
"""
from pathlib import Path
import ast, datetime, hashlib, json, re, subprocess, sys

ROOT=Path(__file__).resolve().parents[4]
H=ROOT/'share/deliverables/integration/cmos_v14_full'
B=ROOT/'share/deliverables/blocks/cmos_v14_full'
SOURCE=ROOT/'research/runs/spectre_cmos_v14_full/rt4center109ssd01/rt4r48_recenter109_k41_tt'
SKILL=Path.home()/'.codex/skills/pdk-callback/scripts/pdk_callback.py'
PRIVATE=ROOT/'research/pdk_callback110';PRIVATE.mkdir(exist_ok=True)
FIELDS=('ad','as','pd','ps','nrd','nrs','sa','sb','sd','sca','scb','scc')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):p.write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def solve(cell,changes,tag):
    inp=PRIVATE/(tag+'_input.json');out=PRIVATE/(tag+'_output.json')
    write(inp,changes)
    subprocess.run([sys.executable,str(SKILL),'solve','--pdk','tsmc180bcd','--cache-dir',str(ROOT/'research/pdk_callback_cache'),'--cell',cell,'--input',str(inp),'--output',str(out)],check=True)
    d=json.loads(out.read_text());assert d['status']=='ok' and d['result']['status']=='ok'
    assert not d['result']['warnings'],d['result']['warnings']
    return d
def parameters(s):return dict(re.findall(r'(\w+)=([^\s]+)',s))
SUFFIX={'f':1e-15,'p':1e-12,'n':1e-9,'u':1e-6,'m':1e-3,'k':1e3,'Meg':1e6}
def number(expr,env):
    expr=re.sub(r'(?<![\w.])((?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)(Meg|[fpnumk])\b',lambda m:str(float(m[1])*SUFFIX[m[2]]),expr)
    tree=ast.parse(expr,mode='eval')
    def rec(x):
        if isinstance(x,ast.Expression):return rec(x.body)
        if isinstance(x,ast.Constant) and isinstance(x.value,(int,float)):return x.value
        if isinstance(x,ast.Name):return env[x.id]
        if isinstance(x,ast.UnaryOp) and isinstance(x.op,ast.USub):return -rec(x.operand)
        if isinstance(x,ast.BinOp):
            a,b=rec(x.left),rec(x.right)
            if isinstance(x.op,ast.Add):return a+b
            if isinstance(x.op,ast.Sub):return a-b
            if isinstance(x.op,ast.Mult):return a*b
            if isinstance(x.op,ast.Div):return a/b
        raise ValueError(expr)
    return float(rec(tree))

def main():
    launch=json.loads((SOURCE/'launch.json').read_text())
    source_files={n:SOURCE/'inputs'/n for n in launch['inputs_sha256'] if n.endswith('.scs') and n!='rt4r48_recenter109_k41_tt.scs'}
    assert all(sha(p)==launch['inputs_sha256'][n] for n,p in source_files.items())
    texts={n:p.read_text() for n,p in source_files.items()}
    combined='\n'.join('// Frozen source: '+n+'\n'+re.sub(r'^include .*\n','',t,flags=re.M) for n,t in texts.items())
    subckts={}
    for m in re.finditer(r'^subckt (\w+)\s*\(([^)]*)\)(.*?)^ends\s+\w+',combined,re.M|re.S):
        defaults={};items=[]
        for line in m[3].splitlines():
            if line.startswith('parameters '):defaults.update(parameters(line))
            q=re.match(r'^\s*(\w+)\s*\(([^)]*)\)\s+(\w+)\s*(.*)$',line)
            if q:items.append((q[1],q[2],q[3],parameters(q[4])))
        subckts[m[1]]=(m[2],defaults,items)
    geometries={};expanded=0;variants={};path_map={}
    def visit(name,overrides,path,depth=0):
        nonlocal expanded
        assert depth<60
        pins,defaults,items=subckts[name];env={}
        for k,v in defaults.items():env[k]=overrides[k] if k in overrides else number(v,env)
        env.update(overrides)
        key=(name,tuple(sorted(env.items())))
        if key not in variants:variants[key]=dict(id=len(variants),name=name,pins=pins,parameters=env,items=[])
        var=variants[key];path_map[path]=var['id'];newitems=[]
        for inst,nodes,model,params in items:
            vals={k:number(v,env) for k,v in params.items()}
            if model in ('nch','pch'):
                assert vals.get('nf',1)==1 and vals.get('m',1)==1,vals
                geom=(model,round(vals['w'],15),round(vals['l'],15))
                geometries.setdefault(geom,[]).append(path+'.'+inst);expanded+=1
            if model in subckts:
                child=visit(model,vals,path+'.'+inst,depth+1)
                newitems.append(dict(instance=inst,nodes=nodes,child=child))
            else:newitems.append(dict(instance=inst,nodes=nodes,model=model,parameters=vals))
        if var['items']:assert var['items']==newitems
        else:var['items']=newitems
        return var['id']
    visit('pll_capture_rt4_r48_recenter109_v14',{},'XPLL')
    checks=[];solved={};providers={}
    for i,((model,w,l),paths) in enumerate(sorted(geometries.items())):
        d=solve('nmos2v' if model=='nch' else 'pmos2v',[['fingers','1'],['simM','1'],['w',format(w,'.12g')],['l',format(l,'.12g')]],'numeric_%03d'%i)
        v=d['result']['values'];providers[model]=d['provider']
        assert abs(number(v['w'],{})/w-1)<1e-7 and abs(number(v['l'],{})/l-1)<1e-7
        assert v['nf']=='1' and v['simM']=='1' and v['wpeflag']=='off'
        solved[(model,w,l)]={k:number(v[k],{}) for k in FIELDS}
        checks.append(dict(model=model,w=w,l=l,nf=1,m=1,instance_count=len(paths),example_path=paths[0],callback_values=solved[(model,w,l)],warnings=[],raw_result_sha256=sha(PRIVATE/('numeric_%03d_output.json'%i))))
    assert len(re.findall(r'^\s*\w+\s*\([^\n)]*\)\s+(?:nch|pch)\s+[^\n]+',combined,re.M))==94
    rows=[];bundles={};fmt=lambda x:format(x,'.16g')
    for version,suffix in [('before','base110'),('after','pdk110')]:
        lines=['simulator lang=spectre','// Numerically specialized current hierarchy. External code pins remain programmable.', '// Fixed W/L/NF/M and passive parameters; do not override geometry without regenerating callbacks.']
        for var in variants.values():
            name=var['name']+'_'+suffix+'_'+str(var['id'])
            lines+=['subckt '+name+' ('+var['pins']+')']
            for item in var['items']:
                prefix=item['instance']+' ('+item['nodes']+') '
                if 'child' in item:
                    child=next(x for x in variants.values() if x['id']==item['child'])
                    lines.append(prefix+child['name']+'_'+suffix+'_'+str(child['id']))
                else:
                    params=item['parameters'].copy();model=item['model']
                    before=prefix+model+' '+' '.join(k+'='+fmt(v) for k,v in params.items())
                    if version=='after' and model in ('nch','pch'):
                        params.update(solved[(model,round(params['w'],15),round(params['l'],15))])
                        after=prefix+model+' '+' '.join(k+'='+fmt(v) for k,v in params.items())
                        rows.append(dict(specialized_subckt=name,before=before,after=after))
                    lines.append(prefix+model+' '+' '.join(k+'='+fmt(v) for k,v in params.items()))
            lines+=['ends '+name,'']
        path=B/('rt4_callback110_'+version+'.scs')
        assert not path.exists(),'Refuse overwrite generated evidence'
        path.write_text('\n'.join(lines),encoding='utf-8');bundles[version]=str(path.relative_to(ROOT))
    entries={}
    for path,idx in path_map.items():
        if path.count('.')==1:
            var=next(x for x in variants.values() if x['id']==idx)
            entries[path]={ver:var['name']+'_'+suf+'_'+str(idx) for ver,suf in [('before','base110'),('after','pdk110')]}
    symbolic={'decision':'Do not apply symbolic normal-diffusion formulas globally. Numeric callback at W=240nm returns different AD/PD/NRD/SA/SD; specialize each unique geometry instead.'}
    result=dict(time=datetime.datetime.now().astimezone().isoformat(),scope='Independent frozen recenter109 complete circuit hierarchy; original files unchanged',providers=providers,source_sha256={n:sha(p) for n,p in source_files.items()},updated_mos_definition_rows=len(rows),source_mos_definition_rows=94,specialized_subcircuits=len(variants),module_entrypoints=entries,bundles=bundles,expanded_mos_instances=expanded,unique_numeric_geometries=len(checks),numeric_callback_checks=checks,symbolic_reductions=symbolic,definition_changes=rows,geometry_policy=dict(nf=1,m=1,w_l_unchanged=True,vshareSD='None',calcDiff=True,calcParam=True,wpeflag='off',meaning='PDK default single-finger unshared-diffusion geometry; not actual layout or PEX; WPE distances not invented'),nmoscap='Existing PDK nmoscap primitive and its lr/wr/mr remain unchanged',outputs_sha256={v:sha(B/('rt4_callback110_'+v+'.scs')) for v in ('before','after')})
    write(H/'results/pdk_callback110_parameters.json',result)
    print(json.dumps({k:result[k] for k in ['updated_mos_definition_rows','expanded_mos_instances','unique_numeric_geometries','outputs_sha256']},indent=2))
if __name__=='__main__':main()
