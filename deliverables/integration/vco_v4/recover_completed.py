"""Recover a timed-out collector after its exact remote Spectre job completes.

The original timeout record is retained; a completed log and input hashes are
required before any waveform is accepted. This does not restart the simulation.
"""
import argparse, datetime, hashlib, json, re, shlex, subprocess, tarfile
from pathlib import Path, PurePosixPath
import numpy as np
from virtuoso_bridge.spectre.parsers import parse_psf_ascii_directory
from run_spectre import ROOT, REMOTE

def main():
    ap=argparse.ArgumentParser();ap.add_argument('run');ap.add_argument('case');a=ap.parse_args()
    assert all(x.replace('_','').isalnum() for x in [a.run,a.case])
    work=ROOT/'research/runs/spectre_vco_v4'/a.run/a.case
    rec=json.loads((work/'result.json').read_text())
    assert not rec['ok'] and any('timed out' in e for e in rec['errors'])
    net=next(x for x in shlex.split(rec['metadata']['spectre_command']) if x.endswith('.scs'))
    remote=str(PurePosixPath(net).parent)
    assert remote.startswith(REMOTE+'/') and PurePosixPath(net).name==a.case+'.scs'
    ssh=['ssh','-F',str(Path.home()/'.virtuoso-bridge/ssh_config_ipv6'),'-o','BatchMode=yes','thu-xia-v6']
    log=subprocess.check_output(ssh+['cat '+shlex.quote(remote+'/spectre.out')],timeout=30).decode()
    assert re.search(r'spectre completes with 0 errors,',log[-3000:]),'Remote simulation has not completed successfully'
    inputs=rec['inputs_sha256']
    proof=subprocess.check_output(ssh+['cd '+shlex.quote(remote)+' && sha256sum '+' '.join(shlex.quote(n) for n in inputs)],timeout=30).decode()
    remote_hashes={line.split()[1]:line.split()[0] for line in proof.splitlines() if len(line.split())==2}
    assert remote_hashes==inputs
    assert {n:hashlib.sha256((work/'inputs'/n).read_bytes()).hexdigest() for n in inputs}==inputs
    archive=work/'completed_recovery.tar.gz'
    if not archive.exists():
        with archive.open('wb') as dest:
            subprocess.run(ssh+['tar -czf - -C '+shlex.quote(remote)+' '+shlex.quote(a.case+'.raw')+' spectre.out'],stdout=dest,check=True,timeout=180)
    with tarfile.open(archive) as tf:
        assert all(m.name=='spectre.out' or (m.isdir() and m.name==a.case+'.raw') or m.name.startswith(a.case+'.raw/') for m in tf.getmembers())
        tf.extractall(work,filter='data')
    original=work/'result.collector_timeout.json'
    assert not original.exists()
    original.write_text(json.dumps(rec,indent=2)+'\n')
    data={k:np.asarray(v) for k,v in parse_psf_ascii_directory(work/(a.case+'.raw')).items() if k!='units'}
    np.savez_compressed(work/'waveforms.npz',**data)
    rec['metadata']['recovered_collector_errors']=rec['errors']
    rec.update(ok=True,errors=[],remote_inputs_sha256=remote_hashes,remote_inputs_match=True,
               recovery_time=datetime.datetime.now().astimezone().isoformat(),
               recovery_note='Original collector timed out; exact remote job completed independently. Final log and input hashes verified before recovery.',
               signals={k:len(v) for k,v in data.items()})
    rec['local_outputs_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in work.iterdir() if p.is_file() and p.name!='result.json'}
    (work/'result.json').write_text(json.dumps(rec,indent=2)+'\n')
    print('Recovered',a.run,a.case,'with final 0 errors; original timeout retained')

if __name__=='__main__':main()
