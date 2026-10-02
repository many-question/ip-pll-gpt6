"""Read-only early mismatch detection; never substitutes for completed unit tests."""
from pathlib import Path
import json,re,subprocess,shlex,sys,datetime
import numpy as np
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
ref=json.loads((H/'results/capture_repair_logic.json').read_text())
ssh=['C:/Windows/System32/OpenSSH/ssh.exe','-F',str(Path.home()/'.virtuoso-bridge/ssh_config_ipv6'),'-o','BatchMode=yes','thu-xia-v6']
for run in sys.argv[1:]:
 for log in (R/run).glob('*/runner.log'):
  job=log.parent;case=job.name
  if (job/'result.json').exists():continue
  dirs=re.findall(r'(/home/jielu/TSMC180/MP/IP-PLL-GPT6/simulation/cmos_v14_full/[a-f0-9]{8})/',log.read_text(errors='replace'))
  if not dirs:continue
  raw=dirs[-1]+'/'+case+'.raw/tran.tran.tran'
  cp=subprocess.run(ssh+['tail -n 3000 '+shlex.quote(raw)],capture_output=True,text=True,timeout=30)
  assert cp.returncode==0,cp.stderr
  records=[]
  for block in cp.stdout.split('"time" ')[1:-1]:
   t=float(block.split()[0])
   vals={k:float(v) for k,v in re.findall(r'"([^"\n]+)"\s+([-+0-9.eE]+)',block)}
   records.append((t,vals))
  if not records:continue
  trace=ref['fll_mos_stimulus' if 'repair_fll_' in case else 'supervisor_mos_stimulus']
  times=np.array([(135+r['cycle']*1000/24)*1e-9 if 'cycle' in r else r['time_us']*1e-6 for r in trace])+10e-9
  ii=np.flatnonzero((times>records[0][0])&(times<records[-1][0]))
  if not len(ii):continue
  i=int(ii[-1]);point=trace[i];mismatches=[]
  for key,value in point['expected'].items():
   width={'coarse':8,'dac':6,'state_out':3}.get(key,1)
   for bit in range(width):
    name=key+str(bit) if width>1 else key
    if not all(name in d for _,d in records):continue
    v=float(np.interp(times[i],[t for t,_ in records],[d[name] for _,d in records]))
    expected=value>>bit&1
    if not (v>1.0 if expected else v<.2):mismatches.append(dict(signal=name,expected=expected,voltage=v))
  out=dict(run=run,case=case,last_raw_us=records[-1][0]*1e6,sample_us=times[i]*1e6,expected=point['expected'],mismatches=mismatches,preliminary_only=True,time=datetime.datetime.now().astimezone().isoformat())
  print(json.dumps(out))
  with (ROOT/'research/capture_unit_progress.jsonl').open('a') as f:f.write(json.dumps(out)+'\n')
