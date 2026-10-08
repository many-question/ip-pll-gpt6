"""Observe and recover the existing SSD RT4 half-ps seed29 run; never launch Spectre.

The lost SSH client's return code is not the simulator's terminal status.
This one-run recovery keeps the launch, protocol and any partial local files.
"""
from pathlib import Path
import argparse, base64, datetime, hashlib, json, os, re, shlex, subprocess, sys, time
import numpy as np
from stream_real_transient import read_real_transient

H = Path(__file__).resolve().parent
ROOT = H.parents[3]
RUN = 'pllrt4halfseed29onssd01'
CASE = 'full_pll_rt4_half_seed29_on_tt'
RD = '/server_local_ssd/jielu/IP-PLL-GPT6/simulation/cmos_v14_full/58110ce2'
WORK = ROOT/'research/runs/spectre_cmos_v14_full'/RUN/CASE
STATE = ROOT/'research/rt4_half_seed29_noise_pipeline.json'
PROTOCOL = H/'results/full_pll_rt4_half_seed29_pair_protocol.json'
SSH = ['C:/Windows/System32/OpenSSH/ssh.exe', '-F', str(Path.home()/'.virtuoso-bridge/ssh_config_ipv6'), '-o', 'BatchMode=yes', 'thu-xia-v6']


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(4*1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def remote(code, timeout=60):
    encoded = base64.b64encode(code.encode()).decode()
    command = '/usr/bin/python -c "import base64;exec(base64.b64decode(\''+encoded+'\'))"'
    return json.loads(subprocess.check_output(SSH+[command], timeout=timeout))


def inspect():
    return remote("""import os,json,re,hashlib
rd=%r
net=rd+'/'+%r+'.scs'
live=[]
for n in os.listdir('/proc'):
 if not n.isdigit():continue
 try:
  if os.stat('/proc/'+n).st_uid!=os.getuid():continue
  args=open('/proc/'+n+'/cmdline','rb').read().split(chr(0))
  exe=os.readlink('/proc/'+n+'/exe')
  if net in args and os.path.basename(exe)=='spectre':live.append(int(n))
 except (IOError,OSError):pass
log=open(rd+'/spectre.out','rb').read()
foot=re.findall(r'spectre completes with (\d+) errors?',log[-6000:])
ep=rd+'/.launch_claim/exit_code'
p=rd+'/'+%r+'.raw/tran.tran.tran'
print(json.dumps(dict(live=live,terminal_errors=int(foot[-1]) if foot else None,exit_code=open(ep).read().strip() if os.path.exists(ep) else None,log_sha256=hashlib.sha256(log).hexdigest(),raw_bytes=os.path.getsize(p),raw_mtime=os.path.getmtime(p))))
""" % (RD, CASE, CASE))


def ready(current, previous):
    return (not current['live'] and current['terminal_errors'] is not None
            and previous is not None and not previous['live']
            and all(current[k] == previous[k] for k in
                    ['terminal_errors', 'exit_code', 'log_sha256', 'raw_bytes', 'raw_mtime']))


def inventory(launch):
    tb = (WORK/'inputs'/(CASE+'.scs')).read_text()
    final = re.search(r'writefinal="([^"]+)"', tb)[1]
    assert final.startswith('/server_local_ssd/jielu/IP-PLL-GPT6/')
    return remote("""import os,json,hashlib
rd=%r
raw=rd+'/'+%r+'.raw'
def hashed(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  while True:
   b=f.read(4194304)
   if not b:break
   h.update(b)
 return dict(path=p,bytes=os.path.getsize(p),sha256=h.hexdigest())
outputs={}
for base,dirs,files in os.walk(raw):
 for name in files:
  p=os.path.join(base,name);outputs[os.path.relpath(p,rd)]=hashed(p)
outputs['spectre.out']=hashed(rd+'/spectre.out')
final=%r
if os.path.isfile(final):outputs['final.ic']=hashed(final)
print(json.dumps(dict(inputs={n:hashed(rd+'/'+n)['sha256'] for n in %r},
 initial_states={n:hashed(n)['sha256'] for n in %r},outputs=outputs)))
""" % (RD, CASE, final, list(launch['inputs_sha256']), list(launch.get('initial_states',{}))), timeout=300)


def collect(launch, terminal):
    before = inventory(launch)
    assert before['inputs'] == launch['inputs_sha256']
    assert before['initial_states'] == {k:v['sha256'] for k,v in launch.get('initial_states',{}).items()}
    assert all(sha(WORK/'inputs'/n) == v for n,v in before['inputs'].items())
    (WORK/'detached_recovery_before82.json').write_text(json.dumps(before, indent=2)+'\n')
    for name, item in before['outputs'].items():
        dest = WORK/name
        assert dest.resolve().is_relative_to(WORK.resolve())
        if dest.exists() and sha(dest) == item['sha256']:
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        part = dest.with_name(dest.name+'.recovery82.part')
        with part.open('wb') as f:
            subprocess.run(SSH+['cat '+shlex.quote(item['path'])], stdout=f, check=True, timeout=3600)
        assert part.stat().st_size == item['bytes'] and sha(part) == item['sha256']
        if dest.exists():
            prior = dest.with_name(dest.name+'.client_partial82')
            assert not prior.exists()
            dest.rename(prior)
        part.replace(dest)
    after = inventory(launch)
    assert after == before, 'Remote completed files changed during transfer'
    end = inspect()
    assert ready(end, terminal), 'Terminal status or raw files changed during recovery'
    log = (WORK/'spectre.out').read_text()
    clean = terminal['terminal_errors'] == 0 and terminal['exit_code'] in (None, '0')
    clean = clean and 'final.ic' in before['outputs']
    data, audit = read_real_transient(WORK/(CASE+'.raw/tran.tran.tran'))
    stop_ok = data['time'][0] == 0 and abs(data['time'][-1]-2.2e-6) < 1e-15
    assert audit['duplicate_records'] == 0
    np.savez_compressed(WORK/'waveforms.npz', **data)
    ok = bool(clean and stop_ok)
    rec = dict(case=CASE, time=datetime.datetime.now().astimezone().isoformat(), ok=ok,
        errors=[] if ok else ['Original simulation terminated without a complete clean target trace.'],
        recovery_note='Original SSH client disconnected. Existing remote run collected only after actual process exit and two stable terminal observations; no simulation restart.',
        metadata=dict(remote_directory=RD, terminal_observation=terminal,
            exit_code_missing=terminal['exit_code'] is None, collection_repaired=True,
            parser='stream_real_transient.py', parser_sha256=sha(H/'stream_real_transient.py'), parser_audit=audit),
        **{k:launch.get(k) for k in ['initial_states','native_state','periodic_state','numerical_overrides','transient_noise_overrides','transient_solver_overrides','inputs_sha256']},
        remote_inputs_sha256=before['inputs'], remote_inputs_match=True,
        remote_initial_states_sha256=before['initial_states'],
        remote_outputs_sha256={k:v['sha256'] for k,v in before['outputs'].items()},
        hashes_stable_during_transfer=True, integrity_valid=True,
        state_file=dict(collected='final.ic' in before['outputs']),
        signals={k:len(v) for k,v in data.items()}, final_values={k:float(v[-1]) for k,v in data.items()},
        local_outputs_sha256={p.name:sha(p) for p in WORK.iterdir() if p.is_file() and p.name!='result.json'})
    assert not (WORK/'result.json').exists()
    tmp = WORK/'result.json.recovery82.tmp'
    tmp.write_text(json.dumps(rec, indent=2)+'\n');tmp.replace(WORK/'result.json')
    return ok


def main():
    parser = argparse.ArgumentParser();parser.add_argument('--check', action='store_true');args=parser.parse_args()
    launch = json.loads((WORK/'launch.json').read_text())
    assert launch['case'] == CASE and launch['launch_policy']['transport_attempts'] == 1
    assert all(sha(WORK/'inputs'/n) == v for n,v in launch['inputs_sha256'].items())
    for path, item in launch.get('initial_states',{}).items():
        assert path.startswith('/server_local_ssd/jielu/IP-PLL-GPT6/')
        assert sha(WORK/'inputs'/item['source']) == item['sha256']
    states = remote("import json,hashlib\nprint(json.dumps({p:hashlib.sha256(open(p,'rb').read()).hexdigest() for p in %r}))" % list(launch.get('initial_states',{})))
    assert states == {k:v['sha256'] for k,v in launch.get('initial_states',{}).items()}
    state = json.loads(STATE.read_text())
    assert state['protocol_sha256'] == sha(PROTOCOL)
    if args.check:
        current=inspect();print(json.dumps(dict(mode='read_only_check', observation=current, collection_ready=False),indent=2));return
    assert not (WORK/'result.json').exists()
    with (WORK/'.detached_recovery82_claim').open('x') as f:f.write(str(os.getpid())+'\n')
    state['detached_recovery'] = dict(no_new_simulations=True, script=str(Path(__file__).relative_to(ROOT)),
        started=datetime.datetime.now().astimezone().isoformat(), original_client_returncode=state.get('noise_returncode'))
    def write(status, **extra):
        state.update(state=status, updated=datetime.datetime.now().astimezone().isoformat(), **extra)
        tmp=STATE.with_suffix('.recovery82.tmp');tmp.write_text(json.dumps(state,indent=2)+'\n');tmp.replace(STATE)
    deadline=time.monotonic()+48*3600;previous=None;errors=0
    try:
        while time.monotonic()<deadline:
            try:current=inspect();errors=0
            except (subprocess.SubprocessError,json.JSONDecodeError) as e:
                errors+=1;write('waiting_existing_remote', observation_error=repr(e), consecutive_errors=errors)
                if errors>=3:raise
                previous=None;time.sleep(60);continue
            write('waiting_existing_remote', observation=current)
            if ready(current, previous):
                write('collecting_existing_remote', observation=current)
                ok=collect(launch,current)
                q=subprocess.run([sys.executable,str(H/'analyze_full_pll_direct_noise_pair.py'),'--protocol',PROTOCOL.name],cwd=ROOT)
                assert ok and q.returncode==0, 'Recovered simulation or paired analysis requires review'
                validation=H/'results/full_pll_rt4_half_seed29_pair_validation.json'
                write('completed_pending_review', validation_sha256=sha(validation));return
            if not current['live'] and current['terminal_errors'] is None and previous and not previous['live']:
                raise RuntimeError('Remote process absent without a Spectre terminal footer; no completion inferred')
            previous=current;time.sleep(60)
        raise TimeoutError('Bounded recovery monitor expired; remote run untouched')
    except Exception as e:
        write('needs_review', recovery_failure=repr(e));raise


if __name__=='__main__':main()
