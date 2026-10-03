"""One finite, gated follow-up to the already launched Gear2 PSS experiment.

Wait for its completed manifest; only a valid periodic/noise probe can launch
one full-band core experiment. Never retry failures or accept a failed state.
This is not a recurring task and does not establish full-PLL jitter.
"""
from pathlib import Path
import datetime,hashlib,json,re,shlex,subprocess,sys,time
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
run='coregear01';case='core_register_noise_gear_tt';j=R/run/case
target_run='coregearband01';target_case='core_register_noise_gear_band_tt'
journal=ROOT/'research/gear_noise_pipeline.json'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def record(state,**extra):
    journal.write_text(json.dumps(dict(updated=datetime.datetime.now().astimezone().isoformat(),state=state,source_run=run,destination_run=target_run,full_pll_acceptance=False,**extra),indent=2)+'\n')
try:
    assert j.exists() and not (R/target_run).exists()
    record('waiting_for_owned_probe')
    deadline=time.monotonic()+30000
    while True:
        rp=j/'result.json'
        if rp.exists():
            r=json.loads(rp.read_text())
            if r.get('local_outputs_sha256'):break
        if time.monotonic()>deadline:raise TimeoutError('No completed source manifest; no follow-up launched')
        time.sleep(10)
    assert r['ok'] and r['remote_inputs_match'],'Probe failed; no band launched'
    assert 'spectre completes with 0 errors' in (j/'spectre.out').read_text()
    assert json.loads((H/'results/pss_reuse_validation.json').read_text())['passed']
    subprocess.run([sys.executable,str(H/'analyze_closedloop_noise.py'),'corenoiseprobe01','coreregisterprobe01',run],check=True)
    v=next(x for x in json.loads((H/'results/closedloop_noise_validation.json').read_text())['cases'] if x['run']==run)
    assert v['periodic_passed'] and v['noise_consistent'],'Periodic/noise probe validation failed'
    state=j/'periodic.state';assert r['periodic_state_file']['collected'] and sha(state)==r['local_outputs_sha256']['periodic.state']
    remote=r['periodic_state_file']['remote'];assert remote.startswith('/home/jielu/TSMC180/MP/IP-PLL-GPT6/simulation/cmos_v14_full/')
    ssh=['C:/Windows/System32/OpenSSH/ssh.exe','-F',str(Path.home()/'.virtuoso-bridge/ssh_config_ipv6'),'-o','BatchMode=yes','thu-xia-v6']
    assert subprocess.check_output(ssh+['sha256sum '+shlex.quote(remote)],timeout=60).decode().split()[0]==sha(state)
    available={p.name:p for p in (H.parents[1]/'blocks').glob('*/*') if p.suffix in ('.scs','.va')}
    available.update({p.name:p for p in (H/'state_inputs').glob('*.ic')})
    for name,digest in r['inputs_sha256'].items():
        if name!=case+'.scs':assert name in available and sha(available[name])==digest,('Changed dependency',name)
    source=(j/'inputs'/(case+'.scs')).read_text()
    s=re.sub(r'readic="[^"]+"','readic="core_register_settled_tt.ic"',source)
    s=re.sub(r'writefinal="[^"]+"','writefinal="__FINAL_STATE__"',s)
    s=re.sub(r'writepss="[^"]+"','writepss="__PERIODIC_STATE__"',s)
    assert 'values=[10k 100k 1M 10M 100M 491.99M]' in s
    s=s.replace('values=[10k 100k 1M 10M 100M 491.99M]','start=10k stop=492M dec=20')
    (H/'tb'/(target_case+'.scs')).write_text(s)
    record('band_running',probe_validation=v,periodic_state_sha256=sha(state))
    subprocess.run([sys.executable,str(H/'run_spectre.py'),'--run-id',target_run,'--cases',target_case,'--mode','ax','--threads','8','--preset-override','all','--timeout','28800','--pss-state',str(state)],cwd=ROOT,check=True)
    subprocess.run([sys.executable,str(H/'analyze_closedloop_noise.py'),'corenoiseprobe01','coreregisterprobe01',run,target_run],check=True)
    record('band_completed_requires_review',validation='share/deliverables/integration/cmos_v14_full/results/closedloop_noise_validation.json',pending=['noise-on groups','maxacfreq/sideband/step and edge-position convergence','harmonic-neighborhood integration','full-DUT boundary'])
except Exception as exc:
    record('stopped_no_automatic_retry',error=str(exc));raise
