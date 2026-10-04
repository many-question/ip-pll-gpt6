"""Run generated testbenches with installed virtuoso-bridge; retain all raw results.

Usage: python .../run_spectre.py --run-id smoke01 --cases tb_vco
Requires existing user-level bridge environment; no project-local .env is created.
"""
import argparse
import datetime
import hashlib
import json
import os
import shutil
import contextlib
import shlex
import subprocess
import tarfile
from pathlib import Path, PurePosixPath
import numpy as np
from virtuoso_bridge.spectre.runner import SpectreSimulator,load_vb_env,spectre_mode_args
from virtuoso_bridge.models import ExecutionStatus
from virtuoso_bridge.spectre.parsers import parse_psf_ascii_directory
from transient_diagnostics import effective as transient_effective, recovery as transient_recovery

HERE=Path(__file__).resolve().parent
DELIVERY=HERE.parents[2]
ROOT=DELIVERY.parent if DELIVERY.name=='share' and (DELIVERY.parent/'AGENTS.md').exists() else DELIVERY
BLOCKS=HERE.parents[1]/'blocks/behavioral_va'
REMOTE='/home/jielu/TSMC180/MP/IP-PLL-GPT6/simulation/cmos_v14_full'
TX=HERE.parents[1]/'blocks/output_v9'

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--run-id',required=True)
    parser.add_argument('--mode',choices=['spectre','aps','ax'],default='spectre')
    parser.add_argument('--threads',type=int,choices=range(1,17),default=1,help='Per-job APS threads; caller must enforce project-wide18-thread cap. Default one.')
    parser.add_argument('--preset-override',choices=['maxstep','maxstep,reltol,method,errpreset','all'],help='Honor named options, or all netlist solver options with bare -preset_override; verify actual log values')
    parser.add_argument('--timeout',type=int,default=3600,help='Per-job wall-clock limit in seconds')
    parser.add_argument('--snapshot-run',help='Replay immutable inputs from a prior local run instead of current design files')
    parser.add_argument('--native-state',help='Locally recovered native .srf checkpoint under project research/; requires --snapshot-run and exactly one case')
    parser.add_argument('--pss-state',help='Recovered converged PSS state under project research/. Checks PSS consistency; caller must compare physical dependency hashes.')
    parser.add_argument('--tran-stop',help='Override transient stop for a native-checkpoint continuation, e.g.10u')
    parser.add_argument('--tran-start',help='Explicit analysis start time on a native continuation; must be validated against the checkpoint')
    parser.add_argument('--native-save-times',nargs='+',help='Explicit future checkpoint times on a native continuation')
    parser.add_argument('--transient-reltol',help='Explicit numerical comparison on a native continuation, e.g.1e-5')
    parser.add_argument('--transient-maxstep',help='Explicit numerical comparison on a native continuation, e.g.1p')
    parser.add_argument('--dense-output',action='store_true',help='Native continuation only: retain every accepted transient point, including when the source used skipcount')
    parser.add_argument('--extra-save',nargs='+',help='Additional node/current observations; no DUT change')
    parser.add_argument('--only-save',nargs='+',help='Native continuation only: replace observation list without changing any circuit element')
    parser.add_argument('--transient-noisefmax',type=float,help='Explicit source-noise bandwidth in Hz on a native transient continuation; zero disables noise')
    parser.add_argument('--transient-noisefmin',type=float,help='Explicit source-noise low-frequency corner in Hz on a native continuation')
    parser.add_argument('--transient-noiseseed',type=int,help='Positive reproducible noise seed on a native transient continuation')
    parser.add_argument('--transient-noisescale',type=float,help='Native continuation noise-amplitude control, for explicitly initialized-noise checkpoint experiments')
    parser.add_argument('--transient-noise-start',type=float,help='Explicit isnoisy=0 to1 event at this absolute time after native restore')
    parser.add_argument('--transient-noisemethod',choices=['default','adaptive'],help='Explicit noise algorithm comparison on a native transient continuation')
    parser.add_argument('--transient-iabstol',type=float,help='Explicit current tolerance comparison on a native continuation; does not alter devices')
    parser.add_argument('--transient-method',choices=['traponly','gear2only','trap','gear2'],help='Explicit integration method comparison on a native continuation')
    parser.add_argument('--dynamic-tolerance',choices=['reltol','vabstol','iabstol'],help='Apply one documented transient dynamic tolerance after native restore')
    parser.add_argument('--dynamic-tolerance-time',type=float,help='Absolute simulation time in seconds, strictly after native checkpoint')
    parser.add_argument('--dynamic-tolerance-value',type=float,help='Positive new tolerance; original value is retained at time zero')
    select=parser.add_mutually_exclusive_group(required=True)
    select.add_argument('--cases',nargs='+')
    select.add_argument('--suite',choices=['timing','control','inductor','loop'])
    args=parser.parse_args()
    if args.native_state:
        assert args.snapshot_run and args.cases and len(args.cases)==1
    if args.pss_state:assert not args.native_state and args.cases and len(args.cases)==1
    if args.dense_output:assert args.native_state
    noise_overrides=dict(noisefmax=args.transient_noisefmax,noisefmin=args.transient_noisefmin,noiseseed=args.transient_noiseseed)
    if args.transient_noisescale is not None:
        assert np.isfinite(args.transient_noisescale) and args.transient_noisescale>0
        noise_overrides['noisescale']=args.transient_noisescale
    if args.transient_noisemethod is not None:noise_overrides['trannoisemethod']=args.transient_noisemethod
    solver_overrides={}
    if args.transient_noise_start is not None:
        assert args.native_state and not args.dynamic_tolerance and np.isfinite(args.transient_noise_start) and args.transient_noise_start>0
        assert args.transient_noisefmax and args.transient_noisefmax>0
        solver_overrides['noise_start_s']=args.transient_noise_start
    if args.dynamic_tolerance:
        assert args.native_state and args.dynamic_tolerance_time and args.dynamic_tolerance_value
        assert all(np.isfinite(v) and v>0 for v in [args.dynamic_tolerance_time,args.dynamic_tolerance_value])
        solver_overrides['dynamic_tolerance']=dict(parameter=args.dynamic_tolerance,time_s=args.dynamic_tolerance_time,value=args.dynamic_tolerance_value)
    else:assert args.dynamic_tolerance_time is None and args.dynamic_tolerance_value is None
    if args.transient_method is not None:
        assert args.native_state
        solver_overrides['method']=args.transient_method
    if args.transient_iabstol is not None:
        assert args.native_state and np.isfinite(args.transient_iabstol) and args.transient_iabstol>0
        solver_overrides['iabstol']=args.transient_iabstol
    if any(value is not None for value in noise_overrides.values()):
        assert args.native_state,'Noise overrides require explicit native continuation provenance.'
        if args.transient_noisefmax is not None:assert np.isfinite(args.transient_noisefmax) and args.transient_noisefmax>=0
        if args.transient_noisefmin is not None:assert np.isfinite(args.transient_noisefmin) and args.transient_noisefmin>0
        if args.transient_noiseseed is not None:assert args.transient_noiseseed>0
        if args.transient_noisefmax and args.transient_noisefmin:assert args.transient_noisefmin<=args.transient_noisefmax
    if args.extra_save or args.only_save:
        import re
        assert not (args.extra_save and args.only_save)
        if args.only_save:assert args.native_state
        assert all(re.fullmatch(r'[A-Za-z0-9_.:]+',x) for x in (args.extra_save or args.only_save))
    if args.tran_stop:
        import re
        assert args.native_state and re.fullmatch(r'[0-9.]+(?:[eE][-+]?\d+|[pnum]?)',args.tran_stop)
    if args.tran_start or args.native_save_times:
        import re
        assert args.native_state
        for token in ([args.tran_start] if args.tran_start else [])+(args.native_save_times or []):
            assert re.fullmatch(r'[0-9.]+(?:[eE][-+]?\d+|[pnum]?)',token)
    if args.transient_reltol or args.transient_maxstep:
        import re
        assert args.native_state
        for value in [args.transient_reltol,args.transient_maxstep]:
            if value:assert re.fullmatch(r'[0-9.]+(?:[eE][-+]?\d+|[pnum]?)',value)
    if args.suite=='timing':args.cases=[f'tb_cp_timing_{c}' for c in ['tt','ss','ff']]
    elif args.suite=='control':args.cases=[f'tb_{b}_{c}' for c in ['tt','ss','ff'] for b in ['config','supervisor']]
    elif args.suite=='inductor':args.cases=[f'tb_inductor_q{q}' for q in [3,5,8]]+[f'tb_rlc_q{q}_c{c}_nom' for q in [3,5,8] for c in [0,255]]
    elif args.suite=='loop':args.cases=['loop_s10_timing_tt','loop_s10_corner_ss','loop_s10_corner_ff','loop_s11_parallel_tt']
    assert args.run_id.replace('_','').isalnum()
    if args.snapshot_run:assert args.snapshot_run.replace('_','').isalnum()
    out=ROOT/'research/runs/spectre_cmos_v14_full'/args.run_id
    out.mkdir(parents=True,exist_ok=False)
    load_vb_env()
    # Keep normal bridge config, explicitly constrain project-specific data roots.
    records=[]
    for case in args.cases:
        assert case.replace('_','').isalnum()
        netlist=HERE/'tb'/f'{case}.scs'
        work=out/case
        sim=SpectreSimulator(remote=True,remote_work_dir=REMOTE,
                             spectre_args=[x for x in spectre_mode_args(args.mode) if x!='+mt']+([f'+mt={args.threads}'] if args.mode in ('aps','ax') else [])+(['-preset_override' if args.preset_override=='all' else f'-preset_override={args.preset_override}'] if args.preset_override else []),timeout=args.timeout,
                             work_dir=work,keep_remote_files=True,output_format='psfascii')
        files=[netlist]+sorted(BLOCKS.glob('*.va'))+sorted((HERE/'state_inputs').glob('*.ic'))
        for folder in ['transistor_v1','transistor_v2','transistor_v3','vco_v4','interface_v5','closure_v6','accuracy_v7','output_v8','output_v9','noise_v10','jitter_v11','cmos_v12','cmos_v13','cmos_v14','cmos_v14_full']:
            files+=sorted((TX.parent/folder).glob('*.scs'))+sorted((TX.parent/folder).glob('*.va'))
        # Resolve only project-owned includes; the PDK remains on the server.
        import re
        available={p.name:p for p in files};needed={netlist.name};pending=[netlist]
        while pending:
            for name in re.findall(r'(?:include|ahdl_include)\s+"([^"]+)"|readic="([^"]+)"',pending.pop().read_text()):
                name=next(x for x in name if x)
                if name.startswith('/') or name in ('disciplines.vams','constants.vams'):continue
                assert name in available,name
                if name not in needed:needed.add(name);pending.append(available[name])
        files=[netlist]+[available[k] for k in sorted(needed) if k!=netlist.name]
        if args.snapshot_run:
            snapshot=out.parent/args.snapshot_run/case/'inputs'
            netlist=snapshot/(case+'.scs')
            assert netlist.is_file(),netlist
            files=[netlist]+[p for p in sorted(snapshot.iterdir()) if p!=netlist and p.suffix in ('.scs','.va','.ic')]
        (work/'inputs').mkdir(parents=True)
        for p in files: shutil.copy2(p,work/'inputs'/p.name)
        # Immutable local snapshot is both simulator input and hash authority.
        # Design work may continue while a long simulation is running.
        files=[work/'inputs'/p.name for p in files]
        netlist=files[0]
        # State outputs are unique to this immutable run and remain under project root.
        state_remote=REMOTE+'/'+args.run_id+'_'+case+'.final.ic'
        body=netlist.read_text()
        if args.snapshot_run:
            if args.native_state:body=re.sub(r'\s+(?:readic|recover)="[^"]+"','',body)
            if (snapshot.parent/'result.json').exists():prior=json.loads((snapshot.parent/'result.json').read_text())
            else:
                assert 'readic=' not in body,'Pending source with an initial-state remapping needs its result manifest'
                prior={}
            for remote,info in prior.get('initial_states',{}).items():
                body=body.replace('readic="'+remote+'"','readic="'+info['source']+'"')
        body=re.sub(r'writefinal="[^"]+"','writefinal="'+state_remote+'"',body)
        pss_state_remote=REMOTE+'/'+args.run_id+'_'+case+'.periodic.state'
        has_pss_state='writepss=' in body
        body=re.sub(r'writepss="[^"]+"','writepss="'+pss_state_remote+'"',body)
        # A continuation must never overwrite its predecessor's native checkpoint.
        native_save_remote=REMOTE+'/'+args.run_id+'_'+case+'.srf'
        body=re.sub(r'savefile="[^"]+"','savefile="'+native_save_remote+'"',body)
        has_final_state='writefinal=' in body
        native_state_info=None
        periodic_state_info=None
        if args.pss_state:
            periodic=Path(args.pss_state).resolve()
            assert periodic.is_relative_to((ROOT/'research').resolve()) and periodic.is_file()
            assert re.search(r'^pss .*\bpss\b',body,re.M)
            periodic_remote=REMOTE+'/'+args.run_id+'_'+case+'.readpss.state'
            ssh=['C:/Windows/System32/OpenSSH/ssh.exe','-F',str(Path.home()/'.virtuoso-bridge/ssh_config_ipv6'),'-o','BatchMode=yes','thu-xia-v6']
            subprocess.run(['C:/Windows/System32/OpenSSH/scp.exe','-F',str(Path.home()/'.virtuoso-bridge/ssh_config_ipv6'),'-o','BatchMode=yes',str(periodic),'thu-xia-v6:'+periodic_remote],check=True,capture_output=True,timeout=300)
            digest=hashlib.sha256(periodic.read_bytes()).hexdigest()
            assert subprocess.check_output(ssh+['sha256sum '+shlex.quote(periodic_remote)],timeout=60).decode().split()[0]==digest
            periodic_state_info=dict(local=periodic.relative_to(ROOT).as_posix(),remote=periodic_remote,sha256=digest,remote_hash_match=True,checkpss='yes')
            body=re.sub(r'\s+readic="[^"]+"','',body)
            body=re.sub(r'\btstab=\S+','tstab=0',body)
            body=re.sub(r'^(pss .*)$',lambda m:m[0]+' readpss="'+periodic_remote+'" checkpss=yes',body,flags=re.M)
        if args.native_state:
            native=Path(args.native_state).resolve()
            assert native.is_relative_to((ROOT/'research').resolve()) and native.suffix=='.srf' and native.is_file()
            native_remote=REMOTE+'/'+args.run_id+'_'+case+'.recover.srf'
            ssh=['C:/Windows/System32/OpenSSH/ssh.exe','-F',str(Path.home()/'.virtuoso-bridge/ssh_config_ipv6'),'-o','BatchMode=yes','thu-xia-v6']
            subprocess.run(ssh+['mkdir -p '+shlex.quote(REMOTE)],check=True,capture_output=True,timeout=30)
            subprocess.run(['C:/Windows/System32/OpenSSH/scp.exe','-F',str(Path.home()/'.virtuoso-bridge/ssh_config_ipv6'),'-o','BatchMode=yes',str(native),'thu-xia-v6:'+native_remote],check=True,capture_output=True,timeout=90)
            digest=hashlib.sha256(native.read_bytes()).hexdigest()
            proof=subprocess.check_output(ssh+['sha256sum '+shlex.quote(native_remote)],timeout=30).decode().split()[0]
            assert proof==digest
            native_state_info=dict(local=native.relative_to(ROOT).as_posix(),remote=native_remote,sha256=digest,remote_hash_match=True,source_snapshot=args.snapshot_run)
            body=re.sub(r'^(tran tran .*)$',lambda m:m[0]+' recover="'+native_remote+'"',body,flags=re.M)
            assert ' recover=' in body
            if args.tran_stop:body=re.sub(r'(?<=\bstop=)\S+',args.tran_stop,body)
            if args.tran_start:
                body=re.sub(r'^tran tran .*$',lambda m:re.sub(r'\bstart=\S+','start='+args.tran_start,m[0]) if re.search(r'\bstart=',m[0]) else m[0]+' start='+args.tran_start,body,flags=re.M)
                solver_overrides['start']=args.tran_start
            if args.native_save_times:
                body,count=re.subn(r'savetime=\[[^]]+\]','savetime=['+' '.join(args.native_save_times)+']',body)
                assert count==1
                solver_overrides['savetime']=args.native_save_times
            if args.transient_reltol:body=re.sub(r'(?<=\breltol=)\S+',args.transient_reltol,body)
            if args.transient_maxstep:body=re.sub(r'(?<=\bmaxstep=)\S+',args.transient_maxstep,body)
            if args.transient_iabstol is not None:
                body,count=re.subn(r'(?<=\biabstol=)\S+',format(args.transient_iabstol,'.17g'),body)
                assert count==1,'Expected one explicit current tolerance.'
            if args.transient_method is not None:
                body,count=re.subn(r'(?<=\bmethod=)\S+',args.transient_method,body)
                assert count==1,'Expected one explicit integration method.'
            if args.dynamic_tolerance:
                assert not re.search(r'\bparam(?:set|_vec)?=',body)
                initial=float(re.search(r'\b'+args.dynamic_tolerance+r'=(\S+)',body)[1])
                dynamic=' param='+args.dynamic_tolerance+' param_vec=[0 '+format(initial,'.17g')+' '+format(args.dynamic_tolerance_time,'.17g')+' '+format(args.dynamic_tolerance_value,'.17g')+']'
                body,count=re.subn(r'^tran tran .*$',lambda m:m[0]+dynamic,body,flags=re.M)
                assert count==1
            if args.transient_noise_start is not None:
                assert not re.search(r'\bparam(?:set|_vec)?=',body)
                dynamic=' param=isnoisy param_vec=[0 0 '+format(args.transient_noise_start,'.17g')+' 1]'
                body,count=re.subn(r'^tran tran .*$',lambda m:m[0]+dynamic,body,flags=re.M)
                assert count==1
            if args.dense_output:
                body=body.replace('strobeoutput=strobeonly','strobeoutput=all')
                body=re.sub(r'\bskipcount=[0-9]+','skipcount=0',body)
            for parameter,value in noise_overrides.items():
                if value is None:continue
                encoded=str(value) if parameter in ('noiseseed','trannoisemethod') else format(value,'.17g')
                def change_noise(match):
                    line=match[0]
                    if re.search(r'\b'+parameter+r'=\S+',line):
                        return re.sub(r'\b'+parameter+r'=\S+',parameter+'='+encoded,line)
                    return line+' '+parameter+'='+encoded
                body,count=re.subn(r'^tran tran .*$',change_noise,body,flags=re.M)
                assert count==1,'Expected one native transient analysis.'
            netlist.write_text(body,encoding='utf-8',newline='\n')
        if args.extra_save:body+='\nsave '+' '.join(args.extra_save)+'\n'
        if args.only_save:
            body=re.sub(r'^save .*(?:\n|$)','',body,flags=re.M)
            body+='\nsave '+' '.join(args.only_save)+'\n'
        netlist.write_text(body,encoding='utf-8',newline='\n')
        initial_states={}
        state_names=re.findall(r'readic="([^"]+)"',netlist.read_text())
        for name in state_names:
            if name.startswith('/'):raise ValueError('Initial states must be local snapshot files, not an unchecked remote path')
            assert Path(name).name==name and name.endswith('.ic')
            local_state=work/'inputs'/name
            dest=REMOTE+'/'+args.run_id+'_'+case+'_'+name
            ssh=['C:/Windows/System32/OpenSSH/ssh.exe','-F',str(Path.home()/'.virtuoso-bridge/ssh_config_ipv6'),'-o','BatchMode=yes','thu-xia-v6']
            subprocess.run(ssh+['mkdir -p '+shlex.quote(REMOTE)],check=True,capture_output=True,timeout=30)
            subprocess.run(['C:/Windows/System32/OpenSSH/scp.exe','-F',str(Path.home()/'.virtuoso-bridge/ssh_config_ipv6'),'-o','BatchMode=yes',str(local_state),'thu-xia-v6:'+dest],check=True,capture_output=True,timeout=60)
            proof=subprocess.check_output(ssh+['sha256sum '+shlex.quote(dest)],timeout=30).decode().split()[0]
            digest=hashlib.sha256(local_state.read_bytes()).hexdigest();assert proof==digest
            initial_states[dest]={'source':name,'sha256':digest,'remote_hash_match':True}
            netlist.write_text(netlist.read_text().replace('readic="'+name+'"','readic="'+dest+'"'),encoding='utf-8',newline='\n')
        # Persist recovery provenance before the potentially hours-long SSH call.
        # The local client may disappear while the remote simulator keeps running.
        launch=dict(case=case,time=datetime.datetime.now().astimezone().isoformat(),
            initial_states=initial_states,native_state=native_state_info,periodic_state=periodic_state_info,
            numerical_overrides=dict(reltol=args.transient_reltol,maxstep=args.transient_maxstep,dense_output=args.dense_output,extra_save=args.extra_save,only_save=args.only_save),
            transient_noise_overrides=noise_overrides,
            transient_solver_overrides=solver_overrides,
            inputs_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
            threads=args.threads,mode=args.mode,wall_timeout_s=args.timeout)
        (work/'launch.json').write_text(json.dumps(launch,indent=2)+'\n',encoding='utf-8',newline='\n')
        print('START',case,flush=True)
        with (work/'runner.log').open('w',encoding='utf-8') as log:
            with contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
                result=sim.run_simulation(netlist,{'include_files':files[1:]})
        if not result.ok and any('Failed to download remote raw' in e for e in result.errors):
            # Windows streaming-tar can truncate the transport despite a successful
            # simulator run. Capture the SSH byte stream completely before extraction.
            remote_net=next(x for x in shlex.split(result.metadata['spectre_command']) if x.endswith('.scs'))
            remote_dir=str(PurePosixPath(remote_net).parent)
            assert remote_dir.startswith(REMOTE+'/')
            archive=work/'recovered_raw.tar.gz'
            ssh_config=Path.home()/'.virtuoso-bridge/ssh_config_ipv6'
            cmd=['ssh','-F',str(ssh_config),'-o','BatchMode=yes','thu-xia-v6',
                 'tar -czf - -C '+shlex.quote(remote_dir)+' '+shlex.quote(case+'.raw')+' spectre.out']
            with archive.open('wb') as dest:subprocess.run(cmd,stdout=dest,check=True,timeout=180)
            with tarfile.open(archive) as tf:tf.extractall(work,filter='data')
            simlog=(work/'spectre.out').read_text(errors='replace')
            if '0 errors' in simlog[-6000:]:
                result.metadata['transport_recovered_errors']=result.errors
                result.errors=[]
                result.status=ExecutionStatus.SUCCESS
                result.data=parse_psf_ascii_directory(work/(case+'.raw'))
        rec={'case':case,'time':datetime.datetime.now().astimezone().isoformat(),
             'ok':result.ok,'errors':result.errors,'metadata':result.metadata,
             'initial_states':initial_states,
             'native_state':native_state_info,
             'periodic_state':periodic_state_info,
             'numerical_overrides':dict(reltol=args.transient_reltol,maxstep=args.transient_maxstep,dense_output=args.dense_output,extra_save=args.extra_save,only_save=args.only_save),
             'transient_noise_overrides':noise_overrides,
             'transient_solver_overrides':solver_overrides,
             'inputs_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
        work.mkdir(parents=True,exist_ok=True)
        if result.ok:
            data={k:np.atleast_1d(v) for k,v in result.data.items() if np.asarray(v).dtype.kind in 'biufc'}
            rec['non_waveform_fields']={k:str(v) for k,v in result.data.items() if np.asarray(v).dtype.kind not in 'biufc'}
            np.savez_compressed(work/'waveforms.npz',**data)
            rec['signals']={k:len(v) for k,v in data.items()}
            rec['final_values']={k:float(v[-1]) for k,v in data.items() if len(v)>0 and np.isrealobj(v) and np.isfinite(v[-1])}
        remote_netlist=next((x for x in shlex.split(rec['metadata'].get('spectre_command','')) if x.endswith('.scs')),None)
        (work/'result.json').write_text(json.dumps(rec,indent=2,default=str)+'\n',encoding='utf-8',newline='\n')
        if remote_netlist:
            remote_dir=str(PurePosixPath(remote_netlist).parent)
            assert remote_dir.startswith(REMOTE+'/')
            with (work/'runner.log').open('a',encoding='utf-8') as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
                proof=sim._get_ssh_runner().run_command('cd '+shlex.quote(remote_dir)+' && sha256sum '+ ' '.join(shlex.quote(p.name) for p in files))
            remote_hashes={line.split()[1]:line.split()[0] for line in proof.stdout.splitlines() if len(line.split())==2 and len(line.split()[0])==64}
            rec['remote_inputs_sha256']=remote_hashes
            rec['remote_inputs_match']=remote_hashes==rec['inputs_sha256']
            assert rec['remote_inputs_match'], 'Remote input hashes differ'
        # Collect text state file when writefinal was requested.
        if has_final_state and remote_netlist:
            cp=subprocess.run(['C:/Windows/System32/OpenSSH/ssh.exe','-F',str(Path.home()/'.virtuoso-bridge/ssh_config_ipv6'),'-o','BatchMode=yes','thu-xia-v6','cat '+shlex.quote(state_remote)],capture_output=True,timeout=60)
            rec['state_file']={'remote':state_remote,'collected':cp.returncode==0,'stderr':cp.stderr.decode(errors='replace')}
            if cp.returncode==0:(work/'final.ic').write_bytes(cp.stdout)
        if has_pss_state and remote_netlist:
            cp=subprocess.run(['C:/Windows/System32/OpenSSH/ssh.exe','-F',str(Path.home()/'.virtuoso-bridge/ssh_config_ipv6'),'-o','BatchMode=yes','thu-xia-v6','cat '+shlex.quote(pss_state_remote)],capture_output=True,timeout=120)
            rec['periodic_state_file']={'remote':pss_state_remote,'collected':cp.returncode==0,'stderr':cp.stderr.decode(errors='replace')}
            if cp.returncode==0:(work/'periodic.state').write_bytes(cp.stdout)
        simlog_path=work/'spectre.out'
        if args.native_state and simlog_path.exists():
            simlog=simlog_path.read_text(errors='replace')
            observed=transient_effective(simlog)
            wanted={}
            if args.transient_reltol:wanted['reltol']=float(args.transient_reltol)
            if args.transient_iabstol is not None:wanted['abstol(I)']=args.transient_iabstol
            if args.transient_method is not None:wanted['method']=args.transient_method
            if args.transient_maxstep:
                m=re.fullmatch(r'([0-9.]+(?:[eE][-+]?\d+)?)([pnum]?)',args.transient_maxstep);assert m
                wanted['maxstep']=float(m[1])*{'':1.,'p':1e-12,'n':1e-9,'u':1e-6,'m':1e-3}[m[2]]
            mismatches={k:dict(requested=v,observed=observed.get(k)) for k,v in wanted.items()
                if not (observed.get(k)==v if isinstance(v,str) else isinstance(observed.get(k),(float,int)) and np.isclose(observed[k],v,rtol=1e-12,atol=0))}
            rec['numerical_log_validation']=dict(effective_initial=observed,requested_static=wanted,mismatches=mismatches,
                overrides_honored=not mismatches,dynamic_tolerance=solver_overrides.get('dynamic_tolerance'),
                note='Dynamic tolerance schedules are stored separately; the log parameter table describes initial analysis settings.')
            rec['numerical_recovery']=transient_recovery(simlog)
            if mismatches:
                rec['simulator_ok']=result.ok;rec['ok']=False
                rec['errors']=rec['errors']+['Requested numerical settings differ from effective analysis settings: '+str(mismatches)]
            resumed=re.findall(r'Restarting at time ([0-9.eE+-]+)\s*([fpnumkMG]?)s\.',simlog)
            failure=any(s in simlog for s in ['SPECTRE-4076','SPECTRE-16532','Failed to recover from'])
            start_time=None
            if len(resumed)==1:
                start_time=float(resumed[0][0])*{'':1.,'f':1e-15,'p':1e-12,'n':1e-9,'u':1e-6,'m':1e-3,'k':1e3,'M':1e6,'G':1e9}[resumed[0][1]]
            waveform_start=rec.get('final_values',{}).get('time')
            if result.ok and 'time' in data:waveform_start=float(data['time'][0])
            resumed_ok=not failure and start_time is not None
            if result.ok:resumed_ok=resumed_ok and waveform_start is not None and abs(waveform_start-start_time)<1e-15
            rec['native_resume_validation']=dict(accepted=resumed_ok,restart_log_time_s=start_time,waveform_start_s=waveform_start,recovery_failure_reported=failure)
            source_cache=out.parent/args.snapshot_run/case/'waveforms.npz'
            if result.ok and resumed_ok and source_cache.exists():
                with np.load(source_cache) as previous:
                    it=int(np.argmin(abs(previous['time']-start_time)))
                    if abs(previous['time'][it]-start_time)<1e-15:
                        # Observation-only VA accumulators can initialize separately;
                        # validate physical saved node voltages, not their bookkeeping.
                        skip={'time','units','energy_nj','power_mw','obsphase','obscycles','obsctrl','obsdivcycles'}
                        names=[k for k in previous.files if k in data and k not in skip and ':' not in k and len(previous[k])==len(previous['time'])]
                        delta={k:abs(float(data[k][0])-float(previous[k][it])) for k in names}
                        worst=max(delta,key=delta.get) if delta else None
                        boundary_ok=bool(delta) and delta[worst]<1e-3
                        rec['native_resume_validation']['physical_boundary']=dict(passed=boundary_ok,compared_nodes=len(delta),
                            max_voltage_difference_v=delta.get(worst),worst_node=worst,source_cache_sha256=hashlib.sha256(source_cache.read_bytes()).hexdigest(),
                            excluded_observer_nodes=sorted(skip-{'time','units'}),limit_v=1e-3)
                        resumed_ok=resumed_ok and boundary_ok
                        rec['native_resume_validation']['accepted']=resumed_ok
            if not resumed_ok:
                rec.setdefault('simulator_ok',result.ok);rec['ok']=False
                rec['errors']=rec['errors']+['Native checkpoint recovery was not verified; never treat a fresh restart as continuation.']
        rec['local_outputs_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in work.iterdir() if p.is_file() and p.name!='result.json'}
        (work/'result.json').write_text(json.dumps(rec,indent=2,default=str)+'\n',encoding='utf-8',newline='\n')
        records.append(rec)
        (out/'index.json').write_text(json.dumps(records,indent=2,default=str)+'\n',encoding='utf-8',newline='\n')
        print('DONE',case,rec['ok'],rec['errors'],flush=True)
        if not rec['ok']: return 1
    return 0

if __name__=='__main__':raise SystemExit(main())
