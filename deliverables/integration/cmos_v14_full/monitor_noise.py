"""Read-only PNoise grid progress; partial spectra are never acceptance evidence."""
from pathlib import Path
import subprocess,re,shlex,base64,sys,json,datetime
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
ssh=['C:/Windows/System32/OpenSSH/ssh.exe','-F',str(Path.home()/'.virtuoso-bridge/ssh_config_ipv6'),'-o','BatchMode=yes','thu-xia-v6']
for run in sys.argv[1:]:
 for p in (R/run).glob('*/runner.log'):
  if (p.parent/'result.json').exists():continue
  dirs=re.findall(r'(/home/jielu/TSMC180/MP/IP-PLL-GPT6/simulation/cmos_v14_full/[a-f0-9]{8})/',p.read_text(errors='replace'))
  if not dirs:continue
  folder=dirs[-1]+'/'+p.parent.name+'.raw'
  # Count numeric VALUE records only; the SWEEP declaration also starts "freq".
  code="import glob,json,os,re\na=[]\nfor p in glob.glob("+repr(folder+"/*.sample.pnoise")+"):\n f=[l.strip() for l in open(p) if re.match(chr(34)+'freq'+chr(34)+r'\\s+[-+0-9.eE]+\\s*$',l)]\n a.append([os.path.basename(p),len(f),f[-1] if f else None])\nprint(json.dumps(a))"
  encoded=base64.b64encode(code.encode()).decode()
  inline="exec(__import__('base64').b64decode('"+encoded+"'))"
  proc=subprocess.run(ssh+['/usr/bin/python -c '+shlex.quote(inline)],capture_output=True,text=True,timeout=60)
  assert proc.returncode==0,proc.stderr
  print(json.dumps(dict(time=datetime.datetime.now().astimezone().isoformat(),run=run,case=p.parent.name,partial_grid_progress=json.loads(proc.stdout),not_acceptance=True)))
