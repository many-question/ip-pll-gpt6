"""Directed tests of actual synthesized gate graph, not analog PLL evidence."""
from pathlib import Path
import datetime, hashlib, json, math
from analyze_fll_async_quantization import Graph

H=Path(__file__).resolve().parent;B=H.parents[1]/'blocks/cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def run(label,k=41,phase=.375,errors=None,offset=0):
    g=Graph('fll_rebracket108_v14')
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
    assert all(11<=x['dac']<=53 for x in checks)
    result=dict(label=label,k=k,phase_initial=phase,offset_hz=offset,checks=checks,
        enable=enabled,range_error=err,final_dac=g.get(v,'dac'),coarse=g.get(v,'coarse'),cycles=cycle)
    # Reset must clear prior success/failure and the finite verification budget.
    g.clock(v,True)
    assert g.get(v,'enable')==0 and g.get(v,'range_error')==0 and v[vb]==0
    assert g.get(v,'coarse')==0 and g.get(v,'dac')==11
    return result

def verification(label,plant,expected,root=None):
    """Exercise mapped verification state; plant provides independent fresh counts."""
    g=Graph('fll_rebracket108_v14');v={'0':0,'1':1}
    v.update({b:0 for b in g.known if isinstance(b,int)})
    g.put(v,'target_k',41);g.put(v,'measured',0);g.clock(v,True)
    def reg(n,x):
        for i,b in enumerate(g.m['netnames'][n]['bits']):
            assert isinstance(b,int);v[b]=(x>>i)&1
    for n,x in [('state',0),('fine',1),('endpoint_checked',1),('verify_mode',1),
      ('dac',32),('coarse',19),('verify_low',11),('verify_high',53)]:reg(n,x)
    checks=[];handoff=[];first_good=None
    for cycle in range(1500):
        dac=g.get(v,'dac');state=g.get(v,'state_out')
        assert 11<=dac<=53 and g.get(v,'coarse')==19
        if state==3:
            e=plant(dac,len(checks));g.put(v,'measured',5248+e)
            checks.append(dict(cycle=cycle,dac=dac,error_count=e))
        if state==4:handoff.append(cycle)
        g.clock(v)
        if g.get(v,'state_out')==5:break
    enabled=bool(g.get(v,'enable'));err=bool(g.get(v,'range_error'))
    assert g.get(v,'state_out')==5 and len(checks)<=8 and enabled!=err
    assert enabled==expected,(label,checks,enabled)
    if enabled:
        assert len(handoff)==32
        assert checks[-1]['dac']==checks[-2]['dac']
        assert all(abs(x['error_count'])<=1 for x in checks[-2:])
        if root is not None:assert checks[-1]['dac']==root
    else:assert not handoff
    assert all(b['cycle']-a['cycle']==164 for a,b in zip(checks,checks[1:]))
    g.clock(v,True);assert g.get(v,'enable')==0 and g.get(v,'range_error')==0
    return dict(label=label,enable=enabled,range_error=err,checks=checks,cycles=cycle)

def main():
    out=H/'results/rt4_rebracket108_logic.json';assert not out.exists()
    full=[]
    for k in [14,41]:
        for ph in [.125,.625]:
            x=run('nominal',k,ph);assert x['enable'];full.append(x)
    for delta in [-1.5e6,1.5e6]:
        x=run('frequency_moves_after_SAR',offset=delta);assert x['enable'];full.append(x)
    direct=[]
    # All legal integer roots; signed frequency slope is external to the controller.
    for root in range(11,54):
        direct.append(verification('legal_root_'+str(root),lambda d,i,r=root:2*(d-r),True,root))
    for label,plant,ok in [
      ('below_low_rail',lambda d,i:2*(d-8),False),
      ('above_high_rail',lambda d,i:2*(d-56),False),
      ('no_representable_deadband',lambda d,i:4*(d-25)+2,False),
      ('first_good_then_drift',lambda d,i:0 if i==0 else 2*(d-21),True),
      ('measurement_moves_each_check',lambda d,i:4 if i%2==0 else -4,False),
      ('two_boundary_good',lambda d,i:1 if i==0 else -1,True),
      ('immediate_two_zero_counts',lambda d,i:0,True)]:
        direct.append(verification(label,plant,ok))
    # Hold a valid DAC while good/bad alternates; eight measurements cannot authorize
    # handoff unless the final two are both good at that same actual DAC.
    for label,seq,ok in [
      ('only_one_good_at_deadline',[0,2,0,-2,0,2,-2,0],False),
      ('second_good_on_deadline',[0,2,0,-2,0,2,0,0],True)]:
        direct.append(verification(label,lambda d,i,s=seq:s[i],ok))
    data=dict(time=datetime.datetime.now().astimezone().isoformat(),passed=True,
      full_sequence_cases=full,verification_cases=direct,
      mapped_sha256=sha(B/'fll_rebracket108_v14_mapped.json'),rtl_sha256=sha(B/'fll_rebracket108_v14.v'),
      boundary='Mapped logic only. Ideal asynchronous frequency plant and independent count perturbations; no MOS delay, analog monotonicity, real capture or noise claim.')
    out.write_text(json.dumps(data,indent=2)+'\n');print(json.dumps(dict(passed=True,full_sequence_cases=len(full),verification_cases=len(direct))))

if __name__=='__main__':main()

