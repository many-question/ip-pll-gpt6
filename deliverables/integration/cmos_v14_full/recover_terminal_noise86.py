"""Collect two already terminated jobs after all revision-85 local owners exited.

No simulator dispatch or process termination. A separate permanent revision-86
claim preserves the earlier ownership record. Failed runs never get result.json.
"""
import argparse, datetime, json, os, shlex, subprocess, sys, time
import psutil
import recover_active_noise_detached85 as x


def now():
    return datetime.datetime.now().astimezone().isoformat()


def main():
    p=argparse.ArgumentParser(); p.add_argument('--target',required=True,choices=sorted(x.SPECS))
    args=p.parse_args(); x.configure(args.target)
    old_owner=int((x.WORK/'.detached_recovery85_claim').read_text())
    assert not psutil.pid_exists(old_owner), 'Previous collector PID still exists; inspect before takeover'
    for process in psutil.process_iter(['pid','cmdline']):
        cmd=process.info['cmdline'] or []
        if process.pid==os.getpid(): continue
        if args.target in cmd and any('recover_' in a and a.endswith('.py') for a in cmd):
            raise RuntimeError('Another collector exists: '+str(process.pid))
    assert not (x.WORK/'result.json').exists()
    state=json.loads(x.STATE.read_text()); launch=json.loads((x.WORK/'launch.json').read_text())
    protocol=json.loads(x.PROTOCOL.read_text())
    assert state['protocol_sha256']==x.sha(x.PROTOCOL)
    assert launch['launch_policy']['implementation_sha256']==protocol['launch_policy_sha256']
    assert all(x.sha(x.WORK/'inputs'/n)==v for n,v in launch['inputs_sha256'].items())
    assert any(c['run']==x.RUN and c['case']==x.CASE for c in protocol['cases'])
    with (x.WORK/'.terminal_recovery86_claim').open('x') as f:
        json.dump(dict(pid=os.getpid(),created=psutil.Process().create_time(),prior_owner=old_owner,time=now()),f)
    (x.WORK/'pipeline_before_recovery86.json').write_text(json.dumps(state,indent=2)+'\n')
    def write(status,**extra):
        state.update(state=status,updated=now(),terminal_recovery86=dict(pid=os.getpid(),prior_owner=old_owner,no_new_simulations=True),**extra)
        tmp=x.STATE.with_suffix('.recovery86.tmp');tmp.write_text(json.dumps(state,indent=2)+'\n');tmp.replace(x.STATE)
    try:
        first=x.inspect(); assert not first['live']
        write('verifying_terminal',observation=first)
        time.sleep(60)
        current=x.inspect(); assert current==first and not current['live']
        (x.WORK/'terminal_observation86.json').write_text(json.dumps(dict(time=now(),observation=current),indent=2)+'\n')
        if args.target=='rt4_half_seed29_retry':
            assert x.ready(current,first) and current['terminal_errors']==0 and current['exit_code']=='0'
            write('collecting_existing_remote',observation=current)
            assert x.collect(launch,current)
            subprocess.run([sys.executable,str(x.H/'analyze_full_pll_direct_noise_pair.py'),'--protocol',x.PROTOCOL.name],cwd=x.ROOT,check=True)
            validation=x.H/'results'/x.PROTOCOL.name.replace('_protocol.json','_validation.json')
            write('completed_pending_review',validation_sha256=x.sha(validation))
        else:
            assert current['exit_code']=='141' and current['terminal_errors'] is None
            write('collecting_failed_terminal',observation=current)
            before=x.inventory(launch)
            assert before['inputs']==launch['inputs_sha256']
            assert before['initial_states']=={k:v['sha256'] for k,v in launch['initial_states'].items()}
            for name,item in before['outputs'].items():
                dest=x.WORK/name; assert dest.resolve().is_relative_to(x.WORK.resolve())
                dest.parent.mkdir(parents=True,exist_ok=True)
                if dest.exists() and x.sha(dest)==item['sha256']: continue
                part=dest.with_name(dest.name+'.failure86.part')
                with part.open('wb') as f:
                    subprocess.run(x.SSH+['cat '+shlex.quote(item['path'])],stdout=f,check=True,timeout=3600)
                assert part.stat().st_size==item['bytes'] and x.sha(part)==item['sha256']
                if dest.exists():
                    previous=dest.with_name(dest.name+'.client_partial86'); assert not previous.exists();dest.rename(previous)
                part.replace(dest);print('Recovered '+name,flush=True)
            assert x.inventory(launch)==before and x.inspect()==current
            raw=x.WORK/(x.CASE+'.raw/tran.tran.tran')
            with raw.open('rb') as f:
                f.seek(max(0,raw.stat().st_size-2048));tail=f.read().decode()
            rec=dict(time=now(),run=x.RUN,case=x.CASE,ok=False,terminal_failure=True,completion_verified=False,
                high_offset_diagnostic_valid=False,full_pll_acceptance=False,observation=current,
                files=before['outputs'],inputs_sha256=before['inputs'],referenced_initial_states_sha256=before['initial_states'],
                remote_local_hashes_match=True,hashes_stable_during_transfer=True,raw_has_end=tail.rstrip().endswith('END'),raw_tail=tail,
                errors=['Exit 141; Spectre terminal footer absent. No valid noise measurement.'],
                interpretation='Consistent with SIGPIPE after the old stdout SSH reader disconnected; not a proven kernel-level cause. All failed evidence retained; retry must use isolated SSD console.')
            assert not rec['raw_has_end']
            (x.WORK/'failed_collection86.json').write_text(json.dumps(rec,indent=2)+'\n')
            proof=x.H/'results/main_iab100_failed_collection86.json';assert not proof.exists()
            proof.write_text(json.dumps(rec,indent=2)+'\n')
            write('failed_terminal_collected',failed_collection_sha256=x.sha(proof),valid_noise_result=False)
        print('Terminal recovery finished: '+args.target,flush=True)
    except Exception as e:
        write('needs_review',recovery_failure=repr(e));raise


if __name__=='__main__': main()
