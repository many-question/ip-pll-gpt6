"""Collect one completed sampled-noise analysis even if later analyses still run.

Does not fabricate a completed whole-job manifest or launch a simulator. The
log must identify analysis completion, PSF files must end in END, and frozen
input/raw hashes must agree before, locally, and after the transfer.
"""
from pathlib import Path
import argparse,base64,datetime,hashlib,json,re,shlex,shutil,subprocess,tarfile
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
ap=argparse.ArgumentParser();ap.add_argument('run');ap.add_argument('case');ap.add_argument('--analysis',default='pn');a=ap.parse_args()
assert all(re.fullmatch(r'[A-Za-z0-9_]+',x) for x in [a.run,a.case,a.analysis])
j=ROOT/'research/runs/spectre_cmos_v14_full'/a.run/a.case
launch=json.loads((j/'launch.json').read_text());runner=(j/'runner.log').read_text(errors='replace')
remote=re.findall(r'(/home/jielu/TSMC180/MP/IP-PLL-GPT6/simulation/cmos_v14_full/[a-f0-9]{8})/'+a.case+r'\.raw',runner)[-1]
files=['pss.td.pss','pss.fd.pss',a.analysis+'Medge.0.sample.pnoise']
ssh=['C:/Windows/System32/OpenSSH/ssh.exe','-F',str(Path.home()/'.virtuoso-bridge/ssh_config_ipv6'),'-o','BatchMode=yes','thu-xia-v6']
def inventory():
    code="""import os,re,hashlib,json,subprocess
base=%r
case=%r
analysis=%r
files=%r
inputs=%r
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  while True:
   b=f.read(1024*1024)
   if not b:break
   h.update(b)
 return h.hexdigest()
log=open(base+'/spectre.out').read()
proof=[s for s in log.splitlines() if 'Total time required for pnoise analysis `'+analysis+\"'\" in s]
if not proof:
 print(json.dumps(dict(status='pending',analysis=analysis,reason='Requested pnoise analysis has not completed')))
 raise SystemExit(0)
assert 'The steady-state solution was achieved' in log
rows=[]
for name in files:
 p=base+'/'+case+'.raw/'+name
 st=os.stat(p)
 with open(p,'rb') as f:
  f.seek(max(0,st.st_size-128));tail=f.read()
 assert tail.rstrip().endswith('END'),name
 rows.append(dict(name=name,bytes=st.st_size,mtime=st.st_mtime,sha256=sha(p)))
live=[]
for row in subprocess.check_output(['/bin/ps','-C','spectre','-o','pid=']).splitlines():
 pid=int(row.strip())
 try:
  if os.stat('/proc/%%d'%%pid).st_uid!=os.getuid():continue
  args=open('/proc/%%d/cmdline'%%pid,'rb').read().split('\\0')
 except IOError:continue
 if base+'/'+case+'.scs' in args:live.append(pid)
print(json.dumps(dict(files=rows,inputs_sha256=dict((k,sha(base+'/'+k)) for k in inputs),completion_log_lines=proof,log=log,live_pids=live)))
"""%(remote,a.case,a.analysis,files,sorted(launch['inputs_sha256']))
    enc=base64.b64encode(code.encode()).decode()
    return json.loads(subprocess.check_output(ssh+['/usr/bin/python -c "import base64;exec(base64.b64decode(\''+enc+'\'))"'],timeout=90))
before=inventory()
if before.get('status')=='pending':print(json.dumps(before));raise SystemExit(0)
assert before['inputs_sha256']==launch['inputs_sha256']
dest=j/('completed_'+a.analysis+'_snapshot');assert not dest.exists();dest.mkdir()
archive=dest/'raw.tar.gz'
with archive.open('wb') as f:
    subprocess.run(ssh+['tar -czf - -C '+shlex.quote(remote+'/'+a.case+'.raw')+' '+' '.join(shlex.quote(x) for x in files)],stdout=f,check=True,timeout=300)
with tarfile.open(archive) as tf:
    assert sorted(tf.getnames())==sorted(files)
    for name in files:
        with tf.extractfile(name) as source,(dest/name).open('wb') as target:shutil.copyfileobj(source,target)
after=inventory();assert before['files']==after['files'] and after['inputs_sha256']==launch['inputs_sha256']
for row in before['files']:
    local=dest/row['name'];assert local.stat().st_size==row['bytes'] and hashlib.sha256(local.read_bytes()).hexdigest()==row['sha256']
(dest/'spectre_snapshot.out').write_text(after['log'])
out=dict(scope=__doc__,run=a.run,case=a.case,analysis=a.analysis,time=datetime.datetime.now().astimezone().isoformat(),
    remote_dir=remote,source_launch_sha256=hashlib.sha256((j/'launch.json').read_bytes()).hexdigest(),
    local_directory=dest.relative_to(ROOT).as_posix(),inputs_sha256=before['inputs_sha256'],files=before['files'],
    completion_log_lines=after['completion_log_lines'],live_pids_before=before['live_pids'],live_pids_after=after['live_pids'],
    completed_analysis_collected=True,whole_job_completion_claimed=False,full_pll_acceptance=False)
(dest/'snapshot.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
