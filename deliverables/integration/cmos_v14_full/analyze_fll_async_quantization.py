"""Gate-graph FLL sweep with continuously advancing independent RF phase.

Linear frequency plant from prior logic validation, not an actual VCO model.
Count-reset no longer resets oscillator phase. Eight initial RF/4 phases perK.
No analog settling, gate-delay or device-noise/capture conclusions.
"""
from pathlib import Path
import json,math,time
H=Path(__file__).resolve().parent;B=H.parents[1]/'blocks/cmos_v14_full'
class Graph:
 def __init__(self,name):
  self.m=json.loads((B/(name+'_mapped.json')).read_text())['modules'][name]
  self.ff=[c for c in self.m['cells'].values() if 'DFF' in c['type']]
  comb=[c for c in self.m['cells'].values() if 'DFF' not in c['type']]
  known={'0','1'}|{b for p in self.m['ports'].values() if p['direction']=='input' for b in p['bits']}|{c['connections']['Q'][0] for c in self.ff};self.known=set(known);self.order=[]
  while comb:
   ready=[c for c in comb if all(b in known for k,v in c['connections'].items() if k!='Y' for b in v)];assert ready
   for c in ready:known.update(c['connections']['Y']);self.order.append(c);comb.remove(c)
  # Compile the inspected combinational graph into straight-line Python; semantics
  # remain the actual synthesized gates, not a duplicate controller implementation.
  body=[]
  for c in self.order:
   p=c['connections'];key=lambda n:repr(p[n][0]);a='v['+key('A')+']';b='v['+key('B')+']' if 'B' in p else '0';typ=c['type']
   expr={'$_NOT_':f'1-{a}','$_AND_':f'{a}&{b}','$_OR_':f'{a}|{b}','$_XOR_':f'{a}^{b}','$_XNOR_':f'1-({a}^{b})','$_MUX_':f'{b} if v[{key("S")}] else {a}' if 'S' in p else ''}[typ]
   body.append(f'v[{key("Y")}]={expr}')
  self.compiled=compile('\n'.join(body),'<synthesized gate graph>','exec')
 def put(self,v,p,n):
  for i,b in enumerate(self.m['ports'][p]['bits']):v[b]=(n>>i)&1
 def get(self,v,p):return sum(v[b]<<i for i,b in enumerate(self.m['ports'][p]['bits']))
 def clock(self,v,reset=False):
  self.put(v,'reset',int(reset));exec(self.compiled,{'v':v})
  v.update({c['connections']['Q'][0]:int(c['type']=='$_DFF_PP1_') if reset else v[c['connections']['D'][0]] for c in self.ff});exec(self.compiled,{'v':v})
def simulate(g,k,phase,f0=4e9,coarse_step=5.4e6,kvco=20e6):
 ratio=next(n for n in [4,6,8,10,12,14] if 2.688e9<=24e6*k*n<=3.936e9)
 v={'0':0,'1':1};v.update({b:0 for b in g.known if isinstance(b,int)});g.put(v,'target_k',k);g.put(v,'measured',0);g.clock(v,True)
 count=0;window=0;windows=[]
 for cycle in range(2000):
  code=g.get(v,'coarse');dac=g.get(v,'dac');rf=f0-coarse_step*code+kvco*(1.2*dac/64-.6)
  advance=rf/4/24e6;n=int(math.floor(phase+advance+1e-9)-math.floor(phase+1e-9));phase+=advance
  if g.get(v,'count_reset'):count=0
  if g.get(v,'count_gate'):count+=n;window+=1
  elif window:windows.append(window);window=0
  g.put(v,'measured',count);g.clock(v)
  if g.get(v,'state_out')==5:break
 assert g.get(v,'state_out')==5
 code=g.get(v,'coarse');dac=g.get(v,'dac');rf=f0-coarse_step*code+kvco*(1.2*dac/64-.6)
 return dict(k=k,ratio=ratio,code=code,dac=dac,rf_error_mhz=(rf-k*24e6*ratio)/1e6,range_error=bool(g.get(v,'range_error')),enable=bool(g.get(v,'enable')),cycles=cycle,windows=windows)
if __name__=='__main__':
 rows=[]
 for name in ['fll_controller_rf4_v14','fll_accuracy64_v14','fll_accuracy128_v14']:
  g=Graph(name);cases=[];start=time.monotonic()
  for k in range(9,42):
   for i in range(8):cases.append(dict(initial_rf4_phase=i/8,**simulate(g,k,i/8)))
  fine=32 if name=='fll_controller_rf4_v14' else (64 if '64_' in name else 128)
  assert all(c['windows']==[32]*9+[fine]*6 for c in cases)
  valid=[c for c in cases if c['enable'] and not c['range_error']]
  row=dict(controller=name,scope='Candidate/logic result only; current physicalDUT remains fll_controller_rf4_v14.',cases=cases,range_error_cases=len(cases)-len(valid),rf_error_range_mhz=[min(c['rf_error_mhz'] for c in valid),max(c['rf_error_mhz'] for c in valid)],max_abs_error_mhz=max(abs(c['rf_error_mhz']) for c in valid),acquisition_ref_cycles=sorted(set(c['cycles'] for c in cases)),runtime_s=time.monotonic()-start);rows.append(row)
  print({k:v for k,v in row.items() if k!='cases'},flush=True)
 (H/'results/fll_async_quantization.json').write_text(json.dumps(dict(scope=__doc__,variants=rows),indent=2)+'\n')
