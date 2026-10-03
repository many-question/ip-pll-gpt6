"""Recover an already finished Spectre job after the local client disappeared.

No simulator is launched. Frozen local inputs and remote raw hashes govern recovery.
"""
from pathlib import Path,PurePosixPath
import argparse,datetime,hashlib,json,re,shlex,subprocess,tarfile
import numpy as np
from virtuoso_bridge.spectre.parsers import parse_psf_ascii_directory
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
REMOTE='/home/jielu/TSMC180/MP/IP-PLL-GPT6/simulation/cmos_v14_full'
p=argparse.ArgumentParser();p.add_argument('run');p.add_argument('case');a=p.parse_args()
assert a.run.isalnum() and a.case.replace('_','').isalnum()
w=ROOT/'research/runs/spectre_cmos_v14_full'/a.run/a.case
assert not (w/'result.json').exists(),'Use existing result manifest; do not overwrite it.'
cmd=re.search(r'^\[Command\] (.+)$',(w/'runner.log').read_text(),re.M)[1]
net=next(x for x in shlex.split(cmd) if x.endswith('.scs'));remote=str(PurePosixPath(net).parent)
assert re.fullmatch(re.escape(REMOTE)+r'/[a-f0-9]{8}',remote)
ssh=['C:/Windows/System32/OpenSSH/ssh.exe','-F',str(Path.home()/'.virtuoso-bridge/ssh_config_ipv6'),'-o','BatchMode=yes','thu-xia-v6']
def read(command,timeout=60):return subprocess.check_output(ssh+[command],timeout=timeout)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
log=read('cat '+shlex.quote(remote+'/spectre.out'))
assert b'spectre completes with 0 errors' in log[-6000:]
files=sorted((w/'inputs').iterdir());local={x.name:sha(x) for x in files if x.is_file()}
proof=read('cd '+shlex.quote(remote)+' && sha256sum '+' '.join(shlex.quote(x) for x in local)).decode()
rh={x.split()[1]:x.split()[0] for x in proof.splitlines()};assert rh==local,'Remote inputs differ'
tb=(w/'inputs'/(a.case+'.scs')).read_text()
launch=json.loads((w/'launch.json').read_text()) if (w/'launch.json').exists() else {}
if launch:assert launch['inputs_sha256']==local
if 'recover=' in tb or 'readic=' in tb:
 assert launch,'Seeded/native jobs need a persisted launch.json; recover explicit provenance before proceeding.'
for remote_state,info in launch.get('initial_states',{}).items():
 assert remote_state.startswith(REMOTE+'/') and info['sha256']==sha(w/'inputs'/info['source'])
 assert read('sha256sum '+shlex.quote(remote_state)).decode().split()[0]==info['sha256']
native=launch.get('native_state')
if native:
 assert native['remote'].startswith(REMOTE+'/') and native['sha256']==sha(ROOT/native['local'])
 assert read('sha256sum '+shlex.quote(native['remote'])).decode().split()[0]==native['sha256']
rawfiles=[a.case+'.raw/tran.tran.tran','spectre.out']
proof=read('cd '+shlex.quote(remote)+' && sha256sum '+' '.join(shlex.quote(x) for x in rawfiles)).decode()
rawhash={x.split()[1]:x.split()[0] for x in proof.splitlines()}
archive=w/'recovered_raw.tar.gz';assert not archive.exists()
with archive.open('wb') as f:
 subprocess.run(ssh+['tar -czf - -C '+shlex.quote(remote)+' '+shlex.quote(a.case+'.raw')+' spectre.out'],stdout=f,check=True,timeout=300)
with tarfile.open(archive) as tf:tf.extractall(w,filter='data')
assert all(sha(w/k)==v for k,v in rawhash.items()),'Raw transport hash mismatch'
final=re.search(r'writefinal="([^"]+)"',tb)[1];assert final.startswith(REMOTE+'/')
blob=read('cat '+shlex.quote(final));fh=read('sha256sum '+shlex.quote(final)).decode().split()[0]
assert hashlib.sha256(blob).hexdigest()==fh;(w/'final.ic').write_bytes(blob)
data=parse_psf_ascii_directory(w/(a.case+'.raw'))
data={k:np.atleast_1d(v) for k,v in data.items() if k!='units' and np.asarray(v).dtype.kind in 'biufc'}
np.savez_compressed(w/'waveforms.npz',**data)
rec=dict(case=a.case,time=datetime.datetime.now().astimezone().isoformat(),ok=True,errors=[],
 recovery_note='Original local runner/finalizer processes were absent. Completed remote simulation recovered without rerunning; simulator zero-error status, frozen inputs and raw waveform hashes verified.',
 metadata=dict(spectre_command=cmd),initial_states=launch.get('initial_states',{}),native_state=native,numerical_overrides=launch.get('numerical_overrides',{}),
 inputs_sha256=local,remote_inputs_sha256=rh,remote_inputs_match=True,
 remote_outputs_sha256=rawhash,state_file=dict(remote=final,collected=True,sha256=fh,remote_hash_match=True),
 signals={k:len(v) for k,v in data.items()},final_values={k:float(v[-1]) for k,v in data.items() if len(v) and np.isrealobj(v) and np.isfinite(v[-1])})
rec['local_outputs_sha256']={x.name:sha(x) for x in w.iterdir() if x.is_file() and x.name not in ['result.json','finalization.json']}
(w/'result.json').write_text(json.dumps(rec,indent=2)+'\n')
(w.parent/'index.json').write_text(json.dumps([rec],indent=2)+'\n')
print('Recovered',a.run,a.case,len(data),'signals; final time',data['time'][-1])
