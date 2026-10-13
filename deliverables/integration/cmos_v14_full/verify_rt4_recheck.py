"""Directed tests of actual synthesized gate graph, not analog PLL evidence."""
from pathlib import Path
import datetime, hashlib, json, math
from analyze_fll_async_quantization import Graph

H=Path(__file__).resolve().parent;B=H.parents[1]/'blocks/cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def run(label,k=41,phase=.375,errors=None,offset=0):
    g=Graph('fll_recheck128_v14')
    v={'0':0,'1':1};v.update({b:0 for b in g.known if isinstance(b,int)})
    g.put(v,'target_k',k);g.put(v,'measured',0);g.clock(v,True)
    m=next(m for m in [4,6,8,10,12,14] if 2688<=24*k*m<=3936)
    target=k*m*32;count=0;checks=[];windows=[];win=0;initial=None
    vb=g.m['netnames']['verify_mode']['bits'][0]
    for cycle in range(3200):
        code=g.get(v,'coarse');dac=g.get(v,'dac');verify=bool(v[vb])
        rf=4e9-5.4e6*code+20e6*(1.2*dac/64-.6)+(offset if verify else 0)
        delta=rf/4/24e6;edges=math.floor(phase+delta+1e-9)-math.floor(phase+1e-9);phase+=delta
        if g.get(v,'count_reset'):count=0
        if g.get(v,'count_gate'):count+=edges;win+=1
        elif win:windows.append(win);win=0
        measured=count
        if verify and g.get(v,'state_out')==3:
            if initial is None:initial=(code,dac)
            assert code==initial[0],'Recheck must not force/change coarse code'
            if errors is not None:measured=target+errors[min(len(checks),len(errors)-1)]
            checks.append(dict(cycle=cycle,dac=dac,error_count=measured-target))
        g.put(v,'measured',measured);g.clock(v)
        if g.get(v,'state_out')==5:break
    assert g.get(v,'state_out')==5 and len(checks)<=8
    enabled=bool(g.get(v,'enable'));err=bool(g.get(v,'range_error'))
    assert enabled!=err
    if enabled:
        assert len(checks)>=2 and all(abs(x['error_count'])<=1 for x in checks[-2:])
        assert checks[-1]['dac']==checks[-2]['dac']
        assert 11<=g.get(v,'dac')<=53
    assert windows==[32]*9+[128]*(6+len(checks)),windows
    result=dict(label=label,k=k,phase_initial=phase,offset_hz=offset,checks=checks,
        enable=enabled,range_error=err,final_dac=g.get(v,'dac'),coarse=g.get(v,'coarse'),cycles=cycle)
    # Reset must clear prior success/failure and the finite verification budget.
    g.clock(v,True)
    assert g.get(v,'enable')==0 and g.get(v,'range_error')==0 and v[vb]==0
    assert g.get(v,'coarse')==0 and g.get(v,'dac')==11
    return result

def main():
    out=H/'results/rt4_recheck_logic101.json';assert not out.exists()
    rows=[]
    for k in [14,41]:
        for phase in [.125,.625]:
            x=run('nominal',k,phase);assert x['enable'];rows.append(x)
    for delta in [-1.5e6,1.5e6]:
        x=run('frequency_moves_after_SAR',offset=delta);assert x['enable'];rows.append(x)
    for label,errors,enabled,n in [
        ('two_fresh_good',[0,0],True,2),
        ('one_good_then_move',[0,3,-3,1,-1],True,5),
        ('never_within_deadband',[4,-4],False,8),
        ('only_one_good_at_deadline',[4,4,4,4,4,4,4,0],False,8),
        ('second_good_on_deadline',[4,4,4,4,4,4,0,0],True,8)]:
        x=run(label,errors=errors);assert x['enable']==enabled and len(x['checks'])==n,(label,x);rows.append(x)
    data=dict(time=datetime.datetime.now().astimezone().isoformat(),passed=True,scope=__doc__,cases=rows,
        mapped_sha256=sha(B/'fll_recheck128_v14_mapped.json'),rtl_sha256=sha(B/'fll_recheck128_v14.v'),
        boundary='Logic only: independent ideal linear frequency plant plus directed count perturbations. Does not establish MOS timing, VCO monotonicity, real capture, or jitter.')
    out.write_text(json.dumps(data,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(passed=True,cases=len(rows),max_cycles=max(r['cycles'] for r in rows))))
if __name__=='__main__':main()
