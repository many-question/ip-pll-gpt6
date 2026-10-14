"""Review short real-bias neighboring-code diagnostic; no PLL lock inference."""
from pathlib import Path
import datetime,hashlib,json,sys
import numpy as np
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=Path(sys.argv[1]);out=Path(sys.argv[2]);assert not out.exists()
    pp=H/'results/rt4_freebias107_protocol.json';p=json.loads(pp.read_text());c=p['cases'][0]
    work=ROOT/'research/runs/spectre_cmos_v14_full'/c['run']/c['case'];rp=work/'result.json';r=json.loads(rp.read_text())
    assert r['ok'] and r['remote_inputs_match'] and sha(work/'waveforms.npz')==r['local_outputs_sha256']['waveforms.npz']
    with np.load(work/'waveforms.npz') as z:d={k:z[k] for k in z.files if k!='units'}
    t=d['time'];assert len(t)==1501 and abs(t[-1]-3e-6)<1e-15 and np.all(np.diff(t)>0)
    assert all(np.isfinite(v).all() for v in d.values())
    a=json.loads(ap.read_text());j=a['jobs'][0];assert not j['alive'] and j['exit_marker']=='0' and j['raw_end'] and j['final_state_sha256'] and j['completed_output_hashes']
    changes=np.r_[False,(np.diff(d['obsphase'])!=0)|(np.diff(d['obscycles'])!=0)|(np.diff(d['obsdivcycles'])!=0)]
    rows=[]
    for s in p['segments']:
        win=(t>s['end_s']-300e-9)&(t<=s['end_s']+1e-15);sel=win&changes
        f=d['obscycles'][sel]*24;o=d['obsdivcycles'][sel]*24;assert len(f)>=6
        nf=d['XV.XL.nfilt'][win]
        rows.append(dict(**s,observations=len(f),rf_mhz=float(f.mean()),rf_range_mhz=[float(f.min()),float(f.max())],rf_drift_mhz=float(f[-1]-f[0]),
          output_mhz=float(o.mean()),divider_ratio_ok=bool(abs(float(f.mean()/o.mean())-4)<.02),nfilt_mean_v=float(nf.mean()),nfilt_range_v=[float(nf.min()),float(nf.max())]))
    assert all(x['divider_ratio_ok'] for x in rows)
    result=dict(time=datetime.datetime.now().astimezone().isoformat(),protocol_sha256=sha(pp),source_result=rp.relative_to(ROOT).as_posix(),source_result_sha256=sha(rp),
      audit=ap.resolve().relative_to(ROOT).as_posix(),audit_sha256=sha(ap),terminal_hashes=j['completed_output_hashes'],final_ic_sha256=j['final_state_sha256'],finite=True,physical_points=len(t),segments=rows,boundary=p['boundary'])
    out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
