"""Collect an explicitly saved checkpoint from a completed job; never signal/restart it."""
from pathlib import Path,PurePosixPath
import argparse,base64,datetime,hashlib,json,re,subprocess

H=Path(__file__).resolve().parent;ROOT=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('run');ap.add_argument('case')
    ap.add_argument('--saved-time',type=float,help='Explicit requested savetime, in seconds; mandatory when several checkpoints exist')
    a=ap.parse_args()
    assert all(re.fullmatch(r'[A-Za-z0-9_]+',s) for s in [a.run,a.case])
    j=ROOT/'research/runs/spectre_cmos_v14_full'/a.run/a.case
    r=json.loads((j/'result.json').read_text())
    assert r['ok'] and r['remote_inputs_match'] and r.get('local_outputs_sha256')
    log=(j/'spectre.out').read_text();assert 'spectre completes with 0 errors' in log
    tb=(j/'inputs'/(a.case+'.scs')).read_text()
    paths=re.findall(r'savefile="([^"]+)"',tb);assert len(paths)==1
    remote=paths[0];prefix='/home/jielu/TSMC180/MP/IP-PLL-GPT6/simulation/cmos_v14_full/'
    assert remote==prefix+a.run+'_'+a.case+'.srf' and '..' not in PurePosixPath(remote).parts
    # Inspect the exact requested path and its possible time-stamped siblings;
    # ambiguity is reviewed instead of silently choosing a checkpoint.
    code="""import os,glob,json,hashlib
p=%r
rows=[]
for s in glob.glob(p+'*'):
 if os.path.isfile(s):
  st=os.stat(s);rows.append(dict(remote=s,bytes=st.st_size,mtime=st.st_mtime,sha256=hashlib.sha256(open(s,'rb').read()).hexdigest()))
print(json.dumps(rows))
"""%remote
    enc=base64.b64encode(code.encode()).decode()
    ssh=['C:/Windows/System32/OpenSSH/ssh.exe','-F',str(Path.home()/'.virtuoso-bridge/ssh_config_ipv6'),'-o','BatchMode=yes','thu-xia-v6']
    rows=json.loads(subprocess.check_output(ssh+['/usr/bin/python -c "import base64;exec(base64.b64decode(\''+enc+'\'))"'],timeout=45))
    inventory=rows
    selected_time=None
    if a.saved_time is not None:
        assert a.saved_time>0
        units={'':1.,'f':1e-15,'p':1e-12,'n':1e-9,'u':1e-6,'m':1e-3,'k':1e3,'M':1e6,'G':1e9}
        requested=re.findall(r'savetime=\[([^\]]+)\]',tb);assert len(requested)==1
        times=[]
        for token in requested[0].split():
            m=re.fullmatch(r'([0-9.]+(?:[eE][-+]?\d+)?)([fpnumkMG]?)',token);assert m,token
            times.append(float(m[1])*units[m[2]])
        assert any(abs(x-a.saved_time)<1e-18 for x in times),(a.saved_time,times)
        selected=[]
        for row in rows:
            m=re.fullmatch(re.escape(remote)+r'_at_([0-9.]+(?:[eE][-+]?\d+)?)([fpnumkMG]?)s',row['remote'])
            if m and abs(float(m[1])*units[m[2]]-a.saved_time)<1e-18:selected.append(row)
        rows=selected;selected_time=a.saved_time
    assert len(rows)==1,dict(requested_time_s=a.saved_time,inventory=inventory,selected=rows)
    row=rows[0];assert row['bytes']>0 and re.fullmatch(re.escape(remote)+r'[A-Za-z0-9_.+-]*',row['remote'])
    blob=subprocess.check_output(ssh+['cat '+row['remote']],timeout=90)
    assert len(blob)==row['bytes'] and hashlib.sha256(blob).hexdigest()==row['sha256']
    folder=j/'checkpoints';folder.mkdir(exist_ok=True)
    dest=folder/('completed.srf' if selected_time is None else f'at_{selected_time:.12g}s.srf')
    if dest.exists():assert sha(dest)==row['sha256']
    else:dest.write_bytes(blob)
    proof=dest.with_suffix('.json')
    result=dict(row,local=dest.relative_to(ROOT).as_posix(),source_result=(j/'result.json').relative_to(ROOT).as_posix(),
        source_result_sha256=sha(j/'result.json'),local_remote_hash_match=True,requested_savefile=remote,
        collection_time=datetime.datetime.now().astimezone().isoformat(),method='Read completed explicitly saved native state. No process signal or rerun.',
        saved_time_log_lines=[s for s in log.splitlines() if re.search(r'sav(e|ing)|restart',s,re.I)])
    if selected_time is not None:result.update(selected_requested_time_s=selected_time,inventory=inventory)
    if proof.exists():
        old=json.loads(proof.read_text());assert old['sha256']==result['sha256'] and old['source_result_sha256']==result['source_result_sha256']
        result=old
    else:proof.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
