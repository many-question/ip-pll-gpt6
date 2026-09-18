"""Inventory local authoritative evidence without copying PDK or raw PSF to share."""
from pathlib import Path
import datetime,hashlib,json
H=Path(__file__).resolve().parent
D=H.parents[2]
ROOT=D.parent if D.name=='share' and (D.parent/'AGENTS.md').exists() else D
R=ROOT/'research/runs/spectre_transistor_v2'
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
    rows=[]
    for p in sorted(R.glob('*/*/result.json')):
        result=json.loads(p.read_text());case=p.parent
        raw=list(case.glob('*.raw/*'))
        rows.append(dict(run=case.parent.name,case=case.name,local_path=str(case.relative_to(ROOT)).replace('\\','/'),
             simulator_ok=result['ok'],reported_errors=result['errors'],input_hashes_match=result.get('remote_inputs_match',False),
             input_sha256=result.get('inputs_sha256',{}),spectre_command=result.get('metadata',{}).get('spectre_command'),
             seconds=result.get('metadata',{}).get('timings',{}).get('remote_exec'),
             local_evidence={str(x.relative_to(case)).replace('\\','/'):dict(bytes=x.stat().st_size,sha256=sha(x))
                 for x in [p,case/'spectre.out',case/'waveforms.npz']+raw if x.is_file()},
             interrupted=(case/'INTERRUPTED.json').exists()))
    manifest=dict(time=datetime.datetime.now().astimezone().isoformat(),model_root_sha256='d44aa9da7ba670f0b4cfb0198b019dc73abf8bae21b15f45ce5a30c7cb5973ff',
         note='Simulator completion is not functional signoff. Failed exploratory designs are retained. See validation.json and README.',
         total_records=len(rows),total_recorded_remote_seconds=sum(x['seconds'] or 0 for x in rows),runs=rows)
    (H/'results/raw_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    inputs=list((H.parents[1]/'blocks/transistor_v2').glob('*'))+list(H.glob('*.py'))+list((H/'tb').glob('*.scs'))
    source={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in sorted(inputs) if p.is_file()}
    (H/'results/source_manifest.json').write_text(json.dumps(source,indent=2)+'\n')
    print('Recovered runs:',len(rows),'recorded remote seconds:',round(manifest['total_recorded_remote_seconds']))
if __name__=='__main__':main()
