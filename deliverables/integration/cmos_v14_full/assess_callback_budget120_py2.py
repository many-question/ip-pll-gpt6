"""Python2-compatible execution of frozen mapped gates; abstract count inputs only."""
from __future__ import print_function
import os, json, hashlib, datetime
H=os.path.dirname(os.path.abspath(__file__))
B=os.path.normpath(os.path.join(H,'../../blocks/cmos_v14_full'))
def sha(p):
    with open(p,'rb') as f:return hashlib.sha256(f.read()).hexdigest()

class Graph(object):
    def __init__(self):
        self.m=json.load(open(B+'/fll_recenter109_v14_mapped.json'))['modules']['fll_recenter109_v14']
        self.ff=[c for c in self.m['cells'].values() if 'DFF' in c['type']]
        assert all(c['type'] in ['$_DFF_PP0_','$_DFF_PP1_'] for c in self.ff)
        comb=[c for c in self.m['cells'].values() if 'DFF' not in c['type']]
        known=set(['0','1'])|set(b for p in self.m['ports'].values() if p['direction']=='input' for b in p['bits'])|set(c['connections']['Q'][0] for c in self.ff)
        self.known=set(known);body=[]
        while comb:
            ready=[c for c in comb if all(b in known for k,v in c['connections'].items() if k!='Y' for b in v)]
            assert ready
            for c in ready:
                p=c['connections'];a='v[%r]'%p['A'][0];b='v[%r]'%p['B'][0] if 'B' in p else '0'
                expr={'$_NOT_':'1-'+a,'$_AND_':a+'&'+b,'$_OR_':a+'|'+b,'$_XOR_':a+'^'+b,'$_XNOR_':'1-('+a+'^'+b+')',
                      '$_MUX_':b+' if v[%r] else '%p['S'][0]+a if 'S' in p else ''}[c['type']]
                body.append('v[%r]=%s'%(p['Y'][0],expr));known.update(p['Y']);comb.remove(c)
        self.code=compile('\n'.join(body),'<frozen mapped gates>','exec')
    def put(self,v,n,x):
        for i,b in enumerate(self.m['ports'][n]['bits']):v[b]=(x>>i)&1
    def get(self,v,n):return sum(v[b]<<i for i,b in enumerate(self.m['ports'][n]['bits']))
    def clock(self,v,reset=False):
        self.put(v,'reset',int(reset));eval(self.code,{'v':v})
        v.update({c['connections']['Q'][0]:int(c['type']=='$_DFF_PP1_') if reset else v[c['connections']['D'][0]] for c in self.ff})
        eval(self.code,{'v':v})

def check(label,plant,expected):
    g=Graph();v={'0':0,'1':1};v.update({b:0 for b in g.known if isinstance(b,int)})
    g.put(v,'target_k',41);g.put(v,'measured',0);g.clock(v,True)
    for n,x in [('state',0),('fine',1),('endpoint_checked',1),('verify_mode',1),('dac',32),('coarse',6),('verify_low',11),('verify_high',53)]:
        for i,b in enumerate(g.m['netnames'][n]['bits']):v[b]=(x>>i)&1
    checks=[];handoff=[]
    for cycle in range(1500):
        d=g.get(v,'dac');c=g.get(v,'coarse');state=g.get(v,'state_out')
        assert c==6 and 11<=d<=53
        if state==3:
            error=plant(d,len(checks));g.put(v,'measured',5248+error)
            checks.append(dict(cycle=cycle,coarse=c,dac=d,error_count=error))
        if state==4:handoff.append(cycle)
        g.clock(v)
        if g.get(v,'state_out')==5:break
    enabled=bool(g.get(v,'enable'));err=bool(g.get(v,'range_error'))
    assert g.get(v,'state_out')==5 and enabled!=err and enabled==expected
    assert len(checks)<=8 and checks[0]['dac']==32 and checks[0]['error_count']==-5 and checks[1]['dac']==43
    assert all(b['cycle']-a['cycle']==164 for a,b in zip(checks,checks[1:]))
    if enabled:
        assert len(handoff)==32 and checks[-2]['dac']==checks[-1]['dac']
        assert abs(checks[-2]['error_count'])<=1 and abs(checks[-1]['error_count'])<=1
    else:assert not handoff
    return dict(label=label,enable=enabled,range_error=err,checks=checks,cycles=cycle)

def main():
    out=H+'/results/rt4_callback_budget120.json';assert not os.path.exists(out)
    lo=json.load(open(H+'/results/rt4_callback_start119_review120.json'))
    hi=json.load(open(H+'/results/rt4_callback_edge118_review119.json'))
    assert lo['coarse']==hi['coarse']==6 and (lo['dac'],hi['dac'])==(32,49)
    assert (lo['physical_snapshot_count'],hi['physical_snapshot_count'])==(5243,5265)
    rows=[]
    for acceptable in range(33,49):
        rows.append(check('hypothetical_single_good_dac_'+str(acceptable),
             lambda d,i,q=acceptable: -5 if d<=32 else 17 if d>=49 else (0 if d==q else -2 if d<q else 2),True))
    failures=[check('hypothetical_bracket_without_acceptable_integer_code',
          lambda d,i:-5 if d<=32 else 17 if d>=49 else (-2 if d<=40 else 2),False),
          check('hypothetical_count_sign_changes_after_first_check',lambda d,i:-5 if i==0 else 17,False)]
    result=dict(time=datetime.datetime.utcnow().isoformat()+'Z',passed=True,
       category='Frozen mapped digital gates with conditional artificial count inputs; not MOS/TT capture.',
       observed_endpoints=dict(coarse=6,dac=[32,49],count=[5243,5265],error=[-5,17]),
       assumptions='Stationary monotone response with exactly one acceptable integer DAC in33..48. Unmeasured counts are abstract +/-2 or0, not a fit or prediction. Physical endpoints do not establish these assumptions.',
       conditional_success_cases=rows,counterexamples=failures,
       maximum_checks=max(len(x['checks']) for x in rows),minimum_checks=min(len(x['checks']) for x in rows),original_budget=8,
       source_sha256={os.path.basename(p):sha(p) for p in [B+'/fll_recenter109_v14_mapped.json',B+'/fll_recenter109_v14.v',__file__]},
       boundary='Verification registers initialized only in DIGITAL unit test; no analog state loading or forced PLL code. No autonomous selection/physical handoff/capture claim. All16 successes keep coarse6; no physical validation of coarse-recenter branch.',
       conclusion='Eight-check budget covers all16 stationary single-good-code alternatives tested. Two counterexamples safely error without enable. No measured lock code or guarantee; do not widen budget or mechanically scan fixed codes.')
    with open(out,'w') as f:f.write(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(passed=True,conditional_cases=len(rows),counterexamples=len(failures),checks=[result['minimum_checks'],result['maximum_checks']])))
if __name__=='__main__':main()
