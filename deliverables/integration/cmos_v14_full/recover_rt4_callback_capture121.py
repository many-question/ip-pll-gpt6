# Revision104: exclude the held OS lock from result-file hashing; simulation/data gates unchanged.
"""Recover the single callback full capture after client loss.

No launch API is called. Preserve the original run; require two stable terminal observations, input/output
hashes and a complete finite 120us real-DAC/count-window diagnostic trace. No simulation launch or cancellation.
"""
from pathlib import Path
import argparse, base64, datetime, hashlib, json, os, re, shlex, subprocess, sys, time
import numpy as np
from stream_real_transient import read_real_transient

H = Path(__file__).resolve().parent
ROOT = H.parents[3]
from rt4_recheckstep_transport105 import SSH


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

