"""Index local authoritative evidence; do not copy PDK or raw PSF into share."""
from pathlib import Path
import datetime,hashlib,json,re,sys
H=Path(__file__).resolve().parent;D=H.parents[2]
ROOT=D.parent if D.name=='share' and (D.parent/'AGENTS.md').exists() else D
R=ROOT/'research/runs/spectre_transistor_v3'
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def source_manifest():
 files=list((H.parents[1]/'blocks/transistor_v3').glob('*'))+list(H.glob('*.py'))+list((H/'tb').glob('*.scs'))
 (H/'results/source_manifest.json').write_text(json.dumps({p.relative_to(ROOT).as_posix():sha(p) for p in sorted(files) if p.is_file()},indent=2)+'\n')
def main():
 rows=[]
 for p in sorted(R.glob('*/*/result.json')):
  r=json.loads(p.read_text());case=p.parent;log=case/'spectre.out'
  local_inputs={name:sha(case/'inputs'/name) for name in r.get('inputs_sha256',{})}
  assert local_inputs==r.get('inputs_sha256',{}),f'Local snapshot changed: {case}'
  text=log.read_text(errors='replace') if log.exists() else ''
  completion=re.findall(r'spectre completes with (\d+) errors?, (\d+) warnings?',text)
  rows.append(dict(run=case.parent.name,case=case.name,local_path=case.relative_to(ROOT).as_posix(),simulator_ok=r['ok'],reported_errors=r['errors'],final_error_warning_counts=completion[-1] if completion else None,input_hashes_match=r.get('remote_inputs_match',False),local_snapshot_hashes_match=True,input_sha256=r.get('inputs_sha256',{}),seconds=r.get('metadata',{}).get('timings',{}).get('remote_exec'),interrupted=(case/'cancellation.json').exists(),local_evidence={x.relative_to(case).as_posix():dict(bytes=x.stat().st_size,sha256=sha(x)) for x in [p,log,case/'waveforms.npz',case/'cancellation.json']+list(case.glob('*.raw/*')) if x.is_file()}))
 manifest=dict(time=datetime.datetime.now().astimezone().isoformat(),model_root_sha256='d44aa9da7ba670f0b4cfb0198b019dc73abf8bae21b15f45ce5a30c7cb5973ff',note='Completion is not functional signoff. Bridge convergence labels can describe a recovered initial DC attempt; inspect final error counts. Interrupted trials retained.',total_records=len(rows),total_recorded_remote_seconds=sum(x['seconds'] or 0 for x in rows),runs=rows)
 (H/'results/raw_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 source_manifest()
 print('Recovered runs:',len(rows),'recorded remote seconds:',round(manifest['total_recorded_remote_seconds']))
if __name__=='__main__':
 if '--sources-only' in sys.argv:source_manifest()
 else:main()
