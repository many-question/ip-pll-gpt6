"""Mapped graph timing, signed coarse motion, saturation and global budget tests."""
from pathlib import Path
import datetime,hashlib,json,math
from analyze_fll_async_quantization import Graph
H=Path(__file__).resolve().parent;B=H.parents[1]/'blocks/cmos_v14_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def check_trace(checks,enabled,handoff):
    assert len(checks)<=8 and all(11<=x['dac']<=53 for x in checks)
    changes=0
    for a,b in zip(checks,checks[1:]):
        assert b['cycle']-a['cycle']==164
        delta=b['coarse']-a['coarse']
        if delta:
            changes+=1;assert abs(delta)==1 and b['dac']==32
            assert (delta==1 and a['dac']<=15 and a['error_count']>0) or (delta==-1 and a['dac']>=49 and a['error_count']<0)
        assert changes<=1
    if enabled:
        assert len(handoff)==32 and len(checks)>=2
        a,b=checks[-2:]
        assert (a['coarse'],a['dac'])==(b['coarse'],b['dac'])
        assert abs(a['error_count'])<=1 and abs(b['error_count'])<=1
        assert not (b['dac']<=15 and b['error_count']>0) and not (b['dac']>=49 and b['error_count']<0)
    else:assert not handoff

def init():
    g=Graph('fll_recenter109_v14');v={'0':0,'1':1}
    v.update({b:0 for b in g.known if isinstance(b,int)})
    g.put(v,'target_k',41);g.put(v,'measured',0);g.clock(v,True)
    return g,v

def verify(label,plant,expected,coarse=19,expected_coarse=None):
    g,v=init()
    def reg(n,x):
        for i,b in enumerate(g.m['netnames'][n]['bits']):
            assert isinstance(b,int);v[b]=(x>>i)&1
    for n,x in [('state',0),('fine',1),('endpoint_checked',1),('verify_mode',1),('dac',32),('coarse',coarse),('verify_low',11),('verify_high',53)]:reg(n,x)
    checks=[];handoff=[]
    for cycle in range(1500):
        d=g.get(v,'dac');c=g.get(v,'coarse');state=g.get(v,'state_out')
        assert 0<=c<=255 and 11<=d<=53
        if state==3:
            e=plant(c,d,len(checks));assert isinstance(e,int) and 0<=5248+e<16384
            g.put(v,'measured',5248+e);checks.append(dict(cycle=cycle,coarse=c,dac=d,error_count=e))
        if state==4:handoff.append(cycle)
        g.clock(v)
        if g.get(v,'state_out')==5:break
    enabled=bool(g.get(v,'enable'));err=bool(g.get(v,'range_error'))
    assert g.get(v,'state_out')==5 and enabled!=err
    if expected is not None:assert enabled==expected,(label,checks,enabled)
    check_trace(checks,enabled,handoff)
    if expected_coarse is not None:assert g.get(v,'coarse')==expected_coarse,(label,checks)
    final=dict(label=label,enable=enabled,range_error=err,checks=checks,cycles=cycle)
    g.clock(v,True)
    assert not g.get(v,'enable') and not g.get(v,'range_error') and g.get(v,'coarse')==0 and g.get(v,'dac')==11
    for n in ['verify_mode','good_once','coarse_recentered','checks']:
        assert sum(v[b]<<i for i,b in enumerate(g.m['netnames'][n]['bits']))==0
    return final

def full(label,k,phase,offset=0):
    g,v=init();g.put(v,'target_k',k)
    m=next(m for m in [4,6,8,10,12,14] if 2688<=24*k*m<=3936)
    target=k*m*32;count=0;win=0;windows=[];checks=[];handoff=[]
    vb=g.m['netnames']['verify_mode']['bits'][0]
    for cycle in range(3200):
        c=g.get(v,'coarse');d=g.get(v,'dac');isverify=bool(v[vb])
        rf=4e9-5.4e6*c+20e6*(1.2*d/64-.6)+(offset if isverify else 0)
        delta=rf/4/24e6;edges=math.floor(phase+delta+1e-9)-math.floor(phase+1e-9);phase+=delta
        if g.get(v,'count_reset'):count=0
        if g.get(v,'count_gate'):count+=edges;win+=1
        elif win:windows.append(win);win=0
        if isverify and g.get(v,'state_out')==3:checks.append(dict(cycle=cycle,coarse=c,dac=d,error_count=count-target))
        if g.get(v,'state_out')==4:handoff.append(cycle)
        g.put(v,'measured',count);g.clock(v)
        if g.get(v,'state_out')==5:break
    enabled=bool(g.get(v,'enable'));err=bool(g.get(v,'range_error'))
    assert g.get(v,'state_out')==5 and enabled and not err,(label,k,checks)
    check_trace(checks,enabled,handoff)
    assert windows==[32]*9+[128]*(6+len(checks))
    return dict(label=label,k=k,offset_hz=offset,checks=checks,enable=enabled,cycles=cycle)

