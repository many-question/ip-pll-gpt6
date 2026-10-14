"""Analyze conditional local bias/control interventions; never infer PLL lock."""
from pathlib import Path
import datetime,hashlib,json
import numpy as np
H=Path(__file__).resolve().parent; ROOT=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    out=H/'results/rt4_biasprobe106_review.json';assert not out.exists()
    pp=H/'results/rt4_biasprobe106_retry_protocol.json';p=json.loads(pp.read_text());c=p['cases'][0]
    work=ROOT/'research/runs/spectre_cmos_v14_full'/c['run']/c['case'];rp=work/'result.json'
    r=json.loads(rp.read_text());assert r['ok'] and r['remote_inputs_match']
    assert sha(work/'waveforms.npz')==r['local_outputs_sha256']['waveforms.npz']
    with np.load(work/'waveforms.npz') as z:d={k:z[k] for k in z.files if k!='units'}
    t=d['time'];assert len(t)==1201 and np.all(np.diff(t)>0) and abs(t[-1]-2.4e-6)<1e-15
    assert all(np.isfinite(v).all() for v in d.values())
    changes=np.r_[False,(np.diff(d['obsphase'])!=0)|(np.diff(d['obscycles'])!=0)|(np.diff(d['obsdivcycles'])!=0)]
    rows=[]
    for s in p['segments']:
        sel=(t>s['end_s']-150e-9)&(t<=s['end_s']+1e-15)&changes
        f=d['obscycles'][sel]*24;o=d['obsdivcycles'][sel]*24
        assert len(f)>=3
        rows.append(dict(**s,observations=len(f),rf_mhz=float(f.mean()),rf_range_mhz=[float(f.min()),float(f.max())],output_mhz=float(o.mean()),
          divider_ratio_ok=bool(abs(float(f.mean()/o.mean())-4)<.02),nfilt_v=float(np.mean(d['XV.XL.nfilt'][sel]))))
    assert all(x['divider_ratio_ok'] for x in rows)
    ap=ROOT/'research/heartbeat_biasprobe_completed106.json';a=json.loads(ap.read_text());j=a['jobs'][0]
    assert not j['alive'] and j['exit_marker']=='0' and j['raw_end'] and j['completed_output_hashes'] and j['final_state_sha256']
    result=dict(time=datetime.datetime.now().astimezone().isoformat(),protocol_sha256=sha(pp),source_result=rp.relative_to(ROOT).as_posix(),source_result_sha256=sha(rp),
       independent_audit=ap.relative_to(ROOT).as_posix(),independent_audit_sha256=sha(ap),terminal_hashes=j['completed_output_hashes'],final_ic_sha256=j['final_state_sha256'],
       physical_points=len(t),finite=True,segments=rows,
       bias_shift_mhz=[dict(control_v=x['control_v'],rf_change_mhz=float(y['rf_mhz']-x['rf_mhz'])) for x in rows[:3] for y in rows[3:] if x['control_v']==y['control_v']],
       boundary=p['boundary'])
    out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
