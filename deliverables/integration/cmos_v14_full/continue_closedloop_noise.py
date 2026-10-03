"""One-shot continuation of the current noise experiment, not a recurring job.

Only after a zero-error, hash-checked periodic/noise probe passes, reuse its
checked PSS solution for the full requested band. Never declare PLL acceptance.
"""
from pathlib import Path
import argparse,datetime,hashlib,json,subprocess,sys,time,re,shlex
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
p=argparse.ArgumentParser();p.add_argument('--wait-seconds',type=int,default=0);a=p.parse_args()
job=R/'corenoiseprobe01/core_noise_probe_tt';deadline=time.monotonic()+a.wait_seconds
assert json.loads((H/'results/pss_reuse_validation.json').read_text())['passed']
note=job/'noise_followup.json'
def record(status,**kw):
 d=dict(time=datetime.datetime.now().astimezone().isoformat(),status=status,scope=__doc__,**kw);note.write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d),flush=True)
record('waiting_for_probe_completion')
while True:
 if (job/'result.json').exists():
  rec=json.loads((job/'result.json').read_text())
  if rec.get('local_outputs_sha256'):break
 if time.monotonic()>=deadline:record('probe_not_complete');raise SystemExit(0)
 time.sleep(20)
if not rec['ok'] or 'spectre completes with 0 errors' not in (job/'spectre.out').read_text(errors='replace'):
 record('probe_failed_no_band_launched');raise SystemExit(0)
assert rec['remote_inputs_match']
preflight=H/'results/core_preflight_validation.json'
if not preflight.exists() or not any(x.get('ready_for_noise') and x.get('run')=='corenoiseprobe01' for x in json.loads(preflight.read_text())['cases']):
 record('operating_point_not_validated_no_band_launched');raise SystemExit(0)
subprocess.run([sys.executable,str(H/'analyze_closedloop_noise.py'),'corenoiseprobe01'],check=True)
validation=json.loads((H/'results/closedloop_noise_validation.json').read_text())['cases'][0]
if not (validation.get('periodic_passed') and validation.get('noise_consistent')):
 record('probe_validation_failed_no_band_launched',validation=validation);raise SystemExit(0)
state=job/'periodic.state';assert state.is_file() and rec['periodic_state_file']['collected']
ssh=['C:/Windows/System32/OpenSSH/ssh.exe','-F',str(Path.home()/'.virtuoso-bridge/ssh_config_ipv6'),'-o','BatchMode=yes','thu-xia-v6']
remote=rec['periodic_state_file']['remote'];assert remote.startswith('/home/jielu/TSMC180/MP/IP-PLL-GPT6/simulation/cmos_v14_full/')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert subprocess.check_output(ssh+['sha256sum '+shlex.quote(remote)],timeout=60).decode().split()[0]==sha(state)
folders=['behavioral_va','transistor_v1','transistor_v2','transistor_v3','vco_v4','interface_v5','closure_v6','accuracy_v7','output_v8','output_v9','noise_v10','jitter_v11','cmos_v12','cmos_v13','cmos_v14','cmos_v14_full']
available={p.name:p for folder in folders if (H.parents[1]/'blocks'/folder).is_dir() for p in (H.parents[1]/'blocks'/folder).iterdir() if p.suffix in ['.scs','.va']}
available.update({p.name:p for p in (H/'state_inputs').glob('*.ic')})
for name,digest in rec['inputs_sha256'].items():
 if name==job.name+'.scs':continue
 assert name in available and sha(available[name])==digest,('Current dependency changed; do not reuse PSS',name)
source=(job/'inputs'/(job.name+'.scs')).read_text();band=(H/'tb/core_noise_band_tt.scs').read_text()
def normalize(s):
 s=re.sub(r'\b(?:writepss|writefinal|readic)="[^"]+"',lambda m:m[0].split('=')[0]+'="STATE"',s)
 return re.sub(r'^pn pnoise .*? pnoisemethod=','pn pnoise SWEEP pnoisemethod=',s,flags=re.M)
assert normalize(source)==normalize(band),'Only the noise frequency grid may change'
record('launching_full_band',probe_periodic_state_sha256=sha(state),threads=1,band_hz=[10000,492000000],full_pll_acceptance=False)
assert not (R/'corenoiseband01').exists(),'Do not duplicate the full-band job'
cmd=[sys.executable,str(H/'run_spectre.py'),'--run-id','corenoiseband01','--cases','core_noise_band_tt','--mode','ax','--threads','1','--preset-override','all','--timeout','14400','--pss-state',str(state)]
code=subprocess.run(cmd,cwd=ROOT).returncode
if code==0:
 subprocess.run([sys.executable,str(H/'analyze_closedloop_noise.py'),'corenoiseprobe01','corenoiseband01'],check=True)
record('full_band_finished' if code==0 else 'full_band_failed',returncode=code,full_pll_acceptance=False)