def main():
    out=H/'results/rt4_recenter109_logic.json';assert not out.exists()
    fulls=[full('nominal',k,ph) for k in [14,41] for ph in [.125,.625]]
    fulls += [full('frequency_moves_after_SAR',41,.375,offset) for offset in [-1.5e6,1.5e6]]
    direct=[]
    # Independent linear count plants: moving the coarse bank lowers frequency.
    for root in range(11,54):
        # A late coarse move can legitimately run out of the unchanged budget.
        # Interior roots must converge; edge-root tests verify safe bounded outcome.
        direct.append(verify('legal_initial_root_'+str(root),lambda c,d,i,r=root:2*(d-r)-32*(c-19),True if 16<=root<=48 else None))
    for label,plant,ok,c,expected in [
      ('low_edge_neighbor_budget_exhaustion',lambda c,d,i:2*(d-8)-32*(c-19),False,19,20),
      ('high_edge_neighbor_budget_exhaustion',lambda c,d,i:2*(d-56)-32*(c-19),False,19,18),
      ('positive_one_near_edge',lambda c,d,i: (4 if d>15 else 1) if c==19 else 2*(d-32),True,19,20),
      ('negative_one_near_edge',lambda c,d,i: (-4 if d<49 else -1) if c==19 else 2*(d-32),True,19,18),
      ('coarse255_no_wrap',lambda c,d,i:4,False,255,255),
      ('coarse0_no_wrap',lambda c,d,i:-4,False,0,0),
      ('still_high_after_one_change',lambda c,d,i:4,False,19,20),
      ('still_low_after_one_change',lambda c,d,i:-4,False,19,18),
      ('no_representable_deadband',lambda c,d,i:4*(d-25)+2,False,19,19),
      ('first_good_then_drift',lambda c,d,i:0 if i==0 else 2*(d-21),True,19,19),
      ('two_boundary_good_center',lambda c,d,i:1 if i==0 else -1,True,19,19),
      ('immediate_zero_twice',lambda c,d,i:0,True,19,19),
      ('alternating_nonconvergent',lambda c,d,i:4 if i%2==0 else -4,False,19,None),
      ('observed108_prefix_then_neighbor_plant',lambda c,d,i: [6,2,2][i] if i<3 else int(round(.5*(d-42))),True,19,20),
      ('one_change_and_drifting_neighbor',lambda c,d,i: [6,2,2][i] if i<3 else int(round(.5*(d-41)+.15*(i-3))),True,19,20),
    ]:
        direct.append(verify(label,plant,ok,c,expected))
    for label,seq,ok in [
      ('one_good_at_deadline',[0,2,0,-2,0,2,-2,0],False),
      ('two_good_at_deadline',[0,2,0,-2,0,2,0,0],True),
      ('coarse_change_does_not_reset_budget',[6,2,2,0,2,0,-2,0],False),
      ('coarse_change_deadline_success',[6,2,2,0,2,0,0],True),
    ]:
        direct.append(verify(label,lambda c,d,i,s=seq:s[min(i,len(s)-1)],ok))
    data=dict(time=datetime.datetime.now().astimezone().isoformat(),passed=True,full_sequence_cases=fulls,verification_cases=direct,
      mapped_sha256=sha(B/'fll_recenter109_v14_mapped.json'),rtl_sha256=sha(B/'fll_recenter109_v14.v'),
      boundary='Actual mapped logic with independent ideal frequency/count plants; no MOS capture/noise/PVT pass. Edge15/49 and one coarse move are candidate assumptions.')
    out.write_text(json.dumps(data,indent=2)+'\n');print(json.dumps(dict(passed=True,full_sequence_cases=len(fulls),verification_cases=len(direct))))
if __name__=='__main__':main()
