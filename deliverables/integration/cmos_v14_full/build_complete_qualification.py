"""Repeat full TT near-lock with a fresh watchdog, after the strict analog check.

This repairs the earlier constructed TB's inherited watchdog history. The DUT
is unchanged, FLL remains initially DONE, and this is not reset acquisition.
"""
from pathlib import Path
import re,json,hashlib
H=Path(__file__).resolve().parent;ROOT=H.parents[3];D=H.parents[1]
source=ROOT/'research/runs/spectre_cmos_v14_full/completestrict01/complete_strict_tt/final.ic'
v={};removed=[];changed={}
for line in source.read_text().splitlines():
 if line and not line.startswith('#'):
  a=line.split();k=a[0]
  if k.startswith(('XE:','XE.','XEM_','XME_','XOBS:','XOBS.','energy_','power_','obs','reference_','rfclock_','output_')):
   removed.append(k);continue
  v[k]=(float(a[1]),' '.join(a[2:]))
def put(k,x,u=''):changed[k]=[v.get(k,[None])[0],x];v[k]=(float(x),u)
def r0(path,q):
 put(path+'.clkb',1.2);put(path+'.resetb',1.2);put(path+'.qm',q)
 for l in ['XM','XS']:
  put(path+'.'+l+'.x',q);put(path+'.'+l+'.qb',1.2-q);put(path+'.'+l+'.XN.x',0.)
def ff(path,kind,q):
 if kind=='tx_dff_r1':put(path+'.db',1.2-q);put(path+'.qb',1.2-q);r0(path+'.XF',1.2-q)
 else:r0(path,q)
for line in (D/'blocks/transistor_v3/frequency_watchdog.scs').read_text().splitlines():
 m=re.match(r'(X\d+) \(\S+ refclk reset (\S+) vdd vss\) (tx_dff_r[01])',line)
 if not m:continue
 q=1.2 if m[2]=='count_reset' else 0.;ff('XP.XC.XW.'+m[1],m[3],q)
 port={'count_reset':'XP.XC.watch_reset','count_gate':'XP.XC.watch_gate','frequency_good':'frequency_good','valid':'XP.XC.watchdog_valid'}.get(m[2],'XP.XC.XW.'+m[2]);put(port,q)
for line in (D/'blocks/transistor_v3/pll_supervisor.scs').read_text().splitlines():
 m=re.match(r'(X\d+) \(\S+ refclk reset (\S+) vdd vss\) (tx_dff_r[01])',line)
 if not m:continue
 ff('XP.XC.XS.'+m[1],m[3],0.)
 put({'qualified':'qualified','restart':'XP.restart','fault':'XP.XC.fault'}.get(m[2],'XP.XC.XS.'+m[2]),0.)
put('XP.en',1.2);put('XP.count_gate',0.);put('XP.count_reset',1.2)
dest=H/'state_inputs/complete_qual_tt.ic'
dest.write_text('# Constructed near-lock; fresh watchdog/qualification, not reset capture.\n'+'\n'.join(f'{k}\t{x:.16g}'+(' '+u if u else '') for k,(x,u) in sorted(v.items()))+'\n')
(H/'results/complete_qualification_seed_provenance.json').write_text(json.dumps(dict(scope=__doc__,source=str(source.relative_to(ROOT)),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),state_sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),changed_voltages=changed,removed_testbench_states=removed),indent=2)+'\n')
s=(H/'tb/complete_strict_tt.scs').read_text().replace('complete_strict_tt.ic','complete_qual_tt.ic').replace('maxstep=1p','maxstep=4p').replace('reltol=1e-5','reltol=1e-4').replace('vabstol=1e-7','vabstol=1e-6').replace('iabstol=1e-13','iabstol=1e-12')
(H/'tb/complete_qual_tt.scs').write_text(s)
print('Prepared fullDUT TT fresh-watchdog qualification fixture; not reset/FLL capture')
