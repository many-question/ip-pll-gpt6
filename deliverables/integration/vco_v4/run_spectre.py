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
REMOTE='/home/jielu/TSMC180/MP/IP-PLL-GPT6/simulation/vco_v4'
TX=HERE.parents[1]/'blocks/vco_v4'

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--run-id',required=True)
    parser.add_argument('--mode',choices=['spectre','aps','ax'],default='spectre')
    parser.add_argument('--threads',type=int,choices=range(1,9),default=1,help='Bound APS threads; default remains one')
    parser.add_argument('--preset-override',choices=['maxstep','maxstep,reltol,method,errpreset'],help='Honor named netlist options in Spectre X; verify effective values in spectre.out')
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
    out=ROOT/'research/runs/spectre_vco_v4'/args.run_id
    out.mkdir(parents=True,exist_ok=False)
    load_vb_env()
    # Keep normal bridge config, explicitly constrain project-specific data roots.
    records=[]
    for case in args.cases:
        assert case.replace('_','').isalnum()
        netlist=HERE/'tb'/f'{case}.scs'
        work=out/case
        sim=SpectreSimulator(remote=True,remote_work_dir=REMOTE,
                             spectre_args=[x for x in spectre_mode_args(args.mode) if x!='+mt']+([f'+mt={args.threads}'] if args.mode in ('aps','ax') else [])+([f'-preset_override={args.preset_override}'] if args.preset_override else []),timeout=args.timeout,
                             work_dir=work,keep_remote_files=True,output_format='psfascii')
        files=[netlist]+sorted(BLOCKS.glob('*.va'))
        for folder in ['transistor_v1','transistor_v2','transistor_v3','vco_v4']:
            files+=sorted((TX.parent/folder).glob('*.scs'))+sorted((TX.parent/folder).glob('*.va'))
        # Resolve only project-owned includes; the PDK remains on the server.
        import re
        available={p.name:p for p in files};needed={netlist.name};pending=[netlist]
        while pending:
            for name in re.findall(r'(?:include|ahdl_include)\s+"([^"]+)"',pending.pop().read_text()):
                if name.startswith('/'):continue
                assert name in available,name
                if name not in needed:needed.add(name);pending.append(available[name])
        files=[netlist]+[available[k] for k in sorted(needed) if k!=netlist.name]
        if args.snapshot_run:
            snapshot=out.parent/args.snapshot_run/case/'inputs'
            netlist=snapshot/(case+'.scs')
            assert netlist.is_file(),netlist
            files=[netlist]+[p for p in sorted(snapshot.iterdir()) if p!=netlist and p.suffix in ('.scs','.va')]
        (work/'inputs').mkdir(parents=True)
        for p in files: shutil.copy2(p,work/'inputs'/p.name)
        # Immutable local snapshot is both simulator input and hash authority.
        # Design work may continue while a long simulation is running.
        files=[work/'inputs'/p.name for p in files]
        netlist=files[0]
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
             'inputs_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
        work.mkdir(parents=True,exist_ok=True)
        if result.ok:
            data={k:np.asarray(v) for k,v in result.data.items() if k!='units'}
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
        rec['local_outputs_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in work.iterdir() if p.is_file() and p.name!='result.json'}
        (work/'result.json').write_text(json.dumps(rec,indent=2,default=str)+'\n',encoding='utf-8',newline='\n')
        records.append(rec)
        (out/'index.json').write_text(json.dumps(records,indent=2,default=str)+'\n',encoding='utf-8',newline='\n')
        print('DONE',case,result.ok,rec['errors'],flush=True)
        if not result.ok: return 1
    return 0

if __name__=='__main__':raise SystemExit(main())
