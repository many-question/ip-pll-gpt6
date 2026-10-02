"""Current-DUT capture probe near the earlier observed FLL residual.

Constructed coarse22/DAC34/control0.62V initial state, with fresh physical
supervisor/watchdog history. No internal node is forced aftert=0. Two reference
phases separated by half an RF cycle; not reset-acquisition evidence.
"""
from pathlib import Path
import re,json,hashlib
H=Path(__file__).resolve().parent;ROOT=H.parents[3];D=H.parents[1];B=D/'blocks/cmos_v14_full'
source=H/'state_inputs/complete_strict_tt.ic';v={}
for line in source.read_text().splitlines():
 if line and not line.startswith('#'):
  a=line.split();v[a[0]]=(float(a[1]),' '.join(a[2:]))
changed={}
def put(k,x,u=''):changed[k]=[v.get(k,[None])[0],x];v[k]=(float(x),u)
def r0(path,q):
 put(path+'.clkb',1.2);put(path+'.resetb',1.2);put(path+'.qm',q)
 for l in ['XM','XS']:
  put(path+'.'+l+'.x',q);put(path+'.'+l+'.qb',1.2-q);put(path+'.'+l+'.XN.x',0.)
def ff(path,kind,q):
 if kind=='tx_dff_r1':put(path+'.db',1.2-q);put(path+'.qb',1.2-q);r0(path+'.XF',1.2-q)
 else:r0(path,q)
for line in (B/'fll_controller_rf4_v14.scs').read_text().splitlines():
 m=re.match(r'(X\d+) \(\S+ refclk reset (coarse\d+|dac\d+) vdd vss\) (tx_dff_r[01])',line)
 if not m:continue
 i=int(re.search(r'\d+',m[2])[0]);value=(22 if m[2].startswith('coarse') else 34)>>i&1
 ff('XP.XC.XF.'+m[1],m[3],1.2*value);put(('XP.b' if m[2].startswith('coarse') else 'XP.XC.d')+str(i),1.2*value)
for line in (D/'blocks/transistor_v3/frequency_watchdog.scs').read_text().splitlines():
 m=re.match(r'(X\d+) \(\S+ refclk reset (\S+) vdd vss\) (tx_dff_r[01])',line)
 if not m:continue
 q=1.2 if m[2]=='count_reset' else 0.;ff('XP.XC.XW.'+m[1],m[3],q)
 port={'count_reset':'XP.XC.watch_reset','count_gate':'XP.XC.watch_gate','frequency_good':'frequency_good','valid':'XP.XC.watchdog_valid'}.get(m[2],'XP.XC.XW.'+m[2]);put(port,q)
for key,value in [('XP.ctrl',.62),('XP.vc1',.62),('XP.XV.XL.nfilt',.7260),('XP.count_gate',0),('XP.count_reset',1.2)]:put(key,value)
dest=H/'state_inputs/handoff_probe_tt.ic';dest.write_text('# Constructed handoff probe, not reset-acquisition evidence.\n'+'\n'.join(f'{k}\t{x:.16g}'+(' '+u if u else '') for k,(x,u) in sorted(v.items()))+'\n')
(H/'results/handoff_probe_provenance.json').write_text(json.dumps(dict(scope=__doc__,source=str(source.relative_to(ROOT)),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),state_sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),changed_voltages=changed),indent=2)+'\n')
base=(H/'tb/complete_warm_tt.scs').read_text().replace('complete_warm_tt.ic','handoff_probe_tt.ic').replace('stop=8u','stop=2u')
for label,delay in [('p0',42.6666666666667),('p180',42.6666666666667+.5/3.936)]:
 s=base.replace('delay=42.6666666666667n',f'delay={delay:.16g}n')
 (H/'tb'/f'handoff_probe_{label}_tt.scs').write_text(s)
print('Built two current-DUT handoff probes; no reset-capture claim')
