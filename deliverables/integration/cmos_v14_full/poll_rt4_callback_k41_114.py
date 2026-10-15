"""Bounded supervision of the single callback K41 diagnostic114 run; never launch/cancel."""
import datetime,json,re,time
import psutil
import recover_rt4_callback_k41_114 as r
from poll_rt4_recheck103 import exclusive
from remote_paths import RUN_DIRECTORY_RE

def main():
    from rt4_recheckstep_transport105 import SSH, verify_identity
    verify_identity();r.SSH=SSH
    r.RUN='rt4cbk41114ssd01';r.CASE='rt4_callback_k41_114_tt'
    r.WORK=r.ROOT/'research/runs/spectre_cmos_v14_full'/r.RUN/r.CASE
    r.STATE=r.ROOT/'research/rt4_callback_k41_114_pipeline.json'
    r.PROTOCOL=r.H/'results/rt4_callback_k41_114_protocol.json'
    # Keep the lock outside the runner's output directory: the runner hashes
    # every file there on completion and Windows forbids reading a held byte.
    with exclusive(r.STATE.with_suffix('.lock')):
        s=json.loads(r.STATE.read_text());p=json.loads(r.PROTOCOL.read_text())
        assert s['protocol_sha256']==r.sha(r.PROTOCOL)
        assert len(p['cases'])==1 and p['cases'][0]['run']==r.RUN and p['cases'][0]['case']==r.CASE
        launch=json.loads((r.WORK/'launch.json').read_text())
        assert launch['case']==r.CASE and launch['launch_policy']['transport_attempts']==1
        assert launch['launch_policy']['implementation_sha256']==r.sha(r.H/'single_launch_transport.py')
        assert not launch.get('initial_states')
        assert all(r.sha(r.WORK/'inputs'/n)==v for n,v in launch['inputs_sha256'].items())
        paths=set(re.findall(RUN_DIRECTORY_RE+'/',(r.WORK/'runner.log').read_text()))
        assert len(paths)==1; r.RD=paths.pop().rstrip('/')
        assert r.RD.startswith('/server_local_ssd/jielu/IP-PLL-GPT6/')
        def write(state,**extra):
            s.update(state=state,updated=datetime.datetime.now().astimezone().isoformat(),**extra)
            tmp=r.STATE.with_suffix('.poll.tmp');tmp.write_text(json.dumps(s,indent=2)+'\n');tmp.replace(r.STATE)
        # The original runner owns download while alive. A reused PID does not.
        alive=[]
        for w in s['workers']:
            try:
                proc=psutil.Process(w['pid'])
                w['running']=proc.is_running() and abs(proc.create_time()-w['create_time'])<1
                if w['running']:assert proc.cmdline()==w['cmdline'];alive.append(w['pid'])
            except psutil.NoSuchProcess:w['running']=False
        current=r.inspect()
        if alive:
            write('runner_active',observation=current,local_workers=alive)
        elif (r.WORK/'result.json').exists():
            write('completed_pending_independent_review',observation=current,result_sha256=r.sha(r.WORK/'result.json'),local_workers=[])
        elif current['live']:
            write('waiting_existing_remote_heartbeat',observation=current,local_workers=[])
        else:
            write('checking_terminal_stability',observation=current,local_workers=[])
            time.sleep(60);second=r.inspect()
            assert r.ready(second,current), 'No stable terminal; never infer completion'
            write('collecting_existing_remote',observation=second)
            ok=r.collect(launch,second)
            write('completed_pending_independent_review' if ok else 'recovered_failed_needs_review',result_sha256=r.sha(r.WORK/'result.json'))
        print(json.dumps({k:s[k] for k in ['state','observation','local_workers']}))

if __name__=='__main__':main()
