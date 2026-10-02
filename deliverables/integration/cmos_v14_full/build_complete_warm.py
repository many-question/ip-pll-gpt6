"""Seed the full programmable DUT from the completed single-mode physical run.

This is explicitly a constructed near-lock test, never cold-capture evidence.
FLL mapped nodes and divider topology differ, so their initial states are rebuilt.
"""
from pathlib import Path
import re,json,hashlib
H=Path(__file__).resolve().parent;ROOT=H.parents[3];B=H.parents[1]/'blocks/cmos_v14_full'
source=ROOT/'research/runs/spectre_cmos_v14_full/fullwarm/full_warm_tt/final.ic'
v={}
for line in source.read_text().splitlines():
 if line and not line.startswith('#'):
  a=line.split();v[a[0]]=(float(a[1]),' '.join(a[2:]))
old=dict(v);removed=[];changed={}
for k in list(v):
 if k.startswith(('XP.XC.XF.','XP.XD.','XMETER.')) or k in ('energy_nj','power_mw'):
  removed.append(k);del v[k]
def put(k,x,unit=''):
 changed[k]=[v.get(k,[None])[0],x];v[k]=(float(x),unit)
def r0(path,q):
 put(path+'.clkb',1.2);put(path+'.resetb',1.2);put(path+'.qm',q)
 for l in ['XM','XS']:
  put(path+'.'+l+'.x',q);put(path+'.'+l+'.qb',1.2-q);put(path+'.'+l+'.XN.x',0.)
targets={'state_out0':('XP.XC.state0',1),'state_out1':('XP.XC.state1',0),'state_out2':('XP.XC.state2',1),
 'enable':('XP.XC.acquired',1),'range_error':('range_error',0),'count_gate':('XP.XC.fll_gate',0),'count_reset':('XP.XC.fll_count_reset',1)}
for i in range(8):targets['coarse'+str(i)]=('XP.b'+str(i),(23>>i)&1)
for i in range(6):targets['dac'+str(i)]=('XP.XC.d'+str(i),(36>>i)&1)
for line in (B/'fll_controller_rf4_v14.scs').read_text().splitlines():
 m=re.match(r'(X\d+) \(\S+ refclk reset (\S+) vdd vss\) (tx_dff_r[01])',line)
 if not m:continue
 port,bit=targets.pop(m[2]) if m[2] in targets else ('XP.XC.XF.'+m[2],0)
 path='XP.XC.XF.'+m[1];q=1.2*bit
 if m[3]=='tx_dff_r1':
  put(path+'.db',1.2-q);put(path+'.qb',1.2-q);r0(path+'.XF',1.2-q)
 else:r0(path,q)
 put(port,q)
assert not targets,targets
# Preserve the genuine RF/2 prescaler state across an instance rename.
for k,(x,u) in old.items():
 if k.startswith('XP.XD.X0.'):put(k.replace('XP.XD.X0.','XP.XD.XPRE.'),x,u)
 elif k in ('XP.XD.q0','XP.XD.qb0'):put(k,x,u)
 elif k.startswith('XP.XD.X1.'):put(k.replace('XP.XD.X1.','XP.XD.XD4.'),x,u)
 elif k=='XP.XD.q2':put('XP.XD.d4b',x,u)
dest=H/'state_inputs/complete_warm_tt.ic'
dest.write_text('# Constructed near-lock state; not autonomous reset-acquisition evidence.\n'+'\n'.join(f'{k}\t{x:.16g}'+(' '+u if u else '') for k,(x,u) in sorted(v.items()))+'\n')
(H/'results/complete_warm_seed_provenance.json').write_text(json.dumps(dict(source=str(source.relative_to(ROOT)),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),initial_condition_sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),removed_nodes=removed,changed_voltages=changed,initialized_fll=dict(coarse=23,dac=36,state=5,acquired=True),scope='Constructed near-lock initial state for full programmable physical DUT; separate cold-start run remains authoritative for capture.'),indent=2)+'\n')
s=(H/'tb/complete_k41_tt.scs').read_text()
s=re.sub(r'^VRST .*','VRST (reset 0) vsource dc=0',s,flags=re.M)
s=re.sub(r'^VAP .*','VAP (apply 0) vsource dc=0',s,flags=re.M)
s=re.sub(r'^ic .*\n','',s,flags=re.M)
s=s.replace('delay=1n','delay=42.6666666666667n').replace('stop=36u','stop=8u readic="complete_warm_tt.ic"')
(H/'tb/complete_warm_tt.scs').write_text(s)
print('Built complete programmable near-lock fixture')
