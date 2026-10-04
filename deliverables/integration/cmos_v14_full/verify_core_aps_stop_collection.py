"""Verify recovered files after intentional APS stop and initial tar failure.

The original result/error record is preserved. File recovery is distinct from
simulation success: this job has no accepted periodic or noise solution.
"""
from pathlib import Path,PurePosixPath
import datetime,hashlib,json,shlex,subprocess

H=Path(__file__).resolve().parent;ROOT=H.parents[3]

def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(8*1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def main():
    j=ROOT/'research/runs/spectre_cmos_v14_full/coredacaps01/core_dac_discharge_noise_tt';r=json.loads((j/'result.json').read_text())
    assert r.get('local_outputs_sha256') and not r['ok'] and (j/'cancellation.json').exists()
    remote=PurePosixPath(next(x for x in shlex.split(r['metadata']['spectre_command']) if x.endswith('.scs'))).parent
    assert str(remote).startswith('/home/jielu/TSMC180/MP/IP-PLL-GPT6/simulation/cmos_v14_full/')
    names=['spectre.out',j.name+'.raw/pss.tran.pss'];assert all((j/n).is_file() for n in names)
    ssh=['C:/Windows/System32/OpenSSH/ssh.exe','-F',str(Path.home()/'.virtuoso-bridge/ssh_config_ipv6'),'-o','BatchMode=yes','thu-xia-v6']
    text=subprocess.check_output(ssh+['cd '+shlex.quote(str(remote))+' && sha256sum '+' '.join(shlex.quote(n) for n in names)],timeout=90).decode()
    remote_hash={line.split()[1]:line.split()[0] for line in text.splitlines()}
    files=[]
    for name in names:
        p=j/name;sha=digest(p);assert sha==remote_hash[name]
        files.append(dict(path=p.relative_to(ROOT).as_posix(),size_bytes=p.stat().st_size,sha256=sha,remote_hash_matched=True))
    out=dict(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),original_result=(j/'result.json').relative_to(ROOT).as_posix(),
             original_result_sha256=digest(j/'result.json'),original_wrapper_errors=r['errors'],
             recovered_archive_sha256=digest(j/'recovered_raw.tar.gz'),verified_files=files,
             simulator_periodic_solution_accepted=False,noise_solution_accepted=False,full_pll_acceptance=False)
    dest=H/'results/core_aps_stop_collection.json';assert not dest.exists();dest.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))

if __name__=='__main__':main()
