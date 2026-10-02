"""Gate-graph tests and MOS unit-test stimuli; not actual-VCO capture evidence."""
from pathlib import Path
import json,math,datetime
from analyze_fll_async_quantization import Graph,simulate,H
B=H.parents[1]/'blocks/cmos_v14_full'
def init(g,inputs):
 v={'0':0,'1':1};v.update({b:0 for b in g.known if isinstance(b,int)})
 for p,n in inputs.items():g.put(v,p,n)
 g.clock(v,True);return v
def traced_fll(g,k=41,phase=.375):
 v=init(g,dict(refclk=0,target_k=k,measured=0));count=0;trace=[];trials=[]
 target=k*4*32
 for cycle in range(2000):
  code=g.get(v,'coarse');dac=g.get(v,'dac')
  freq=4e9-5.4e6*code+20e6*(1.2*dac/64-.6)
  advance=freq/4/24e6
  edges=math.floor(phase+advance+1e-9)-math.floor(phase+1e-9);phase+=advance
  if g.get(v,'count_reset'):count=0
  if g.get(v,'count_gate'):count+=edges
  # Fine SAR uses bitmask<=32 and the synthesized fine register.
  fine_bit=g.m['netnames']['fine']['bits'][0]
  if g.get(v,'state_out')==3 and v[fine_bit]:
   trials.append(dict(dac=dac,count=count,error=abs(count-target)))
  g.put(v,'measured',count);g.clock(v)
  out={p:g.get(v,p) for p,i in g.m['ports'].items() if i['direction']=='output'}
  trace.append(dict(cycle=cycle,measured=count,expected=out))
  if g.get(v,'state_out')==5:break
 best=min(trials,key=lambda x:(x['error'],x['dac']))
 assert g.get(v,'dac')==best['dac']
 return trace,trials

def supervisor_trace():
 g=Graph('pll_supervisor_capture_v14')
 def inputs(t):
  return dict(refclk=0,cfg_ready=int(t>=.2 and not 31<=t<32),
   fll_enable=int(t>=1),range_error=int(30.5<=t<31),
   phase_good=int(t>=24 and not 26.3<=t<26.38 and not 27.3<=t<27.7),
   frequency_good=1)
 v=init(g,inputs(0));rows=[]
 for n in range(838):
  t=(135+n*1000/24)*1e-3
  x=inputs(t)
  for p,b in x.items():g.put(v,p,b)
  g.clock(v)
  rows.append(dict(time_us=t,inputs=x,expected={p:g.get(v,p) for p,i in g.m['ports'].items() if i['direction']=='output'}))
 restarts=[i for i,r in enumerate(rows) if r['expected']['restart'] and (i==0 or not rows[i-1]['expected']['restart'])]
 assert len(restarts)==2,restarts
 enabled_start=next(i for i,r in enumerate(rows) if r['inputs']['fll_enable'])
 assert restarts[0]-enabled_start==511
 assert all(sum(r['expected']['restart'] for r in rows[i:i+8])==8 and rows[i+8]['expected']['restart']==0 for i in restarts)
 assert any(r['expected']['qualified'] for r in rows if 25.5<r['time_us']<26.3)
 assert all(r['expected']['qualified'] for r in rows if 26.3<r['time_us']<27.3)
 assert all(r['expected']['fault']==0 for r in rows if 31.1<r['time_us']<32.0)
 # Deadline:480 bad cycles followed by32 good cycles must qualify without restart.
 v=init(g,dict(refclk=0,cfg_ready=1,fll_enable=1,range_error=0,phase_good=0,frequency_good=1))
 for n in range(512):
  g.put(v,'phase_good',int(n>=480));g.clock(v)
 assert g.get(v,'qualified')==1 and g.get(v,'restart')==0
 return rows

def pwl(values,initial=0,edge=50e-12):
 pairs=[(0,1.2*initial)];last=initial
 for t,n in values:
  if n!=last:pairs.extend([(t,1.2*last),(t+edge,1.2*n)]);last=n
 return ' '.join(f'{t:.16g} {v:.8g}' for t,v in pairs)

