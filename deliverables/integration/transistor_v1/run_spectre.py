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
from pathlib import Path, PurePosixPath
import numpy as np
from virtuoso_bridge.spectre.runner import SpectreSimulator,load_vb_env,spectre_mode_args

HERE=Path(__file__).resolve().parent
DELIVERY=HERE.parents[2]
ROOT=DELIVERY.parent if DELIVERY.name=='share' and (DELIVERY.parent/'AGENTS.md').exists() else DELIVERY
BLOCKS=HERE.parents[1]/'blocks/behavioral_va'
REMOTE='/home/jielu/TSMC180/MP/IP-PLL-GPT6/simulation/transistor_v1'
TX=HERE.parents[1]/'blocks/transistor_v1'

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--run-id',required=True)
    parser.add_argument('--mode',choices=['spectre','aps'],default='spectre')
    select=parser.add_mutually_exclusive_group(required=True)
    select.add_argument('--cases',nargs='+')
    select.add_argument('--suite',choices=['modules','incremental'])
    args=parser.parse_args()
    if args.suite=='modules':args.cases=[p.stem for p in sorted((HERE/'tb').glob('tb_*.scs'))]
    elif args.suite=='incremental':args.cases=[f'loop_s{s}_k41' for s in range(1,5)]+['loop_s5_k41_moderate','loop_s6_k41_moderate','top_s5_k41_moderate']
    assert args.run_id.replace('_','').isalnum()
    out=ROOT/'research/runs/spectre_transistor'/args.run_id
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
        files=[netlist]+sorted(BLOCKS.glob('*.va'))+sorted(TX.glob('*.scs'))+sorted(TX.glob('*.va'))
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
