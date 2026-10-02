"""Map measured endpoint gaps to the unchanged kickstart frequency plan.

An endpoint bracket is only a screening condition, never proof of continuous
tuning or channel lock. The endpoint fixture's output divider varies, so its
loads are not identical to every planned channel.
"""
from pathlib import Path
import csv,json,hashlib
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
p=ROOT/'share/deliverables/architecture/initial_screen/frequency_plan.csv'
rows=list(csv.DictReader(p.open()))
assert len(rows)==33
assert [int(r['k']) for r in rows]==list(range(9,42))
for r in rows:
 k=int(r['k']);m=int(r['m'])
 expected=14 if k==9 else 12 if k<=11 else 10 if k<=13 else 8 if k<=18 else 6 if k<=27 else 4
 assert m==expected and int(r['n'])==k*m
 assert int(r['fout_hz'])==k*24000000 and int(r['fvco_hz'])==k*m*24000000
end=json.loads((H/'results/range_endpoints.json').read_text())
print('Plan fields:',list(rows[0]))
result=dict(scope=__doc__,plan_path=str(p.relative_to(ROOT)),plan_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
            condition=end['condition'],corners={},not_a_channel_lock_test=True)
for corner in ['tt','ss','ff']:
 cases=[x for x in end['cases'] if x['corner']==corner]
 lo=min(x['rf_mhz'] for x in cases);hi=max(x['rf_mhz'] for x in cases)
 channels=[]
 for r in rows:
  f=float(r['fvco_hz'])/1e6
  channels.append(dict(k=int(r['k']),m=int(r['m']),target_rf_mhz=f,
                       target_output_mhz=float(r['fout_hz'])/1e6,
                       bracketed_by_tested_endpoints=bool(lo<=f<=hi),
                       low_endpoint_minus_target_mhz=lo-f))
 result['corners'][corner]=dict(tested_bounds_mhz=[lo,hi],channels=channels,
                               unbracketed_k=[x['k'] for x in channels if not x['bracketed_by_tested_endpoints']])
(H/'results/channel_endpoint_screen.json').write_text(json.dumps(result,indent=2)+'\n')
for c,d in result['corners'].items():print(c,d['unbracketed_k'])
