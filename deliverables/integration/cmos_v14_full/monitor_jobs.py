"""Read-only progress snapshots; never use partial records as accepted results."""
from pathlib import Path
import subprocess,re,json,sys,shlex,datetime
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
ssh=['C:/Windows/System32/OpenSSH/ssh.exe','-F',str(Path.home()/'.virtuoso-bridge/ssh_config_ipv6'),'-o','BatchMode=yes','thu-xia-v6']
for run in sys.argv[1:]:
 for log in (R/run).glob('*/runner.log'):
  case=log.parent.name;dirs=re.findall(r'(/home/jielu/TSMC180/MP/IP-PLL-GPT6/simulation/cmos_v14_full/[a-f0-9]{8})/'+re.escape(case)+r'\.raw',log.read_text(errors='replace'))
  if not dirs:continue
  folder=dirs[-1];cmd='tail -n 600 '+shlex.quote(folder+'/'+case+'.raw/tran.tran.tran')
  cp=subprocess.run(ssh+[cmd],capture_output=True,text=True,timeout=30)
  records=cp.stdout.split('"time" ')[1:]
  if len(records)<2:print(case,'no complete live record',cp.stderr[:150]);continue
  record=records[-2];time=float(record.split()[0]);vals={k:float(v) for k,v in re.findall(r'"([^"\n]+)"\s+([-+0-9.eE]+)',record)}
  out={'run':run,'case':case,'time_us':time*1e6,'read_time':datetime.datetime.now().astimezone().isoformat(),'preliminary':True}
  for key in ['obsphase','obscycles','obsctrl','obsdivcycles','ctrl','XP.ctrl','phase_good','amp_good','qualified','cfg_ready','range_error','XP.en','XP.XC.acquired','frequency_good','XP.XC.phase_held','energy_nj','power_mw']:
   if key in vals:out[key]=vals[key]
  for name,prefix,n in [('coarse','XP.b',8),('dac','XP.XC.d',6),('count','XP.XC.m',14),('state','XP.XC.state',3)]:
   if prefix+'0' in vals:out[name]=sum(int(vals[prefix+str(i)]>.6)<<i for i in range(n))
  print(json.dumps(out))
  with (ROOT/'research/v14_full_progress.jsonl').open('a') as f:f.write(json.dumps(out)+'\n')
