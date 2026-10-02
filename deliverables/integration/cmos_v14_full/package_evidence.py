"""Index locally recovered simulation evidence without publishing raw PDK state."""
from pathlib import Path
import json,hashlib,datetime
H=Path(__file__).resolve().parent;ROOT=H.parents[3];R=ROOT/'research/runs/spectre_cmos_v14_full'
rows=[]
for p in sorted(R.glob('*/*/result.json')):
 r=json.loads(p.read_text());job=p.parent
 rows.append(dict(run=job.parent.name,case=job.name,result_path=p.relative_to(ROOT).as_posix(),
  result_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),remote_inputs_match=r.get('remote_inputs_match',False),
  inputs_sha256=r.get('inputs_sha256',{}),local_outputs_sha256=r.get('local_outputs_sha256',{}),
  raw_files=[dict(path=x.relative_to(ROOT).as_posix(),bytes=x.stat().st_size,sha256=hashlib.sha256(x.read_bytes()).hexdigest()) for x in sorted(job.glob('*.raw/*')) if x.is_file()],
  scope='Result.ok/bridge error classification is not acceptance. Use validation.json and actual Spectre final status. Native checkpoints are local research artifacts, not published.'))
(H/'results/raw_manifest.json').write_text(json.dumps(dict(generated_at=datetime.datetime.now().astimezone().isoformat(),runs=rows),indent=2)+'\n')
print('Indexed',len(rows),'locally recovered cases')
