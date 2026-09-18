"""Cycle simulation of synthesized gate graph, with an independent frequency plant.

This is functional digital evidence only, separate from Spectre device evidence.
"""
from pathlib import Path
import json,collections
H=Path(__file__).resolve().parent
B=H.parents[1]/'blocks/transistor_v2'
m=json.loads((B/'fll_mapped.json').read_text())['modules']['fll_controller']
ff=[c for c in m['cells'].values() if 'DFF' in c['type']]
comb=[c for c in m['cells'].values() if 'DFF' not in c['type']]
known={'0','1'}|{b for v in m['ports'].values() if v['direction']=='input' for b in v['bits']}|{c['connections']['Q'][0] for c in ff}
order=[]
while comb:
    ready=[c for c in comb if all(b in known for k,v in c['connections'].items() if k!='Y' for b in v)]
    assert ready,'Combinational loop or unsupported cell'
    for c in ready:known.update(c['connections']['Y']);order.append(c);comb.remove(c)
def put(v,p,num):
    for i,b in enumerate(m['ports'][p]['bits']):v[b]=(num>>i)&1
def get(v,p):return sum(v[b]<<i for i,b in enumerate(m['ports'][p]['bits']))
def settle(v):
    for c in order:
        p=c['connections'];a=v[p['A'][0]];b=v[p['B'][0]] if 'B' in p else 0;t=c['type']
        if t=='$_NOT_':x=1-a
        elif t=='$_AND_':x=a&b
        elif t=='$_OR_':x=a|b
        elif t=='$_XOR_':x=a^b
        elif t=='$_XNOR_':x=1-(a^b)
        elif t=='$_MUX_':x=b if v[p['S'][0]] else a
        else:raise ValueError(t)
        v[p['Y'][0]]=x
def clock(v,reset=False):
    put(v,'reset',int(reset));settle(v)
    new={c['connections']['Q'][0]:int(c['type']=='$_DFF_PP1_') if reset else v[c['connections']['D'][0]] for c in ff}
    v.update(new);settle(v)
def main():
    results=[]
    cases=[dict(k=k,name=f'k{k}',f0=4e9,step=5.4e6,expect_error=False) for k in range(9,42)]
    cases += [dict(k=41,name='code_zero_required',f0=3.932e9,step=20e6,expect_error=False),
              dict(k=41,name='above_maximum',f0=3.8e9,step=5.4e6,expect_error=True),
              dict(k=9,name='below_minimum',f0=4e9,step=1e6,expect_error=True)]
    for case in cases:
        k=case['k'];f0=case['f0'];step=case['step']
        ratio=next(n for n in [4,6,8,10,12,14] if 2.688e9<=24e6*k*n<=3.936e9)
        v={'0':0,'1':1};v.update({b:0 for b in known if isinstance(b,int)})
        put(v,'target_k',k);put(v,'measured',0);clock(v,True)
        accumulated=0.;window_cycles=0;windows=[];trace=[]
        for cycle in range(4500):
            code=get(v,'coarse');dac=get(v,'dac');freq=(f0-step*code+20e6*(1.2*dac/64-.6))/ratio
            if get(v,'count_reset'):accumulated=0.
            if get(v,'count_gate'):accumulated+=freq/24e6;window_cycles+=1
            elif window_cycles:windows.append(window_cycles);window_cycles=0
            put(v,'measured',int(accumulated));clock(v)
            if get(v,'state_out')==3:trace.append([cycle,code,dac,int(accumulated)])
            if get(v,'state_out')==5:break
        assert get(v,'state_out')==5,(case,trace)
        assert bool(get(v,'range_error'))==case['expect_error'],(case,trace)
        assert bool(get(v,'enable'))!=case['expect_error'],(case,trace)
        expected_windows=7 if case['name'] in ['code_zero_required','above_maximum'] else 15
        assert windows==[256]*expected_windows,(case,windows)
        code=get(v,'coarse');dac=get(v,'dac')
        error=f0-step*code+20e6*(1.2*dac/64-.6)-24e6*k*ratio
        if not case['expect_error']:assert abs(error)<ratio*24e6/256+0.375e6,(case,error)
        if case['name']=='code_zero_required':assert code==0
        results.append(dict(**case,ratio=ratio,coarse=code,dac=dac,enable=bool(get(v,'enable')),range_error=bool(get(v,'range_error')),done_cycle=cycle,vco_error_hz=error,windows=windows,trace=trace))
    (H/'results/fll_logic_validation.json').write_text(json.dumps(results,indent=2)+'\n')
    print('PASS 33 channels + code-zero boundary + 2 out-of-range cases; nominal 15 windows, code-zero 7 windows; max valid residual',max(abs(x['vco_error_hz']) for x in results if not x['expect_error']))
if __name__=='__main__':main()
