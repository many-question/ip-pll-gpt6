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
REMOTE='/home/jielu/TSMC180/MP/IP-PLL-GPT6/simulation/transistor_v2'
TX=HERE.parents[1]/'blocks/transistor_v2'

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--run-id',required=True)
    parser.add_argument('--mode',choices=['spectre','aps'],default='spectre')
    select=parser.add_mutually_exclusive_group(required=True)
    select.add_argument('--cases',nargs='+')
    select.add_argument('--suite',choices=['divider','fll','noise','incremental'])
    args=parser.parse_args()
    if args.suite=='divider':args.cases=[f'tb_bank_m{m}_{c}_light' for c in ['ss','tt','ff'] for m in [4,6,8,10,12,14]]
    elif args.suite=='fll':args.cases=[f'tb_fll_counter_{c}' for c in ['tt','ss','ff']]+['tb_fll_counter_window','tb_fll_controller_r3','tb_fll_controller_r3_zero','tb_fll_controller_r3_rangehigh','tb_fll_acquire_r3_first_window']
    elif args.suite=='noise':args.cases=['tb_noise_retimer_sp25_tt','tb_noise_retimer_sp25_ss','tb_noise_retimer_sp25_ff','tb_joint_final_center','tb_vco_filtered_slow_c0']
    elif args.suite=='incremental':args.cases=['loop_s8_divider','loop_s9_noise_output']
    assert args.run_id.replace('_','').isalnum()
    out=ROOT/'research/runs/spectre_transistor_v2'/args.run_id
    out.mkdir(parents=True,exist_ok=False)
    load_vb_env()
    # Keep normal bridge config, explicitly constrain project-specific data roots.
    records=[]
    for case in args.cases:
        assert case.replace('_','').isalnum()
        netlist=HERE/'tb'/f'{case}.scs'
        work=out/case
        sim=SpectreSimulator(remote=True,remote_work_dir=REMOTE,
                             spectre_args=spectre_mode_args(args.mode)+(['+mt=1'] if args.mode=='aps' else []),timeout=3600,
                             work_dir=work,keep_remote_files=True,output_format='psfascii')
        files=[netlist]+sorted(BLOCKS.glob('*.va'))+sorted((TX.parent/'transistor_v1').glob('*.scs'))+sorted((TX.parent/'transistor_v1').glob('*.va'))+sorted(TX.glob('*.scs'))+sorted(TX.glob('*.va'))
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
