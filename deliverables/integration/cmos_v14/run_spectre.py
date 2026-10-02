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

HERE=Path(__file__).resolve().parent
DELIVERY=HERE.parents[2]
ROOT=DELIVERY.parent if DELIVERY.name=='share' and (DELIVERY.parent/'AGENTS.md').exists() else DELIVERY
BLOCKS=HERE.parents[1]/'blocks/behavioral_va'
REMOTE='/home/jielu/TSMC180/MP/IP-PLL-GPT6/simulation/cmos_v14'
TX=HERE.parents[1]/'blocks/output_v9'

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--run-id',required=True)
    parser.add_argument('--mode',choices=['spectre','aps','ax'],default='spectre')
    parser.add_argument('--threads',type=int,choices=range(1,9),default=1,help='Bound APS threads; default remains one')
    parser.add_argument('--preset-override',choices=['maxstep','maxstep,reltol,method,errpreset','all'],help='Honor named options, or all netlist solver options with bare -preset_override; verify actual log values')
    parser.add_argument('--timeout',type=int,default=3600,help='Per-job wall-clock limit in seconds')
    parser.add_argument('--snapshot-run',help='Replay immutable inputs from a prior local run instead of current design files')
    select=parser.add_mutually_exclusive_group(required=True)
    select.add_argument('--cases',nargs='+')
    select.add_argument('--suite',choices=['timing','control','inductor','loop'])
    args=parser.parse_args()
    if args.suite=='timing':args.cases=[f'tb_cp_timing_{c}' for c in ['tt','ss','ff']]
    elif args.suite=='control':args.cases=[f'tb_{b}_{c}' for c in ['tt','ss','ff'] for b in ['config','supervisor']]
    elif args.suite=='inductor':args.cases=[f'tb_inductor_q{q}' for q in [3,5,8]]+[f'tb_rlc_q{q}_c{c}_nom' for q in [3,5,8] for c in [0,255]]
    elif args.suite=='loop':args.cases=['loop_s10_timing_tt','loop_s10_corner_ss','loop_s10_corner_ff','loop_s11_parallel_tt']
    assert args.run_id.replace('_','').isalnum()
    if args.snapshot_run:assert args.snapshot_run.replace('_','').isalnum()
    out=ROOT/'research/runs/spectre_cmos_v14'/args.run_id
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
        for folder in ['transistor_v1','transistor_v2','transistor_v3','vco_v4','interface_v5','closure_v6','accuracy_v7','output_v8','output_v9','noise_v10','jitter_v11','cmos_v12','cmos_v13','cmos_v14']:
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
            prior=json.loads((snapshot.parent/'result.json').read_text())
            for remote,info in prior.get('initial_states',{}).items():
                body=body.replace('readic="'+remote+'"','readic="'+info['source']+'"')
        body=re.sub(r'writefinal="[^"]+"','writefinal="'+state_remote+'"',body)
        pss_state_remote=REMOTE+'/'+args.run_id+'_'+case+'.periodic.state'
        has_pss_state='writepss=' in body
        body=re.sub(r'writepss="[^"]+"','writepss="'+pss_state_remote+'"',body)
        has_final_state='writefinal=' in body
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
        rec['local_outputs_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in work.iterdir() if p.is_file() and p.name!='result.json'}
        (work/'result.json').write_text(json.dumps(rec,indent=2,default=str)+'\n',encoding='utf-8',newline='\n')
        records.append(rec)
        (out/'index.json').write_text(json.dumps(records,indent=2,default=str)+'\n',encoding='utf-8',newline='\n')
        print('DONE',case,result.ok,rec['errors'],flush=True)
        if not result.ok: return 1
    return 0

if __name__=='__main__':raise SystemExit(main())
