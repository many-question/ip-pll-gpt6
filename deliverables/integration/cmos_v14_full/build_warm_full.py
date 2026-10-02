"""Full physical K41 DUT near-lock initialization, explicitly NOT cold capture.

Use a genuine configured full-DUT state for config/supervisor/counter wiring,
and a converged physical main-loop state for analog/output nodes. Set the
FLL output registers to a declared DONE state through initial voltages only.
After t=0 every control node is driven solely by the physical DUT.
"""
from pathlib import Path
import re,json,hashlib
H=Path(__file__).resolve().parent;ROOT=H.parents[3];B=H.parents[1]/'blocks/cmos_v14_full'
R=ROOT/'research/runs/spectre_cmos_v14_full'
full=R/'acquirefast3/acquire_fast3_tt/final.ic';analog=R/'warmtt/warm_center_tt/final.ic'
def read(p):
 d={}
 for l in p.read_text().splitlines():
  if l and not l.startswith('#'):
   a=l.split();d[a[0]]=(float(a[1]),' '.join(a[2:]))
 return d
v=read(full);a=read(analog);modified={}
def put(k,x,unit=''):
 modified[k]=[v.get(k,[None])[0],x];v[k]=(float(x),unit)
prefixes=['XV.','XBM.','XS.','XCP.','XLF.','XRX.','XD.','XR.','XDET.','XREF.']
scalars=['vp','vn','ctrl','vc1','vmid','sp','sn','hp','hn','refb','clk','q1','data','vco_vdd','rx_vdd','rt_vdd']
for k in list(v):
 if k.startswith('XP.') and (k[3:] in scalars or any(k[3:].startswith(p) for p in prefixes)):
  value,unit=a.get(k[3:],(0.,v[k][1]));put(k,value,unit)
put('out',a['out'][0])
# An initialized FF is a charged physical latch, not a voltage source override.
def init_r0(path,q):
 put(path+'.clkb',1.2);put(path+'.resetb',1.2);put(path+'.qm',q)
 for l in ['XM','XS']:
  put(path+'.'+l+'.x',q);put(path+'.'+l+'.qb',1.2-q);put(path+'.'+l+'.XN.x',0.)
def init_ff(inst,kind,port,bit):
 path='XP.XC.XF.'+inst;q=1.2*bit
 if kind=='tx_dff_r1':
  put(path+'.db',1.2-q);put(path+'.qb',1.2-q);init_r0(path+'.XF',1.2-q)
 else:init_r0(path,q)
 put(port,q)
targets={'state_out0':('XP.XC.state0',1),'state_out1':('XP.XC.state1',0),'state_out2':('XP.XC.state2',1),
         'enable':('XP.XC.acquired',1),'range_error':('range_error',0),
         'count_gate':('XP.XC.fll_gate',0),'count_reset':('XP.XC.fll_count_reset',1)}
for i in range(8):targets['coarse'+str(i)]=('XP.b'+str(i),(23>>i)&1)
for i in range(6):targets['dac'+str(i)]=('XP.XC.d'+str(i),(36>>i)&1)
for line in (B/'fll_controller_full_v14.scs').read_text().splitlines():
 m=re.match(r'(X\d+) \(\S+ refclk reset (\S+) vdd vss\) (tx_dff_r[01])',line)
 if m and m[2] in targets:
  port,bit=targets.pop(m[2]);init_ff(m[1],m[3],port,bit)
assert not targets,targets
put('XP.en',1.2);put('XP.XC.phase_held',0)
init_r0('XP.XC.XPH',0)
v['vdd_source']=(1.2,'')
dest=H/'state_inputs/full_warm_tt.ic'
dest.write_text('# Constructed near-lock initial condition; NOT reset/cold-capture evidence.\n'+
                '\n'.join(f'{k}\t{x:.16g}'+(' '+u if u else '') for k,(x,u) in sorted(v.items()))+'\n')
manifest=dict(scope='Full physical K41 near-lock initialization; no internally forced sources. Not autonomous acquisition evidence.',
              source_files={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [full,analog]},
              initialized_fll=dict(coarse=23,dac=36,state=5,acquired=True),
              changed_initial_voltages=modified,initial_condition_sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),
              reference_note='First reference edge deferred by exactly one24MHz period to allow constructed digital initial voltages to settle; subsequent reference phase is unchanged.')
(H/'results/full_warm_seed_provenance.json').write_text(json.dumps(manifest,indent=2)+'\n')
s=(B/'pll_complete_k41_v14.scs').read_text().replace('pll_complete_k41_v14','pll_complete_k41_sampled_v14').replace('pll_control_full_v14','pll_control_sampled_v14')
(B/'pll_complete_k41_sampled_v14.scs').write_text(s)
s=(H/'tb/acquire_k41_tt.scs').read_text().replace('pll_complete_k41_v14','pll_complete_k41_sampled_v14')
s=s.replace('VDD (vdd 0) vsource dc=1.2','VDD (vdd_source 0) vsource dc=1.2\nahdl_include "supply_energy_observer.va"\nXMETER (vdd_source vdd 0 energy_nj power_mw) supply_energy_observer')
s=re.sub(r'^VRST .*','VRST (reset 0) vsource dc=0',s,flags=re.M)
s=re.sub(r'^VAP .*','VAP (apply 0) vsource dc=0',s,flags=re.M)
s=re.sub(r'^ic .*\n','',s,flags=re.M)
s=s.replace('delay=1n','delay=42.6666666666667n')
s=s.replace('stop=42u','stop=4u readic="full_warm_tt.ic"')
s+='\nsave energy_nj power_mw XP.XC.phase_held\n'
(H/'tb/full_warm_tt.scs').write_text(s)
print('Built complete near-lock physical DUT fixture; autonomous reset acquisition remains separate')
