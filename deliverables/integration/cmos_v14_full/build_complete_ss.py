"""Full-DUT SS60 near-lock check, constructed from actual SS analog state.

Fresh watchdog and zero qualification history. The six-bank programmable DUT
is unchanged. Coarse24/DAC36,1.2V,K41/M4,10fF. Not a reset-capture test.
"""
from pathlib import Path
import json,re,hashlib
H=Path(__file__).resolve().parent;ROOT=H.parents[3];B=H.parents[1]/'blocks/cmos_v14_full'
source=H/'state_inputs/handoff_probe_tt.ic';analog=ROOT/'research/runs/spectre_cmos_v14_full/warmss/warm_center_ss/final.ic'
def read(p):
 d={}
 for line in p.read_text().splitlines():
  if line and not line.startswith('#'):
   a=line.split();d[a[0]]=(float(a[1]),' '.join(a[2:]))
 return d
v=read(source);a=read(analog);changed={}
def put(k,x,u=''):changed[k]=[v.get(k,[None])[0],x];v[k]=(float(x),u)
prefix=['XV.','XBM.','XS.','XCP.','XLF.','XRX.','XR.','XDET.','XREF.']
scalars=['vp','vn','ctrl','vc1','vmid','sp','sn','hp','hn','refb','clk','q1','data','vco_vdd','rx_vdd','rt_vdd']
for k in list(v):
 if k.startswith('XP.') and (k[3:] in scalars or any(k[3:].startswith(p) for p in prefix)) and k[3:] in a:put(k,*a[k[3:]])
put('out',*a['out'])
for k,(x,u) in a.items():
 if k.startswith('XD.X0.'):put('XP.'+k.replace('XD.X0.','XD.XPRE.'),x,u)
 elif k in ['XD.q0','XD.qb0']:put('XP.'+k,x,u)
 elif k.startswith('XD.X1.'):put('XP.'+k.replace('XD.X1.','XD.XD4.'),x,u)
 elif k=='XD.q2':put('XP.XD.d4b',x,u)
def r0(path,q):
 put(path+'.clkb',1.2);put(path+'.resetb',1.2);put(path+'.qm',q)
 for l in ['XM','XS']:
  put(path+'.'+l+'.x',q);put(path+'.'+l+'.qb',1.2-q);put(path+'.'+l+'.XN.x',0.)
for line in (B/'fll_controller_rf4_v14.scs').read_text().splitlines():
 m=re.match(r'(X\d+) \(\S+ refclk reset (coarse\d+|dac\d+) vdd vss\) (tx_dff_r[01])',line)
 if not m:continue
 i=int(re.search(r'\d+',m[2])[0]);q=1.2*((24 if m[2].startswith('coarse') else 36)>>i&1);path='XP.XC.XF.'+m[1]
 if m[3]=='tx_dff_r1':put(path+'.db',1.2-q);put(path+'.qb',1.2-q);r0(path+'.XF',1.2-q)
 else:r0(path,q)
 put(('XP.b' if m[2].startswith('coarse') else 'XP.XC.d')+str(i),q)
dest=H/'state_inputs/complete_near_ss.ic'
dest.write_text('# Constructed SS60 near-lock state; no reset-capture claim.\n'+'\n'.join(f'{k}\t{x:.16g}'+(' '+u if u else '') for k,(x,u) in sorted(v.items()))+'\n')
(H/'results/complete_ss_seed_provenance.json').write_text(json.dumps(dict(scope=__doc__,source_sha256={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in [source,analog]},state_sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),changed_initial_voltages=changed),indent=2)+'\n')
s=(H/'tb/complete_strict_tt.scs').read_text().replace('section=tt','section=ss').replace('temp=27','temp=60').replace('complete_strict_tt.ic','complete_near_ss.ic')
(H/'tb/complete_near_ss.scs').write_text(s)
print('Prepared unchanged fullDUT SS60 constructed near-lock4us/1ps/1e-5 with fresh watchdog history')
