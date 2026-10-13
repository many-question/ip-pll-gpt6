# Revision104: exclude the held OS lock from result-file hashing; simulation/data gates unchanged.
"""Recover the single allowlisted surviving RT4 recheck capture after client loss.

No launch API is called. Preserve the original run; require two stable terminal observations, input/output
hashes and a complete finite 120us trace. No simulation launch or cancellation.
"""
from pathlib import Path
import argparse, base64, datetime, hashlib, json, os, re, shlex, subprocess, sys, time
import numpy as np
from stream_real_transient import read_real_transient

H = Path(__file__).resolve().parent
ROOT = H.parents[3]
SPECS = {
    'recheck': ('rt4recheckk41ssd01', 'rt4r48_recheck_k41_tt', 'aafa4165',
        'rt4_recheck_pipeline.json', 'rt4_recheck_protocol.json'),
}


def configure(target):
    global RUN, CASE, RD, WORK, STATE, PROTOCOL
    RUN, CASE, folder, state, protocol = SPECS[target]
    RD = '/server_local_ssd/jielu/IP-PLL-GPT6/simulation/cmos_v14_full/' + folder
    WORK = ROOT/'research/runs/spectre_cmos_v14_full'/RUN/CASE
    STATE = ROOT/'research'/state
    PROTOCOL = H/'results'/protocol


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
log=open(rd+'/spectre.out','rb').read() if os.path.isfile(rd+'/spectre.out') else ''
foot=re.findall(r'spectre completes with (\d+) errors?',log[-6000:])
ep=rd+'/.launch_claim/exit_code'
p=rd+'/'+%r+'.raw/tran.tran.tran'
print(json.dumps(dict(live=live,terminal_errors=int(foot[-1]) if foot else None,exit_code=open(ep).read().strip() if os.path.exists(ep) else None,log_sha256=hashlib.sha256(log).hexdigest(),raw_bytes=os.path.getsize(p) if os.path.isfile(p) else 0,raw_mtime=os.path.getmtime(p) if os.path.isfile(p) else None)))
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
if os.path.isfile(rd+'/console.log'):outputs['console.log']=hashed(rd+'/console.log')
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
    (WORK/'detached_recovery_before102.json').write_text(json.dumps(before, indent=2)+'\n')
    for name, item in before['outputs'].items():
        dest = WORK/name
        assert dest.resolve().is_relative_to(WORK.resolve())
        if dest.exists() and sha(dest) == item['sha256']:
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        part = dest.with_name(dest.name+'.recovery102.part')
        with part.open('wb') as f:
            subprocess.run(SSH+['cat '+shlex.quote(item['path'])], stdout=f, check=True, timeout=3600)
        assert part.stat().st_size == item['bytes'] and sha(part) == item['sha256']
        if dest.exists():
            prior = dest.with_name(dest.name+'.client_partial102')
            assert not prior.exists()
            dest.rename(prior)
        part.replace(dest)
    after = inventory(launch)
    assert after == before, 'Remote completed files changed during transfer'
    end = inspect()
    assert ready(end, terminal), 'Terminal status or raw files changed during recovery'
    log = (WORK/'spectre.out').read_text()
    clean = terminal['terminal_errors'] == 0 and terminal['exit_code'] == '0'
    clean = clean and 'final.ic' in before['outputs']
    raw = WORK/(CASE+'.raw/tran.tran.tran')
    with raw.open('rb') as f:
        f.seek(max(0,raw.stat().st_size-1024))
        assert f.read().rstrip().endswith(b'END'), 'Missing complete PSF END marker'
    data, audit = read_real_transient(raw)
    stop_ok = data['time'][0] == 0 and abs(data['time'][-1]-120e-6) < 1e-15 and len(data['time']) == 60001
    assert audit['duplicate_records'] == 0
    np.savez_compressed(WORK/'waveforms.npz', **data)
    ok = bool(clean and stop_ok)
    rec = dict(case=CASE, time=datetime.datetime.now().astimezone().isoformat(), ok=ok,
        errors=[] if ok else ['Original simulation terminated without a complete clean target trace.'],
        recovery_note='Original local workers disappeared; cause unconfirmed. Existing remote run collected only after actual process exit and two stable terminal observations; no simulation restart.',
        metadata=dict(remote_directory=RD, terminal_observation=terminal,
            exit_code_missing=terminal['exit_code'] is None, collection_repaired=True,
            parser='stream_real_transient.py', parser_sha256=sha(H/'stream_real_transient.py'), parser_audit=audit),
        **{k:launch.get(k) for k in ['initial_states','native_state','periodic_state','numerical_overrides','transient_noise_overrides','transient_solver_overrides','inputs_sha256']},
        remote_inputs_sha256=before['inputs'], remote_inputs_match=True,
        remote_initial_states_sha256=before['initial_states'],
        remote_outputs_sha256={k:v['sha256'] for k,v in before['outputs'].items()},
        hashes_stable_during_transfer=True, integrity_valid=True,
        state_file=dict(collected='final.ic' in before['outputs'],remote=before['outputs'].get('final.ic',{}).get('path')),
        signals={k:len(v) for k,v in data.items()}, final_values={k:float(v[-1]) for k,v in data.items()},
        local_outputs_sha256={p.name:sha(p) for p in WORK.iterdir() if p.is_file() and p.name not in {'result.json', '.heartbeat_collection103.lock'}})
    assert not (WORK/'result.json').exists()
    tmp = WORK/'result.json.recovery102.tmp'
    tmp.write_text(json.dumps(rec, indent=2)+'\n');tmp.replace(WORK/'result.json')
    return ok


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--target', required=True, choices=sorted(SPECS))
    parser.add_argument('--check', action='store_true')
    args=parser.parse_args();configure(args.target)
    launch = json.loads((WORK/'launch.json').read_text())
    protocol = json.loads(PROTOCOL.read_text())
    assert launch['case'] == CASE and launch['launch_policy']['transport_attempts'] == 1
    assert launch['launch_policy']['implementation_sha256'] == sha(H/'single_launch_transport.py')
    assert any(c['run']==RUN and c['case']==CASE for c in protocol['cases'])
    assert RD+'/' in (WORK/'runner.log').read_text()
    assert all(sha(WORK/'inputs'/n) == v for n,v in launch['inputs_sha256'].items())
    for path, item in launch.get('initial_states',{}).items():
        assert path.startswith('/server_local_ssd/jielu/IP-PLL-GPT6/')
        assert sha(WORK/'inputs'/item['source']) == item['sha256']
    states = remote("import json,hashlib\nprint(json.dumps({p:hashlib.sha256(open(p,'rb').read()).hexdigest() for p in %r}))" % list(launch.get('initial_states',{})))
    assert states == {k:v['sha256'] for k,v in launch.get('initial_states',{}).items()}
    state = json.loads(STATE.read_text())
    assert state['protocol_sha256'] == sha(PROTOCOL)
    if args.check:
        current=inspect();print(json.dumps(dict(mode='read_only_check',target=args.target,observation=current,collection_ready=False),indent=2));return
    assert state['state']=='capture_running' and not (WORK/'result.json').exists()
    proof=json.loads((ROOT/'research/client_loss102_before.json').read_text(encoding='utf-8'))
    import psutil
    assert all(not psutil.pid_exists(w['pid']) for w in proof['workers']), 'Old worker PID must remain absent; review PID reuse manually'
    expected={'recheck':'9b15d24ec8633b922975ba4cc7aca66e0ecc7509a970e49184c73b6dd586b359'}
    assert sha(PROTOCOL)==expected[args.target]
    with (WORK/'.detached_recovery102_claim').open('x') as f:f.write(str(os.getpid())+'\n')
    if 'failure' in state:state['original_pipeline_failure']=state.pop('failure')
    for worker in state.get('workers',[]):
        worker.update(running=False,exit_cause='local process absent; unconfirmed cause')
    state['detached_recovery'] = dict(no_new_simulations=True, script=str(Path(__file__).relative_to(ROOT)),
        started=datetime.datetime.now().astimezone().isoformat(), original_client_returncode=state.get('noise_returncode'),
        owner_pid=os.getpid(), owner_create_time=psutil.Process().create_time(), owner_cmdline=psutil.Process().cmdline(),
        incident='research/client_loss102_before.json')
    def write(status, **extra):
        state.update(state=status, updated=datetime.datetime.now().astimezone().isoformat(), **extra)
        tmp=STATE.with_suffix('.recovery102.tmp');tmp.write_text(json.dumps(state,indent=2)+'\n');tmp.replace(STATE)
    deadline=time.monotonic()+48*3600;previous=None;errors=0
    try:
        while time.monotonic()<deadline:
            try:
                current=inspect();errors=0
                if 'observation_error' in state:
                    state.setdefault('recovered_observation_errors',[]).append(state.pop('observation_error'))
            except (subprocess.SubprocessError,json.JSONDecodeError) as e:
                errors+=1;write('read_retrying_no_cancellation', observation_error=repr(e), consecutive_errors=errors)
                previous=None;time.sleep(min(300,60*errors));continue
            write('waiting_existing_remote', observation=current, consecutive_errors=0)
            if ready(current, previous):
                write('collecting_existing_remote', observation=current)
                ok=collect(launch,current)
                write('completed_pending_remote_review' if ok else 'recovered_failed_needs_review',result_sha256=sha(WORK/'result.json'));return
            if not current['live'] and current['terminal_errors'] is None and previous and not previous['live']:
                raise RuntimeError('Remote process absent without a Spectre terminal footer; no completion inferred')
            previous=current;time.sleep(60)
        raise TimeoutError('Bounded recovery monitor expired; remote run untouched')
    except Exception as e:
        write('needs_review', recovery_failure=repr(e));raise


if __name__=='__main__':main()
