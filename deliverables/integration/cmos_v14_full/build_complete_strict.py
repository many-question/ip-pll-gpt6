"""Strict complete-DUT near-lock check, using an explicitly constructed state.

Analog seed comes from the previous1ps physical main loop; digital configuration
and FLL DONE state from the same complete programmable DUT. Qualification history
is initialized low to permit settling. No internal node is forced after t=0.
This does not replace the independent reset-acquisition experiment.
"""
from pathlib import Path
import re,json,hashlib
H=Path(__file__).resolve().parent;ROOT=H.parents[3];D=H.parents[1];B=D/'blocks/cmos_v14_full';R=ROOT/'research/runs/spectre_cmos_v14_full'
full=R/'completedense01/complete_warm_tt/final.ic';analog=R/'warmtt/warm_center_tt/final.ic'
def read(p):
 d={}
 for line in p.read_text().splitlines():
  if line and not line.startswith('#'):
   a=line.split();d[a[0]]=(float(a[1]),' '.join(a[2:]))
 return d
v=read(full);a=read(analog);changed={};removed=[]
def put(k,x,u=''):
 changed[k]=[v.get(k,[None])[0],x];v[k]=(float(x),u)
for k in list(v):
 if k.startswith(('XOBS.','XE.')) or k in ['energy_nj','power_mw','obsphase','obscycles','obsctrl','obsdivcycles']:
  removed.append(k);del v[k]
prefix=['XV.','XBM.','XS.','XCP.','XLF.','XRX.','XR.','XDET.','XREF.']
scalars=['vp','vn','ctrl','vc1','vmid','sp','sn','hp','hn','refb','clk','q1','data','vco_vdd','rx_vdd','rt_vdd']
for k in list(v):
 if k.startswith('XP.') and (k[3:] in scalars or any(k[3:].startswith(p) for p in prefix)) and k[3:] in a:
  put(k,*a[k[3:]])
put('out',*a['out'])
for k,(x,u) in a.items():
 if k.startswith('XD.X0.'):put('XP.'+k.replace('XD.X0.','XD.XPRE.'),x,u)
 elif k in ['XD.q0','XD.qb0']:put('XP.'+k,x,u)
 elif k.startswith('XD.X1.'):put('XP.'+k.replace('XD.X1.','XD.XD4.'),x,u)
 elif k=='XD.q2':put('XP.XD.d4b',x,u)
def r0(path,q):
 put(path+'.clkb',1.2);put(path+'.resetb',1.2);put(path+'.qm',q)
 for latch in ['XM','XS']:
  put(path+'.'+latch+'.x',q);put(path+'.'+latch+'.qb',1.2-q);put(path+'.'+latch+'.XN.x',0.)
for line in (D/'blocks/transistor_v3/pll_supervisor.scs').read_text().splitlines():
 m=re.match(r'(X\d+) \(\S+ refclk reset (\S+) vdd vss\) tx_dff_r0',line)
 if not m:continue
 port={'qualified':'qualified','restart':'XP.restart','fault':'XP.XC.fault'}.get(m[2],'XP.XC.XS.'+m[2])
 r0('XP.XC.XS.'+m[1],0.);put(port,0.)
put('XP.en',1.2)
dest=H/'state_inputs/complete_strict_tt.ic'
dest.write_text('# Constructed strict near-lock state; not reset-acquisition evidence.\n'+'\n'.join(f'{k}\t{x:.16g}'+(' '+u if u else '') for k,(x,u) in sorted(v.items()))+'\n')
(H/'results/complete_strict_seed_provenance.json').write_text(json.dumps(dict(scope=__doc__,source_sha256={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in [full,analog]},state_sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),changed_initial_voltages=changed,removed_observer_nodes=removed),indent=2)+'\n')
s=(H/'tb/complete_warm_tt.scs').read_text().replace('complete_warm_tt.ic','complete_strict_tt.ic').replace('stop=8u','stop=4u').replace('maxstep=4p','maxstep=1p').replace('reltol=1e-4','reltol=1e-5').replace('vabstol=1e-6','vabstol=1e-7').replace('iabstol=1e-12','iabstol=1e-13')
s+='\nahdl_include "tb_edge_observer.va"\nahdl_include "tb_power_integrator.va"\n'
for label,node in [('reference','XP.refb'),('rfclock','XP.clk'),('output','out')]:
 s+=f'XME_{label} ({node} vdd 0 {label}_rise_ns {label}_fall_ns {label}_period_ns {label}_duty_percent) tb_edge_observer\n'
 s+='save '+' '.join(label+'_'+p for p in ['rise_ns','fall_ns','period_ns','duty_percent'])+'\n'
for label,probe in [('vco','XP.VVCO'),('rx','XP.VRX'),('rt','XP.VRT')]:
 s+=f'BM_{label} (power_{label}_w 0) bsource v=-v(vdd)*i("{probe}:1")\n'
 s+=f'XEM_{label} (power_{label}_w 0 energy_{label}_nj) tb_power_integrator\nsave energy_{label}_nj\n'
s+='save XP.refb XP.clk XP.vp XP.vn\n'
(H/'tb/complete_strict_tt.scs').write_text(s)
print('Built strict1ps/1e-5 full-DUT near-lock fixture with external edge/power observations')
