"""Supplement a timed-out observer record after the remote noise job completes.

Keep the original result.json intact. Completed analysis snapshots are the
raw measurement evidence; recover final/PSS state separately for archiving,
not for automatic reuse in MOS noise analysis.
"""
from pathlib import Path
import argparse,datetime,hashlib,json,re,shlex,subprocess
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('run');ap.add_argument('case');ap.add_argument('--last-analysis',required=True);a=ap.parse_args()
    assert all(re.fullmatch(r'[A-Za-z0-9_]+',s) for s in [a.run,a.case,a.last_analysis])
    j=ROOT/'research/runs/spectre_cmos_v14_full'/a.run/a.case;original=j/'result.json';r=json.loads(original.read_text());assert not r['ok']
    snap=j/('completed_'+a.last_analysis+'_snapshot');m=json.loads((snap/'snapshot.json').read_text());log=(snap/'spectre_snapshot.out').read_text()
    assert m['completed_analysis_collected'] and not m['live_pids_after'] and 'spectre completes with 0 errors' in log[-6000:]
    launch=json.loads((j/'launch.json').read_text());assert launch['inputs_sha256']==m['inputs_sha256']
    assert all(sha(j/'inputs'/k)==v for k,v in launch['inputs_sha256'].items())
    dest=j/'completed_state_snapshot';assert not dest.exists();dest.mkdir()
    tb=(j/'inputs'/(a.case+'.scs')).read_text();paths=re.findall(r'\b(writefinal|writepss)="([^"]+)"',tb)
    ssh=['C:/Windows/System32/OpenSSH/ssh.exe','-F',str(Path.home()/'.virtuoso-bridge/ssh_config_ipv6'),'-o','BatchMode=yes','thu-xia-v6']
    rows=[]
    for kind,remote in paths:
        assert remote.startswith('/home/jielu/TSMC180/MP/IP-PLL-GPT6/simulation/cmos_v14_full/'+a.run+'_'+a.case+'.') and '..' not in Path(remote).parts
        before=subprocess.check_output(ssh+['sha256sum '+shlex.quote(remote)],timeout=60).decode().split()[0]
        local=dest/('final.ic' if kind=='writefinal' else 'periodic.state')
        with local.open('wb') as f:subprocess.run(ssh+['cat '+shlex.quote(remote)],stdout=f,check=True,timeout=120)
        after=subprocess.check_output(ssh+['sha256sum '+shlex.quote(remote)],timeout=60).decode().split()[0]
        assert sha(local)==before==after
        rows.append(dict(kind=kind,remote=remote,local=local.relative_to(ROOT).as_posix(),bytes=local.stat().st_size,sha256=after))
    out=dict(scope=__doc__,time=datetime.datetime.now().astimezone().isoformat(),original_observer_result_sha256=sha(original),
        completed_analysis_snapshot_sha256=sha(snap/'snapshot.json'),completion_log_sha256=sha(snap/'spectre_snapshot.out'),
        remote_simulation_completed_zero_errors=True,original_observer_result_preserved=True,states=rows,
        archived_state_noise_reuse_authorized=False,full_pll_acceptance=False)
    (j/'completion_after_timeout.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))

if __name__=='__main__':main()
