"""Run one full-band diagnostic only after completed physical-register PSS probe.

No background wait or recurring schedule. No full PLL acceptance: fixed slow
controls, approximate reference loading and external-noise exclusions remain.
"""
from pathlib import Path
import hashlib,json,re,shlex,subprocess,sys
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
run='coreregisterprobe01';case='core_register_noise_probe_tt';j=R/run/case
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert json.loads((H/'results/core_settle_validation.json').read_text())['preflight_passed']
assert json.loads((H/'results/pss_reuse_validation.json').read_text())['passed']
r=json.loads((j/'result.json').read_text());assert r.get('local_outputs_sha256') and r['ok'] and r['remote_inputs_match']
assert 'spectre completes with 0 errors' in (j/'spectre.out').read_text()
subprocess.run([sys.executable,str(H/'analyze_closedloop_noise.py'),'corenoiseprobe01',run],check=True)
v=next(x for x in json.loads((H/'results/closedloop_noise_validation.json').read_text())['cases'] if x['run']==run)
assert v['periodic_passed'] and v['noise_consistent'],'Valid periodic trajectory and noise contributions required'
state=j/'periodic.state';assert state.is_file() and r['periodic_state_file']['collected']
assert sha(state)==r['local_outputs_sha256']['periodic.state']
remote=r['periodic_state_file']['remote'];assert remote.startswith('/home/jielu/TSMC180/MP/IP-PLL-GPT6/simulation/cmos_v14_full/')
ssh=['C:/Windows/System32/OpenSSH/ssh.exe','-F',str(Path.home()/'.virtuoso-bridge/ssh_config_ipv6'),'-o','BatchMode=yes','thu-xia-v6']
assert subprocess.check_output(ssh+['sha256sum '+shlex.quote(remote)],timeout=60).decode().split()[0]==sha(state)
available={p.name:p for p in (H.parents[1]/'blocks').glob('*/*') if p.suffix in ('.scs','.va')}
available.update({p.name:p for p in (H/'state_inputs').glob('*.ic')})
for name,digest in r['inputs_sha256'].items():
 if name==case+'.scs':continue
 assert name in available and sha(available[name])==digest,('Changed dependency; do not reuse PSS',name)
def normalized(s):
 s=re.sub(r'\b(?:writepss|writefinal|readic)="[^"]+"',lambda m:m[0].split('=')[0]+'="STATE"',s)
 return re.sub(r'^pn pnoise .*? pnoisemethod=','pn pnoise SWEEP pnoisemethod=',s,flags=re.M)
assert normalized((j/'inputs'/(case+'.scs')).read_text())==normalized((H/'tb/core_register_noise_band_tt.scs').read_text())
assert not (R/'coreregisterband01').exists(),'Never duplicate an existing full-band run'
print('Validated periodic core probe; launching full10kHz–492MHz diagnostic, not fullPLL signoff.',flush=True)
subprocess.run([sys.executable,str(H/'run_spectre.py'),'--run-id','coreregisterband01','--cases','core_register_noise_band_tt','--mode','ax','--threads','8','--preset-override','all','--timeout','28800','--pss-state',str(state)],cwd=ROOT,check=True)
subprocess.run([sys.executable,str(H/'analyze_closedloop_noise.py'),'corenoiseprobe01',run,'coreregisterband01'],check=True)