if __name__=='__main__':
 g=Graph('fll_best128_v14');rows=[]
 for k in range(9,42):
  for i in range(8):rows.append(dict(initial_phase=i/8,**simulate(g,k,i/8)))
 assert all(r['enable'] and not r['range_error'] for r in rows)
 assert all(r['windows']==[32]*9+[128]*6 for r in rows)
 assert max(abs(r['rf_error_mhz']) for r in rows)<=1.125+1e-9
 endpoint=[]
 for label,f0,err in [('code_zero',3939e6,False),('too_slow',3900e6,True),('too_fast',5400e6,True)]:
  for i in range(8):
   r=simulate(g,41,i/8,f0=f0);r.update(label=label,initial_phase=i/8)
   assert r['range_error']==err and r['enable']!=err
   if label=='code_zero':assert r['code']==0
   endpoint.append(r)
 trace,trials=traced_fll(g);sup=supervisor_trace()
 model='/home/process/tsmc180bcd_gen2_2022/PDK/TSMC180BCD/models/spectre/c018bcd_gen2_v1d6.scs'
 for corner,temp in [('tt',27),('ss',60),('ff',0)]:
  base=[f'simulator lang=spectre\nglobal 0\ninclude "{model}" section={corner}',f'include "{model}" section=stat_noise',
   'simulator lang=spectre insensitive=no','include "cells.scs"','include "digital_cells_v2.scs"',
   f'simulatorOptions options temp={temp} reltol=1e-4 vabstol=1e-6 iabstol=1e-12',
   'VDD (vdd 0) vsource dc=1.2',
   'VREF (refclk 0) vsource type=pulse val0=0 val1=1.2 delay=10n rise=50p fall=50p width=20.7833333333333n period=41.6666666666667n',
   'VRST (reset 0) vsource type=pwl wave=[0 1.2 100n 1.2 100.05n 0]']
  s=base+['include "fll_best128_v14.scs"']
  for i in range(6):s.append(f'VK{i} (k{i} 0) vsource dc={1.2 if 41>>i&1 else 0}')
  for b in range(14):
   vals=[((135+x['cycle']*1000/24-1000/48)*1e-9,x['measured']>>b&1) for x in trace]
   s.append(f'VM{b} (m{b} 0) vsource type=pwl wave=[{pwl(vals)}]')
  ports=['refclk','reset']+[f'k{i}' for i in range(6)]+[f'm{i}' for i in range(14)]+[f'coarse{i}' for i in range(8)]+[f'dac{i}' for i in range(6)]+['count_gate','count_reset','enable','range_error']+[f'state_out{i}' for i in range(3)]
  outputs=ports[22:]
  s+=['XF ('+' '.join(ports)+' vdd 0) tx_fll_best128_v14']
  s += [f'C{i} ({p} 0) capacitor c=20f' for i,p in enumerate(outputs)]
  s += [f'tran tran stop={(135+(len(trace)+4)*1000/24)*1e-9:.16g} maxstep=500p method=traponly errpreset=moderate strobeperiod=1n strobeoutput=strobeonly',
   'save refclk reset '+' '.join(outputs),'saveOptions options save=selected']
  (H/'tb'/f'repair_fll_{corner}.scs').write_text('\n'.join(s)+'\n')
  s=base+['include "pll_supervisor_capture_v14.scs"']
  for p in ['cfg_ready','fll_enable','range_error','phase_good','frequency_good']:
   vals=[((x['time_us']-1/48)*1e-6,x['inputs'][p]) for x in sup]
   s.append(f'V{p} ({p} 0) vsource type=pwl wave=[{pwl(vals,initial=1 if p=="frequency_good" else 0)}]')
  outputs=['pll_enable','qualified','restart','fault']
  s+=['XS (refclk reset cfg_ready fll_enable range_error phase_good frequency_good pll_enable qualified restart fault vdd 0) tx_pll_supervisor_capture_v14']
  s += [f'C{i} ({p} 0) capacitor c=20f' for i,p in enumerate(outputs)]
  s += ['tran tran stop=35.1u maxstep=500p method=traponly errpreset=moderate strobeperiod=1n strobeoutput=strobeonly',
        'save refclk reset '+' '.join(outputs),'saveOptions options save=selected']
  (H/'tb'/f'repair_supervisor_{corner}.scs').write_text('\n'.join(s)+'\n')
 out=dict(scope=__doc__,created=datetime.datetime.now().astimezone().isoformat(),passed=True,
  nominal_cases=rows,range_endpoint_cases=endpoint,
  residual_mhz=[min(r['rf_error_mhz'] for r in rows),max(r['rf_error_mhz'] for r in rows)],
  fll_mos_stimulus=trace,fine_trial_selection=trials,supervisor_mos_stimulus=sup,
  supervisor_checks=['512-clock initial timeout','8-clock restart pulses','32-good qualification','brief-loss rejection','4-bad loss restart','fault clear with configuration reset','qualification wins on timeout deadline'],
  mos_boundary='Controller-only ideal measured-bus stimulus at midcycle,20fF outputs; excludes actual counter/DAC/VCO. FullDUT test remains required.',
  numerical_criteria='Sample10ns after each reference edge, every expected output bit must agree and lie<0.2V or>1.0V. Refinement on a failing case before attributing it to the circuit.')
 (H/'results/capture_repair_logic.json').write_text(json.dumps(out,indent=2)+'\n')
 print('PASS',len(rows),'nominal +',len(endpoint),'endpoint gate cases; residual MHz',out['residual_mhz'])
