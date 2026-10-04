"""Recover a stable initialization trace after a live PSS enters Newton solving.

The input and raw hashes must agree before and after transfer. An incomplete
last PSF record may remain in the simulator's buffer; the existing period-drift
analyzer identifies that boundary explicitly. This does not claim a PSS result.
"""
from pathlib import Path
import argparse,base64,datetime,hashlib,json,re,shlex,shutil,subprocess,tarfile

H=Path(__file__).resolve().parent;ROOT=H.parents[3]
ap=argparse.ArgumentParser();ap.add_argument('run');ap.add_argument('case');ap.add_argument('--audit',required=True);a=ap.parse_args()
assert all(re.fullmatch(r'[A-Za-z0-9_]+',x) for x in [a.run,a.case])
assert Path(a.audit).name==a.audit and a.audit.endswith('.json')
j=ROOT/'research/runs/spectre_cmos_v14_full'/a.run/a.case
launch=json.loads((j/'launch.json').read_text())
remote=re.findall(r'(/home/jielu/TSMC180/MP/IP-PLL-GPT6/simulation/cmos_v14_full/[a-f0-9]{8})/'+a.case+r'\.raw',(j/'runner.log').read_text())[-1]
ssh=['C:/Windows/System32/OpenSSH/ssh.exe','-F',str(Path.home()/'.virtuoso-bridge/ssh_config_ipv6'),'-o','BatchMode=yes','thu-xia-v6']
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        while chunk:=f.read(1024*1024):h.update(chunk)
    return h.hexdigest()
def inventory():
    code="""import os,json,hashlib,subprocess
base=%r
case=%r
files=%r
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  while True:
   b=f.read(1024*1024)
   if not b:break
   h.update(b)
 return h.hexdigest()
log=open(base+'/spectre.out').read()
proof=[s for s in log.splitlines() if s.startswith('Conv norm')]
if not proof:
 print(json.dumps(dict(status='pending',reason='PSS has not yet reported a Newton residual')))
 raise SystemExit(0)
live=[]
for row in subprocess.check_output(['/bin/ps','-C','spectre','-o','pid=']).splitlines():
 pid=int(row.strip())
 try:
  if os.stat('/proc/%%d'%%pid).st_uid!=os.getuid():continue
  args=open('/proc/%%d/cmdline'%%pid,'rb').read().split('\\0')
 except IOError:continue
 if base+'/'+case+'.scs' in args:live.append(pid)
assert live,'Use the completed-run collector after the simulator exits'
raw=base+'/'+case+'.raw/pss.tran.pss';st=os.stat(raw)
print(json.dumps(dict(bytes=st.st_size,mtime=st.st_mtime,sha256=sha(raw),inputs_sha256=dict((k,sha(base+'/'+k)) for k in files),live_pids=live,newton_log_lines=proof,log=log)))
"""%(remote,a.case,sorted(launch['inputs_sha256']))
    enc=base64.b64encode(code.encode()).decode()
    return json.loads(subprocess.check_output(ssh+['/usr/bin/python -c "import base64;exec(base64.b64decode(\''+enc+'\'))"'],timeout=120))
before=inventory()
if before.get('status')=='pending':print(json.dumps(before));raise SystemExit(0)
assert before['inputs_sha256']==launch['inputs_sha256']
dest=j/'live_tstab';outpath=H/'results'/a.audit
assert not dest.exists() and not outpath.exists();dest.mkdir()
archive=dest/'trace.tar.gz'
with archive.open('wb') as f:
    subprocess.run(ssh+['tar -czf - -C '+shlex.quote(remote+'/'+a.case+'.raw')+' pss.tran.pss'],stdout=f,check=True,timeout=300)
target=dest/'pss.tran.pss'
with tarfile.open(archive) as tf:
    assert tf.getnames()==['pss.tran.pss']
    with tf.extractfile('pss.tran.pss') as source,target.open('wb') as sink:shutil.copyfileobj(source,sink)
after=inventory()
assert all(before[k]==after[k] for k in ['bytes','mtime','sha256','inputs_sha256'])
assert target.stat().st_size==before['bytes'] and sha(target)==before['sha256']
(dest/'spectre_snapshot.out').write_text(after['log'])
out=dict(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),run=a.run,case=a.case,
    remote_dir=remote,launch_sha256=sha(j/'launch.json'),remote_inputs_verified=True,snapshot_stable_before_and_after=True,
    process_pids_before=before['live_pids'],process_pids_after=after['live_pids'],newton_log_lines=after['newton_log_lines'],
    raw_tstab=dict(path=target.relative_to(ROOT).as_posix(),bytes=target.stat().st_size,sha256=before['sha256']),
    periodic_state_valid=False,random_jitter_measured=False,
    limitation='Initialization trajectory only; not the subsequently iterated orbit. No fabricated result.json or periodic/noise acceptance.')
outpath.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
