"""One heartbeat observation/collection of the existing RT4 run; never dispatch.

No resident worker. A Windows byte lock serializes invocations and is released
by the OS on exit/reboot. The old permanent recovery claim remains evidence.
"""
from contextlib import contextmanager
import datetime
import json
import msvcrt
import os
import time
import psutil
import recover_rt4_recheck_detached102 as recovery


def now():
    return datetime.datetime.now().astimezone().isoformat()


@contextmanager
def exclusive(path):
    with path.open('a+b') as lock:
        if path.stat().st_size == 0:
            lock.write(b'0'); lock.flush()
        lock.seek(0)
        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        try:
            yield
        finally:
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)


def preflight():
    r = recovery
    assert r.sha(r.H/'recover_rt4_recheck_detached102.py') == 'e867994c8a2f7fb1bce974fdc8910ee2e9469119bfbccf0f17681493191ba945'
    assert r.sha(r.PROTOCOL) == '9b15d24ec8633b922975ba4cc7aca66e0ecc7509a970e49184c73b6dd586b359'
    launch = json.loads((r.WORK/'launch.json').read_text())
    assert launch['case'] == r.CASE and launch['launch_policy']['transport_attempts'] == 1
    assert launch['launch_policy']['implementation_sha256'] == r.sha(r.H/'single_launch_transport.py')
    assert r.RD+'/' in (r.WORK/'runner.log').read_text()
    assert all(r.sha(r.WORK/'inputs'/n) == v for n,v in launch['inputs_sha256'].items())
    assert not launch.get('initial_states'), 'This entry is only for the existing cold capture'
    state = json.loads(r.STATE.read_text())
    assert state['protocol_sha256'] == r.sha(r.PROTOCOL)
    previous = state['detached_recovery']
    # Conservative PID gate: even reuse requires explicit inspection.
    for pid in {state['owner_pid'], previous['owner_pid'], *(w['pid'] for w in state['workers'])}:
        assert not psutil.pid_exists(pid), 'An old PID is present; inspect identity before takeover'
    assert (r.WORK/'.detached_recovery102_claim').read_text().strip() == str(previous['owner_pid'])
    return launch, state


def main():
    r = recovery
    r.configure('recheck')
    with exclusive(r.WORK/'.heartbeat_collection103.lock'):
        launch, state = preflight()
        state['detached_recovery'].update(retired=True, running=False, superseded_by='heartbeat_collection')
        state['heartbeat_collection'] = dict(script='share/deliverables/integration/cmos_v14_full/poll_rt4_recheck103.py',
            mode='bounded_heartbeat', resident_worker=False, last_invocation_pid=os.getpid(), started=now(),
            no_new_simulations=True, old_claim_preserved=True)

        def write(status, **extra):
            state.update(state=status, updated=now(), **extra)
            tmp = r.STATE.with_suffix('.heartbeat103.tmp')
            tmp.write_text(json.dumps(state, indent=2)+'\n'); tmp.replace(r.STATE)

        try:
            if (r.WORK/'result.json').exists():
                write('collected_pending_independent_review', result_sha256=r.sha(r.WORK/'result.json'))
                print(json.dumps(dict(state=state['state'], no_new_simulations=True))); return
            first = r.inspect()
            if first['live']:
                write('waiting_existing_remote_heartbeat', observation=first)
                print(json.dumps(dict(state=state['state'], observation=first))); return
            write('checking_terminal_stability', observation=first)
            time.sleep(60)
            second = r.inspect()
            if not r.ready(second, first):
                write('terminal_not_stable_needs_review', observation=second)
                raise RuntimeError('No stable Spectre terminal evidence; no completion inferred')
            write('collecting_existing_remote', observation=second)
            ok = r.collect(launch, second)
            write('completed_pending_remote_review' if ok else 'recovered_failed_needs_review', result_sha256=r.sha(r.WORK/'result.json'))
            print(json.dumps(dict(state=state['state'], no_new_simulations=True)))
        except Exception as e:
            write('heartbeat_collection_needs_review', collection_failure=repr(e))
            raise


if __name__ == '__main__':
    main()
